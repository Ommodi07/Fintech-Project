"""
SQLAlchemy Models for PostgreSQL
Covers: Transactions, Categories, Goals, Alerts, Bank Statements
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    ForeignKey, Text, JSON, Date, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from .connection import Base


class GoalStatus(enum.Enum):
    """Goal status enumeration"""
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class GoalPriority(enum.Enum):
    """Goal priority levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertSeverity(enum.Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class BankStatement(Base):
    """Bank statement uploads and metadata"""
    __tablename__ = "bank_statements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), index=True, nullable=True)  # Optional user association
    filename = Column(String(255), nullable=False)
    bank_name = Column(String(100), nullable=True)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    statement_start_date = Column(Date, nullable=True)
    statement_end_date = Column(Date, nullable=True)
    total_transactions = Column(Integer, default=0)
    parsing_method = Column(String(50), nullable=True)
    raw_data = Column(JSON, nullable=True)  # Store original parsed JSON
    
    # Relationships
    transactions = relationship("Transaction", back_populates="statement", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BankStatement(id={self.id}, filename='{self.filename}')>"


class Category(Base):
    """Transaction categories"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_essential = Column(Boolean, default=False)  # Essential vs discretionary
    keywords = Column(JSON, nullable=True)  # Keywords for auto-categorization
    icon = Column(String(50), nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    transactions = relationship("Transaction", back_populates="category")
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


class Transaction(Base):
    """Individual financial transactions"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey("bank_statements.id"), nullable=True)
    user_id = Column(String(36), index=True, nullable=True)
    
    # Transaction details
    date = Column(Date, nullable=False, index=True)
    description = Column(Text, nullable=True)
    reference = Column(String(100), nullable=True)
    
    # Amounts
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)
    balance = Column(Float, nullable=True)
    
    # Categorization
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category_name = Column(String(100), nullable=True)  # Denormalized for performance
    
    # Metadata
    is_recurring = Column(Boolean, default=False)
    is_anomaly = Column(Boolean, default=False)
    anomaly_score = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    statement = relationship("BankStatement", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, date='{self.date}', debit={self.debit}, credit={self.credit})>"


class MonthlySummary(Base):
    """Monthly aggregated financial summary"""
    __tablename__ = "monthly_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), index=True, nullable=True)
    
    # Period
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    
    # Aggregates
    total_income = Column(Float, default=0.0)
    total_expense = Column(Float, default=0.0)
    savings = Column(Float, default=0.0)
    savings_rate = Column(Float, default=0.0)
    
    # Category-wise breakdown (JSON)
    category_breakdown = Column(JSON, nullable=True)
    
    # Health metrics
    health_score = Column(Float, nullable=True)
    spending_volatility = Column(Float, nullable=True)
    
    # Timestamps
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<MonthlySummary(year={self.year}, month={self.month})>"


class Goal(Base):
    """Financial goals"""
    __tablename__ = "goals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), index=True, nullable=True)
    
    # Goal details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    goal_type = Column(String(50), nullable=True)  # emergency_fund, house, vacation, etc.
    
    # Financial targets
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    monthly_contribution = Column(Float, default=0.0)
    
    # Timeline
    start_date = Column(Date, nullable=True)
    deadline = Column(Date, nullable=True)
    time_horizon_months = Column(Integer, nullable=True)
    
    # Status
    status = Column(SQLEnum(GoalStatus), default=GoalStatus.ACTIVE)
    priority = Column(SQLEnum(GoalPriority), default=GoalPriority.MEDIUM)
    
    # Progress
    progress_percentage = Column(Float, default=0.0)
    
    # Feasibility analysis
    feasibility_score = Column(Float, nullable=True)
    required_monthly_saving = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    contributions = relationship("GoalContribution", back_populates="goal", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Goal(id={self.id}, name='{self.name}', target={self.target_amount})>"


class GoalContribution(Base):
    """Contributions towards goals"""
    __tablename__ = "goal_contributions"
    
    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)
    
    amount = Column(Float, nullable=False)
    contribution_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    goal = relationship("Goal", back_populates="contributions")
    
    def __repr__(self):
        return f"<GoalContribution(goal_id={self.goal_id}, amount={self.amount})>"


class Alert(Base):
    """Financial alerts and notifications"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), index=True, nullable=True)
    
    # Alert details
    alert_type = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    # Severity and status
    severity = Column(SQLEnum(AlertSeverity), default=AlertSeverity.INFO)
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    action_required = Column(Boolean, default=False)
    
    # Related data
    related_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<Alert(id={self.id}, type='{self.alert_type}', severity={self.severity})>"


class RecurringExpense(Base):
    """Detected recurring expenses"""
    __tablename__ = "recurring_expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), index=True, nullable=True)
    
    # Details
    description = Column(String(255), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category_name = Column(String(100), nullable=True)
    
    # Amount and frequency
    estimated_amount = Column(Float, nullable=False)
    frequency = Column(String(20), nullable=True)  # monthly, weekly, quarterly
    
    # Tracking
    last_occurrence = Column(Date, nullable=True)
    next_expected = Column(Date, nullable=True)
    occurrences_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_subscription = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<RecurringExpense(description='{self.description}', amount={self.estimated_amount})>"
