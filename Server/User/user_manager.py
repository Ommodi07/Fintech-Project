"""
User Management Module
Purpose: Handle user registration, authentication, profile management
"""

import json
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid

# In-memory storage (replace with database in production)
users_store: Dict[str, Dict] = {}
sessions_store: Dict[str, Dict] = {}
user_contexts: Dict[str, Dict] = {}  # For MCP context persistence

# User profile templates
INCOME_RANGES = [
    {"id": "0-25k", "label": "Below ₹25,000", "range": (0, 25000)},
    {"id": "25k-50k", "label": "₹25,000 - ₹50,000", "range": (25000, 50000)},
    {"id": "50k-1L", "label": "₹50,000 - ₹1,00,000", "range": (50000, 100000)},
    {"id": "1L-2L", "label": "₹1,00,000 - ₹2,00,000", "range": (100000, 200000)},
    {"id": "2L+", "label": "Above ₹2,00,000", "range": (200000, float('inf'))}
]

FINANCIAL_GOALS = [
    "emergency_fund",
    "house_purchase",
    "retirement",
    "debt_free",
    "net_worth_target",
    "education",
    "travel",
    "investment_growth"
]

AGE_GROUPS = [
    {"id": "18-25", "label": "18-25 years", "investment_horizon": "long"},
    {"id": "26-35", "label": "26-35 years", "investment_horizon": "long"},
    {"id": "36-45", "label": "36-45 years", "investment_horizon": "medium"},
    {"id": "46-55", "label": "46-55 years", "investment_horizon": "medium"},
    {"id": "55+", "label": "55+ years", "investment_horizon": "short"}
]


def hash_password(password: str, salt: str = None) -> tuple:
    """Hash password with salt"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    
    return hashed, salt


def generate_session_token() -> str:
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)


def register_user(
    email: str,
    password: str,
    name: str,
    age_group: str = None,
    income_range: str = None,
    financial_goals: List[str] = None
) -> Dict[str, Any]:
    """Register a new user"""
    
    # Validate email not already registered
    for user in users_store.values():
        if user['email'].lower() == email.lower():
            return {"error": "Email already registered"}
    
    user_id = str(uuid.uuid4())
    hashed_password, salt = hash_password(password)
    
    user = {
        "id": user_id,
        "email": email.lower(),
        "name": name,
        "password_hash": hashed_password,
        "salt": salt,
        "profile": {
            "age_group": age_group,
            "income_range": income_range,
            "financial_goals": financial_goals or [],
            "risk_tolerance": "moderate",  # Default, can be updated
            "onboarding_complete": False
        },
        "accounts": [],  # Linked bank accounts
        "preferences": {
            "notifications_enabled": True,
            "email_alerts": True,
            "budget_alerts": True,
            "weekly_summary": True
        },
        "consent": {
            "data_processing": True,
            "analytics": True,
            "marketing": False,
            "consent_date": datetime.now().isoformat()
        },
        "created_at": datetime.now().isoformat(),
        "last_login": None,
        "is_active": True
    }
    
    users_store[user_id] = user
    
    # Initialize user context for MCP
    user_contexts[user_id] = {
        "conversation_history": [],
        "financial_snapshot": {},
        "last_updated": datetime.now().isoformat()
    }
    
    return {
        "status": "success",
        "user_id": user_id,
        "message": "Registration successful",
        "next_step": "complete_profile" if not age_group else "upload_statement"
    }


def login_user(email: str, password: str) -> Dict[str, Any]:
    """Authenticate user and create session"""
    
    # Find user by email
    user = None
    for u in users_store.values():
        if u['email'].lower() == email.lower():
            user = u
            break
    
    if not user:
        return {"error": "Invalid email or password"}
    
    if not user['is_active']:
        return {"error": "Account is deactivated"}
    
    # Verify password
    hashed_input, _ = hash_password(password, user['salt'])
    if hashed_input != user['password_hash']:
        return {"error": "Invalid email or password"}
    
    # Create session
    session_token = generate_session_token()
    session = {
        "user_id": user['id'],
        "token": session_token,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
        "is_valid": True
    }
    
    sessions_store[session_token] = session
    user['last_login'] = datetime.now().isoformat()
    
    return {
        "status": "success",
        "session_token": session_token,
        "user": {
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "profile": user['profile']
        },
        "expires_at": session['expires_at']
    }


def logout_user(session_token: str) -> Dict[str, Any]:
    """Invalidate user session"""
    
    if session_token in sessions_store:
        sessions_store[session_token]['is_valid'] = False
        return {"status": "success", "message": "Logged out successfully"}
    
    return {"error": "Invalid session"}


def validate_session(session_token: str) -> Optional[Dict]:
    """Validate session token and return user if valid"""
    
    if session_token not in sessions_store:
        return None
    
    session = sessions_store[session_token]
    
    if not session['is_valid']:
        return None
    
    if datetime.fromisoformat(session['expires_at']) < datetime.now():
        session['is_valid'] = False
        return None
    
    user_id = session['user_id']
    if user_id in users_store:
        return users_store[user_id]
    
    return None


def update_profile(
    user_id: str,
    age_group: str = None,
    income_range: str = None,
    financial_goals: List[str] = None,
    risk_tolerance: str = None
) -> Dict[str, Any]:
    """Update user profile"""
    
    if user_id not in users_store:
        return {"error": "User not found"}
    
    user = users_store[user_id]
    profile = user['profile']
    
    if age_group:
        profile['age_group'] = age_group
    if income_range:
        profile['income_range'] = income_range
    if financial_goals is not None:
        profile['financial_goals'] = financial_goals
    if risk_tolerance:
        profile['risk_tolerance'] = risk_tolerance
    
    # Check if onboarding is complete
    if all([profile.get('age_group'), profile.get('income_range'), profile.get('financial_goals')]):
        profile['onboarding_complete'] = True
    
    return {
        "status": "success",
        "profile": profile
    }


def add_bank_account(
    user_id: str,
    account_name: str,
    account_type: str,  # savings, current, investment
    bank_name: str,
    is_primary: bool = False
) -> Dict[str, Any]:
    """Link a bank account to user's profile"""
    
    if user_id not in users_store:
        return {"error": "User not found"}
    
    account_id = str(uuid.uuid4())[:8]
    
    account = {
        "id": account_id,
        "name": account_name,
        "type": account_type,
        "bank": bank_name,
        "is_primary": is_primary,
        "linked_at": datetime.now().isoformat(),
        "last_synced": None,
        "statement_file": None
    }
    
    # If this is primary, unset others
    if is_primary:
        for acc in users_store[user_id]['accounts']:
            acc['is_primary'] = False
    
    users_store[user_id]['accounts'].append(account)
    
    return {
        "status": "success",
        "account_id": account_id,
        "message": "Bank account linked successfully"
    }


def get_user_accounts(user_id: str) -> List[Dict]:
    """Get all linked accounts for a user"""
    
    if user_id not in users_store:
        return []
    
    return users_store[user_id]['accounts']


def update_preferences(
    user_id: str,
    notifications_enabled: bool = None,
    email_alerts: bool = None,
    budget_alerts: bool = None,
    weekly_summary: bool = None
) -> Dict[str, Any]:
    """Update user notification preferences"""
    
    if user_id not in users_store:
        return {"error": "User not found"}
    
    prefs = users_store[user_id]['preferences']
    
    if notifications_enabled is not None:
        prefs['notifications_enabled'] = notifications_enabled
    if email_alerts is not None:
        prefs['email_alerts'] = email_alerts
    if budget_alerts is not None:
        prefs['budget_alerts'] = budget_alerts
    if weekly_summary is not None:
        prefs['weekly_summary'] = weekly_summary
    
    return {
        "status": "success",
        "preferences": prefs
    }


def update_consent(
    user_id: str,
    data_processing: bool = None,
    analytics: bool = None,
    marketing: bool = None
) -> Dict[str, Any]:
    """Update data privacy consent"""
    
    if user_id not in users_store:
        return {"error": "User not found"}
    
    consent = users_store[user_id]['consent']
    
    if data_processing is not None:
        consent['data_processing'] = data_processing
    if analytics is not None:
        consent['analytics'] = analytics
    if marketing is not None:
        consent['marketing'] = marketing
    
    consent['consent_date'] = datetime.now().isoformat()
    
    return {
        "status": "success",
        "consent": consent
    }


def get_user_context(user_id: str) -> Dict[str, Any]:
    """Get user context for MCP integration"""
    
    if user_id not in user_contexts:
        return {}
    
    context = user_contexts[user_id]
    
    # Enrich with user profile
    if user_id in users_store:
        user = users_store[user_id]
        context['user_profile'] = {
            "name": user['name'],
            "age_group": user['profile'].get('age_group'),
            "income_range": user['profile'].get('income_range'),
            "financial_goals": user['profile'].get('financial_goals'),
            "risk_tolerance": user['profile'].get('risk_tolerance')
        }
    
    return context


def update_user_context(user_id: str, financial_data: Dict = None, 
                        conversation_entry: Dict = None) -> Dict[str, Any]:
    """Update user context for MCP persistence"""
    
    if user_id not in user_contexts:
        user_contexts[user_id] = {
            "conversation_history": [],
            "financial_snapshot": {},
            "last_updated": datetime.now().isoformat()
        }
    
    context = user_contexts[user_id]
    
    if financial_data:
        context['financial_snapshot'] = financial_data
    
    if conversation_entry:
        # Keep last 20 conversation entries
        context['conversation_history'].append(conversation_entry)
        context['conversation_history'] = context['conversation_history'][-20:]
    
    context['last_updated'] = datetime.now().isoformat()
    
    return {"status": "success"}


def get_profile_options() -> Dict[str, Any]:
    """Get available options for profile setup"""
    return {
        "income_ranges": INCOME_RANGES,
        "age_groups": AGE_GROUPS,
        "financial_goals": [
            {"id": g, "label": g.replace("_", " ").title()} 
            for g in FINANCIAL_GOALS
        ],
        "risk_tolerances": [
            {"id": "conservative", "label": "Conservative", "description": "Prefer safety over returns"},
            {"id": "moderate", "label": "Moderate", "description": "Balance between growth and safety"},
            {"id": "aggressive", "label": "Aggressive", "description": "Higher risk for higher returns"}
        ]
    }


def delete_user(user_id: str) -> Dict[str, Any]:
    """Delete user account and all associated data (GDPR compliance)"""
    
    if user_id not in users_store:
        return {"error": "User not found"}
    
    # Remove user data
    del users_store[user_id]
    
    # Remove user context
    if user_id in user_contexts:
        del user_contexts[user_id]
    
    # Invalidate all sessions
    for token, session in sessions_store.items():
        if session['user_id'] == user_id:
            session['is_valid'] = False
    
    return {
        "status": "success",
        "message": "Account and all associated data deleted"
    }
