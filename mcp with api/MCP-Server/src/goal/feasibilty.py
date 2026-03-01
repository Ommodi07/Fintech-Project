"""
Goal Feasibility Analysis Module for MCP
Determines if financial goals are achievable based on user's financial data
"""

import httpx
from typing import Dict, Any, List

# Server API endpoint
API_BASE_URL = "http://localhost:5000"

async def get_financial_data() -> Dict[str, Any]:
    """Fetch current financial data from the server API"""
    try:
        async with httpx.AsyncClient() as client:
            # Get summary
            summary_response = await client.get(f"{API_BASE_URL}/analytics/summary")
            health_response = await client.get(f"{API_BASE_URL}/analytics/health_score")
            
            data = {}
            if summary_response.status_code == 200:
                summary = summary_response.json().get('data', {})
                data['savings'] = summary.get('savings', 0)
                data['income'] = summary.get('total_income', 0)
                data['expense'] = summary.get('total_expense', 0)
            
            if health_response.status_code == 200:
                health = health_response.json()
                data['health_score'] = health.get('overall_score', 0)
                data['savings_rate'] = health.get('metrics', {}).get('savings_rate', 0)
            
            return data
    except Exception as e:
        print(f"Error fetching financial data: {e}")
    
    return {
        "savings": 0,
        "income": 0,
        "expense": 0,
        "health_score": 50,
        "savings_rate": 10
    }

def calculate_sip_returns(monthly_investment: float, months: int, 
                          annual_rate: float = 0.12) -> float:
    """Calculate future value of SIP investments"""
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return monthly_investment * months
    
    fv = monthly_investment * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
    return fv

def is_goal_feasible(goal_name: str, amount: float, time_horizon: int) -> str:
    """
    Comprehensive goal feasibility analysis
    
    Args:
        goal_name: Name of the financial goal
        amount: Target amount for the goal
        time_horizon: Timeline in months
    
    Returns:
        Detailed feasibility analysis with recommendations
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
        financial_data = {
            "savings": 5000, 
            "income": 50000, 
            "expense": 35000,
            "health_score": 60,
            "savings_rate": 30
        }
    
    current_savings = financial_data.get('savings', 0)
    income = financial_data.get('income', 0)
    expense = financial_data.get('expense', 0)
    health_score = financial_data.get('health_score', 50)
    
    # Calculate metrics
    disposable_income = income - expense
    available_monthly = disposable_income * 0.7  # 70% for goals
    required_monthly = amount / max(time_horizon, 1)
    
    # Calculate feasibility score (0-100)
    if available_monthly <= 0:
        feasibility_score = 0
    elif required_monthly <= available_monthly:
        feasibility_score = 100
    elif required_monthly <= available_monthly * 1.2:
        feasibility_score = 85
    elif required_monthly <= available_monthly * 1.5:
        feasibility_score = 65
    elif required_monthly <= available_monthly * 2:
        feasibility_score = 45
    else:
        feasibility_score = max(0, 25 - ((required_monthly / max(available_monthly, 1) - 2) * 10))
    
    # Build response
    response = []
    response.append(f"🎯 **Goal Feasibility Analysis: {goal_name}**")
    response.append(f"")
    
    # Financial context
    response.append(f"📊 **Your Financial Context:**")
    response.append(f"- Monthly Disposable Income: ₹{disposable_income:,.2f}")
    response.append(f"- Available for Goals: ₹{available_monthly:,.2f}/month")
    response.append(f"- Financial Health Score: {health_score}/100")
    response.append(f"")
    
    # Goal analysis
    response.append(f"🎯 **Goal Analysis:**")
    response.append(f"- Target: ₹{amount:,.2f}")
    response.append(f"- Timeline: {time_horizon} months ({time_horizon//12} years {time_horizon%12} months)")
    response.append(f"- Required Monthly Saving: ₹{required_monthly:,.2f}")
    response.append(f"- Feasibility Score: {feasibility_score:.0f}/100")
    response.append(f"")
    
    # Decision
    if feasibility_score >= 80:
        response.append(f"✅ **Goal is ACHIEVABLE!**")
        response.append(f"")
        response.append(f"You can comfortably achieve this goal with your current savings capacity.")
        
        # Investment suggestion
        if time_horizon >= 12:
            sip_amount = required_monthly
            expected_returns = calculate_sip_returns(sip_amount, time_horizon)
            if expected_returns > amount:
                response.append(f"")
                response.append(f"💡 **Investment Tip:**")
                response.append(f"Investing ₹{sip_amount:,.2f}/month in equity mutual funds (expected 12% returns)")
                response.append(f"could grow to ₹{expected_returns:,.2f} - exceeding your goal!")
                
    elif feasibility_score >= 60:
        response.append(f"⚠️ **Goal is ACHIEVABLE with minor adjustments**")
        response.append(f"")
        gap = required_monthly - available_monthly
        response.append(f"You need to either:")
        response.append(f"- Reduce monthly expenses by ₹{gap:,.2f}")
        response.append(f"- Or extend timeline slightly")
        
    elif feasibility_score >= 40:
        response.append(f"⚠️ **Goal requires SIGNIFICANT adjustments**")
        response.append(f"")
        
        # Alternative scenarios
        if available_monthly > 0:
            extended_months = int(amount / available_monthly) + 1
            response.append(f"**Option 1:** Extend timeline to {extended_months} months ({extended_months//12} years)")
        
        reduced_target = available_monthly * time_horizon
        response.append(f"**Option 2:** Reduce target to ₹{reduced_target:,.2f}")
        
        # With investments
        if time_horizon >= 12:
            # Calculate SIP needed for target with returns
            monthly_rate = 0.12 / 12
            fv_factor = (((1 + monthly_rate) ** time_horizon - 1) / monthly_rate) * (1 + monthly_rate)
            sip_needed = amount / fv_factor
            if sip_needed < required_monthly:
                response.append(f"**Option 3:** Invest ₹{sip_needed:,.2f}/month in SIP (12% expected returns)")
        
    else:
        response.append(f"❌ **Goal needs MAJOR revision**")
        response.append(f"")
        response.append(f"Current financial situation doesn't support this goal.")
        response.append(f"")
        response.append(f"**Recommendations:**")
        
        if available_monthly > 0:
            realistic_amount = available_monthly * time_horizon
            extended_months = int(amount / available_monthly) + 1
            response.append(f"1. Set a target of ₹{realistic_amount:,.2f} for {time_horizon} months")
            response.append(f"2. Or extend timeline to {extended_months} months ({extended_months//12} years)")
        
        response.append(f"3. Focus on increasing income or reducing expenses first")
        response.append(f"4. Build an emergency fund before pursuing this goal")
    
    # Personalized tips based on health score
    response.append(f"")
    response.append(f"💡 **Personalized Tips:**")
    
    if health_score < 40:
        response.append(f"- Focus on improving overall financial health first")
        response.append(f"- Build 3-month emergency fund before big goals")
    elif health_score < 60:
        response.append(f"- Review and optimize your monthly expenses")
        response.append(f"- Consider automating savings transfers")
    else:
        response.append(f"- Great financial health! You're well-positioned for goals")
        response.append(f"- Consider investing surplus in equity for long-term goals")
    
    return "\n".join(response)