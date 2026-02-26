"""
Trend Analysis Module
Purpose: Analyze spending trends over time and provide insights
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from collections import defaultdict

def analyze_spending_trends(file_path: str = "categorized_transactions.json") -> Dict[str, Any]:
    """
    Comprehensive spending trend analysis over time
    
    Returns:
        Dictionary containing trend data, patterns, and insights
    """
    if not os.path.exists(file_path):
        return {"error": "Transaction file not found"}
    
    with open(file_path, "r") as f:
        data = json.load(f)
    
    monthly_breakdown = data.get('monthly_breakdown', {})
    categories = data.get('categories', {})
    summary = data.get('summary', {})
    
    # Monthly trends
    monthly_totals = []
    for month, cats in sorted(monthly_breakdown.items()):
        total_expense = sum(cat.get('total_debit', 0) for cat in cats.values())
        total_income = sum(cat.get('total_credit', 0) for cat in cats.values())
        monthly_totals.append({
            "month": month,
            "expense": total_expense,
            "income": total_income,
            "net": total_income - total_expense,
            "savings_rate": round((total_income - total_expense) / max(total_income, 1) * 100, 1)
        })
    
    # Category trends
    category_trends = {}
    for month, cats in sorted(monthly_breakdown.items()):
        for cat_name, cat_data in cats.items():
            if cat_name not in category_trends:
                category_trends[cat_name] = []
            category_trends[cat_name].append({
                "month": month,
                "expense": cat_data.get('total_debit', 0),
                "transactions": cat_data.get('count', 0)
            })
    
    # Trend direction analysis
    trend_analysis = calculate_trend_directions(monthly_totals)
    
    # Spending patterns by day of week
    day_of_week_patterns = analyze_day_of_week_patterns(categories)
    
    # Identify spending spikes
    spending_spikes = identify_spending_spikes(monthly_totals)
    
    # Generate insights
    insights = generate_trend_insights(monthly_totals, category_trends, trend_analysis)
    
    return {
        "monthly_trends": monthly_totals,
        "category_trends": category_trends,
        "trend_direction": trend_analysis,
        "day_of_week_patterns": day_of_week_patterns,
        "spending_spikes": spending_spikes,
        "insights": insights
    }


def calculate_trend_directions(monthly_totals: List[Dict]) -> Dict[str, Any]:
    """Calculate trend direction for expenses and savings"""
    
    if len(monthly_totals) < 2:
        return {
            "expense_trend": "insufficient_data",
            "savings_trend": "insufficient_data",
            "overall": "Need more data for trend analysis"
        }
    
    expenses = [m['expense'] for m in monthly_totals]
    savings_rates = [m['savings_rate'] for m in monthly_totals]
    
    # Simple linear regression for trend
    n = len(expenses)
    x_mean = (n - 1) / 2  # 0, 1, 2, ... n-1
    
    # Expense trend
    expense_mean = sum(expenses) / n
    expense_slope = sum((i - x_mean) * (e - expense_mean) for i, e in enumerate(expenses))
    expense_slope /= sum((i - x_mean) ** 2 for i in range(n)) or 1
    
    # Savings rate trend
    savings_mean = sum(savings_rates) / n
    savings_slope = sum((i - x_mean) * (s - savings_mean) for i, s in enumerate(savings_rates))
    savings_slope /= sum((i - x_mean) ** 2 for i in range(n)) or 1
    
    # Determine trend direction
    expense_trend = (
        "increasing" if expense_slope > expense_mean * 0.05 else
        "decreasing" if expense_slope < -expense_mean * 0.05 else
        "stable"
    )
    
    savings_trend = (
        "improving" if savings_slope > 2 else  # 2% improvement per month
        "declining" if savings_slope < -2 else
        "stable"
    )
    
    # Overall assessment
    if expense_trend == "decreasing" and savings_trend == "improving":
        overall = "🎉 Excellent progress! Expenses down, savings up!"
    elif expense_trend == "increasing" and savings_trend == "declining":
        overall = "⚠️ Watch out! Expenses rising, savings declining."
    elif expense_trend == "stable" and savings_trend == "stable":
        overall = "📊 Stable financial patterns. Consider opportunities to save more."
    elif savings_trend == "improving":
        overall = "✅ Good job! Your savings rate is improving."
    elif expense_trend == "increasing":
        overall = "💡 Expenses are rising. Review discretionary spending."
    else:
        overall = "📊 Your finances are relatively stable."
    
    return {
        "expense_trend": expense_trend,
        "expense_change_per_month": round(expense_slope, 2),
        "savings_trend": savings_trend,
        "savings_rate_change_per_month": round(savings_slope, 2),
        "overall": overall
    }


def analyze_day_of_week_patterns(categories: Dict) -> Dict[str, Any]:
    """Analyze spending patterns by day of week"""
    
    day_spending = defaultdict(lambda: {"count": 0, "total": 0})
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    for cat_name, transactions in categories.items():
        for txn in transactions:
            date_str = txn.get('date', '')
            amount = txn.get('debit', 0)
            
            if date_str and amount > 0:
                try:
                    # Try multiple date formats
                    for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
                        try:
                            date_obj = datetime.strptime(date_str, fmt)
                            day_idx = date_obj.weekday()
                            day_spending[day_idx]["count"] += 1
                            day_spending[day_idx]["total"] += amount
                            break
                        except ValueError:
                            continue
                except:
                    pass
    
    # Format results
    patterns = []
    for day_idx in range(7):
        data = day_spending[day_idx]
        avg = data["total"] / data["count"] if data["count"] > 0 else 0
        patterns.append({
            "day": day_names[day_idx],
            "transactions": data["count"],
            "total_spending": round(data["total"], 2),
            "average_per_transaction": round(avg, 2)
        })
    
    # Find highest spending day
    max_day = max(patterns, key=lambda x: x["total_spending"]) if patterns else None
    min_day = min(patterns, key=lambda x: x["total_spending"]) if patterns else None
    
    return {
        "daily_breakdown": patterns,
        "highest_spending_day": max_day["day"] if max_day else None,
        "lowest_spending_day": min_day["day"] if min_day else None,
        "insight": f"You tend to spend most on {max_day['day']}s" if max_day else None
    }


def identify_spending_spikes(monthly_totals: List[Dict]) -> List[Dict]:
    """Identify unusual spending spikes"""
    
    if len(monthly_totals) < 2:
        return []
    
    expenses = [m['expense'] for m in monthly_totals]
    mean_expense = sum(expenses) / len(expenses)
    std_dev = (sum((e - mean_expense) ** 2 for e in expenses) / len(expenses)) ** 0.5
    
    threshold = mean_expense + (1.5 * std_dev)
    
    spikes = []
    for monthly in monthly_totals:
        if monthly['expense'] > threshold:
            spikes.append({
                "month": monthly["month"],
                "expense": monthly["expense"],
                "average": round(mean_expense, 2),
                "above_average_by": round(monthly['expense'] - mean_expense, 2),
                "percentage_above": round((monthly['expense'] - mean_expense) / mean_expense * 100, 1)
            })
    
    return spikes


def generate_trend_insights(
    monthly_totals: List[Dict],
    category_trends: Dict,
    trend_analysis: Dict
) -> List[str]:
    """Generate actionable insights from trend data"""
    
    insights = []
    
    # Overall trend insight
    if trend_analysis.get('expense_trend') == 'increasing':
        avg_increase = abs(trend_analysis.get('expense_change_per_month', 0))
        insights.append(f"📈 Your monthly expenses are increasing by ~₹{avg_increase:,.0f} per month")
    elif trend_analysis.get('expense_trend') == 'decreasing':
        avg_decrease = abs(trend_analysis.get('expense_change_per_month', 0))
        insights.append(f"📉 Great! Your expenses are decreasing by ~₹{avg_decrease:,.0f} per month")
    
    # Savings insight
    if trend_analysis.get('savings_trend') == 'improving':
        insights.append("💰 Your savings rate is improving - keep it up!")
    elif trend_analysis.get('savings_trend') == 'declining':
        insights.append("⚠️ Your savings rate is declining. Review recent spending changes.")
    
    # Highest spending month
    if monthly_totals:
        highest_month = max(monthly_totals, key=lambda x: x['expense'])
        lowest_month = min(monthly_totals, key=lambda x: x['expense'])
        
        if highest_month['expense'] > lowest_month['expense'] * 1.5:
            insights.append(
                f"📊 Highest spending was in {highest_month['month']} "
                f"(₹{highest_month['expense']:,.0f}), lowest in {lowest_month['month']} "
                f"(₹{lowest_month['expense']:,.0f})"
            )
    
    # Category-specific insights
    for category, trend_data in category_trends.items():
        if len(trend_data) >= 2:
            first_half = sum(t['expense'] for t in trend_data[:len(trend_data)//2])
            second_half = sum(t['expense'] for t in trend_data[len(trend_data)//2:])
            
            if second_half > first_half * 1.3 and second_half > 1000:
                insights.append(
                    f"🔺 {category} spending has increased significantly recently"
                )
    
    # Savings opportunity
    if monthly_totals:
        avg_savings_rate = sum(m['savings_rate'] for m in monthly_totals) / len(monthly_totals)
        if avg_savings_rate < 20:
            target = 20 - avg_savings_rate
            insights.append(
                f"💡 Tip: Increase your savings rate by {target:.0f}% to reach the "
                f"recommended 20% savings benchmark"
            )
    
    return insights


def get_comparison_analysis(file_path: str = "categorized_transactions.json") -> Dict[str, Any]:
    """Compare current month with previous months"""
    
    trends = analyze_spending_trends(file_path)
    
    if "error" in trends:
        return trends
    
    monthly_totals = trends.get('monthly_trends', [])
    
    if len(monthly_totals) < 2:
        return {"message": "Need at least 2 months of data for comparison"}
    
    current = monthly_totals[-1]
    previous = monthly_totals[-2]
    
    expense_change = current['expense'] - previous['expense']
    expense_change_pct = (expense_change / previous['expense'] * 100) if previous['expense'] > 0 else 0
    
    savings_change = current['savings_rate'] - previous['savings_rate']
    
    return {
        "current_month": current['month'],
        "previous_month": previous['month'],
        "expense_comparison": {
            "current": current['expense'],
            "previous": previous['expense'],
            "change": expense_change,
            "change_percentage": round(expense_change_pct, 1),
            "trend": "increased" if expense_change > 0 else "decreased" if expense_change < 0 else "unchanged"
        },
        "savings_comparison": {
            "current_rate": current['savings_rate'],
            "previous_rate": previous['savings_rate'],
            "change": round(savings_change, 1),
            "trend": "improved" if savings_change > 0 else "declined" if savings_change < 0 else "unchanged"
        },
        "summary": generate_comparison_summary(expense_change, savings_change)
    }


def generate_comparison_summary(expense_change: float, savings_change: float) -> str:
    """Generate human-readable comparison summary"""
    
    if expense_change < 0 and savings_change > 0:
        return "🎉 Excellent month! Lower expenses and better savings!"
    elif expense_change > 0 and savings_change < 0:
        return "⚠️ Expenses up, savings down. Review your spending."
    elif expense_change < 0:
        return "✅ Good job reducing expenses!"
    elif savings_change > 0:
        return "💰 Great improvement in savings rate!"
    else:
        return "📊 Similar to last month. Look for savings opportunities."
