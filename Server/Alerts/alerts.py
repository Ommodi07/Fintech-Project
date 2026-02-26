"""
Alerts & Notifications Module
Purpose: Proactive financial guidance through smart alerts and nudges
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Alert severity levels
SEVERITY = {
    "critical": 1,
    "warning": 2,
    "info": 3
}

class AlertEngine:
    """Engine for generating financial alerts and notifications"""
    
    def __init__(self, transaction_file: str = "categorized_transactions.json"):
        self.transaction_file = transaction_file
        self.alerts: List[Dict] = []
    
    def load_transactions(self) -> Optional[Dict]:
        """Load transaction data from file"""
        if not os.path.exists(self.transaction_file):
            return None
        
        with open(self.transaction_file, "r") as f:
            return json.load(f)
    
    def generate_all_alerts(self) -> List[Dict]:
        """Generate all types of alerts"""
        self.alerts = []
        
        data = self.load_transactions()
        if not data:
            return []
        
        # Run all alert checks
        self._check_overspending(data)
        self._check_unusual_transactions(data)
        self._check_subscription_renewals(data)
        self._check_low_balance_trend(data)
        self._check_category_budget_breach(data)
        self._check_recurring_payment_changes(data)
        
        # Sort by severity
        self.alerts.sort(key=lambda x: SEVERITY.get(x.get('severity', 'info'), 3))
        
        return self.alerts
    
    def _add_alert(self, alert_type: str, title: str, message: str, 
                   severity: str = "info", data: Dict = None, 
                   action_required: bool = False):
        """Add an alert to the list"""
        self.alerts.append({
            "id": f"{alert_type}_{len(self.alerts)}",
            "type": alert_type,
            "title": title,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "data": data or {},
            "action_required": action_required,
            "read": False
        })
    
    def _check_overspending(self, data: Dict):
        """Check for overspending alerts"""
        summary = data.get('summary', {})
        
        total_income = sum(cat.get('total_credit', 0) for cat in summary.values())
        total_expense = sum(cat.get('total_debit', 0) for cat in summary.values())
        
        # Alert if spending exceeds income
        if total_expense > total_income:
            self._add_alert(
                alert_type="overspending",
                title="⚠️ Spending Exceeds Income",
                message=f"You've spent ₹{total_expense - total_income:,.2f} more than your income this period.",
                severity="critical",
                data={
                    "income": total_income,
                    "expense": total_expense,
                    "difference": total_expense - total_income
                },
                action_required=True
            )
        
        # Alert if spending is 90%+ of income
        elif total_income > 0 and (total_expense / total_income) >= 0.9:
            self._add_alert(
                alert_type="high_spending",
                title="⚠️ High Spending Alert",
                message=f"You're spending {(total_expense/total_income)*100:.1f}% of your income. Consider cutting back.",
                severity="warning",
                data={
                    "spending_percentage": round((total_expense/total_income)*100, 1)
                }
            )
    
    def _check_unusual_transactions(self, data: Dict):
        """Check for unusual/anomalous transactions"""
        categories = data.get('categories', {})
        
        for cat_name, transactions in categories.items():
            debits = [t.get('debit', 0) for t in transactions if t.get('debit', 0) > 0]
            
            if len(debits) >= 3:
                mean = sum(debits) / len(debits)
                std_dev = (sum((x - mean) ** 2 for x in debits) / len(debits)) ** 0.5
                threshold = mean + (2 * std_dev)
                
                for txn in transactions:
                    if txn.get('debit', 0) > threshold:
                        self._add_alert(
                            alert_type="unusual_transaction",
                            title="🔍 Unusual Transaction Detected",
                            message=f"Large {cat_name} expense: ₹{txn.get('debit'):,.2f}",
                            severity="warning",
                            data={
                                "category": cat_name,
                                "amount": txn.get('debit'),
                                "description": txn.get('description', txn.get('transaction_details', '')),
                                "average": round(mean, 2)
                            }
                        )
    
    def _check_subscription_renewals(self, data: Dict):
        """Detect and alert about subscription payments"""
        categories = data.get('categories', {})
        
        subscription_keywords = [
            'netflix', 'spotify', 'prime', 'hotstar', 'youtube', 'zee5',
            'apple', 'google', 'microsoft', 'adobe', 'subscription',
            'premium', 'membership', 'renew', 'auto-debit'
        ]
        
        subscriptions_found = []
        
        for cat_name, transactions in categories.items():
            for txn in transactions:
                description = txn.get('description', txn.get('transaction_details', '')).lower()
                
                for keyword in subscription_keywords:
                    if keyword in description:
                        subscriptions_found.append({
                            "name": description[:50],
                            "amount": txn.get('debit', 0),
                            "date": txn.get('date', ''),
                            "category": cat_name
                        })
                        break
        
        if subscriptions_found:
            total_subscriptions = sum(s['amount'] for s in subscriptions_found)
            self._add_alert(
                alert_type="subscription_summary",
                title="📱 Subscription Tracker",
                message=f"Found {len(subscriptions_found)} subscription(s) totaling ₹{total_subscriptions:,.2f}",
                severity="info",
                data={
                    "subscriptions": subscriptions_found,
                    "total": total_subscriptions
                }
            )
    
    def _check_low_balance_trend(self, data: Dict):
        """Check if balance trend is declining"""
        categories = data.get('categories', {})
        
        # Extract all transactions with balance
        all_txns = []
        for transactions in categories.values():
            for txn in transactions:
                if txn.get('balance') and txn.get('date'):
                    all_txns.append(txn)
        
        # Sort by date
        all_txns.sort(key=lambda x: x.get('date', ''))
        
        if len(all_txns) >= 5:
            # Compare first half vs second half average balance
            mid = len(all_txns) // 2
            first_half_avg = sum(t.get('balance', 0) for t in all_txns[:mid]) / mid
            second_half_avg = sum(t.get('balance', 0) for t in all_txns[mid:]) / (len(all_txns) - mid)
            
            if second_half_avg < first_half_avg * 0.8:  # 20% decline
                self._add_alert(
                    alert_type="balance_decline",
                    title="📉 Balance Declining",
                    message=f"Your account balance has declined by {((first_half_avg - second_half_avg)/first_half_avg)*100:.1f}%",
                    severity="warning",
                    data={
                        "earlier_avg": round(first_half_avg, 2),
                        "recent_avg": round(second_half_avg, 2)
                    },
                    action_required=True
                )
    
    def _check_category_budget_breach(self, data: Dict, budgets: Dict = None):
        """Check if spending exceeds budget in any category"""
        # Default budgets as percentage of income
        default_budget_pct = {
            "Food & Dining": 0.15,
            "Entertainment": 0.10,
            "Shopping": 0.15,
            "Transportation": 0.10
        }
        
        summary = data.get('summary', {})
        total_income = sum(cat.get('total_credit', 0) for cat in summary.values())
        
        for category, budget_pct in default_budget_pct.items():
            if category in summary:
                budget = total_income * budget_pct
                actual = summary[category].get('total_debit', 0)
                
                if actual > budget and budget > 0:
                    overspend_pct = ((actual - budget) / budget) * 100
                    self._add_alert(
                        alert_type="budget_breach",
                        title=f"💸 {category} Budget Exceeded",
                        message=f"Spent ₹{actual:,.2f} vs budget of ₹{budget:,.2f} ({overspend_pct:.1f}% over)",
                        severity="warning",
                        data={
                            "category": category,
                            "budget": round(budget, 2),
                            "actual": actual,
                            "overspend": round(actual - budget, 2)
                        }
                    )
    
    def _check_recurring_payment_changes(self, data: Dict):
        """Detect changes in recurring payment amounts"""
        categories = data.get('categories', {})
        
        # Group transactions by similar descriptions
        desc_groups = defaultdict(list)
        
        for transactions in categories.values():
            for txn in transactions:
                desc = txn.get('description', txn.get('transaction_details', ''))[:30].lower()
                if desc and txn.get('debit', 0) > 0:
                    desc_groups[desc].append(txn.get('debit'))
        
        # Check for amount changes in recurring payments
        for desc, amounts in desc_groups.items():
            if len(amounts) >= 2:
                amounts.sort()
                if len(set(amounts)) > 1:  # Different amounts
                    # Check if latest is higher
                    if amounts[-1] > amounts[0] * 1.1:  # 10% increase
                        self._add_alert(
                            alert_type="recurring_change",
                            title="📊 Recurring Payment Changed",
                            message=f"'{desc}' increased from ₹{amounts[0]:,.2f} to ₹{amounts[-1]:,.2f}",
                            severity="info",
                            data={
                                "description": desc,
                                "old_amount": amounts[0],
                                "new_amount": amounts[-1],
                                "increase_pct": round(((amounts[-1] - amounts[0]) / amounts[0]) * 100, 1)
                            }
                        )


def get_alerts(transaction_file: str = "categorized_transactions.json") -> Dict[str, Any]:
    """Get all alerts for the user"""
    engine = AlertEngine(transaction_file)
    alerts = engine.generate_all_alerts()
    
    return {
        "total_alerts": len(alerts),
        "critical": len([a for a in alerts if a['severity'] == 'critical']),
        "warnings": len([a for a in alerts if a['severity'] == 'warning']),
        "info": len([a for a in alerts if a['severity'] == 'info']),
        "action_required": len([a for a in alerts if a['action_required']]),
        "alerts": alerts
    }


def get_smart_nudges(transaction_file: str = "categorized_transactions.json") -> List[Dict]:
    """Generate smart nudges and tips based on spending patterns"""
    nudges = []
    
    if not os.path.exists(transaction_file):
        return nudges
    
    with open(transaction_file, "r") as f:
        data = json.load(f)
    
    summary = data.get('summary', {})
    
    total_income = sum(cat.get('total_credit', 0) for cat in summary.values())
    total_expense = sum(cat.get('total_debit', 0) for cat in summary.values())
    savings = total_income - total_expense
    
    # Saving rate nudges
    if total_income > 0:
        savings_rate = (savings / total_income) * 100
        
        if savings_rate < 10:
            nudges.append({
                "type": "savings",
                "message": "💡 Tip: Try the 50-30-20 rule - 50% needs, 30% wants, 20% savings",
                "priority": "high"
            })
        elif savings_rate >= 30:
            nudges.append({
                "type": "savings",
                "message": "🎉 Great job! You're saving over 30% of your income!",
                "priority": "low"
            })
    
    # Category-specific nudges
    food_expense = summary.get('Food & Dining', {}).get('total_debit', 0)
    if total_expense > 0 and (food_expense / total_expense) > 0.3:
        nudges.append({
            "type": "food",
            "message": "🍕 Food expenses are high. Consider meal planning or cooking at home.",
            "priority": "medium"
        })
    
    entertainment = summary.get('Entertainment', {}).get('total_debit', 0)
    if total_expense > 0 and (entertainment / total_expense) > 0.15:
        nudges.append({
            "type": "entertainment",
            "message": "🎬 Entertainment spending is elevated. Look for free alternatives.",
            "priority": "medium"
        })
    
    return nudges


def generate_bill_reminders(transaction_file: str = "categorized_transactions.json") -> List[Dict]:
    """Generate bill payment reminders based on historical patterns"""
    reminders = []
    
    if not os.path.exists(transaction_file):
        return reminders
    
    with open(transaction_file, "r") as f:
        data = json.load(f)
    
    categories = data.get('categories', {})
    
    # Keywords that indicate bills
    bill_keywords = [
        'electricity', 'water', 'gas', 'rent', 'emi', 'loan',
        'insurance', 'internet', 'broadband', 'mobile', 'dth'
    ]
    
    bills_detected = []
    
    for transactions in categories.values():
        for txn in transactions:
            desc = txn.get('description', txn.get('transaction_details', '')).lower()
            date = txn.get('date', '')
            amount = txn.get('debit', 0)
            
            for keyword in bill_keywords:
                if keyword in desc and amount > 0:
                    bills_detected.append({
                        "type": keyword,
                        "description": desc[:50],
                        "amount": amount,
                        "last_paid": date
                    })
                    break
    
    # Generate reminders for each detected bill type
    today = datetime.now()
    for bill in bills_detected:
        reminders.append({
            "type": "bill_reminder",
            "title": f"💳 {bill['type'].title()} Bill Due",
            "message": f"Expected amount: ₹{bill['amount']:,.2f}",
            "expected_date": (today + timedelta(days=30)).strftime("%Y-%m-%d"),
            "last_amount": bill['amount']
        })
    
    return reminders
