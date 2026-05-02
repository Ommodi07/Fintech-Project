"""
Indicator Engine - Compute Bollinger Bands
Pure mathematical computation with no AI involvement
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple


class BollingerBands:
    """
    Compute Bollinger Bands with standard formula:
    - Middle Band = SMA(period)
    - Upper Band = Middle Band + (multiplier × Standard Deviation)
    - Lower Band = Middle Band - (multiplier × Standard Deviation)
    """
    
    def __init__(self, period: int = 20, multiplier: float = 2.0):
        """
        Initialize Bollinger Bands calculator
        
        Args:
            period: Number of periods for moving average (default: 20)
            multiplier: Standard deviation multiplier (default: 2.0)
        """
        self.period = period
        self.multiplier = multiplier
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Bollinger Bands for given OHLCV data
        
        Args:
            df: DataFrame with at least 'Close' column
            
        Returns:
            DataFrame with additional columns:
            - BB_Middle: Middle band (SMA)
            - BB_Upper: Upper band
            - BB_Lower: Lower band
            - BB_Width: Band width (upper - lower)
            - BB_Position: Price position relative to bands (0-1 scale)
        """
        # Make a copy to avoid modifying original
        result = df.copy()
        
        # Calculate Middle Band (Simple Moving Average)
        result['BB_Middle'] = result['Close'].rolling(window=self.period).mean()
        
        # Calculate Standard Deviation
        std_dev = result['Close'].rolling(window=self.period).std()
        
        # Calculate Upper and Lower Bands
        result['BB_Upper'] = result['BB_Middle'] + (self.multiplier * std_dev)
        result['BB_Lower'] = result['BB_Middle'] - (self.multiplier * std_dev)
        
        # Calculate Band Width (measure of volatility)
        result['BB_Width'] = result['BB_Upper'] - result['BB_Lower']
        
        # Calculate %B (price position within bands)
        # %B = (Price - Lower Band) / (Upper Band - Lower Band)
        # %B > 1 means price above upper band
        # %B < 0 means price below lower band
        # %B = 0.5 means price at middle band
        result['BB_PercentB'] = (
            (result['Close'] - result['BB_Lower']) / 
            (result['BB_Upper'] - result['BB_Lower'])
        )
        
        return result
    
    def get_latest_values(self, df_with_bb: pd.DataFrame) -> Dict[str, Any]:
        """
        Get the most recent Bollinger Bands values
        
        Returns:
            Dictionary with current values and metadata
        """
        if df_with_bb.empty:
            return {}
        
        latest = df_with_bb.iloc[-1]
        
        # Check if values are valid (not NaN)
        if pd.isna(latest['BB_Middle']):
            return {"error": "Insufficient data for Bollinger Bands calculation"}
        
        return {
            "current_price": round(float(latest['Close']), 2),
            "middle_band": round(float(latest['BB_Middle']), 2),
            "upper_band": round(float(latest['BB_Upper']), 2),
            "lower_band": round(float(latest['BB_Lower']), 2),
            "band_width": round(float(latest['BB_Width']), 2),
            "percent_b": round(float(latest['BB_PercentB']), 4),
            "timestamp": latest.name.isoformat() if hasattr(latest.name, 'isoformat') else str(latest.name)
        }
    
    def get_volatility_state(self, df_with_bb: pd.DataFrame, lookback: int = 20) -> str:
        """
        Determine the current volatility state based on band width
        
        Args:
            df_with_bb: DataFrame with Bollinger Bands calculated
            lookback: Number of periods to compare against
            
        Returns:
            String describing volatility: 'squeeze', 'expansion', 'normal'
        """
        if len(df_with_bb) < lookback + 1:
            return "insufficient_data"
        
        current_width = df_with_bb['BB_Width'].iloc[-1]
        historical_width = df_with_bb['BB_Width'].iloc[-lookback:-1]
        
        # Calculate percentile of current width
        percentile = (historical_width < current_width).sum() / len(historical_width) * 100
        
        if percentile < 20:
            return "squeeze"  # Low volatility
        elif percentile > 80:
            return "expansion"  # High volatility
        else:
            return "normal"
    
    def to_json_format(self, df_with_bb: pd.DataFrame) -> list:
        """
        Convert Bollinger Bands data to JSON format for frontend
        Format: [[timestamp, middle, upper, lower], ...]
        """
        result = []
        for idx, row in df_with_bb.iterrows():
            if pd.notna(row['BB_Middle']):  # Only include valid data points
                result.append([
                    idx.isoformat(),
                    round(float(row['BB_Middle']), 2),
                    round(float(row['BB_Upper']), 2),
                    round(float(row['BB_Lower']), 2)
                ])
        return result


class BollingerBandsAnalyzer:
    """Higher-level analysis of Bollinger Bands behavior"""
    
    @staticmethod
    def calculate_band_touches(df_with_bb: pd.DataFrame, threshold: float = 0.01) -> Dict[str, int]:
        """
        Count how many times price touched upper/lower bands
        
        Args:
            df_with_bb: DataFrame with Bollinger Bands
            threshold: Percentage threshold to consider a "touch" (default 1%)
        """
        upper_touches = 0
        lower_touches = 0
        
        for _, row in df_with_bb.iterrows():
            if pd.notna(row['BB_Upper']) and pd.notna(row['BB_Lower']):
                # Check if price came within threshold of bands
                if abs(row['Close'] - row['BB_Upper']) / row['BB_Upper'] < threshold:
                    upper_touches += 1
                if abs(row['Close'] - row['BB_Lower']) / row['BB_Lower'] < threshold:
                    lower_touches += 1
        
        return {
            "upper_band_touches": upper_touches,
            "lower_band_touches": lower_touches
        }
    
    @staticmethod
    def detect_walking_bands(df_with_bb: pd.DataFrame, consecutive: int = 3) -> Dict[str, bool]:
        """
        Detect if price is "walking" the upper or lower band
        (staying near band for consecutive periods - indicates strong trend)
        """
        if len(df_with_bb) < consecutive:
            return {"walking_upper": False, "walking_lower": False}
        
        recent = df_with_bb.iloc[-consecutive:]
        
        # Check if %B stayed above 0.9 (near upper) or below 0.1 (near lower)
        walking_upper = (recent['BB_PercentB'] > 0.9).all()
        walking_lower = (recent['BB_PercentB'] < 0.1).all()
        
        return {
            "walking_upper": bool(walking_upper),
            "walking_lower": bool(walking_lower)
        }


# Example usage
if __name__ == "__main__":
    # Test with sample data
    dates = pd.date_range(start='2024-01-01', periods=50, freq='5min')
    sample_data = pd.DataFrame({
        'Close': np.random.randn(50).cumsum() + 100,
        'Open': np.random.randn(50).cumsum() + 100,
        'High': np.random.randn(50).cumsum() + 101,
        'Low': np.random.randn(50).cumsum() + 99,
        'Volume': np.random.randint(1000, 10000, 50)
    }, index=dates)
    
    # Calculate Bollinger Bands
    bb = BollingerBands(period=20, multiplier=2.0)
    result = bb.calculate(sample_data)
    
    print("Latest Bollinger Bands values:")
    print(bb.get_latest_values(result))
    print(f"\nVolatility state: {bb.get_volatility_state(result)}")
