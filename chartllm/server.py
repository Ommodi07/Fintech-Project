"""
ChartLLM Server - FastAPI backend integrating all layers
Architecture: Data Layer → Indicator Engine → Event Detector → LLM Engine
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv
from google import genai
from typing import Optional, List, Dict, Any

# Import our modular architecture
from data_layer import DataFetcher
from indicator_engine import BollingerBands, BollingerBandsAnalyzer
from event_detector import EventDetector
from llm_engine import LLMPromptBuilder, ConversationManager

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="ChartLLM API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

client = genai.Client(api_key=GEMINI_API_KEY)

# Initialize components
data_fetcher = DataFetcher()
prompt_builder = LLMPromptBuilder()

# Store conversation managers per session (simple in-memory storage)
conversations = {}


# === REQUEST/RESPONSE MODELS ===

class ChartDataRequest(BaseModel):
    symbol: str
    interval: str = "5m"
    period: str = "1d"
    bb_period: int = 20
    bb_multiplier: float = 2.0


class ChatRequest(BaseModel):
    message: str
    symbol: str
    interval: str = "5m"
    session_id: Optional[str] = "default"


class ChartDataResponse(BaseModel):
    symbol: str
    interval: str
    candles: List[List]  # [timestamp, open, high, low, close, volume]
    bollinger_bands: List[List]  # [timestamp, middle, upper, lower]
    latest_values: Dict[str, Any]
    current_state: Dict[str, Any]
    detected_events: List[Dict[str, Any]]
    summary: Dict[str, Any]


# === API ENDPOINTS ===

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "ChartLLM API",
        "version": "1.0.0"
    }


@app.post("/api/chart-data", response_model=ChartDataResponse)
async def get_chart_data(request: ChartDataRequest):
    """
    Fetch stock data and compute Bollinger Bands with event detection
    This is the main data endpoint for the frontend
    """
    try:
        # Layer 1: Fetch data
        df = data_fetcher.fetch_stock_data(
            symbol=request.symbol,
            interval=request.interval,
            period=request.period
        )
        
        if df is None or df.empty:
            raise HTTPException(
                status_code=404, 
                detail=f"No data found for {request.symbol}"
            )
        
        # Layer 2: Compute Bollinger Bands
        bb = BollingerBands(period=request.bb_period, multiplier=request.bb_multiplier)
        df_with_bb = bb.calculate(df)
        
        # Layer 3: Detect events
        detector = EventDetector()
        events = detector.detect_all_events(df_with_bb)
        current_state = detector.get_current_state(df_with_bb)
        
        # Prepare response
        return ChartDataResponse(
            symbol=request.symbol,
            interval=request.interval,
            candles=data_fetcher.to_json_format(df),
            bollinger_bands=bb.to_json_format(df_with_bb),
            latest_values=bb.get_latest_values(df_with_bb),
            current_state=current_state,
            detected_events=events,
            summary=data_fetcher.get_data_summary(df)
        )
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error fetching chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Layer 4: LLM Explanation Engine
    Process user questions with full context and safety guardrails
    """
    try:
        # Get or create conversation manager
        if request.session_id not in conversations:
            conversations[request.session_id] = ConversationManager()
        
        conv_manager = conversations[request.session_id]
        
        # Fetch fresh data for context
        df = data_fetcher.fetch_stock_data(
            symbol=request.symbol,
            interval=request.interval,
            period="1d"
        )
        
        if df is None or df.empty:
            return {
                "response": prompt_builder.build_fallback_response(),
                "status": "no_data"
            }
        
        # Compute indicators and detect events
        bb = BollingerBands(period=20, multiplier=2.0)
        df_with_bb = bb.calculate(df)
        
        detector = EventDetector()
        events = detector.detect_all_events(df_with_bb)
        current_state = detector.get_current_state(df_with_bb)
        bb_values = bb.get_latest_values(df_with_bb)
        
        # Build context-rich prompt
        context = prompt_builder.build_context_prompt(
            symbol=request.symbol,
            interval=request.interval,
            bb_values=bb_values,
            current_state=current_state,
            detected_events=events
        )
        
        # Add conversation history
        context += conv_manager.get_context()
        
        # Build full prompt
        full_prompt = prompt_builder.build_user_query_prompt(
            user_question=request.message,
            context=context
        )
        
        # Call LLM with safety-focused system prompt
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
            config={
                "system_instruction": prompt_builder.SYSTEM_PROMPT,
                "temperature": 0.7,
                "max_output_tokens": 2048
            }
        )
        
        assistant_response = response.text
        
        # Clean up response formatting
        # Remove asterisks used for markdown emphasis
        assistant_response = assistant_response.replace('**', '')
        
        # Post-process for safety
        assistant_response = prompt_builder.format_educational_response(assistant_response)
        
        # Store in conversation history
        conv_manager.add_exchange(request.message, assistant_response)
        
        return {
            "response": assistant_response,
            "status": "success",
            "detected_events": [e["event_type"] for e in events]
        }
        
    except Exception as e:
        print(f"Error generating chat response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/example-questions")
async def get_example_questions():
    """Get example questions users can ask"""
    return {
        "examples": prompt_builder.build_example_questions()
    }


@app.post("/api/clear-conversation")
async def clear_conversation(session_id: str = "default"):
    """Clear conversation history for a session"""
    if session_id in conversations:
        conversations[session_id].clear_history()
    return {"status": "cleared", "session_id": session_id}


@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "gemini_configured": bool(GEMINI_API_KEY),
        "active_sessions": len(conversations),
        "components": {
            "data_layer": "operational",
            "indicator_engine": "operational",
            "event_detector": "operational",
            "llm_engine": "operational"
        }
    }


# Serve frontend
@app.get("/app")
async def serve_frontend():
    """Serve the main HTML file"""
    return FileResponse("main.html")


if __name__ == '__main__':
    print("="*80)
    print("ChartLLM Server Starting...")
    print("="*80)
    print(f"Gemini API Key configured: {bool(GEMINI_API_KEY)}")
    print("Architecture loaded:")
    print("  ✓ Data Layer (yfinance)")
    print("  ✓ Indicator Engine (Bollinger Bands)")
    print("  ✓ Event Detection Engine")
    print("  ✓ LLM Explanation Engine")
    print("="*80)
    uvicorn.run(app, host='0.0.0.0', port=8000)
