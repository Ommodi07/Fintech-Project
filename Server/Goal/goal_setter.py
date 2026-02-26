from Analytics import analytic
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import os
import uuid

# In-memory storage (replace with database in production)
goals_store: Dict[str, Dict] = {}

# Goal types with recommended parameters
GOAL_TEMPLATES = {
    "emergency_fund": {
        "name": "Emergency Fund",
        "description": "3-6 months of expenses for unexpected situations",
        "recommended_months": 12,
        "priority": "high"
    },
    "house": {
        "name": "Buy a House",
        "description": "Down payment for home purchase",
        "recommended_months": 60,
        "priority": "medium"
    },
    "vacation": {
        "name": "Vacation",
        "description": "Travel and leisure fund",
        "recommended_months": 12,
        "priority": "low"
    },
    "retirement": {
        "name": "Retirement",
        "description": "Long-term retirement savings",
        "recommended_months": 240,
        "priority": "high"
    },
    "net_worth": {
        "name": "Net Worth Target",
        "description": "Overall wealth accumulation goal",
        "recommended_months": 60,
        "priority": "medium"
    },
    "education": {
        "name": "Education Fund",
        "description": "Higher education or skill development",
        "recommended_months": 36,
        "priority": "medium"
    },
    "car": {
        "name": "Buy a Car",
        "description": "Vehicle purchase fund",
        "recommended_months": 24,
        "priority": "low"
    },
    "custom": {
        "name": "Custom Goal",
        "description": "User-defined financial goal",
        "recommended_months": 12,
        "priority": "medium"
    }
}

def get_current_financial_status() -> Dict[str, Any]:
    """Get current financial metrics from analytics"""
    dataobj = analytic.main_analytic("categorized_transactions.json")
    
    if isinstance(dataobj, str):
        return {
            "current_savings": 0,
            "monthly_income": 0,
            "monthly_expense": 0,
            "available_for_goals": 0
        }
    
    return {
        "current_savings": dataobj.get('savings', 0),
        "monthly_income": dataobj.get('total_income', 0),
        "monthly_expense": dataobj.get('total_expense', 0),
        "available_for_goals": dataobj.get('savings', 0) * 0.7  # 70% of savings can go to goals
    }

def calculate_feasibility(target_amount: float, time_horizon_months: int, 
                          available_monthly: float) -> Dict[str, Any]:
    """Calculate detailed feasibility analysis for a goal"""
    
    required_monthly = target_amount / max(time_horizon_months, 1)
    
    # Calculate feasibility score (0-100)
    if available_monthly <= 0:
        feasibility_score = 0
    elif required_monthly <= available_monthly:
        feasibility_score = 100
    elif required_monthly <= available_monthly * 1.2:  # Within 20% stretch
        feasibility_score = 80
    elif required_monthly <= available_monthly * 1.5:  # Within 50% stretch
        feasibility_score = 60
    elif required_monthly <= available_monthly * 2:    # Within 2x
        feasibility_score = 40
    else:
        feasibility_score = max(0, 20 - ((required_monthly / max(available_monthly, 1) - 2) * 10))
    
    # Calculate alternative scenarios
    scenarios = []
    
    # Scenario 1: Extend timeline
    if required_monthly > available_monthly and available_monthly > 0:
        extended_months = int(target_amount / available_monthly) + 1
        scenarios.append({
            "name": "Extended Timeline",
            "description": f"Extend goal to {extended_months} months",
            "new_monthly_requirement": available_monthly,
            "new_timeline_months": extended_months
        })
    
    # Scenario 2: Reduce target
    if required_monthly > available_monthly:
        achievable_amount = available_monthly * time_horizon_months
        scenarios.append({
            "name": "Reduced Target",
            "description": f"Reduce target to ₹{achievable_amount:,.2f}",
            "new_target": achievable_amount,
            "same_timeline": True
        })
    
    # Scenario 3: With investment returns (8% annual)
    if time_horizon_months >= 12:
        monthly_rate = 0.08 / 12
        fv_factor = ((1 + monthly_rate) ** time_horizon_months - 1) / monthly_rate
        sip_needed = target_amount / fv_factor
        if sip_needed < required_monthly:
            scenarios.append({
                "name": "With Investment Returns",
                "description": f"Invest in mutual funds (8% expected return)",
                "monthly_sip": round(sip_needed, 2),
                "savings_vs_direct": round((required_monthly - sip_needed) * time_horizon_months, 2)
            })
    
    return {
        "feasibility_score": round(feasibility_score, 1),
        "required_monthly_saving": round(required_monthly, 2),
        "available_monthly": round(available_monthly, 2),
        "gap": round(max(0, required_monthly - available_monthly), 2),
        "gap_percentage": round(max(0, (required_monthly - available_monthly) / max(required_monthly, 1) * 100), 1),
        "alternative_scenarios": scenarios
    }

def set_goal(data) -> Dict[str, Any]:
    """Create a new financial goal with comprehensive analysis"""
    
    goal_id = str(uuid.uuid4())[:8]
    
    # Get current financial status
    financial_status = get_current_financial_status()
    available_monthly = financial_status.get('available_for_goals', 0)
    
    # Calculate feasibility
    feasibility = calculate_feasibility(
        data.target_amount, 
        data.time_horizon_months,
        available_monthly
    )
    
    # Determine decision
    if feasibility['feasibility_score'] >= 80:
        decision = "✅ Achievable"
        decision_detail = "Your current savings rate supports this goal"
    elif feasibility['feasibility_score'] >= 60:
        decision = "⚠️ Achievable with adjustments"
        decision_detail = "Minor spending cuts or timeline extension recommended"
    elif feasibility['feasibility_score'] >= 40:
        decision = "⚠️ Challenging but possible"
        decision_detail = "Significant lifestyle changes needed"
    else:
        decision = "❌ Needs revision"
        decision_detail = "Consider extending timeline or reducing target"
    
    # Create goal object
    goal_obj = {
        "id": goal_id,
        "name": data.goal_name,
        "target_amount": data.target_amount,
        "time_horizon_months": data.time_horizon_months,
        "deadline": (datetime.now() + timedelta(days=data.time_horizon_months * 30)).strftime("%Y-%m-%d"),
        "priority": getattr(data, 'priority', 'medium'),
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "progress": {
            "invested": 0,
            "pending": data.target_amount,
            "percentage": 0
        },
        "monthly_contribution": {
            "required": feasibility['required_monthly_saving'],
            "recommended": min(feasibility['required_monthly_saving'], available_monthly)
        }
    }
    
    # Store goal
    goals_store[goal_id] = goal_obj
    
    return {
        "goal_id": goal_id,
        "decision": decision,
        "decision_detail": decision_detail,
        "feasibility": feasibility,
        "goal_details": goal_obj,
        "financial_status": financial_status,
        "recommendations": generate_goal_recommendations(feasibility, financial_status)
    }

def generate_goal_recommendations(feasibility: Dict, financial_status: Dict) -> List[str]:
    """Generate actionable recommendations for achieving the goal"""
    recommendations = []
    
    if feasibility['feasibility_score'] >= 80:
        recommendations.append("💰 Set up automatic monthly transfers to a dedicated savings account")
        recommendations.append("📊 Review goal progress monthly")
    else:
        if feasibility['gap'] > 0:
            recommendations.append(f"💡 Need to increase savings by ₹{feasibility['gap']:,.2f}/month")
        
        if feasibility.get('alternative_scenarios'):
            for scenario in feasibility['alternative_scenarios']:
                if scenario['name'] == "With Investment Returns":
                    recommendations.append(
                        f"📈 Consider SIP of ₹{scenario['monthly_sip']:,.2f} for better returns"
                    )
    
    if financial_status.get('monthly_expense', 0) > financial_status.get('monthly_income', 0) * 0.7:
        recommendations.append("⚠️ Your expenses are high. Review discretionary spending.")
    
    return recommendations

def update_goal_progress(goal_id: str, amount_contributed: float) -> Dict[str, Any]:
    """Update progress on a specific goal"""
    
    if goal_id not in goals_store:
        return {"error": "Goal not found"}
    
    goal = goals_store[goal_id]
    goal['progress']['invested'] += amount_contributed
    goal['progress']['pending'] = max(0, goal['target_amount'] - goal['progress']['invested'])
    goal['progress']['percentage'] = round(
        (goal['progress']['invested'] / goal['target_amount']) * 100, 1
    )
    
    if goal['progress']['percentage'] >= 100:
        goal['status'] = 'completed'
    
    return {
        "goal_id": goal_id,
        "updated_progress": goal['progress'],
        "status": goal['status']
    }

def get_all_goals() -> List[Dict]:
    """Get all active goals"""
    return list(goals_store.values())

def get_goal_dashboard() -> Dict[str, Any]:
    """Get comprehensive goal tracking dashboard"""
    
    goals = list(goals_store.values())
    financial_status = get_current_financial_status()
    
    total_target = sum(g['target_amount'] for g in goals)
    total_invested = sum(g['progress']['invested'] for g in goals)
    total_pending = sum(g['progress']['pending'] for g in goals)
    total_monthly_required = sum(g['monthly_contribution']['required'] for g in goals)
    
    # Prioritize goals
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    sorted_goals = sorted(goals, key=lambda x: priority_order.get(x.get('priority', 'medium'), 1))
    
    # Check if goals are on track
    goals_on_track = []
    goals_at_risk = []
    
    for goal in goals:
        months_remaining = goal['time_horizon_months']
        if months_remaining > 0:
            required_monthly = goal['progress']['pending'] / months_remaining
            if required_monthly <= financial_status['available_for_goals']:
                goals_on_track.append(goal['name'])
            else:
                goals_at_risk.append(goal['name'])
    
    return {
        "summary": {
            "total_goals": len(goals),
            "total_target": total_target,
            "total_invested": total_invested,
            "total_pending": total_pending,
            "overall_progress": round((total_invested / max(total_target, 1)) * 100, 1),
            "total_monthly_requirement": total_monthly_required,
            "available_monthly": financial_status['available_for_goals']
        },
        "by_priority": {
            "high": [g for g in goals if g.get('priority') == 'high'],
            "medium": [g for g in goals if g.get('priority') == 'medium'],
            "low": [g for g in goals if g.get('priority') == 'low']
        },
        "status": {
            "on_track": goals_on_track,
            "at_risk": goals_at_risk
        },
        "goals": sorted_goals
    }

def get_goal_templates() -> Dict:
    """Get available goal templates"""
    return GOAL_TEMPLATES

def delete_goal(goal_id: str) -> Dict[str, Any]:
    """Delete a goal"""
    if goal_id in goals_store:
        del goals_store[goal_id]
        return {"status": "deleted", "goal_id": goal_id}
    return {"error": "Goal not found"}