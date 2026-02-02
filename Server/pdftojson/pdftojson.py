from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import os
import google.generativeai as genai
import dotenv

dotenv.load_dotenv()

OUTPUT_TEXT_FILE = "output.txt"
IMAGE_FOLDER = "extracted_images"

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


def format_Data(text):
    GEMINI_API = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=GEMINI_API)
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""
        Extract only the transaction table from the text below. Ignore all non-transaction content.

Return the result as a JSON array. Each array element must represent exactly one transaction with the following fields:
- date
- transaction_details
- cheque/reference
- debit
- credit
- balance

Rules:
- Include only transaction entries.
- If a value is missing, use an empty string "" for text fields and 0 for numeric fields.
- Output valid JSON only. Do not include explanations or extra text.

Example format:
[
  {{
    "date": "2022-01-01",
    "transaction_details": "",
    "cheque/reference": "upi-3424",
    "debit": 344,
    "credit": 0,
    "balance": 1234
  }},
  {{
    "date": "2022-01-02",
    "transaction_details": "",
    "cheque/reference": "upi-3424",
    "debit": 0,
    "credit": 344,
    "balance": 1234
  }}
]
Text to process:
{text}

    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None

def main_pdftojson(PDF_PATH):
    # print("Converting PDF to images...")
    image_paths = pdf_to_images(PDF_PATH, IMAGE_FOLDER)
    
    # print("Running OCR...")
    extracted_text = ocr_images(image_paths)
    
    with open(OUTPUT_TEXT_FILE, "w", encoding="utf-8") as f:
        f.write(extracted_text)
    
    # print("Done! Extracted text saved to:", OUTPUT_TEXT_FILE)

    # print("Formatting data with Gemini...")
    formatted_json = format_Data(extracted_text)
    
    if formatted_json:
        lines = formatted_json.splitlines()
        formatted_json = "\n".join(lines[1:-1])
        # print("Formatted Data:")
        print(formatted_json)
        # Optionally save to file
        output_json_path = "output.json"
        with open(output_json_path, "w", encoding="utf-8") as f:
            f.write(formatted_json)
        print("Saved formatted data to output.json")
        
        # Clean up temporary image files
        try:
            import shutil
            if os.path.exists(IMAGE_FOLDER):
                shutil.rmtree(IMAGE_FOLDER)
        except Exception as e:
            print(f"Warning: Could not clean up image folder: {e}")
        
        return output_json_path
    
    return None
