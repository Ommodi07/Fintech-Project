"""
LLM Explanation Engine - Prompt engineering for educational responses
Ensures LLM never calculates, never hallucinates, only explains
"""

from typing import Dict, Any, List


class LLMPromptBuilder:
    """
    Builds structured prompts that force LLM to be educational, not predictive
    Provides calculated data so LLM never hallucinates numbers
    """
    
    SYSTEM_PROMPT = """You are ChartLLM, an educational stock chart analysis assistant. Provide SHORT, CLEAR responses (2-3 sentences max).

CRITICAL RULES:
1. NEVER calculate indicators - all numbers are provided
2. NEVER predict prices or give trading advice
3. NEVER use deterministic language ("will", "must", "definitely")
4. BE CONCISE: Use 2-3 sentences maximum
5. FOCUS on key insights only

RESPONSE FORMAT:
- Lead with the main point
- Add brief context if needed
- End with educational note (optional)

APPROVED LANGUAGE:
✓ "This suggests..." ✓ "Often indicates..." ✓ "May signal..."

FORBIDDEN:
✗ "Price will..." ✗ "Buy/sell..." ✗ "Definitely means..."

Be a CONCISE TEACHER - explain what users see, not what to do."""

    @staticmethod
    def build_context_prompt(
        symbol: str,
        interval: str,
        bb_values: Dict[str, Any],
        current_state: Dict[str, Any],
        detected_events: List[Dict[str, Any]],
        recent_candles: List[Dict[str, Any]] = None
    ) -> str:
        """
        Build comprehensive context for LLM with all calculated values
        
        Args:
            symbol: Stock ticker symbol
            interval: Time interval (e.g., '5m')
            bb_values: Current Bollinger Bands values
            current_state: Current market state
            detected_events: List of detected events
            recent_candles: Recent price action data (optional)
        """
        context = f"""CHART CONTEXT FOR {symbol} ({interval} timeframe):

CALCULATED BOLLINGER BANDS VALUES:
- Current Price: ${bb_values.get('current_price', 'N/A')}
- Middle Band (SMA): ${bb_values.get('middle_band', 'N/A')}
- Upper Band: ${bb_values.get('upper_band', 'N/A')}
- Lower Band: ${bb_values.get('lower_band', 'N/A')}
- Band Width: ${bb_values.get('band_width', 'N/A')}
- %B (Position): {bb_values.get('percent_b', 'N/A')}

CURRENT STATE:
- Position Relative to Bands: {current_state.get('position', 'N/A')}
- %B Value: {current_state.get('percent_b', 'N/A')}
"""

        if detected_events:
            context += "\nDETECTED EVENTS (rule-based analysis):\n"
            for i, event in enumerate(detected_events, 1):
                context += f"{i}. {event['event_type']} (Strength: {event.get('strength', 'N/A')})\n"
                context += f"   Context: {event.get('explanation_hint', '')}\n"
        else:
            context += "\nDETECTED EVENTS: No significant events detected at this time.\n"

        if recent_candles:
            context += f"\nRECENT PRICE ACTION (last {len(recent_candles)} candles):\n"
            for candle in recent_candles[-5:]:  # Show last 5
                context += f"- {candle.get('timestamp', 'N/A')}: O: ${candle.get('open', 'N/A')} H: ${candle.get('high', 'N/A')} L: ${candle.get('low', 'N/A')} C: ${candle.get('close', 'N/A')}\n"

        context += "\nREMEMBER: All numbers above are ALREADY CALCULATED. Do not recalculate. Only explain their meaning."
        
        return context
    
    @staticmethod
    def build_user_query_prompt(user_question: str, context: str) -> str:
        """
        Combine user question with context
        """
        return f"""{context}

USER QUESTION: {user_question}

Provide a SHORT educational explanation (2-3 sentences maximum) using the calculated values above. Focus on the key insight. No predictions or trading advice."""

    @staticmethod
    def build_example_questions() -> List[Dict[str, str]]:
        """
        Provide example questions users can ask
        """
        return [
            {
                "question": "What does band squeeze mean here?",
                "hint": "Educational question about volatility"
            },
            {
                "question": "Why did price reject the upper band?",
                "hint": "Understanding resistance behavior"
            },
            {
                "question": "Is this volatility expansion?",
                "hint": "Learning about band width interpretation"
            },
            {
                "question": "What does it mean when price walks the band?",
                "hint": "Understanding trending behavior"
            },
            {
                "question": "Explain this candle relative to the bands",
                "hint": "Contextual price action analysis"
            },
            {
                "question": "What is %B telling us?",
                "hint": "Understanding position indicator"
            },
            {
                "question": "How do traders interpret this pattern?",
                "hint": "Learning common interpretations"
            }
        ]
    
    @staticmethod
    def build_safety_layer_prompt() -> str:
        """
        Additional safety layer to prevent harmful responses
        """
        return """
SAFETY CHECK:
Before responding, verify:
1. Did I avoid making price predictions?
2. Did I use only provided calculated values?
3. Did I use probabilistic language?
4. Did I avoid give trading advice or recommendations?
5. Is my response educational and beginner-friendly?

If any answer is NO, revise your response.
"""
    
    @staticmethod
    def build_fallback_response() -> str:
        """
        Safe fallback response when data is insufficient
        """
        return """I don't have enough data to provide a meaningful analysis right now. Bollinger Bands typically require at least 20 periods of data to calculate properly. 

In the meantime, here's what Bollinger Bands show:
- **Middle Band**: A simple moving average showing the average price
- **Upper/Lower Bands**: Typically 2 standard deviations from the middle, showing volatility range
- **Band Width**: Narrow bands suggest low volatility; wide bands suggest high volatility

As more data loads, I'll be able to explain what's happening in this specific chart."""

    @staticmethod
    def format_educational_response(response: str) -> str:
        """
        Post-process LLM response to ensure educational formatting and brevity
        """
        # Check if response contains forbidden patterns
        forbidden_phrases = ["you should buy", "you should sell", "i recommend", "will definitely", "price will"]
        
        response_lower = response.lower()
        contains_forbidden = any(phrase in response_lower for phrase in forbidden_phrases)
        
        # Truncate if too long (keep it under 200 characters)
        sentences = response.split('. ')
        if len(sentences) > 3:
            response = '. '.join(sentences[:3]) + '.'
        
        if contains_forbidden:
            response = "⚠️ Educational only. " + response
        
        return response


class ConversationManager:
    """
    Manages conversation context for more natural interactions
    """
    
    def __init__(self, max_history: int = 5):
        self.history = []
        self.max_history = max_history
    
    def add_exchange(self, user_message: str, assistant_response: str):
        """Add a user-assistant exchange to history"""
        self.history.append({
            "user": user_message,
            "assistant": assistant_response
        })
        
        # Keep only recent history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_context(self) -> str:
        """Get conversation history as context"""
        if not self.history:
            return ""
        
        context = "\nRECENT CONVERSATION:\n"
        for exchange in self.history[-3:]:  # Last 3 exchanges
            context += f"User: {exchange['user']}\n"
            context += f"Assistant: {exchange['assistant'][:100]}...\n\n"  # Truncate long responses
        
        return context
    
    def clear_history(self):
        """Clear conversation history"""
        self.history = []


# Example usage
if __name__ == "__main__":
    # Sample data
    bb_values = {
        "current_price": 150.45,
        "middle_band": 148.20,
        "upper_band": 152.80,
        "lower_band": 143.60,
        "band_width": 9.20,
        "percent_b": 0.76
    }
    
    current_state = {
        "position": "upper_half",
        "percent_b": 0.76
    }
    
    detected_events = [
        {
            "event_type": "band_expansion",
            "strength": "moderate",
            "explanation_hint": "Bands expanding - increasing volatility"
        }
    ]
    
    # Build prompt
    builder = LLMPromptBuilder()
    context = builder.build_context_prompt(
        symbol="AAPL",
        interval="5m",
        bb_values=bb_values,
        current_state=current_state,
        detected_events=detected_events
    )
    
    print("SYSTEM PROMPT:")
    print(builder.SYSTEM_PROMPT)
    print("\n" + "="*80 + "\n")
    print("CONTEXT:")
    print(context)
    print("\n" + "="*80 + "\n")
    print("EXAMPLE QUESTIONS:")
    for q in builder.build_example_questions():
        print(f"- {q['question']}")
