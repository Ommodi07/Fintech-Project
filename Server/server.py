from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Header, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import tempfile
import json
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

app = FastAPI(
    title="Personal Finance Manager API",
    description="Complete financial management with analytics, goals, alerts, and AI assistance",
    version="2.0.0"
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