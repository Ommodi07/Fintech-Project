import json
from Analytics import analytic
import os
from typing import Dict, List, Any, Tuple
from datetime import datetime
from collections import defaultdict

def get_detailed_metrics(file_path: str) -> Dict[str, Any]:
    """Extract comprehensive financial metrics from transaction data"""
    metrics = {
        "spending_volatility": 0,
        "discretionary_spending": 0,
        "essential_spending": 0,
        "recurring_expenses": 0,
        "total_transactions": 0,
        "avg_transaction_size": 0,
        "monthly_spending_trend": [],
        "category_breakdown": {}
    }
    
    if not os.path.exists(file_path):
        return metrics

    with open(file_path, "r") as f:
        data = json.load(f)
        
    categories = data.get('categories', {})
    summary = data.get('summary', {})
    monthly_breakdown = data.get('monthly_breakdown', {})
    
    # Categorize spending types
    essential_categories = ['Utilities', 'Medical & Healthcare', 'Transportation']
    discretionary_categories = ['Food & Dining', 'Entertainment', 'Shopping']
    
    all_debits = []
    
    for cat_name, transactions in categories.items():
        cat_total = 0
        for txn in transactions:
            debit = txn.get('debit', 0)
            if debit > 0:
                all_debits.append(debit)
                cat_total += debit
        
        if cat_name in essential_categories:
            metrics["essential_spending"] += cat_total
        elif cat_name in discretionary_categories:
            metrics["discretionary_spending"] += cat_total
            
        metrics["category_breakdown"][cat_name] = cat_total
    
    metrics["total_transactions"] = len(all_debits)
    
    # Calculate spending volatility (coefficient of variation)
    if all_debits:
        mean = sum(all_debits) / len(all_debits)
        variance = sum((x - mean) ** 2 for x in all_debits) / len(all_debits)
        std_dev = variance ** 0.5
        metrics["spending_volatility"] = (std_dev / mean) if mean > 0 else 0
        metrics["avg_transaction_size"] = mean
    
    # Monthly spending trend
    for month, cats in sorted(monthly_breakdown.items()):
        month_total = sum(cat_data.get('total_debit', 0) for cat_data in cats.values())
        metrics["monthly_spending_trend"].append({
            "month": month,
            "total": month_total
        })
    
    return metrics

def detect_anomalies(file_path: str) -> List[Dict[str, Any]]:
    """Detect unusual spending patterns or anomalies"""
    anomalies = []
    
    if not os.path.exists(file_path):
        return anomalies

    with open(file_path, "r") as f:
        data = json.load(f)
    
    categories = data.get('categories', {})
    
    for cat_name, transactions in categories.items():
        debits = [txn.get('debit', 0) for txn in transactions if txn.get('debit', 0) > 0]
        
        if len(debits) >= 3:
            mean = sum(debits) / len(debits)
            std_dev = (sum((x - mean) ** 2 for x in debits) / len(debits)) ** 0.5
            threshold = mean + (2 * std_dev)
            
            for txn in transactions:
                if txn.get('debit', 0) > threshold:
                    anomalies.append({
                        "type": "unusual_spending",
                        "category": cat_name,
                        "amount": txn.get('debit'),
                        "description": txn.get('description', txn.get('transaction_details', '')),
                        "date": txn.get('date', ''),
                        "threshold": round(threshold, 2),
                        "severity": "high" if txn.get('debit', 0) > mean + (3 * std_dev) else "medium"
                    })
    
    return anomalies

def detect_recurring_expenses(file_path: str) -> List[Dict[str, Any]]:
    """Detect recurring expenses like subscriptions, EMIs, rent"""
    recurring = []
    
    if not os.path.exists(file_path):
        return recurring

    with open(file_path, "r") as f:
        data = json.load(f)
    
    categories = data.get('categories', {})
    
    # Group transactions by similar amounts and descriptions
    amount_groups = defaultdict(list)
    
    for cat_name, transactions in categories.items():
        for txn in transactions:
            debit = txn.get('debit', 0)
            if debit > 0:
                # Round to nearest 10 for grouping similar amounts
                rounded_amount = round(debit / 10) * 10
                amount_groups[rounded_amount].append({
                    "amount": debit,
                    "description": txn.get('description', txn.get('transaction_details', '')),
                    "date": txn.get('date', ''),
                    "category": cat_name
                })
    
    # Identify recurring patterns (2+ similar transactions)
    recurring_keywords = ['emi', 'subscription', 'rent', 'insurance', 'loan', 'netflix', 
                         'spotify', 'amazon prime', 'premium', 'monthly', 'recurring']
    
    for amount, txns in amount_groups.items():
        if len(txns) >= 2:
            # Check if descriptions contain recurring keywords
            desc_lower = ' '.join(t['description'].lower() for t in txns)
            is_recurring = any(kw in desc_lower for kw in recurring_keywords) or len(txns) >= 3
            
            if is_recurring:
                recurring.append({
                    "type": "recurring_expense",
                    "estimated_amount": round(sum(t['amount'] for t in txns) / len(txns), 2),
                    "frequency": "monthly" if len(txns) <= 3 else "frequent",
                    "occurrences": len(txns),
                    "sample_description": txns[0]['description'],
                    "category": txns[0]['category']
                })
    
    return recurring

def calculate_component_scores(dataobj: Dict, metrics: Dict) -> Dict[str, float]:
    """Calculate individual component scores for financial health"""
    scores = {}
    
    total_income = dataobj.get('total_income', 0)
    total_expense = dataobj.get('total_expense', 0)
    savings = dataobj.get('savings', 0)
    
    # 1. Savings Score (0-100): Higher savings rate = better
    if total_income > 0:
        savings_rate = savings / total_income
        scores['savings'] = min(100, savings_rate * 200)  # 50% savings rate = 100
    else:
        scores['savings'] = 0
    
    # 2. Spending Discipline Score (0-100): Lower volatility = better
    volatility = metrics.get('spending_volatility', 1)
    scores['spending_discipline'] = max(0, 100 - (volatility * 50))
    
    # 3. Essential vs Discretionary Score (0-100): Higher essential ratio = better
    essential = metrics.get('essential_spending', 0)
    discretionary = metrics.get('discretionary_spending', 0)
    if total_expense > 0:
        essential_ratio = essential / total_expense
        # Ideal: 60-70% essential spending
        scores['expense_balance'] = 100 - abs(0.65 - essential_ratio) * 100
        scores['expense_balance'] = max(0, min(100, scores['expense_balance']))
    else:
        scores['expense_balance'] = 50
    
    # 4. Cash Flow Score (0-100): Positive cash flow = better
    if total_income > 0:
        cash_flow_ratio = (total_income - total_expense) / total_income
        scores['cash_flow'] = min(100, max(0, (cash_flow_ratio + 0.5) * 100))
    else:
        scores['cash_flow'] = 0
    
    return scores

def generate_improvement_tips(scores: Dict, metrics: Dict, anomalies: List) -> List[str]:
    """Generate personalized improvement tips based on scores"""
    tips = []
    
    if scores.get('savings', 0) < 50:
        tips.append("💡 Try to save at least 20% of your income. Consider automating savings transfers.")
    
    if scores.get('spending_discipline', 0) < 60:
        tips.append("💡 Your spending varies significantly. Create a budget to maintain consistency.")
    
    if scores.get('expense_balance', 0) < 50:
        discretionary = metrics.get('discretionary_spending', 0)
        if discretionary > 0:
            tips.append(f"💡 Consider reducing discretionary spending (currently ₹{discretionary:.2f}).")
    
    if scores.get('cash_flow', 0) < 40:
        tips.append("💡 Your expenses are close to or exceeding income. Review and cut non-essential costs.")
    
    if len(anomalies) > 0:
        tips.append(f"⚠️ {len(anomalies)} unusual transactions detected. Review for potential issues.")
    
    if not tips:
        tips.append("✅ Great financial health! Keep maintaining your current habits.")
    
    return tips

def health_score_main(file_path: str = "categorized_transactions.json") -> Dict[str, Any]:
    """
    Calculate comprehensive financial health score (0-100)
    
    Components:
    - Savings Rate (30%): Higher savings = better
    - Spending Discipline (25%): Lower volatility = better  
    - Expense Balance (20%): Essential vs discretionary ratio
    - Cash Flow (25%): Income - Expense ratio
    """
    # Get basic analytics data
    dataobj = analytic.main_analytic(file_path)
    
    if isinstance(dataobj, str):
        return {"error": dataobj}
        
    try:
        # Get detailed metrics
        metrics = get_detailed_metrics(file_path)
        
        # Detect anomalies
        anomalies = detect_anomalies(file_path)
        
        # Detect recurring expenses
        recurring = detect_recurring_expenses(file_path)
        
        # Calculate component scores
        component_scores = calculate_component_scores(dataobj, metrics)
        
        # Calculate weighted overall score
        weights = {
            'savings': 0.30,
            'spending_discipline': 0.25,
            'expense_balance': 0.20,
            'cash_flow': 0.25
        }
        
        overall_score = sum(
            component_scores.get(component, 0) * weight 
            for component, weight in weights.items()
        )
        
        # Generate improvement tips
        tips = generate_improvement_tips(component_scores, metrics, anomalies)
        
        # Determine health grade
        if overall_score >= 80:
            grade = "Excellent"
            grade_emoji = "🏆"
        elif overall_score >= 60:
            grade = "Good"
            grade_emoji = "✅"
        elif overall_score >= 40:
            grade = "Fair"
            grade_emoji = "⚠️"
        else:
            grade = "Needs Improvement"
            grade_emoji = "🔴"
        
        return {
            "overall_score": round(overall_score, 1),
            "grade": f"{grade_emoji} {grade}",
            "component_scores": {k: round(v, 1) for k, v in component_scores.items()},
            "metrics": {
                "total_income": dataobj.get('total_income', 0),
                "total_expense": dataobj.get('total_expense', 0),
                "savings": dataobj.get('savings', 0),
                "savings_rate": round(dataobj.get('savings', 0) / max(dataobj.get('total_income', 1), 1) * 100, 1),
                "avg_transaction": round(metrics.get('avg_transaction_size', 0), 2),
                "transaction_count": metrics.get('total_transactions', 0)
            },
            "anomalies": anomalies[:5],  # Top 5 anomalies
            "recurring_expenses": recurring,
            "improvement_tips": tips,
            "category_breakdown": metrics.get('category_breakdown', {})
        }
        
    except Exception as e:
        return {"error": f"Calculation error: {str(e)}"}
