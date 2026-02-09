from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import tempfile
import json
from pdftojson import pdftojson
from Categorize import categorical
from Analytics import analytic
from Analytics import health_score

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)

class dataobj:
    def __init__(self):
        self.total_expense = 0
        self.total_income = 0
        self.savings = 0
        self.max_spending_category = ""

@app.get("/")
async def root():
    return {"content" : {"GET" : {
        "health" : "/health"
    }, "POST" : {
        "upload bank statement" : "/upload_bank_statement"
    }}}

@app.get("/health") 
async def health():
    return {"Health" : "ok"}

@app.post("/upload_bank_statement")
async def upload_bank_statement(file: UploadFile = File(...)):
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        temp_dir = tempfile.mkdtemp()
        temp_pdf_path = os.path.join(temp_dir, file.filename)
        
        with open(temp_pdf_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        print(f"Processing PDF: {file.filename}")
        json_file_path = pdftojson.main_pdftojson(PDF_PATH=temp_pdf_path)
        
        if not json_file_path or not os.path.exists(json_file_path):
            raise HTTPException(status_code=500, detail="Failed to extract data from PDF")
        
        categorized_file_path = categorical.main_categorizer(json_file_path)
        
        if not categorized_file_path or not os.path.exists(categorized_file_path):
            raise HTTPException(status_code=500, detail="Failed to categorize transactions")
        
        with open(categorized_file_path, 'r', encoding='utf-8') as f:
            categorized_data = json.load(f)
        
        try:
            os.remove(temp_pdf_path)
            os.rmdir(temp_dir)
            if os.path.exists(json_file_path):
                os.remove(json_file_path)
            # if os.path.exists(categorized_file_path):
            #     os.remove(categorized_file_path)
            if os.path.exists("output.txt"):
                os.remove("output.txt")
        except Exception as cleanup_error:
            print(f"Warning: Could not clean up temporary files: {cleanup_error}")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Bank statement processed successfully",
                "filename": file.filename,
                "data": categorized_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing bank statement: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/analytics/summary")
async def analytics_summary():
    dataobj = analytic.main_analytic("categorized_transactions.json")
    return {
        "data" : dataobj
    }

@app.get("/analytics/health_score")
async def analytics_health():
    return {
        "Health Score" : health_score.health_score_main("categorized_transactions.json")
    }

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5000)