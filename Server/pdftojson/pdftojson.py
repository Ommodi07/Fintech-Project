from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import os
try:
    import google.genai as genai
    GENAI_AVAILABLE = True
except ImportError:
    try:
        import google.generativeai as genai
        GENAI_AVAILABLE = True
    except ImportError:
        print("Warning: Google AI package not available. AI parsing will be disabled.")
        genai = None
        GENAI_AVAILABLE = False
import dotenv
import json
import re
from typing import Dict, List, Optional

# Import utility classes - simplified approach
UTILS_AVAILABLE = True
try:
    from . import fallback_parser
    from . import bank_config_manager
    FallbackParser = fallback_parser.FallbackParser
    BankConfigManager = bank_config_manager.BankConfigManager
except ImportError:
    try:
        import fallback_parser
        import bank_config_manager  
        FallbackParser = fallback_parser.FallbackParser
        BankConfigManager = bank_config_manager.BankConfigManager
    except ImportError:
        print("Warning: Utility classes not available. Running with basic functionality.")
        FallbackParser = None
        BankConfigManager = None
        UTILS_AVAILABLE = False

dotenv.load_dotenv()

OUTPUT_TEXT_FILE = "output.txt"
IMAGE_FOLDER = "extracted_images"

# Bank configurations for different statement formats
BANK_CONFIGS = {
    'sbi': {
        'name': 'State Bank of India',
        'identifiers': ['state bank', 'sbi', 'sbiin'],
        'common_fields': {
            'date': ['date', 'txn date', 'transaction date', 'value date'],
            'description': ['description', 'particulars', 'transaction details', 'narration'],
            'reference': ['ref no', 'reference', 'cheq no', 'utr no', 'transaction id'],
            'debit': ['debit', 'dr', 'withdrawal', 'debit amount'],
            'credit': ['credit', 'cr', 'deposit', 'credit amount'],
            'balance': ['balance', 'running balance', 'available balance']
        }
    },
    'hdfc': {
        'name': 'HDFC Bank',
        'identifiers': ['hdfc', 'housing development'],
        'common_fields': {
            'date': ['date', 'transaction date', 'value date'],
            'description': ['description', 'narration', 'transaction remarks'],
            'reference': ['reference number', 'ref no', 'cheque number'],
            'debit': ['debit amount', 'withdrawal amt', 'debit'],
            'credit': ['credit amount', 'deposit amt', 'credit'],
            'balance': ['balance', 'closing balance']
        }
    },
    'icici': {
        'name': 'ICICI Bank',
        'identifiers': ['icici', 'industrial credit'],
        'common_fields': {
            'date': ['transaction date', 'date', 'value date'],
            'description': ['transaction remarks', 'description', 'particulars'],
            'reference': ['reference', 'serial number', 'transaction id'],
            'debit': ['debit', 'withdrawal', 'debit amount'],
            'credit': ['credit', 'deposit', 'credit amount'],
            'balance': ['balance', 'running balance']
        }
    },
    'axis': {
        'name': 'Axis Bank',
        'identifiers': ['axis', 'axis bank'],
        'common_fields': {
            'date': ['tran date', 'transaction date', 'date'],
            'description': ['particulars', 'description', 'transaction details'],
            'reference': ['reference', 'instrument', 'chq/ref number'],
            'debit': ['debit', 'dr amount', 'withdrawal'],
            'credit': ['credit', 'cr amount', 'deposit'],
            'balance': ['balance', 'running balance']
        }
    },
    'kotak': {
        'name': 'Kotak Mahindra Bank',
        'identifiers': ['kotak', 'mahindra'],
        'common_fields': {
            'date': ['transaction date', 'date', 'value date'],
            'description': ['description', 'transaction particulars', 'narration'],
            'reference': ['reference number', 'instrument number', 'reference'],
            'debit': ['debit amount', 'debit', 'withdrawal amount'],
            'credit': ['credit amount', 'credit', 'deposit amount'],
            'balance': ['balance amount', 'balance', 'closing balance']
        }
    },
    'generic': {
        'name': 'Generic Bank',
        'identifiers': [],
        'common_fields': {
            'date': ['date', 'transaction date', 'txn date'],
            'description': ['description', 'particulars', 'details', 'narration'],
            'reference': ['reference', 'ref', 'cheque', 'utr'],
            'debit': ['debit', 'withdrawal', 'dr'],
            'credit': ['credit', 'deposit', 'cr'],
            'balance': ['balance', 'closing balance', 'running balance']
        }
    }
}

def pdf_to_images(pdf_path, image_folder):
    os.makedirs(image_folder, exist_ok=True)
    pages = convert_from_path(pdf_path, dpi=300)
    
    image_paths = []
    for i, page in enumerate(pages):
        image_path = os.path.join(image_folder, f"page_{i+1}.png")
        page.save(image_path, "PNG")
        image_paths.append(image_path)
    
    return image_paths

def ocr_images(image_paths):
    full_text = []
    
    for img_path in image_paths:
        text = pytesseract.image_to_string(Image.open(img_path))
        full_text.append(f"\n--- Page {os.path.basename(img_path)} ---\n")
        full_text.append(text)
    
    return "\n".join(line.strip() for line in full_text if line.strip())


def detect_bank_type(text: str) -> str:
    """Detect bank type from the extracted text"""
    text_lower = text.lower()
    
    for bank_code, config in BANK_CONFIGS.items():
        if bank_code == 'generic':
            continue
        for identifier in config['identifiers']:
            if identifier.lower() in text_lower:
                return bank_code
    
    return 'generic'

def extract_table_structure(text: str) -> Dict:
    """Extract table headers and identify column structure"""
    lines = text.split('\n')
    potential_headers = []
    
    # Look for lines that might contain table headers
    for i, line in enumerate(lines):
        line_clean = line.strip().lower()
        # Common header indicators
        if any(word in line_clean for word in ['date', 'particulars', 'debit', 'credit', 'balance', 'description', 'reference']):
            if len(line_clean.split()) > 2:  # Likely a header row
                potential_headers.append({'line_number': i, 'content': line.strip(), 'words': line_clean.split()})
    
    return {'headers': potential_headers, 'total_lines': len(lines)}

def _truncate_text(text, max_chars=30000):
    """Truncate text to stay within Gemini token limits while preserving transaction data."""
    if len(text) <= max_chars:
        return text
    
    lines = text.split('\n')
    # Keep the first ~10 lines (account info/headers) and as many transaction lines as possible
    header_lines = lines[:10]
    remaining_lines = lines[10:]
    
    header_text = '\n'.join(header_lines)
    remaining_budget = max_chars - len(header_text) - 100  # buffer
    
    kept_lines = []
    current_len = 0
    for line in remaining_lines:
        if current_len + len(line) + 1 > remaining_budget:
            break
        kept_lines.append(line)
        current_len += len(line) + 1
    
    truncated = header_text + '\n' + '\n'.join(kept_lines)
    print(f"Text truncated from {len(text)} to {len(truncated)} chars ({len(header_lines) + len(kept_lines)}/{len(lines)} lines kept)")
    return truncated

def format_Data(text):
    if not GENAI_AVAILABLE or genai is None:
        print("Google AI not available. Skipping AI-based parsing.")
        return None
        
    GEMINI_API = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API:
        print("GEMINI_API_KEY not found in environment. Skipping AI-based parsing.")
        return None
        
    try:
        from google.genai import types
        client = genai.Client(api_key=GEMINI_API)
    except Exception as e:
        print(f"Failed to initialize AI client: {e}")
        return None
    
    # Detect bank type
    bank_type = detect_bank_type(text)
    bank_config = BANK_CONFIGS.get(bank_type, BANK_CONFIGS['generic'])
    
    # Extract table structure
    table_info = extract_table_structure(text)
    
    print(f"Detected bank type: {bank_config['name']}")
    print(f"Found {len(table_info['headers'])} potential header rows")
    
    # Truncate text to avoid oversized prompts that cause 504 timeouts
    truncated_text = _truncate_text(text)
    
    # Create dynamic prompt based on detected bank
    prompt = f"""You are analyzing a bank statement from {bank_config['name']}. Extract ONLY the transaction data from the text below.

IMPORTANT INSTRUCTIONS:
1. Look for the transaction table/data section and ignore headers, footers, account info, etc.
2. Each transaction should be a separate JSON object in an array
3. Map the columns to these standardized field names:
   - "date": Transaction date (normalize to YYYY-MM-DD format if possible)
   - "description": Transaction description/particulars/narration
   - "reference": Reference number/cheque number/UPI ID
   - "debit": Debit/withdrawal amount (number only, 0 if not applicable)
   - "credit": Credit/deposit amount (number only, 0 if not applicable)  
   - "balance": Account balance after transaction (number only)

COLUMN MAPPING HINTS for {bank_config['name']}:
- Date columns might be called: {', '.join(bank_config['common_fields']['date'])}
- Description columns might be called: {', '.join(bank_config['common_fields']['description'])}
- Reference columns might be called: {', '.join(bank_config['common_fields']['reference'])}
- Debit columns might be called: {', '.join(bank_config['common_fields']['debit'])}
- Credit columns might be called: {', '.join(bank_config['common_fields']['credit'])}
- Balance columns might be called: {', '.join(bank_config['common_fields']['balance'])}

FORMAT RULES:
- Return ONLY valid JSON array, no explanations
- Use empty string "" for missing text fields
- Use 0 for missing numeric fields
- Remove currency symbols and commas from numbers
- Extract only actual transaction rows, not headers or totals

Example output format:
[
  {{
    "date": "2022-01-15",
    "description": "UPI-GROCERY STORE",
    "reference": "UPI-123456789",
    "debit": 245.50,
    "credit": 0,
    "balance": 15430.25
  }}
]

Bank statement text to process:
{truncated_text}
"""
    
    import time
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Sending request to Gemini API (attempt {attempt}/{max_retries})...")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=65536,
                    temperature=0.1,
                    http_options=types.HttpOptions(timeout=180_000),
                ),
            )
            print("Gemini API response received")
            return response.text
        except Exception as e:
            print(f"Error calling Gemini API (attempt {attempt}): {e}")
            if attempt < max_retries:
                wait_time = 5 * attempt  # longer backoff: 5s, 10s
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
    print("All Gemini API attempts failed.")
    return None

def _repair_json(json_str: str) -> str:
    """Attempt to fix common JSON issues from AI output, including truncation."""
    # Remove trailing commas before ] or }
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    # Fix missing commas between } and { (adjacent objects in array)
    json_str = re.sub(r'}\s*{', '},{', json_str)
    # Fix missing commas between a quoted value and the next key
    #   "value"  "key"  or  "value"\n  "key"
    json_str = re.sub(r'(\")\s*\n?\s*(\")', r'\1,\2', json_str)
    # Fix missing commas after numbers before a key:  123  "key"  or  123\n  "key"
    json_str = re.sub(r'(\d)\s*\n?\s*(\")', r'\1,\2', json_str)
    # Fix missing commas after booleans/null before a key
    json_str = re.sub(r'(true|false|null)\s*\n?\s*(\")', r'\1,\2', json_str)
    # Fix missing commas between } and "  (end of nested obj and next key)
    json_str = re.sub(r'}\s*\n?\s*(\")', r'},\1', json_str)
    # Fix missing commas between ] and " (end of array and next key)
    json_str = re.sub(r']\s*\n?\s*(\")', r'],\1', json_str)
    # Fix missing commas between } and [ or { (adjacent structures)
    json_str = re.sub(r'}\s*\n?\s*(\[)', r'},\1', json_str)
    
    # Handle truncated JSON: try to close the array after the last complete object
    json_str = json_str.strip()
    if json_str.startswith('[') and not json_str.endswith(']'):
        # Find the last complete object (last occurrence of })
        last_brace = json_str.rfind('}')
        if last_brace > 0:
            json_str = json_str[:last_brace + 1] + ']'
            # Remove any trailing comma before ]
            json_str = re.sub(r',\s*\]$', ']', json_str)
    
    return json_str

def validate_json_output(json_str: str) -> tuple:
    """Validate if the AI output is valid JSON and contains reasonable transaction data"""
    try:
        # Clean the JSON string (remove code block markers if present)
        json_str = json_str.strip()
        if json_str.startswith('```json'):
            json_str = json_str[7:]
        if json_str.startswith('```'):
            json_str = json_str[3:]
        if json_str.endswith('```'):
            json_str = json_str[:-3]
        json_str = json_str.strip()
        
        # Always apply repair (handles truncation and formatting issues)
        repaired = _repair_json(json_str)
        
        # Try repaired first, then original
        data = None
        for attempt_str in [repaired, json_str]:
            try:
                data = json.loads(attempt_str)
                if attempt_str is repaired and attempt_str != json_str:
                    print("JSON repair successful (recovered from truncated/malformed response)")
                break
            except json.JSONDecodeError:
                continue
        
        if data is None:
            print("JSON parsing failed even after repair")
            return False, None
        
        # Check if it's a list
        if not isinstance(data, list):
            return False, None
        
        # Check if list has reasonable content
        if len(data) == 0:
            return False, None
        
        # Validate transaction structure
        valid_transactions = 0
        for item in data:
            if isinstance(item, dict):
                # Check for required fields
                has_date = 'date' in item and item['date']
                has_amount = (item.get('debit', 0) > 0) or (item.get('credit', 0) > 0)
                has_description = 'description' in item and str(item['description']).strip()
                
                if has_date and (has_amount or has_description):
                    valid_transactions += 1
        
        # Must have at least 50% valid transactions
        if valid_transactions / len(data) >= 0.5:
            return True, data
        
        return False, None
        
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"JSON validation failed: {e}")
        return False, None

def basic_transaction_extraction(text: str) -> List[Dict]:
    """
    Very basic transaction extraction as last resort
    This doesn't depend on any external utilities
    """
    lines = text.split('\n')
    transactions = []
    
    # Simple patterns for date and amount
    date_patterns = [
        r'\b(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b',
        r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,.]?\s*\d{4})\b',
    ]
    amount_pattern = r'[-+]?\d{1,3}(?:,\d{3})*\.\d{2}'
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Look for lines with dates and amounts
        dates = []
        for dp in date_patterns:
            dates.extend(re.findall(dp, line, re.IGNORECASE))
        amounts = re.findall(amount_pattern, line)
        
        if dates and amounts and len(line.split()) > 3:
            try:
                # Skip summary/total lines
                line_lower = line.lower()
                if any(word in line_lower for word in ['total', 'summary', 'opening balance', 'closing balance']):
                    continue
                    
                # Parse amounts - handle +/- prefixed values
                parsed_amounts = []
                for a in amounts:
                    clean = a.replace(',', '')
                    parsed_amounts.append(float(clean))
                
                debit = 0
                credit = 0
                balance = 0
                
                # Assign amounts based on sign or position
                for pa in parsed_amounts[:-1] if len(parsed_amounts) > 1 else parsed_amounts:
                    if pa < 0:
                        debit = abs(pa)
                    elif pa > 0:
                        credit = pa
                if len(parsed_amounts) > 1:
                    balance = abs(parsed_amounts[-1])
                
                # If no sign-based assignment, use keywords
                if debit == 0 and credit == 0 and parsed_amounts:
                    val = abs(parsed_amounts[0])
                    if any(word in line_lower for word in ['credit', 'deposit', 'salary', 'interest']):
                        credit = val
                    else:
                        debit = val
                
                transaction = {
                    'date': dates[0],
                    'description': line,
                    'reference': '',
                    'debit': debit,
                    'credit': credit,
                    'balance': balance
                }
                
                transactions.append(transaction)
            except (ValueError, IndexError):
                continue
    
    return transactions  # Return all found transactions

def main_pdftojson(PDF_PATH):
    """Enhanced PDF to JSON conversion with fallback parsing"""
    print(f"Processing PDF: {os.path.basename(PDF_PATH)}")
    
    # Initialize utility classes with error handling
    config_manager = None
    fallback_parser = None
    
    if UTILS_AVAILABLE:
        if BankConfigManager:
            try:
                config_manager = BankConfigManager()
            except Exception as e:
                print(f"Warning: Could not initialize BankConfigManager: {e}")
        
        if FallbackParser:
            try:
                fallback_parser = FallbackParser()
            except Exception as e:
                print(f"Warning: Could not initialize FallbackParser: {e}")
    else:
        print("Running with basic functionality (utility classes not available)")
    
    # Convert PDF to images
    image_paths = pdf_to_images(PDF_PATH, IMAGE_FOLDER)
    
    # Run OCR
    extracted_text = ocr_images(image_paths)
    
    # Save extracted text for debugging
    with open(OUTPUT_TEXT_FILE, "w", encoding="utf-8") as f:
        f.write(extracted_text)
    print(f"Extracted text saved to: {OUTPUT_TEXT_FILE}")
    
    # If config manager is available, analyze the statement
    if config_manager:
        try:
            analysis = config_manager.analyze_statement_structure(extracted_text)
            print(f"Statement analysis: {analysis['total_lines']} lines, {len(analysis['potential_headers'])} headers, {len(analysis['potential_data_rows'])} data rows")
        except Exception as e:
            print(f"Warning: Statement analysis failed: {e}")
    
    # Try AI-based parsing first
    if GENAI_AVAILABLE:
        print("Attempting AI-based parsing with Gemini...")
        formatted_json = format_Data(extracted_text)
    else:
        print("AI parsing not available, skipping to fallback...")
        formatted_json = None
        
    parsed_transactions = None
    parsing_method = "AI"
    
    if formatted_json:
        # Debug: save raw AI response for inspection
        try:
            with open("ai_raw_response.txt", "w", encoding="utf-8") as dbg:
                dbg.write(formatted_json)
            print(f"Raw AI response saved to ai_raw_response.txt ({len(formatted_json)} chars)")
        except Exception:
            pass
        is_valid, transactions = validate_json_output(formatted_json)
        if is_valid:
            parsed_transactions = transactions
            print(f"AI parsing successful: {len(transactions)} transactions extracted")
        else:
            print("AI parsing produced invalid results, trying fallback...")
    else:
        print("AI parsing failed, trying fallback...")
    
    # Try fallback parsing if AI failed
    if parsed_transactions is None:
        print("Using rule-based fallback parser...")
        try:
            if fallback_parser:
                bank_type = detect_bank_type(extracted_text)
                bank_config = BANK_CONFIGS.get(bank_type, BANK_CONFIGS['generic'])
                fallback_transactions = fallback_parser.parse_statement_text(extracted_text, bank_config)
                
                if fallback_transactions and len(fallback_transactions) > 0:
                    parsed_transactions = fallback_transactions
                    parsing_method = "Fallback"
                    print(f"Fallback parsing successful: {len(fallback_transactions)} transactions extracted")
                else:
                    print("Fallback parsing produced no results")
            else:
                print("Fallback parser not available, using basic extraction")
                parsed_transactions = basic_transaction_extraction(extracted_text)
                if parsed_transactions:
                    parsing_method = "Basic"
                    print(f"Basic parsing extracted {len(parsed_transactions)} transactions")
        except Exception as e:
            print(f"Fallback parsing error: {e}")
            # Try basic extraction as last resort
            try:
                parsed_transactions = basic_transaction_extraction(extracted_text)
                if parsed_transactions:
                    parsing_method = "Basic"
                    print(f"Basic parsing extracted {len(parsed_transactions)} transactions")
            except Exception as e2:
                print(f"Basic parsing also failed: {e2}")
    
    # Save results
    if parsed_transactions:
        output_json_path = "output.json"
        
        # Add metadata
        result_data = {
            "metadata": {
                "parsing_method": parsing_method,
                "bank_type": detect_bank_type(extracted_text) if 'detect_bank_type' in globals() else "unknown",
                "transaction_count": len(parsed_transactions),
                "source_file": os.path.basename(PDF_PATH)
            },
            "transactions": parsed_transactions
        }
        
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(parsed_transactions)} transactions to {output_json_path} using {parsing_method} method")
        
        # Validate results if config manager is available
        if config_manager:
            try:
                validation_result = config_manager.validate_transaction_data(parsed_transactions)
                print(f"Validation: {'PASSED' if validation_result['is_valid'] else 'FAILED'}")
                if validation_result['warnings']:
                    print(f"Warnings: {len(validation_result['warnings'])}")
                if validation_result['errors']:
                    print(f"Errors: {len(validation_result['errors'])}")
            except Exception as e:
                print(f"Validation failed: {e}")
        else:
            # Basic validation without config manager
            valid_count = sum(1 for t in parsed_transactions if t.get('date') and (t.get('debit', 0) > 0 or t.get('credit', 0) > 0))
            print(f"Basic validation: {valid_count}/{len(parsed_transactions)} transactions have date and amount")
        
        # Clean up temporary image files
        try:
            import shutil
            if os.path.exists(IMAGE_FOLDER):
                shutil.rmtree(IMAGE_FOLDER)
        except Exception as e:
            print(f"Warning: Could not clean up image folder: {e}")
        
        return output_json_path
    
    else:
        print("Failed to extract transactions using both AI and fallback methods")
        return None
