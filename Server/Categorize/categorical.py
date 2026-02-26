import json
import re
from datetime import datetime
from collections import defaultdict

class TransactionCategorizer:
    def __init__(self):
        # Define category keywords and patterns
        self.categories = {
            'Food & Dining': [
                'vadapav', 'restaurant', 'food', 'hotel', 'cafe', 'dhosa', 
                'chicken', 'chulha', 'dining', 'meal', 'kitchen', 'canteen'
            ],
            'Transportation': [
                'petroleum', 'petrol', 'fuel', 'cab', 'taxi', 'auto', 'uber', 
                'ola', 'bus', 'train', 'irctc', 'railway', 'travel', 'fare'
            ],
            'Medical & Healthcare': [
                'medical', 'medicines', 'pharmacy', 'hospital', 'clinic', 
                'doctor', 'health', 'medicine'
            ],
            'Utilities': [
                'light bill', 'electricity', 'water bill', 'gas bill', 
                'utility', 'bill payment', 'recharge'
            ],
            'Entertainment': [
                'movie', 'cinema', 'ticket', 'entertainment', 'game', 
                'kingsman', 'paragliding', 'sports', 'fun'
            ],
            'Shopping': [
                'store', 'shop', 'market', 'mall', 'amazon', 'flipkart', 
                'shopping', 'purchase', 'notebook'
            ],
            # 'Digital Services': [
            #     'google', 'upi', 'digital', 'online', 'app', 'software', 
            #     'subscription', 'internet'
            # ],
            'Income': [
                'salary', 'interest', 'int.pd', 'credit', 'refund', 'cashback'
            ],
            'Miscellaneous': []
        }
    
    def categorize_transaction(self, transaction):
        """Categorize a single transaction based on its details"""
        # Handle both old and new field names for backward compatibility
        description_field = transaction.get('description') or transaction.get('transaction_details', '')
        transaction_text = str(description_field).lower()
        
        # Check if it's income (credit > 0)
        if transaction.get('credit', 0) > 0:
            if 'int.pd' in transaction_text or 'interest' in transaction_text or 'salary' in transaction_text:
                return 'Income'
        
        # Check against category keywords
        for category, keywords in self.categories.items():
            if category == 'Miscellaneous':
                continue
            
            for keyword in keywords:
                if keyword.lower() in transaction_text:
                    return category
        
        # Default to miscellaneous if no match found
        return 'Miscellaneous'
    
    def analyze_transactions(self, json_file_path):
        """Load and categorize all transactions from JSON file"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Handle both old format (direct list) and new format (with metadata)
            if isinstance(data, dict) and 'transactions' in data:
                print(f"Processing {data.get('metadata', {}).get('transaction_count', 'unknown')} transactions")
                print(f"Source: {data.get('metadata', {}).get('source_file', 'unknown')} (Method: {data.get('metadata', {}).get('parsing_method', 'unknown')})")
                transactions = data['transactions']
            elif isinstance(data, list):
                transactions = data
            else:
                print(f"Error: Unexpected data format in {json_file_path}")
                return None
            
            categorized_data = {
                'categories': defaultdict(list),
                'summary': defaultdict(lambda: {'count': 0, 'total_debit': 0, 'total_credit': 0}),
                'monthly_breakdown': defaultdict(lambda: defaultdict(lambda: {'count': 0, 'total_debit': 0, 'total_credit': 0}))
            }
            
            for transaction in transactions:
                category = self.categorize_transaction(transaction)
                
                # Add transaction to category
                transaction_with_category = transaction.copy()
                transaction_with_category['category'] = category
                categorized_data['categories'][category].append(transaction_with_category)
                
                # Update summary statistics
                debit_amount = transaction.get('debit', 0)
                credit_amount = transaction.get('credit', 0)
                
                # Ensure amounts are numbers
                try:
                    debit_amount = float(debit_amount) if debit_amount else 0
                    credit_amount = float(credit_amount) if credit_amount else 0
                except (ValueError, TypeError):
                    debit_amount = 0
                    credit_amount = 0
                
                categorized_data['summary'][category]['count'] += 1
                categorized_data['summary'][category]['total_debit'] += debit_amount
                categorized_data['summary'][category]['total_credit'] += credit_amount
                
                # Monthly breakdown
                date_str = transaction.get('date', '')
                if date_str:
                    try:
                        # Handle different date formats
                        date_formats = ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']
                        date_obj = None
                        
                        for fmt in date_formats:
                            try:
                                date_obj = datetime.strptime(date_str, fmt)
                                break
                            except ValueError:
                                continue
                        
                        if date_obj:
                            month_year = date_obj.strftime('%Y-%m')
                            categorized_data['monthly_breakdown'][month_year][category]['count'] += 1
                            categorized_data['monthly_breakdown'][month_year][category]['total_debit'] += debit_amount
                            categorized_data['monthly_breakdown'][month_year][category]['total_credit'] += credit_amount
                        
                    except Exception as e:
                        print(f"Date parsing error for '{date_str}': {e}")
                        pass  # Skip if date format is invalid
                    except ValueError:
                        pass  # Skip if date format is invalid
            
            return categorized_data
            
        except FileNotFoundError:
            print(f"Error: File {json_file_path} not found.")
            return None
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in {json_file_path}")
            return None
    
    def print_summary(self, categorized_data):
        """Print a formatted summary of categorized transactions"""
        if not categorized_data:
            return
        
        print("\n" + "="*60)
        print("SPENDING ANALYSIS SUMMARY")
        print("="*60)
        
        summary = categorized_data['summary']
        total_debit = sum(cat['total_debit'] for cat in summary.values())
        total_credit = sum(cat['total_credit'] for cat in summary.values())
        
        print(f"\nOverall Totals:")
        print(f"Total Spent (Debit): ₹{total_debit:.2f}")
        print(f"Total Received (Credit): ₹{total_credit:.2f}")
        print(f"Net Change: ₹{total_credit - total_debit:.2f}")
        
        print(f"\nCategory Breakdown:")
        print("-" * 60)
        
        # Sort categories by spending amount
        sorted_categories = sorted(summary.items(), key=lambda x: x[1]['total_debit'], reverse=True)
        
        for category, data in sorted_categories:
            if data['count'] > 0:
                percentage = (data['total_debit'] / total_debit * 100) if total_debit > 0 else 0
                print(f"{category:<20} | Transactions: {data['count']:>3} | "
                      f"Spent: ₹{data['total_debit']:>8.2f} ({percentage:>5.1f}%) | "
                      f"Received: ₹{data['total_credit']:>7.2f}")
    
    def save_categorized_data(self, categorized_data, output_file):
        """Save categorized data to a JSON file"""
        if not categorized_data:
            return
        
        # Convert defaultdict to regular dict for JSON serialization
        output_data = {
            'categories': dict(categorized_data['categories']),
            'summary': dict(categorized_data['summary']),
            'monthly_breakdown': dict(categorized_data['monthly_breakdown'])
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as file:
                json.dump(output_data, file, indent=2, ensure_ascii=False)
            print(f"\nCategorized data saved to: {output_file}")
        except Exception as e:
            print(f"Error saving file: {e}")

def main_categorizer(json_path):
    """Main function to run the categorization analysis"""
    categorizer = TransactionCategorizer()
    
    # Analyze transactions from output.json
    input_file = json_path
    output_file = 'categorized_transactions.json'
    
    print("Starting transaction categorization analysis...")
    
    categorized_data = categorizer.analyze_transactions(input_file)
    
    if categorized_data:
        # Print summary to console
        categorizer.print_summary(categorized_data)
        
        # Save detailed categorized data
        categorizer.save_categorized_data(categorized_data, output_file)
        
        # Print some sample transactions per category
        print(f"\nSample Transactions by Category:")
        print("-" * 60)
        
        for category, transactions in categorized_data['categories'].items():
            if transactions:
                print(f"\n{category} (showing first 3 transactions):")
                for i, transaction in enumerate(transactions[:3]):
                    amount = f"₹{transaction.get('debit', 0):.2f}" if transaction.get('debit', 0) > 0 else f"+₹{transaction.get('credit', 0):.2f}"
                    # Handle both old and new field names
                    description = transaction.get('description') or transaction.get('transaction_details', 'N/A')
                    print(f"  {transaction.get('date', 'N/A')} - {str(description)[:50]}... - {amount}")
        
        return output_file
    
    else:
        print("Failed to analyze transactions. Please check the input file.")
        return None