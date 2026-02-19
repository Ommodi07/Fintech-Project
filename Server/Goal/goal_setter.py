from Analytics import analytic
goal = []
def set_goal(data):
    required_monthly_saving = data.target_amount / data.time_horizon_months
    dataobj = analytic.main_analytic("categorized_transactions.json")
    current_savings = dataobj.get('savings')
    if required_monthly_saving < current_savings:
        return {"Decision" : "✅ Achievable", "Monthly Saving Required" : required_monthly_saving}
        goal.append({
            "Name" : data.goal_name,
            "Monthly Saving Required" : required_monthly_saving, 
            "tenure" : data.time_horizon_months, 
            "Money invested" : 0, 
            "Money investment pending" : data.target_amount
        })
    elif required_monthly_saving < (current_savings+1000):
        return {"Decision" : "⚠️ Needs spending reduction", "Monthly Saving Required" : required_monthly_saving}
        goal.append({
            "Name" : data.goal_name,
            "Monthly Saving Required" : required_monthly_saving, 
            "tenure" : data.time_horizon_months, 
            "Money invested" : 0, 
            "Money investment pending" : data.target_amount
        })
    else:
        return {"Decision" : "❌ Not Achievable", "Monthly Saving Required" : required_monthly_saving}