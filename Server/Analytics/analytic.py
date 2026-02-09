import json
import os 

def main_analytic(file_path : str):
    if not os.path.exists(file_path):
        return "File not found"

    with open(file_path, "r") as f:
        data = json.load(f)

        summary = data['summary']
        total_expense = 0
        total_income = 0
        max_spending_category = "Miscellaneous"
        savings = 0

        for category in summary:
            total_expense += summary[category]['total_debit']
            total_income += summary[category]['total_credit']
            if summary[category]['total_debit'] > summary[max_spending_category]['total_debit']:
                max_spending_category = category
        
        savings = (total_income - total_expense) if (total_income - total_expense)>0 else 0

        dataobj =  {
            "total_expense": total_expense,
            "total_income": total_income,
            "savings": savings,
            "max_spending_category": max_spending_category
        }
        return dataobj