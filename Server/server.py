from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Header, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import os
import tempfile
import json
from datetime import date, datetime
from pdftojson import pdftojson
from Categorize import categorical
from Analytics import analytic
from Analytics import health_score
from Analytics import trends
from Goal import goal_setter
from Alerts import alerts
from User import user_manager
from pydantic import BaseModel
from typing import List, Optional

# Database imports
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db, init_db, engine
from database.crud import (
    TransactionCRUD, BankStatementCRUD, GoalCRUD, 
    AlertCRUD, CategoryCRUD, RecurringExpenseCRUD, AnalyticsCRUD
)
from database.models import GoalStatus, GoalPriority, AlertSeverity

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    print("Initializing database...")
    await init_db()
    # Seed default categories
    async for db in get_db():
        await CategoryCRUD.seed_default_categories(db)
        break
    print("Database initialized successfully!")
    yield
    # Shutdown: Close connections
    await engine.dispose()
    print("Database connections closed.")

app = FastAPI(
    title="Personal Finance Manager API",
    description="Complete financial management with analytics, goals, alerts, and AI assistance",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)

# ==================== PYDANTIC MODELS ====================

class DataObj(BaseModel):
    total_expense: float = 0
    total_income: float = 0
    savings: float = 0
    max_spending_category: str = ""

class Goal(BaseModel):
    goal_name: str = ""
    target_amount: float = 0
    time_horizon_months: int = 0
    priority: str = "medium"

class GoalUpdate(BaseModel):
    goal_id: str
    amount_contributed: float

class UserRegister(BaseModel):
    email: str
    password: str
    name: str
    age_group: Optional[str] = None
    income_range: Optional[str] = None
    financial_goals: Optional[List[str]] = None

class UserLogin(BaseModel):
    email: str
    password: str

class ProfileUpdate(BaseModel):
    age_group: Optional[str] = None
    income_range: Optional[str] = None
    financial_goals: Optional[List[str]] = None
    risk_tolerance: Optional[str] = None

class BankAccount(BaseModel):
    account_name: str
    account_type: str
    bank_name: str
    is_primary: bool = False

class PreferencesUpdate(BaseModel):
    notifications_enabled: Optional[bool] = None
    email_alerts: Optional[bool] = None
    budget_alerts: Optional[bool] = None
    weekly_summary: Optional[bool] = None


# ==================== DATABASE PYDANTIC MODELS ====================

class TransactionFilter(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    skip: int = 0
    limit: int = 100

class GoalCreateDB(BaseModel):
    name: str
    target_amount: float
    time_horizon_months: int
    goal_type: Optional[str] = None
    priority: str = "medium"
    description: Optional[str] = None

class GoalUpdateDB(BaseModel):
    goal_id: int
    amount: float

class AlertCreate(BaseModel):
    alert_type: str
    title: str
    message: str
    severity: str = "info"
    action_required: bool = False


# ==================== AUTHENTICATION HELPER ====================

async def get_current_user(authorization: str = Header(None)):
    """Validate session token and return user"""
    if not authorization:
        return None
    
    token = authorization.replace("Bearer ", "")
    user = user_manager.validate_session(token)
    return user


# ==================== ROOT ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "service": "Personal Finance Manager API",
        "version": "2.0.0",
        "endpoints": {
            "Auth": {
                "POST /auth/register": "Register new user",
                "POST /auth/login": "Login user",
                "POST /auth/logout": "Logout user"
            },
            "User": {
                "GET /user/profile": "Get user profile",
                "PUT /user/profile": "Update profile",
                "GET /user/accounts": "Get linked accounts",
                "POST /user/accounts": "Link bank account"
            },
            "Financial Data": {
                "POST /upload_bank_statement": "Upload & parse bank statement",
                "GET /analytics/summary": "Get spending summary",
                "GET /analytics/health_score": "Get financial health score",
                "GET /analytics/trends": "Get spending trends"
            },
            "Goals": {
                "POST /goal": "Create new goal",
                "GET /goals": "Get all goals",
                "GET /goals/dashboard": "Goal tracking dashboard",
                "PUT /goal/progress": "Update goal progress",
                "GET /goals/templates": "Get goal templates"
            },
            "Alerts": {
                "GET /alerts": "Get all alerts",
                "GET /alerts/nudges": "Get smart nudges",
                "GET /alerts/reminders": "Get bill reminders"
            }
        }
    }

@app.get("/test")
async def test_page():
    """Serve the test upload page"""
    try:
        with open("test_upload.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Test page not found</h1>", status_code=404)

@app.get("/health") 
async def health():
    return {"Health": "ok", "version": "2.0.0"}


# ==================== AUTH ENDPOINTS ====================

@app.post("/auth/register")
async def register(data: UserRegister):
    """Register a new user"""
    result = user_manager.register_user(
        email=data.email,
        password=data.password,
        name=data.name,
        age_group=data.age_group,
        income_range=data.income_range,
        financial_goals=data.financial_goals
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/auth/login")
async def login(data: UserLogin):
    """Login user"""
    result = user_manager.login_user(data.email, data.password)
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

@app.post("/auth/logout")
async def logout(authorization: str = Header(None)):
    """Logout user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    return user_manager.logout_user(token)

@app.get("/auth/profile-options")
async def get_profile_options():
    """Get available profile setup options"""
    return user_manager.get_profile_options()


# ==================== USER ENDPOINTS ====================

@app.get("/user/profile")
async def get_profile(user=Depends(get_current_user)):
    """Get current user profile"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "profile": user["profile"],
        "preferences": user["preferences"]
    }

@app.put("/user/profile")
async def update_profile(data: ProfileUpdate, user=Depends(get_current_user)):
    """Update user profile"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_manager.update_profile(
        user_id=user["id"],
        age_group=data.age_group,
        income_range=data.income_range,
        financial_goals=data.financial_goals,
        risk_tolerance=data.risk_tolerance
    )

@app.get("/user/accounts")
async def get_accounts(user=Depends(get_current_user)):
    """Get user's linked bank accounts"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"accounts": user_manager.get_user_accounts(user["id"])}

@app.post("/user/accounts")
async def add_account(data: BankAccount, user=Depends(get_current_user)):
    """Link a new bank account"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_manager.add_bank_account(
        user_id=user["id"],
        account_name=data.account_name,
        account_type=data.account_type,
        bank_name=data.bank_name,
        is_primary=data.is_primary
    )

@app.put("/user/preferences")
async def update_user_preferences(data: PreferencesUpdate, user=Depends(get_current_user)):
    """Update notification preferences"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_manager.update_preferences(
        user_id=user["id"],
        notifications_enabled=data.notifications_enabled,
        email_alerts=data.email_alerts,
        budget_alerts=data.budget_alerts,
        weekly_summary=data.weekly_summary
    )

@app.get("/user/context")
async def get_user_context(user=Depends(get_current_user)):
    """Get user context for MCP integration"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_manager.get_user_context(user["id"])


# ==================== FINANCIAL DATA ENDPOINTS ====================

@app.post("/upload_bank_statement")
async def upload_bank_statement(file: UploadFile = File(...)):
    try:
        # Debug information
        print(f"File received: {file.filename if file else 'None'}")
        print(f"File content type: {file.content_type if file else 'None'}")
        
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file uploaded. Please select a PDF file.")
            
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        temp_dir = tempfile.mkdtemp()
        temp_pdf_path = os.path.join(temp_dir, file.filename)
        
        with open(temp_pdf_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        print(f"Processing PDF: {file.filename}")
        json_file_path = pdftojson.main_pdftojson(PDF_PATH=temp_pdf_path)
        
        if not json_file_path or not os.path.exists(json_file_path):
            raise HTTPException(status_code=500, detail="Failed to extract data from PDF")
        
        categorized_file_path = categorical.main_categorizer(json_file_path)
        
        if not categorized_file_path or not os.path.exists(categorized_file_path):
            raise HTTPException(status_code=500, detail="Failed to categorize transactions")
        
        with open(categorized_file_path, 'r', encoding='utf-8') as f:
            categorized_data = json.load(f)
        
        try:
            os.remove(temp_pdf_path)
            os.rmdir(temp_dir)
            if os.path.exists(json_file_path):
                os.remove(json_file_path)
            if os.path.exists("output.txt"):
                os.remove("output.txt")
        except Exception as cleanup_error:
            print(f"Warning: Could not clean up temporary files: {cleanup_error}")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Bank statement processed successfully",
                "filename": file.filename,
                "data": categorized_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing bank statement: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/analytics/summary")
async def analytics_summary():
    """Get spending summary"""
    dataobj = analytic.main_analytic("categorized_transactions.json")
    return {"data": dataobj}

@app.get("/analytics/health_score")
async def analytics_health():
    """Get comprehensive financial health score"""
    return health_score.health_score_main("categorized_transactions.json")

@app.get("/analytics/anomalies")
async def get_anomalies():
    """Get detected spending anomalies"""
    return {
        "anomalies": health_score.detect_anomalies("categorized_transactions.json")
    }

@app.get("/analytics/recurring")
async def get_recurring_expenses():
    """Get detected recurring expenses"""
    return {
        "recurring_expenses": health_score.detect_recurring_expenses("categorized_transactions.json")
    }

@app.get("/analytics/trends")
async def get_spending_trends():
    """Get comprehensive spending trends over time"""
    return trends.analyze_spending_trends("categorized_transactions.json")

@app.get("/analytics/trends/comparison")
async def get_monthly_comparison():
    """Compare current month with previous months"""
    return trends.get_comparison_analysis("categorized_transactions.json")


# ==================== GOAL ENDPOINTS ====================

@app.post("/goal") 
async def set_goal(data: Goal):
    """Create a new financial goal with feasibility analysis"""
    res = goal_setter.set_goal(data)
    return res

@app.get("/goals")
async def get_all_goals():
    """Get all active goals"""
    return {"goals": goal_setter.get_all_goals()}

@app.get("/goals/dashboard")
async def get_goals_dashboard():
    """Get comprehensive goal tracking dashboard"""
    return goal_setter.get_goal_dashboard()

@app.put("/goal/progress")
async def update_goal_progress(data: GoalUpdate):
    """Update progress on a specific goal"""
    return goal_setter.update_goal_progress(data.goal_id, data.amount_contributed)

@app.get("/goals/templates")
async def get_goal_templates():
    """Get available goal templates"""
    return goal_setter.get_goal_templates()

@app.delete("/goal/{goal_id}")
async def delete_goal(goal_id: str):
    """Delete a goal"""
    return goal_setter.delete_goal(goal_id)


# ==================== ALERTS ENDPOINTS ====================

@app.get("/alerts")
async def get_all_alerts():
    """Get all financial alerts and notifications"""
    return alerts.get_alerts("categorized_transactions.json")

@app.get("/alerts/nudges")
async def get_smart_nudges():
    """Get smart nudges and financial tips"""
    return {"nudges": alerts.get_smart_nudges("categorized_transactions.json")}

@app.get("/alerts/reminders")
async def get_bill_reminders():
    """Get upcoming bill payment reminders"""
    return {"reminders": alerts.generate_bill_reminders("categorized_transactions.json")}


# ==================== DATABASE ENDPOINTS ====================
# These endpoints use PostgreSQL for persistent storage

@app.post("/db/upload_statement")
async def db_upload_statement(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload bank statement and store transactions in database"""
    try:
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file uploaded")
        
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Create temp file
        temp_dir = tempfile.mkdtemp()
        temp_pdf_path = os.path.join(temp_dir, file.filename)
        
        with open(temp_pdf_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Parse PDF
        json_file_path = pdftojson.main_pdftojson(PDF_PATH=temp_pdf_path)
        
        if not json_file_path or not os.path.exists(json_file_path):
            raise HTTPException(status_code=500, detail="Failed to extract data from PDF")
        
        # Categorize transactions
        categorized_file_path = categorical.main_categorizer(json_file_path)
        
        if not categorized_file_path or not os.path.exists(categorized_file_path):
            raise HTTPException(status_code=500, detail="Failed to categorize transactions")
        
        with open(categorized_file_path, 'r', encoding='utf-8') as f:
            categorized_data = json.load(f)
        
        # Create bank statement record
        statement = await BankStatementCRUD.create(
            db=db,
            filename=file.filename,
            total_transactions=len(categorized_data.get('categories', {}).get('all', [])),
            parsing_method="gemini_ai",
            raw_data=categorized_data
        )
        
        # Flatten and store transactions
        all_transactions = []
        for category_name, transactions in categorized_data.get('categories', {}).items():
            for txn in transactions:
                txn['category'] = category_name
                all_transactions.append(txn)
        
        # Bulk create transactions
        if all_transactions:
            await TransactionCRUD.bulk_create(
                db=db,
                transactions_data=all_transactions,
                statement_id=statement.id
            )
        
        # Cleanup temp files
        try:
            os.remove(temp_pdf_path)
            os.rmdir(temp_dir)
            if os.path.exists(json_file_path):
                os.remove(json_file_path)
        except:
            pass
        
        return {
            "message": "Bank statement uploaded and stored in database",
            "statement_id": statement.id,
            "transactions_count": len(all_transactions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/db/transactions")
async def db_get_transactions(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get transactions from database with filters"""
    start = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
    end = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
    
    transactions = await TransactionCRUD.get_all(
        db=db,
        skip=skip,
        limit=limit,
        start_date=start,
        end_date=end,
        category=category
    )
    
    return {
        "transactions": [
            {
                "id": t.id,
                "date": t.date.isoformat() if t.date else None,
                "description": t.description,
                "debit": t.debit,
                "credit": t.credit,
                "balance": t.balance,
                "category": t.category_name
            }
            for t in transactions
        ],
        "count": len(transactions)
    }


@app.get("/db/analytics/summary")
async def db_analytics_summary(db: AsyncSession = Depends(get_db)):
    """Get financial summary from database"""
    summary = await TransactionCRUD.get_summary(db)
    breakdown = await TransactionCRUD.get_category_breakdown(db)
    
    # Find max spending category
    max_category = "Miscellaneous"
    max_spending = 0
    for cat in breakdown:
        if cat['total_debit'] > max_spending and cat['category'] != 'Income':
            max_spending = cat['total_debit']
            max_category = cat['category']
    
    return {
        "total_income": summary['total_income'],
        "total_expense": summary['total_expense'],
        "savings": summary['savings'],
        "max_spending_category": max_category,
        "transaction_count": summary['transaction_count'],
        "category_breakdown": breakdown
    }


@app.get("/db/analytics/monthly")
async def db_analytics_monthly(db: AsyncSession = Depends(get_db)):
    """Get monthly breakdown from database"""
    monthly = await TransactionCRUD.get_monthly_breakdown(db)
    return {"monthly_data": monthly}


@app.get("/db/analytics/health")
async def db_health_score(db: AsyncSession = Depends(get_db)):
    """Calculate health score from database data"""
    data = await AnalyticsCRUD.get_health_score_data(db)
    
    summary = data['summary']
    total_income = summary['total_income']
    total_expense = summary['total_expense']
    savings = summary['savings']
    
    # Component scores calculation
    scores = {}
    
    # Savings score
    if total_income > 0:
        savings_rate = savings / total_income
        scores['savings'] = min(100, savings_rate * 200)
    else:
        scores['savings'] = 0
    
    # Spending discipline (lower volatility = better)
    volatility = data['spending_volatility']
    scores['spending_discipline'] = max(0, 100 - (volatility * 50))
    
    # Essential vs discretionary balance
    essential = data['essential_spending']
    discretionary = data['discretionary_spending']
    if total_expense > 0:
        essential_ratio = essential / total_expense
        scores['expense_balance'] = 100 - abs(0.65 - essential_ratio) * 100
        scores['expense_balance'] = max(0, min(100, scores['expense_balance']))
    else:
        scores['expense_balance'] = 50
    
    # Cash flow score
    if total_income > 0:
        cash_flow_ratio = (total_income - total_expense) / total_income
        scores['cash_flow'] = min(100, max(0, (cash_flow_ratio + 0.5) * 100))
    else:
        scores['cash_flow'] = 0
    
    # Weighted overall score
    weights = {'savings': 0.30, 'spending_discipline': 0.25, 'expense_balance': 0.20, 'cash_flow': 0.25}
    overall_score = sum(scores.get(c, 0) * w for c, w in weights.items())
    
    # Grade
    if overall_score >= 80:
        grade = "🏆 Excellent"
    elif overall_score >= 60:
        grade = "✅ Good"
    elif overall_score >= 40:
        grade = "⚠️ Fair"
    else:
        grade = "🔴 Needs Improvement"
    
    return {
        "overall_score": round(overall_score, 1),
        "grade": grade,
        "component_scores": {k: round(v, 1) for k, v in scores.items()},
        "metrics": {
            "total_income": total_income,
            "total_expense": total_expense,
            "savings": savings,
            "savings_rate": round(savings / max(total_income, 1) * 100, 1),
            "spending_volatility": round(volatility, 4)
        },
        "category_breakdown": data['category_breakdown']
    }


# ==================== DATABASE GOAL ENDPOINTS ====================

@app.post("/db/goals")
async def db_create_goal(data: GoalCreateDB, db: AsyncSession = Depends(get_db)):
    """Create a new goal in database"""
    priority_map = {"high": GoalPriority.HIGH, "medium": GoalPriority.MEDIUM, "low": GoalPriority.LOW}
    
    goal = await GoalCRUD.create(
        db=db,
        name=data.name,
        target_amount=data.target_amount,
        time_horizon_months=data.time_horizon_months,
        goal_type=data.goal_type,
        priority=priority_map.get(data.priority, GoalPriority.MEDIUM),
        description=data.description
    )
    
    return {
        "id": goal.id,
        "name": goal.name,
        "target_amount": goal.target_amount,
        "monthly_required": goal.required_monthly_saving,
        "deadline": goal.deadline.isoformat() if goal.deadline else None,
        "status": goal.status.value
    }


@app.get("/db/goals")
async def db_get_goals(db: AsyncSession = Depends(get_db)):
    """Get all goals from database"""
    goals = await GoalCRUD.get_all(db)
    
    return {
        "goals": [
            {
                "id": g.id,
                "name": g.name,
                "target_amount": g.target_amount,
                "current_amount": g.current_amount,
                "progress": g.progress_percentage,
                "priority": g.priority.value if g.priority else "medium",
                "status": g.status.value if g.status else "active",
                "deadline": g.deadline.isoformat() if g.deadline else None,
                "monthly_required": g.required_monthly_saving
            }
            for g in goals
        ]
    }


@app.get("/db/goals/dashboard")
async def db_goals_dashboard(db: AsyncSession = Depends(get_db)):
    """Get goal tracking dashboard from database"""
    return await GoalCRUD.get_dashboard(db)


@app.put("/db/goals/{goal_id}/contribute")
async def db_goal_contribute(goal_id: int, data: GoalUpdateDB, db: AsyncSession = Depends(get_db)):
    """Add contribution to a goal"""
    goal = await GoalCRUD.update_progress(db, goal_id, data.amount)
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    return {
        "id": goal.id,
        "name": goal.name,
        "current_amount": goal.current_amount,
        "progress": goal.progress_percentage,
        "status": goal.status.value
    }


@app.delete("/db/goals/{goal_id}")
async def db_delete_goal(goal_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a goal from database"""
    deleted = await GoalCRUD.delete(db, goal_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"status": "deleted", "goal_id": goal_id}


# ==================== DATABASE ALERT ENDPOINTS ====================

@app.get("/db/alerts")
async def db_get_alerts(
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get alerts from database"""
    alerts_list = await AlertCRUD.get_all(db, unread_only=unread_only)
    summary = await AlertCRUD.get_summary(db)
    
    return {
        "summary": summary,
        "alerts": [
            {
                "id": a.id,
                "type": a.alert_type,
                "title": a.title,
                "message": a.message,
                "severity": a.severity.value,
                "is_read": a.is_read,
                "action_required": a.action_required,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in alerts_list
        ]
    }


@app.post("/db/alerts")
async def db_create_alert(data: AlertCreate, db: AsyncSession = Depends(get_db)):
    """Create a new alert"""
    severity_map = {"critical": AlertSeverity.CRITICAL, "warning": AlertSeverity.WARNING, "info": AlertSeverity.INFO}
    
    alert = await AlertCRUD.create(
        db=db,
        alert_type=data.alert_type,
        title=data.title,
        message=data.message,
        severity=severity_map.get(data.severity, AlertSeverity.INFO),
        action_required=data.action_required
    )
    
    return {"id": alert.id, "title": alert.title, "severity": alert.severity.value}


@app.put("/db/alerts/{alert_id}/read")
async def db_mark_alert_read(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Mark an alert as read"""
    alert = await AlertCRUD.mark_read(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"id": alert.id, "is_read": alert.is_read}


@app.delete("/db/alerts/{alert_id}")
async def db_dismiss_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Dismiss an alert"""
    dismissed = await AlertCRUD.dismiss(db, alert_id)
    if not dismissed:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "dismissed", "alert_id": alert_id}


# ==================== DATABASE RECURRING EXPENSES ====================

@app.get("/db/recurring")
async def db_get_recurring(db: AsyncSession = Depends(get_db)):
    """Get recurring expenses from database"""
    recurring = await RecurringExpenseCRUD.get_all(db)
    
    return {
        "recurring_expenses": [
            {
                "id": r.id,
                "description": r.description,
                "amount": r.estimated_amount,
                "frequency": r.frequency,
                "category": r.category_name,
                "is_subscription": r.is_subscription,
                "last_occurrence": r.last_occurrence.isoformat() if r.last_occurrence else None
            }
            for r in recurring
        ]
    }


# ==================== DATABASE STATEMENTS ====================

@app.get("/db/statements")
async def db_get_statements(db: AsyncSession = Depends(get_db)):
    """Get all uploaded bank statements"""
    statements = await BankStatementCRUD.get_all(db)
    
    return {
        "statements": [
            {
                "id": s.id,
                "filename": s.filename,
                "bank_name": s.bank_name,
                "upload_date": s.upload_date.isoformat() if s.upload_date else None,
                "total_transactions": s.total_transactions
            }
            for s in statements
        ]
    }


@app.get("/db/statements/{statement_id}/transactions")
async def db_get_statement_transactions(statement_id: int, db: AsyncSession = Depends(get_db)):
    """Get all transactions for a specific statement"""
    transactions = await TransactionCRUD.get_by_statement(db, statement_id)
    
    return {
        "statement_id": statement_id,
        "transactions": [
            {
                "id": t.id,
                "date": t.date.isoformat() if t.date else None,
                "description": t.description,
                "debit": t.debit,
                "credit": t.credit,
                "category": t.category_name
            }
            for t in transactions
        ]
    }


if __name__ == '__main__':
    print("="*60)
    print("Personal Finance Manager API v2.0.0")
    print("="*60)
    print("Modules loaded:")
    print("  ✓ User Management & Authentication")
    print("  ✓ Bank Statement Parser (PDF → JSON)")
    print("  ✓ Transaction Categorization")
    print("  ✓ Analytics & Health Score")
    print("  ✓ Goal Planning & Tracking")
    print("  ✓ Alerts & Notifications")
    print("="*60)
    uvicorn.run(app, host='0.0.0.0', port=5000)