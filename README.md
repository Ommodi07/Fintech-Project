# Fintech Project API Documentation

This project provides a FastAPI-based server for analyzing bank statements, categorizing transactions, and setting financial goals.

## Server Setup

The server is located in the `Server` directory.

### Prerequisites

- Python 3.x
- FastAPI
- Uvicorn
- PDF processing libraries (as required by `pdftojson`)

### Running the Server

```bash
cd Server
python server.py
# The server will start on http://0.0.0.0:5000
```

## API Endpoints

### 1. Root

Check available endpoints.

- **URL:** `/`
- **Method:** `GET`
- **Response:** JSON object mapping endpoints.

```json
{
  "content": {
    "GET": {
      "health": "/health",
      "summary": "/analytics/summary",
      "health_score": "/analytics/health_score"
    },
    "POST": {
      "upload bank statement": "/upload_bank_statement (file as param)",
      "Goal setter": "/goal"
    }
  }
}
```

### 2. Health Check

Verify the server is running.

- **URL:** `/health`
- **Method:** `GET`
- **Response:**

```json
{
  "Health": "ok"
}
```

### 3. Upload Bank Statement

Upload a PDF bank statement for processing and categorization.

- **URL:** `/upload_bank_statement`
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Request Parameters:**
    - `file`: The PDF file to upload.

- **Response:**

```json
{
  "message": "Bank statement processed successfully",
  "filename": "statement.pdf",
  "data": {
      // Categorized transaction data
  }
}
```

### 4. Analytics Summary

Get a summary of expenses, income, and savings based on the processed data.

- **URL:** `/analytics/summary`
- **Method:** `GET`
- **Response:**

```json
{
  "data": {
    "total_expense": 1500.00,
    "total_income": 3000.00,
    "savings": 1500.00,
    "max_spending_category": "Food & Dining"
  }
}
```

### 5. Health Score

Get a calculated financial health score based on volatility, savings rate, and discretionary spending.

- **URL:** `/analytics/health_score`
- **Method:** `GET`
- **Response:**

```json
{
  "Health Score": 6.75
}
```

### 6. Goal Setter

Evaluate if a financial goal is achievable based on current savings patterns.

- **URL:** `/goal`
- **Method:** `POST`
- **Content-Type:** `application/json`
- **Request Body:**

```json
{
  "goal_name": "Buy a Car",
  "target_amount": 20000,
  "time_horizon_months": 24,
}
```

- **Response:**

Returns a decision and the required monthly savings.

**Example 1: Achievable**
```json
{
  "Decision": "✅ Achievable",
  "Monthly Saving Required": 833.33
}
```

**Example 2: Needs Detail**
```json
{
  "Decision": "⚠️ Needs spending reduction",
  "Monthly Saving Required": 1200.00
}
```

**Example 3: Not Achievable**
```json
{
  "Decision": "❌ Not Achievable",
  "Monthly Saving Required": 5000.00
}
```
