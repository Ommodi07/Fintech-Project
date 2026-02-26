"""
CRUD Operations for Database Models
Async SQLAlchemy operations for transactions, goals, alerts, and analytics
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, extract
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from .models import (
    Transaction, Category, Goal, GoalContribution, Alert,
    BankStatement, MonthlySummary, RecurringExpense,
    GoalStatus, GoalPriority, AlertSeverity
)


# ==================== TRANSACTION CRUD ====================

class TransactionCRUD:
    """CRUD operations for transactions"""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        date: date,
        description: str = None,
        reference: str = None,
        debit: float = 0.0,
        credit: float = 0.0,
        balance: float = None,
        category_name: str = None,
        statement_id: int = None,
        user_id: str = None
    ) -> Transaction:
        """Create a new transaction"""
        transaction = Transaction(
            date=date,
            description=description,
            reference=reference,
            debit=debit,
            credit=credit,
            balance=balance,
            category_name=category_name,
            statement_id=statement_id,
            user_id=user_id
        )
        db.add(transaction)
        await db.flush()
        await db.refresh(transaction)
        return transaction
    
    @staticmethod
    async def bulk_create(
        db: AsyncSession,
        transactions_data: List[Dict[str, Any]],
        statement_id: int = None,
        user_id: str = None
    ) -> List[Transaction]:
        """Bulk create transactions from a list of dictionaries"""
        transactions = []
        for data in transactions_data:
            txn = Transaction(
                date=data.get('date') if isinstance(data.get('date'), date) 
                     else datetime.strptime(data.get('date', '2024-01-01'), '%Y-%m-%d').date(),
                description=data.get('description') or data.get('transaction_details', ''),
                reference=data.get('reference', ''),
                debit=float(data.get('debit', 0) or 0),
                credit=float(data.get('credit', 0) or 0),
                balance=float(data.get('balance', 0) or 0) if data.get('balance') else None,
                category_name=data.get('category', 'Miscellaneous'),
                statement_id=statement_id,
                user_id=user_id
            )
            transactions.append(txn)
        
        db.add_all(transactions)
        await db.flush()
        return transactions
    
    @staticmethod
    async def get_by_id(db: AsyncSession, transaction_id: int) -> Optional[Transaction]:
        """Get transaction by ID"""
        result = await db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all(
        db: AsyncSession,
        user_id: str = None,
        skip: int = 0,
        limit: int = 100,
        start_date: date = None,
        end_date: date = None,
        category: str = None
    ) -> List[Transaction]:
        """Get all transactions with filters"""
        query = select(Transaction)
        
        conditions = []
        if user_id:
            conditions.append(Transaction.user_id == user_id)
        if start_date:
            conditions.append(Transaction.date >= start_date)
        if end_date:
            conditions.append(Transaction.date <= end_date)
        if category:
            conditions.append(Transaction.category_name == category)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(Transaction.date.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_by_statement(db: AsyncSession, statement_id: int) -> List[Transaction]:
        """Get all transactions for a statement"""
        result = await db.execute(
            select(Transaction)
            .where(Transaction.statement_id == statement_id)
            .order_by(Transaction.date)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_summary(
        db: AsyncSession,
        user_id: str = None,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """Get aggregated summary of transactions"""
        conditions = []
        if user_id:
            conditions.append(Transaction.user_id == user_id)
        if start_date:
            conditions.append(Transaction.date >= start_date)
        if end_date:
            conditions.append(Transaction.date <= end_date)
        
        # Total income and expense
        query = select(
            func.sum(Transaction.credit).label('total_income'),
            func.sum(Transaction.debit).label('total_expense'),
            func.count(Transaction.id).label('transaction_count')
        )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await db.execute(query)
        row = result.one()
        
        total_income = float(row.total_income or 0)
        total_expense = float(row.total_expense or 0)
        
        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "savings": total_income - total_expense,
            "transaction_count": row.transaction_count or 0
        }
    
    @staticmethod
    async def get_category_breakdown(
        db: AsyncSession,
        user_id: str = None,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get spending breakdown by category"""
        conditions = []
        if user_id:
            conditions.append(Transaction.user_id == user_id)
        if start_date:
            conditions.append(Transaction.date >= start_date)
        if end_date:
            conditions.append(Transaction.date <= end_date)
        
        query = select(
            Transaction.category_name,
            func.sum(Transaction.debit).label('total_debit'),
            func.sum(Transaction.credit).label('total_credit'),
            func.count(Transaction.id).label('count')
        ).group_by(Transaction.category_name)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await db.execute(query)
        
        breakdown = []
        for row in result.all():
            breakdown.append({
                "category": row.category_name or "Uncategorized",
                "total_debit": float(row.total_debit or 0),
                "total_credit": float(row.total_credit or 0),
                "count": row.count
            })
        
        return sorted(breakdown, key=lambda x: x['total_debit'], reverse=True)
    
    @staticmethod
    async def get_monthly_breakdown(
        db: AsyncSession,
        user_id: str = None
    ) -> List[Dict[str, Any]]:
        """Get monthly aggregated data"""
        conditions = []
        if user_id:
            conditions.append(Transaction.user_id == user_id)
        
        query = select(
            extract('year', Transaction.date).label('year'),
            extract('month', Transaction.date).label('month'),
            func.sum(Transaction.debit).label('total_expense'),
            func.sum(Transaction.credit).label('total_income'),
            func.count(Transaction.id).label('count')
        ).group_by(
            extract('year', Transaction.date),
            extract('month', Transaction.date)
        ).order_by(
            extract('year', Transaction.date),
            extract('month', Transaction.date)
        )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await db.execute(query)
        
        monthly = []
        for row in result.all():
            income = float(row.total_income or 0)
            expense = float(row.total_expense or 0)
            monthly.append({
                "year": int(row.year),
                "month": int(row.month),
                "month_str": f"{int(row.year)}-{int(row.month):02d}",
                "total_income": income,
                "total_expense": expense,
                "savings": income - expense,
                "savings_rate": round((income - expense) / income * 100, 1) if income > 0 else 0,
                "transaction_count": row.count
            })
        
        return monthly
    
    @staticmethod
    async def delete(db: AsyncSession, transaction_id: int) -> bool:
        """Delete a transaction"""
        result = await db.execute(
            delete(Transaction).where(Transaction.id == transaction_id)
        )
        return result.rowcount > 0
    
    @staticmethod
    async def mark_anomaly(
        db: AsyncSession,
        transaction_id: int,
        is_anomaly: bool = True,
        anomaly_score: float = None
    ) -> Optional[Transaction]:
        """Mark a transaction as anomaly"""
        await db.execute(
            update(Transaction)
            .where(Transaction.id == transaction_id)
            .values(is_anomaly=is_anomaly, anomaly_score=anomaly_score)
        )
        return await TransactionCRUD.get_by_id(db, transaction_id)


# ==================== BANK STATEMENT CRUD ====================

class BankStatementCRUD:
    """CRUD operations for bank statements"""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        filename: str,
        bank_name: str = None,
        total_transactions: int = 0,
        parsing_method: str = None,
        raw_data: Dict = None,
        user_id: str = None
    ) -> BankStatement:
        """Create a new bank statement record"""
        statement = BankStatement(
            filename=filename,
            bank_name=bank_name,
            total_transactions=total_transactions,
            parsing_method=parsing_method,
            raw_data=raw_data,
            user_id=user_id
        )
        db.add(statement)
        await db.flush()
        await db.refresh(statement)
        return statement
    
    @staticmethod
    async def get_all(db: AsyncSession, user_id: str = None) -> List[BankStatement]:
        """Get all bank statements"""
        query = select(BankStatement).order_by(BankStatement.upload_date.desc())
        if user_id:
            query = query.where(BankStatement.user_id == user_id)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_by_id(db: AsyncSession, statement_id: int) -> Optional[BankStatement]:
        """Get bank statement by ID"""
        result = await db.execute(
            select(BankStatement)
            .options(selectinload(BankStatement.transactions))
            .where(BankStatement.id == statement_id)
        )
        return result.scalar_one_or_none()


# ==================== GOAL CRUD ====================

class GoalCRUD:
    """CRUD operations for financial goals"""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        name: str,
        target_amount: float,
        time_horizon_months: int = None,
        goal_type: str = None,
        priority: GoalPriority = GoalPriority.MEDIUM,
        description: str = None,
        user_id: str = None
    ) -> Goal:
        """Create a new financial goal"""
        deadline = None
        if time_horizon_months:
            deadline = date.today() + timedelta(days=time_horizon_months * 30)
        
        required_monthly = target_amount / time_horizon_months if time_horizon_months else 0
        
        goal = Goal(
            name=name,
            target_amount=target_amount,
            time_horizon_months=time_horizon_months,
            goal_type=goal_type,
            priority=priority,
            description=description,
            start_date=date.today(),
            deadline=deadline,
            required_monthly_saving=required_monthly,
            user_id=user_id
        )
        db.add(goal)
        await db.flush()
        await db.refresh(goal)
        return goal
    
    @staticmethod
    async def get_all(
        db: AsyncSession,
        user_id: str = None,
        status: GoalStatus = None
    ) -> List[Goal]:
        """Get all goals with optional filters"""
        query = select(Goal).options(selectinload(Goal.contributions))
        
        conditions = []
        if user_id:
            conditions.append(Goal.user_id == user_id)
        if status:
            conditions.append(Goal.status == status)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(Goal.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_by_id(db: AsyncSession, goal_id: int) -> Optional[Goal]:
        """Get goal by ID"""
        result = await db.execute(
            select(Goal)
            .options(selectinload(Goal.contributions))
            .where(Goal.id == goal_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_progress(
        db: AsyncSession,
        goal_id: int,
        amount: float
    ) -> Optional[Goal]:
        """Add contribution and update goal progress"""
        goal = await GoalCRUD.get_by_id(db, goal_id)
        if not goal:
            return None
        
        # Add contribution
        contribution = GoalContribution(
            goal_id=goal_id,
            amount=amount,
            contribution_date=date.today()
        )
        db.add(contribution)
        
        # Update goal
        new_current = goal.current_amount + amount
        new_progress = (new_current / goal.target_amount) * 100 if goal.target_amount > 0 else 0
        
        await db.execute(
            update(Goal)
            .where(Goal.id == goal_id)
            .values(
                current_amount=new_current,
                progress_percentage=min(new_progress, 100),
                status=GoalStatus.COMPLETED if new_progress >= 100 else GoalStatus.ACTIVE,
                completed_at=datetime.now() if new_progress >= 100 else None
            )
        )
        
        await db.refresh(goal)
        return goal
    
    @staticmethod
    async def update(
        db: AsyncSession,
        goal_id: int,
        **kwargs
    ) -> Optional[Goal]:
        """Update goal fields"""
        await db.execute(
            update(Goal)
            .where(Goal.id == goal_id)
            .values(**kwargs, updated_at=datetime.now())
        )
        return await GoalCRUD.get_by_id(db, goal_id)
    
    @staticmethod
    async def delete(db: AsyncSession, goal_id: int) -> bool:
        """Delete a goal"""
        result = await db.execute(
            delete(Goal).where(Goal.id == goal_id)
        )
        return result.rowcount > 0
    
    @staticmethod
    async def get_dashboard(db: AsyncSession, user_id: str = None) -> Dict[str, Any]:
        """Get goal dashboard summary"""
        goals = await GoalCRUD.get_all(db, user_id=user_id)
        
        active_goals = [g for g in goals if g.status == GoalStatus.ACTIVE]
        completed_goals = [g for g in goals if g.status == GoalStatus.COMPLETED]
        
        total_target = sum(g.target_amount for g in goals)
        total_current = sum(g.current_amount for g in goals)
        total_monthly_required = sum(g.required_monthly_saving or 0 for g in active_goals)
        
        return {
            "total_goals": len(goals),
            "active_goals": len(active_goals),
            "completed_goals": len(completed_goals),
            "total_target": total_target,
            "total_current": total_current,
            "total_pending": total_target - total_current,
            "overall_progress": round((total_current / total_target) * 100, 1) if total_target > 0 else 0,
            "total_monthly_required": total_monthly_required,
            "goals": [
                {
                    "id": g.id,
                    "name": g.name,
                    "target": g.target_amount,
                    "current": g.current_amount,
                    "progress": g.progress_percentage,
                    "priority": g.priority.value if g.priority else "medium",
                    "status": g.status.value if g.status else "active",
                    "deadline": g.deadline.isoformat() if g.deadline else None
                }
                for g in goals
            ]
        }


# ==================== ALERT CRUD ====================

class AlertCRUD:
    """CRUD operations for alerts"""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        alert_type: str,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        action_required: bool = False,
        related_data: Dict = None,
        user_id: str = None
    ) -> Alert:
        """Create a new alert"""
        alert = Alert(
            alert_type=alert_type,
            title=title,
            message=message,
            severity=severity,
            action_required=action_required,
            related_data=related_data,
            user_id=user_id
        )
        db.add(alert)
        await db.flush()
        await db.refresh(alert)
        return alert
    
    @staticmethod
    async def bulk_create(
        db: AsyncSession,
        alerts_data: List[Dict[str, Any]],
        user_id: str = None
    ) -> List[Alert]:
        """Bulk create alerts"""
        alerts = []
        for data in alerts_data:
            alert = Alert(
                alert_type=data.get('type', 'info'),
                title=data.get('title', ''),
                message=data.get('message', ''),
                severity=AlertSeverity(data.get('severity', 'info')),
                action_required=data.get('action_required', False),
                related_data=data.get('data'),
                user_id=user_id
            )
            alerts.append(alert)
        
        db.add_all(alerts)
        await db.flush()
        return alerts
    
    @staticmethod
    async def get_all(
        db: AsyncSession,
        user_id: str = None,
        unread_only: bool = False,
        severity: AlertSeverity = None
    ) -> List[Alert]:
        """Get all alerts with filters"""
        query = select(Alert)
        
        conditions = []
        if user_id:
            conditions.append(Alert.user_id == user_id)
        if unread_only:
            conditions.append(Alert.is_read == False)
        if severity:
            conditions.append(Alert.severity == severity)
        
        conditions.append(Alert.is_dismissed == False)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(Alert.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def mark_read(db: AsyncSession, alert_id: int) -> Optional[Alert]:
        """Mark alert as read"""
        await db.execute(
            update(Alert)
            .where(Alert.id == alert_id)
            .values(is_read=True, read_at=datetime.now())
        )
        result = await db.execute(select(Alert).where(Alert.id == alert_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def dismiss(db: AsyncSession, alert_id: int) -> bool:
        """Dismiss an alert"""
        result = await db.execute(
            update(Alert)
            .where(Alert.id == alert_id)
            .values(is_dismissed=True)
        )
        return result.rowcount > 0
    
    @staticmethod
    async def get_summary(db: AsyncSession, user_id: str = None) -> Dict[str, int]:
        """Get alert count summary"""
        query = select(
            Alert.severity,
            func.count(Alert.id).label('count')
        ).where(
            Alert.is_dismissed == False
        ).group_by(Alert.severity)
        
        if user_id:
            query = query.where(Alert.user_id == user_id)
        
        result = await db.execute(query)
        
        summary = {"critical": 0, "warning": 0, "info": 0, "total": 0}
        for row in result.all():
            summary[row.severity.value] = row.count
            summary["total"] += row.count
        
        return summary


# ==================== CATEGORY CRUD ====================

class CategoryCRUD:
    """CRUD operations for categories"""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        name: str,
        description: str = None,
        is_essential: bool = False,
        keywords: List[str] = None
    ) -> Category:
        """Create a new category"""
        category = Category(
            name=name,
            description=description,
            is_essential=is_essential,
            keywords=keywords
        )
        db.add(category)
        await db.flush()
        await db.refresh(category)
        return category
    
    @staticmethod
    async def get_all(db: AsyncSession) -> List[Category]:
        """Get all categories"""
        result = await db.execute(
            select(Category).order_by(Category.name)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Optional[Category]:
        """Get category by name"""
        result = await db.execute(
            select(Category).where(Category.name == name)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def seed_default_categories(db: AsyncSession):
        """Seed default categories"""
        default_categories = [
            {"name": "Food & Dining", "is_essential": False, "keywords": ["food", "restaurant", "cafe", "hotel"]},
            {"name": "Transportation", "is_essential": True, "keywords": ["petrol", "fuel", "uber", "ola", "bus"]},
            {"name": "Medical & Healthcare", "is_essential": True, "keywords": ["medical", "pharmacy", "hospital"]},
            {"name": "Utilities", "is_essential": True, "keywords": ["electricity", "water", "gas", "bill"]},
            {"name": "Entertainment", "is_essential": False, "keywords": ["movie", "cinema", "game", "sports"]},
            {"name": "Shopping", "is_essential": False, "keywords": ["amazon", "flipkart", "mall", "store"]},
            {"name": "Income", "is_essential": False, "keywords": ["salary", "interest", "refund"]},
            {"name": "Miscellaneous", "is_essential": False, "keywords": []}
        ]
        
        for cat_data in default_categories:
            existing = await CategoryCRUD.get_by_name(db, cat_data["name"])
            if not existing:
                await CategoryCRUD.create(
                    db,
                    name=cat_data["name"],
                    is_essential=cat_data["is_essential"],
                    keywords=cat_data["keywords"]
                )


# ==================== RECURRING EXPENSE CRUD ====================

class RecurringExpenseCRUD:
    """CRUD operations for recurring expenses"""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        description: str,
        estimated_amount: float,
        frequency: str = "monthly",
        category_name: str = None,
        is_subscription: bool = False,
        user_id: str = None
    ) -> RecurringExpense:
        """Create a recurring expense record"""
        recurring = RecurringExpense(
            description=description,
            estimated_amount=estimated_amount,
            frequency=frequency,
            category_name=category_name,
            is_subscription=is_subscription,
            last_occurrence=date.today(),
            user_id=user_id
        )
        db.add(recurring)
        await db.flush()
        await db.refresh(recurring)
        return recurring
    
    @staticmethod
    async def get_all(db: AsyncSession, user_id: str = None, active_only: bool = True) -> List[RecurringExpense]:
        """Get all recurring expenses"""
        query = select(RecurringExpense)
        
        conditions = []
        if user_id:
            conditions.append(RecurringExpense.user_id == user_id)
        if active_only:
            conditions.append(RecurringExpense.is_active == True)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(RecurringExpense.estimated_amount.desc())
        result = await db.execute(query)
        return result.scalars().all()


# ==================== ANALYTICS CRUD ====================

class AnalyticsCRUD:
    """Analytics and reporting queries"""
    
    @staticmethod
    async def get_health_score_data(
        db: AsyncSession,
        user_id: str = None
    ) -> Dict[str, Any]:
        """Get data needed for health score calculation"""
        summary = await TransactionCRUD.get_summary(db, user_id=user_id)
        breakdown = await TransactionCRUD.get_category_breakdown(db, user_id=user_id)
        monthly = await TransactionCRUD.get_monthly_breakdown(db, user_id=user_id)
        
        # Calculate volatility
        expenses = [t['total_expense'] for t in monthly if t['total_expense'] > 0]
        volatility = 0
        if len(expenses) >= 2:
            mean = sum(expenses) / len(expenses)
            variance = sum((e - mean) ** 2 for e in expenses) / len(expenses)
            volatility = (variance ** 0.5) / mean if mean > 0 else 0
        
        # Essential vs discretionary
        essential = sum(c['total_debit'] for c in breakdown if c['category'] in 
                       ['Utilities', 'Medical & Healthcare', 'Transportation'])
        discretionary = sum(c['total_debit'] for c in breakdown if c['category'] in 
                           ['Food & Dining', 'Entertainment', 'Shopping'])
        
        return {
            "summary": summary,
            "category_breakdown": breakdown,
            "monthly_trends": monthly,
            "spending_volatility": round(volatility, 4),
            "essential_spending": essential,
            "discretionary_spending": discretionary
        }
    
    @staticmethod
    async def save_monthly_summary(
        db: AsyncSession,
        year: int,
        month: int,
        total_income: float,
        total_expense: float,
        category_breakdown: Dict = None,
        health_score: float = None,
        user_id: str = None
    ) -> MonthlySummary:
        """Save or update monthly summary"""
        # Check if exists
        result = await db.execute(
            select(MonthlySummary).where(
                and_(
                    MonthlySummary.year == year,
                    MonthlySummary.month == month,
                    MonthlySummary.user_id == user_id
                )
            )
        )
        existing = result.scalar_one_or_none()
        
        savings = total_income - total_expense
        savings_rate = (savings / total_income * 100) if total_income > 0 else 0
        
        if existing:
            await db.execute(
                update(MonthlySummary)
                .where(MonthlySummary.id == existing.id)
                .values(
                    total_income=total_income,
                    total_expense=total_expense,
                    savings=savings,
                    savings_rate=savings_rate,
                    category_breakdown=category_breakdown,
                    health_score=health_score,
                    calculated_at=datetime.now()
                )
            )
            await db.refresh(existing)
            return existing
        else:
            summary = MonthlySummary(
                year=year,
                month=month,
                total_income=total_income,
                total_expense=total_expense,
                savings=savings,
                savings_rate=savings_rate,
                category_breakdown=category_breakdown,
                health_score=health_score,
                user_id=user_id
            )
            db.add(summary)
            await db.flush()
            await db.refresh(summary)
            return summary
