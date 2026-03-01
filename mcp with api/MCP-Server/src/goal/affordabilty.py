"""
Affordability Analysis Module for MCP
Determines if user can afford specific purchases or goals
"""

import httpx
from typing import Dict, Any

# Server API endpoint
API_BASE_URL = "http://localhost:5000"

async def get_financial_data() -> Dict[str, Any]:
    """Fetch current financial data from the server API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/analytics/summary")
            if response.status_code == 200:
                data = response.json().get('data', {})
                return {
                    "current_savings": data.get('savings', 0),
                    "monthly_income": data.get('total_income', 0),
                    "monthly_expense": data.get('total_expense', 0)
                }
    except Exception as e:
        print(f"Error fetching financial data: {e}")
    
    # Fallback to default values if API fails
    return {
        "current_savings": 0,
        "monthly_income": 0,
        "monthly_expense": 0
    }

def is_affordable(goal_name: str, amount: float, time_horizon: int) -> str:
    """
    Determine if user can afford a specific item or goal
    
    Args:
        goal_name: Name of the item or goal
        amount: Target amount needed
        time_horizon: Number of months to achieve this
    
    Returns:
        Detailed affordability analysis
    """
    import asyncio
    
    # Get financial data
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            financial_data = loop.run_until_complete(get_financial_data())
        else:
            financial_data = asyncio.run(get_financial_data())
    except:
        # Fallback
        financial_data = {"current_savings": 5000, "monthly_income": 50000, "monthly_expense": 35000}
    
    current_savings = financial_data.get('current_savings', 0)
    monthly_income = financial_data.get('monthly_income', 0)
    monthly_expense = financial_data.get('monthly_expense', 0)
    
    # Calculate available for goals
    disposable_income = monthly_income - monthly_expense
    available_monthly = disposable_income * 0.7  # 70% of disposable for goals
    
    required_monthly = amount / max(time_horizon, 1)
    
    # Build response
    response_parts = []
    response_parts.append(f"📊 **Affordability Analysis for '{goal_name}'**")
    response_parts.append(f"")
    response_parts.append(f"💰 **Your Financial Snapshot:**")
    response_parts.append(f"- Monthly Savings: ₹{current_savings:,.2f}")
    response_parts.append(f"- Available for Goals: ₹{available_monthly:,.2f}/month")
    response_parts.append(f"")
    response_parts.append(f"🎯 **Goal Details:**")
    response_parts.append(f"- Target Amount: ₹{amount:,.2f}")
    response_parts.append(f"- Timeline: {time_horizon} months")
    response_parts.append(f"- Required Monthly: ₹{required_monthly:,.2f}")
    response_parts.append(f"")
    
    if required_monthly <= available_monthly:
        response_parts.append(f"✅ **Yes, you can afford this!**")
        response_parts.append(f"You have sufficient savings capacity to achieve this goal.")
        
        if required_monthly < available_monthly * 0.5:
            response_parts.append(f"💡 Tip: You could even achieve this faster by increasing contributions.")
    elif required_monthly <= available_monthly * 1.2:
        response_parts.append(f"⚠️ **Possible with minor adjustments**")
        gap = required_monthly - available_monthly
        response_parts.append(f"You need to reduce expenses by ₹{gap:,.2f}/month or extend the timeline.")
    elif required_monthly <= available_monthly * 1.5:
        response_parts.append(f"⚠️ **Challenging but achievable**")
        response_parts.append(f"Consider:")
        response_parts.append(f"- Extending timeline to {int(amount/available_monthly)+1} months")
        response_parts.append(f"- Reducing target amount to ₹{available_monthly * time_horizon:,.2f}")
    else:
        response_parts.append(f"❌ **Not affordable with current finances**")
        response_parts.append(f"")
        response_parts.append(f"📌 **Alternatives:**")
        if available_monthly > 0:
            extended_months = int(amount / available_monthly) + 1
            response_parts.append(f"- Extend timeline to {extended_months} months")
        achievable_amount = available_monthly * time_horizon
        response_parts.append(f"- Reduce target to ₹{achievable_amount:,.2f}")
        response_parts.append(f"- Increase income or reduce discretionary spending")
    
    return "\n".join(response_parts)