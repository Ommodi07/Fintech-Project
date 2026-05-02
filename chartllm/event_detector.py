"""
Event Detection Engine - Rule-based logic to detect chart events
Provides structured, machine-readable events for LLM reasoning
NO AI INVOLVEMENT - Pure deterministic logic
"""

from typing import Dict, Any, List
import pandas as pd


class EventDetector:
    """
    Detects significant events in price action relative to Bollinger Bands
    Returns structured events that LLM can explain educationally
    """
    
    def __init__(self, touch_threshold: float = 0.015):
        """
        Args:
            touch_threshold: Distance threshold to consider band "touch" (1.5% default)
        """
        self.touch_threshold = touch_threshold
    
    def detect_all_events(self, df_with_bb: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect all significant events in the current chart state
        
        Returns:
            List of event dictionaries with type, strength, and context
        """
        if df_with_bb.empty or len(df_with_bb) < 2:
            return []
        
        events = []
        
        # Get latest data point
        latest = df_with_bb.iloc[-1]
        previous = df_with_bb.iloc[-2]
        
        # Check if bands are calculated
        if pd.isna(latest['BB_Middle']):
            return [{"event_type": "insufficient_data", "message": "Not enough data for Bollinger Bands"}]
        
        # 1. Band Touch Events
        upper_touch = self._check_upper_band_touch(latest)
        if upper_touch:
            events.append(upper_touch)
        
        lower_touch = self._check_lower_band_touch(latest)
        if lower_touch:
            events.append(lower_touch)
        
        # 2. Band Squeeze Detection
        squeeze = self._detect_squeeze(df_with_bb)
        if squeeze:
            events.append(squeeze)
        
        # 3. Band Expansion Detection
        expansion = self._detect_expansion(df_with_bb)
        if expansion:
            events.append(expansion)
        
        # 4. Mean Reversion Setup
        mean_reversion = self._detect_mean_reversion(latest, previous)
        if mean_reversion:
            events.append(mean_reversion)
        
        # 5. Walking Bands (Trend Riding)
        walking = self._detect_walking_bands(df_with_bb)
        if walking:
            events.append(walking)
        
        # 6. Band Breakout
        breakout = self._detect_breakout(latest, previous)
        if breakout:
            events.append(breakout)
        
        # 7. Middle Band Cross
        middle_cross = self._detect_middle_band_cross(latest, previous)
        if middle_cross:
            events.append(middle_cross)
        
        return events
    
    def _check_upper_band_touch(self, latest: pd.Series) -> Dict[str, Any]:
        """Check if price is touching or near upper band"""
        distance_to_upper = (latest['BB_Upper'] - latest['Close']) / latest['BB_Upper']
        
        if distance_to_upper < self.touch_threshold:
            # Calculate strength based on how close
            strength = "strong" if distance_to_upper < 0.005 else "moderate"
            
            return {
                "event_type": "upper_band_touch",
                "strength": strength,
                "price": round(float(latest['Close']), 2),
                "upper_band": round(float(latest['BB_Upper']), 2),
                "distance_pct": round(distance_to_upper * 100, 2),
                "explanation_hint": "Price near upper band - often indicates overbought condition or strong uptrend"
            }
        return None
    
    def _check_lower_band_touch(self, latest: pd.Series) -> Dict[str, Any]:
        """Check if price is touching or near lower band"""
        distance_to_lower = (latest['Close'] - latest['BB_Lower']) / latest['BB_Lower']
        
        if distance_to_lower < self.touch_threshold:
            strength = "strong" if distance_to_lower < 0.005 else "moderate"
            
            return {
                "event_type": "lower_band_touch",
                "strength": strength,
                "price": round(float(latest['Close']), 2),
                "lower_band": round(float(latest['BB_Lower']), 2),
                "distance_pct": round(distance_to_lower * 100, 2),
                "explanation_hint": "Price near lower band - often indicates oversold condition or strong downtrend"
            }
        return None
    
    def _detect_squeeze(self, df_with_bb: pd.DataFrame, lookback: int = 20) -> Dict[str, Any]:
        """Detect Bollinger Band squeeze (low volatility)"""
        if len(df_with_bb) < lookback:
            return None
        
        current_width = df_with_bb['BB_Width'].iloc[-1]
        recent_widths = df_with_bb['BB_Width'].iloc[-lookback:]
        
        # Check if current width is in lowest 15%
        percentile = (recent_widths < current_width).sum() / len(recent_widths)
        
        if percentile < 0.15:
            return {
                "event_type": "band_squeeze",
                "strength": "strong" if percentile < 0.05 else "moderate",
                "current_width": round(float(current_width), 2),
                "percentile": round(percentile * 100, 1),
                "explanation_hint": "Bands are squeezing - indicates low volatility and potential breakout setup"
            }
        return None
    
    def _detect_expansion(self, df_with_bb: pd.DataFrame, lookback: int = 20) -> Dict[str, Any]:
        """Detect Bollinger Band expansion (high volatility)"""
        if len(df_with_bb) < lookback:
            return None
        
        current_width = df_with_bb['BB_Width'].iloc[-1]
        recent_widths = df_with_bb['BB_Width'].iloc[-lookback:]
        
        # Check if current width is in highest 15%
        percentile = (recent_widths < current_width).sum() / len(recent_widths)
        
        if percentile > 0.85:
            return {
                "event_type": "band_expansion",
                "strength": "strong" if percentile > 0.95 else "moderate",
                "current_width": round(float(current_width), 2),
                "percentile": round(percentile * 100, 1),
                "explanation_hint": "Bands are expanding - indicates increasing volatility and active trading"
            }
        return None
    
    def _detect_mean_reversion(self, latest: pd.Series, previous: pd.Series) -> Dict[str, Any]:
        """Detect potential mean reversion setup"""
        # Check if price was far from middle band and is now moving back
        prev_distance = abs(previous['Close'] - previous['BB_Middle']) / previous['BB_Middle']
        curr_distance = abs(latest['Close'] - latest['BB_Middle']) / latest['BB_Middle']
        
        # Mean reversion: was far, now coming back
        if prev_distance > 0.02 and curr_distance < prev_distance:
            direction = "from_upper" if previous['Close'] > previous['BB_Middle'] else "from_lower"
            
            return {
                "event_type": "mean_reversion",
                "strength": "strong" if prev_distance > 0.03 else "moderate",
                "direction": direction,
                "previous_distance_pct": round(prev_distance * 100, 2),
                "current_distance_pct": round(curr_distance * 100, 2),
                "explanation_hint": f"Price reverting toward middle band {direction} - classic mean reversion pattern"
            }
        return None
    
    def _detect_walking_bands(self, df_with_bb: pd.DataFrame, consecutive: int = 5) -> Dict[str, Any]:
        """Detect if price is walking along upper or lower band (strong trend)"""
        if len(df_with_bb) < consecutive:
            return None
        
        recent = df_with_bb.iloc[-consecutive:]
        
        # Check %B values
        walking_upper = (recent['BB_PercentB'] > 0.85).sum() >= consecutive - 1
        walking_lower = (recent['BB_PercentB'] < 0.15).sum() >= consecutive - 1
        
        if walking_upper:
            return {
                "event_type": "walking_upper_band",
                "strength": "strong",
                "consecutive_periods": consecutive,
                "explanation_hint": "Price walking upper band - indicates strong uptrend, not just overbought"
            }
        
        if walking_lower:
            return {
                "event_type": "walking_lower_band",
                "strength": "strong",
                "consecutive_periods": consecutive,
                "explanation_hint": "Price walking lower band - indicates strong downtrend, not just oversold"
            }
        
        return None
    
    def _detect_breakout(self, latest: pd.Series, previous: pd.Series) -> Dict[str, Any]:
        """Detect breakout beyond bands"""
        # Check if price broke outside bands
        if latest['Close'] > latest['BB_Upper'] and previous['Close'] <= previous['BB_Upper']:
            return {
                "event_type": "breakout_above",
                "strength": "strong",
                "price": round(float(latest['Close']), 2),
                "upper_band": round(float(latest['BB_Upper']), 2),
                "excess_pct": round((latest['Close'] - latest['BB_Upper']) / latest['BB_Upper'] * 100, 2),
                "explanation_hint": "Price broke above upper band - may indicate strong momentum or potential exhaustion"
            }
        
        if latest['Close'] < latest['BB_Lower'] and previous['Close'] >= previous['BB_Lower']:
            return {
                "event_type": "breakout_below",
                "strength": "strong",
                "price": round(float(latest['Close']), 2),
                "lower_band": round(float(latest['BB_Lower']), 2),
                "excess_pct": round((latest['BB_Lower'] - latest['Close']) / latest['BB_Lower'] * 100, 2),
                "explanation_hint": "Price broke below lower band - may indicate strong selling or potential reversal"
            }
        
        return None
    
    def _detect_middle_band_cross(self, latest: pd.Series, previous: pd.Series) -> Dict[str, Any]:
        """Detect crossing of middle band (momentum shift)"""
        if pd.isna(latest['BB_Middle']) or pd.isna(previous['BB_Middle']):
            return None
        
        # Cross from below to above
        if previous['Close'] < previous['BB_Middle'] and latest['Close'] > latest['BB_Middle']:
            return {
                "event_type": "middle_band_cross_up",
                "strength": "moderate",
                "price": round(float(latest['Close']), 2),
                "middle_band": round(float(latest['BB_Middle']), 2),
                "explanation_hint": "Price crossed above middle band - may signal bullish momentum shift"
            }
        
        # Cross from above to below
        if previous['Close'] > previous['BB_Middle'] and latest['Close'] < latest['BB_Middle']:
            return {
                "event_type": "middle_band_cross_down",
                "strength": "moderate",
                "price": round(float(latest['Close']), 2),
                "middle_band": round(float(latest['BB_Middle']), 2),
                "explanation_hint": "Price crossed below middle band - may signal bearish momentum shift"
            }
        
        return None
    
    def get_current_state(self, df_with_bb: pd.DataFrame) -> Dict[str, Any]:
        """
        Get comprehensive current state summary
        """
        if df_with_bb.empty or pd.isna(df_with_bb['BB_Middle'].iloc[-1]):
            return {"state": "insufficient_data"}
        
        latest = df_with_bb.iloc[-1]
        
        # Determine position
        percent_b = latest['BB_PercentB']
        if percent_b > 1:
            position = "above_upper_band"
        elif percent_b > 0.8:
            position = "near_upper_band"
        elif percent_b > 0.6:
            position = "upper_half"
        elif percent_b > 0.4:
            position = "middle_zone"
        elif percent_b > 0.2:
            position = "lower_half"
        elif percent_b > 0:
            position = "near_lower_band"
        else:
            position = "below_lower_band"
        
        return {
            "position": position,
            "percent_b": round(float(percent_b), 4),
            "price": round(float(latest['Close']), 2),
            "middle_band": round(float(latest['BB_Middle']), 2),
            "upper_band": round(float(latest['BB_Upper']), 2),
            "lower_band": round(float(latest['BB_Lower']), 2),
            "band_width": round(float(latest['BB_Width']), 2)
        }


# Example usage
if __name__ == "__main__":
    import numpy as np
    
    # Create sample data with Bollinger Bands
    dates = pd.date_range(start='2024-01-01', periods=50, freq='5min')
    sample_data = pd.DataFrame({
        'Close': np.random.randn(50).cumsum() + 100,
        'Open': np.random.randn(50).cumsum() + 100,
        'High': np.random.randn(50).cumsum() + 101,
        'Low': np.random.randn(50).cumsum() + 99,
        'Volume': np.random.randint(1000, 10000, 50)
    }, index=dates)
    
    # Add mock Bollinger Bands
    sample_data['BB_Middle'] = sample_data['Close'].rolling(20).mean()
    sample_data['BB_Upper'] = sample_data['BB_Middle'] + 2 * sample_data['Close'].rolling(20).std()
    sample_data['BB_Lower'] = sample_data['BB_Middle'] - 2 * sample_data['Close'].rolling(20).std()
    sample_data['BB_Width'] = sample_data['BB_Upper'] - sample_data['BB_Lower']
    sample_data['BB_PercentB'] = (sample_data['Close'] - sample_data['BB_Lower']) / (sample_data['BB_Upper'] - sample_data['BB_Lower'])
    
    # Detect events
    detector = EventDetector()
    events = detector.detect_all_events(sample_data)
    
    print("Detected Events:")
    for event in events:
        print(f"- {event['event_type']}: {event.get('explanation_hint', 'N/A')}")
    
    print(f"\nCurrent State: {detector.get_current_state(sample_data)}")
