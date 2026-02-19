import json
from Analytics import analytic
import os

def standard_deviation(file_path):
    sd = 0
    mean = 0
    n = 0
    food = 0
    entertainment = 0
    
    if not os.path.exists(file_path):
        return 0, 0, 0 # Return safe defaults if file missing

    with open(file_path, "r") as f:
        data = json.load(f)
        
        # Calculate mean
        category = data.get('categories', {})
        for obj in category:
            entries = category[obj]
            for entry in entries:
                if entry.get('debit', 0) != 0:
                    n += 1
                    mean += entry['debit']
        
        if n > 0:
            mean = mean/n
        
        # Calculate standard deviation
        for obj in category:
            entries = category[obj]
            for entry in entries:
                if entry.get('debit', 0) != 0:
                    sd += (entry['debit'] - mean)**2
        
        if n > 0:
            sd = (sd/n)**0.5
            
        # Extract food and entertainment expenses
        summary = data.get('summary', {})
        for summ in summary:
            if summ == "Food & Dining":
                food = summary[summ].get('total_debit', 0)
            elif summ == "Entertainment":
                entertainment = summary[summ].get('total_debit', 0)
                
    return sd, food, entertainment

def health_score_main(file_path="categorized_transactions.json"):
    # Get basic analytics data
    dataobj = analytic.main_analytic(file_path)
    
    # Check if analytic returned an error string or valid dict
    if isinstance(dataobj, str):
        return {"error": dataobj} # Return error if file not found or other issue
        
    try:
        total_expense = dataobj.get("total_expense", 0)
        total_income = dataobj.get('total_income', 0)
        savings = dataobj.get('savings', 0)
        
        # Get standard deviation and specific category expenses
        volatility, food, entertainment = standard_deviation(file_path)
        
        # Avoid division by zero
        saving_rate = (savings/total_income) if total_income > 0 else 0
        discretionary_ratio = ((food + entertainment) / total_expense) if total_expense > 0 else 0
        
        score = 0.4*saving_rate + 0.3*volatility + 0.3*discretionary_ratio
        return round(score, 2)
    except Exception as e:
        return {"error": f"Calculation error: {str(e)}"}
