from mcp.server.fastmcp import FastMCP
from src.goal.feasibilty import is_goal_feasible
from src.goal.affordabilty import is_affordable
import httpx
from typing import Optional

mcp = FastMCP("Finance Agent")

# Server API endpoint
API_BASE_URL = "http://localhost:5000"

async def fetch_from_api(endpoint: str) -> dict:
    """Helper to fetch data from the backend API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}{endpoint}")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        return {"error": str(e)}
    return {}

@mcp.tool()
async def say_hello(name: str) -> str:
    """
    Greet the user and introduce the finance assistant

    Args:
        name: Name of user
    """
    return f"""Hello {name}! 👋 Welcome to your Personal Finance Assistant!

I can help you with:
📊 Analyzing your spending patterns
🎯 Planning and tracking financial goals
💰 Checking if you can afford purchases
⚠️ Alerting you about unusual spending
📈 Understanding your financial health

What would you like to explore today?"""

@mcp.tool()
async def goal_feasibility(amount: float, time_horizon: int, goal_name: str) -> str:
    """
    Check if a financial goal is achievable based on current finances.
    Provides detailed analysis and recommendations.

    Args:
        goal_name: Name of the goal (e.g., "Buy a House", "Emergency Fund")
        amount: Target amount needed in rupees
        time_horizon: Time to achieve this goal in months
    """
    return is_goal_feasible(goal_name, amount, time_horizon)

@mcp.tool()
async def affordability_check(amount: float, time_horizon: int, item_name: str) -> str:
    """
    Check if user can afford a specific purchase or item.
    Analyzes current savings and spending to determine affordability.

    Args:
        item_name: Name of item or purchase (e.g., "New Phone", "Vacation")
        amount: Cost of the item in rupees
        time_horizon: Months to save for this purchase
    """
    return is_affordable(item_name, amount, time_horizon)

@mcp.tool()
async def get_financial_summary() -> str:
    """
    Get a summary of current financial status including income, expenses, and savings.
    Useful for understanding overall financial picture.
    """
    data = await fetch_from_api("/analytics/summary")
    
    if "error" in data:
        return f"Unable to fetch financial data: {data['error']}"
    
    summary = data.get('data', {})
    income = summary.get('total_income', 0)
    expense = summary.get('total_expense', 0)
    savings = summary.get('savings', 0)
    max_category = summary.get('max_spending_category', 'Unknown')
    
    savings_rate = (savings / income * 100) if income > 0 else 0
    
    return f"""📊 **Your Financial Summary**

💵 **Income:** ₹{income:,.2f}
💸 **Expenses:** ₹{expense:,.2f}
💰 **Savings:** ₹{savings:,.2f}
📈 **Savings Rate:** {savings_rate:.1f}%

🏷️ **Highest Spending Category:** {max_category}

{"✅ Great! You're saving money!" if savings > 0 else "⚠️ Your expenses exceed income. Review your spending!"}"""

@mcp.tool()
async def get_health_score() -> str:
    """
    Get your comprehensive financial health score.
    Score includes savings discipline, spending patterns, and cash flow analysis.
    """
    data = await fetch_from_api("/analytics/health_score")
    
    if "error" in data:
        return f"Unable to calculate health score: {data.get('error', 'Unknown error')}"
    
    score = data.get('overall_score', 0)
    grade = data.get('grade', 'Unknown')
    components = data.get('component_scores', {})
    tips = data.get('improvement_tips', [])
    
    response = [f"🏥 **Your Financial Health Score**", ""]
    response.append(f"**Overall Score:** {score}/100 {grade}")
    response.append("")
    
    response.append("**Component Breakdown:**")
    for component, value in components.items():
        emoji = "✅" if value >= 60 else "⚠️" if value >= 40 else "❌"
        response.append(f"- {component.replace('_', ' ').title()}: {value}/100 {emoji}")
    
    if tips:
        response.append("")
        response.append("**Improvement Tips:**")
        for tip in tips[:3]:
            response.append(f"- {tip}")
    
    return "\n".join(response)

@mcp.tool()
async def get_alerts() -> str:
    """
    Get all financial alerts and notifications.
    Includes overspending alerts, unusual transactions, and subscription reminders.
    """
    data = await fetch_from_api("/alerts")
    
    if "error" in data:
        return f"Unable to fetch alerts: {data.get('error', 'Unknown error')}"
    
    total = data.get('total_alerts', 0)
    critical = data.get('critical', 0)
    warnings = data.get('warnings', 0)
    alerts_list = data.get('alerts', [])
    
    if total == 0:
        return "✅ Great news! You have no financial alerts at this time."
    
    response = [f"🔔 **Financial Alerts** ({total} total)", ""]
    
    if critical > 0:
        response.append(f"🔴 **Critical Alerts:** {critical}")
    if warnings > 0:
        response.append(f"⚠️ **Warnings:** {warnings}")
    
    response.append("")
    
    for alert in alerts_list[:5]:
        response.append(f"**{alert.get('title', 'Alert')}**")
        response.append(f"  {alert.get('message', '')}")
        response.append("")
    
    return "\n".join(response)

@mcp.tool()
async def get_spending_breakdown() -> str:
    """
    Get detailed breakdown of spending by category.
    Shows where your money is going each month.
    """
    data = await fetch_from_api("/analytics/health_score")
    
    if "error" in data:
        return f"Unable to fetch spending data: {data.get('error', 'Unknown error')}"
    
    breakdown = data.get('category_breakdown', {})
    metrics = data.get('metrics', {})
    
    total_expense = metrics.get('total_expense', 0)
    
    response = ["📊 **Spending Breakdown by Category**", ""]
    
    # Sort by amount
    sorted_cats = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
    
    for category, amount in sorted_cats:
        if amount > 0:
            pct = (amount / total_expense * 100) if total_expense > 0 else 0
            bar_length = int(pct / 5)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            response.append(f"**{category}**")
            response.append(f"  ₹{amount:,.2f} ({pct:.1f}%)")
            response.append(f"  {bar}")
            response.append("")
    
    return "\n".join(response)

@mcp.tool()
async def get_smart_nudges() -> str:
    """
    Get personalized financial tips and nudges based on your spending patterns.
    """
    data = await fetch_from_api("/alerts/nudges")
    
    nudges = data.get('nudges', [])
    
    if not nudges:
        return "✅ You're doing great! No specific recommendations at this time."
    
    response = ["💡 **Smart Financial Tips for You**", ""]
    
    for nudge in nudges:
        priority = nudge.get('priority', 'medium')
        emoji = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
        response.append(f"{emoji} {nudge.get('message', '')}")
        response.append("")
    
    return "\n".join(response)

@mcp.tool()
async def net_worth_planning(target_amount: float, years: int) -> str:
    """
    Calculate how to reach a target net worth.
    Provides SIP recommendations and timelines.

    Args:
        target_amount: Target net worth in rupees
        years: Number of years to achieve this
    """
    # Get current financial data
    data = await fetch_from_api("/analytics/summary")
    summary = data.get('data', {})
    
    current_savings = summary.get('savings', 0)
    monthly_income = summary.get('total_income', 0)
    monthly_expense = summary.get('total_expense', 0)
    
    months = years * 12
    
    # Simple savings projection
    if current_savings > 0:
        simple_projection = current_savings * months
    else:
        simple_projection = 0
    
    # Calculate required monthly investment
    annual_rate = 0.12  # Expected 12% returns
    monthly_rate = annual_rate / 12
    
    if monthly_rate > 0:
        # Future value of SIP
        fv_factor = (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
        required_sip = target_amount / fv_factor
    else:
        required_sip = target_amount / months
    
    available_for_investment = max(0, current_savings * 0.7)
    
    response = [f"💎 **Net Worth Planning: ₹{target_amount:,.0f} in {years} Years**", ""]
    
    response.append("**Current Situation:**")
    response.append(f"- Monthly Savings: ₹{current_savings:,.2f}")
    response.append(f"- Available for Investment: ₹{available_for_investment:,.2f}/month")
    response.append("")
    
    response.append("**To Reach Your Goal:**")
    response.append(f"- Required Monthly SIP: ₹{required_sip:,.2f}")
    response.append(f"- Assumed Returns: 12% p.a. (equity)")
    response.append("")
    
    if required_sip <= available_for_investment:
        response.append(f"✅ **Achievable!** You can afford ₹{required_sip:,.2f}/month SIP")
        surplus = available_for_investment - required_sip
        response.append(f"💰 You'll have ₹{surplus:,.2f}/month for other goals")
    elif required_sip <= available_for_investment * 1.3:
        gap = required_sip - available_for_investment
        response.append(f"⚠️ **Almost there!** Need to increase savings by ₹{gap:,.2f}/month")
    else:
        # Calculate achievable timeline
        achievable_years = 0
        test_months = 12
        while test_months <= 360:  # Max 30 years
            test_fv_factor = (((1 + monthly_rate) ** test_months - 1) / monthly_rate) * (1 + monthly_rate)
            if available_for_investment * test_fv_factor >= target_amount:
                achievable_years = test_months / 12
                break
            test_months += 12
        
        response.append(f"❌ **Needs adjustment**")
        if achievable_years > 0:
            response.append(f"💡 With ₹{available_for_investment:,.2f}/month, you could reach this in {achievable_years:.0f} years")
        
        achievable_amount = available_for_investment * fv_factor
        response.append(f"💡 In {years} years, you could reach ₹{achievable_amount:,.0f}")
    
    response.append("")
    response.append("**Recommended Investment Mix:**")
    if years >= 10:
        response.append("- 80% Equity Mutual Funds")
        response.append("- 15% Debt Funds")
        response.append("- 5% Gold/Alternative")
    elif years >= 5:
        response.append("- 60% Equity Mutual Funds")
        response.append("- 30% Debt Funds")
        response.append("- 10% Fixed Deposits")
    else:
        response.append("- 40% Balanced Funds")
        response.append("- 40% Debt Funds")
        response.append("- 20% Fixed Deposits")
    
    return "\n".join(response)

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()