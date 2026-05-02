"""
Data Layer - Fetch and prepare stock data using yfinance
Handles intraday timeframes and provides clean OHLCV data
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class DataFetcher:
    """Fetches and processes stock data with support for intraday intervals"""
    
    VALID_INTERVALS = ['1m', '5m', '15m', '30m', '60m', '1h', '1d']
    
    def __init__(self):
        self.cache = {}
    
    def fetch_stock_data(
        self, 
        symbol: str, 
        interval: str = '5m',
        period: str = '1d'
    ) -> Optional[pd.DataFrame]:
        """
        Fetch stock data from yfinance
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
            interval: Data interval ('1m', '5m', '15m', '30m', '60m', '1h', '1d')
            period: Time period ('1d', '5d', '1mo', '3mo', etc.)
            
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
            or None if fetch fails
        """
        if interval not in self.VALID_INTERVALS:
            raise ValueError(f"Invalid interval. Must be one of {self.VALID_INTERVALS}")
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                return None
            
            # Clean data
            df = self._clean_data(df)
            
            return df
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean OHLCV data
        - Remove NaN values
        - Ensure proper data types
        - Sort by date
        """
        # Keep only OHLCV columns
        columns_to_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
        df = df[columns_to_keep]
        
        # Drop rows with any NaN values
        df = df.dropna()
        
        # Sort by index (datetime)
        df = df.sort_index()
        
        # Ensure numeric types
        for col in columns_to_keep:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def get_latest_price(self, df: pd.DataFrame) -> float:
        """Get the most recent closing price"""
        return float(df['Close'].iloc[-1])
    
    def to_json_format(self, df: pd.DataFrame) -> list:
        """
        Convert DataFrame to JSON-serializable format for frontend
        Format: [[timestamp, open, high, low, close, volume], ...]
        """
        result = []
        for idx, row in df.iterrows():
            result.append([
                idx.isoformat(),  # ISO format timestamp
                round(float(row['Open']), 2),
                round(float(row['High']), 2),
                round(float(row['Low']), 2),
                round(float(row['Close']), 2),
                int(row['Volume'])
            ])
        return result
    
    def get_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get summary statistics of the data"""
        return {
            "row_count": len(df),
            "start_date": df.index[0].isoformat(),
            "end_date": df.index[-1].isoformat(),
            "latest_close": round(float(df['Close'].iloc[-1]), 2),
            "high": round(float(df['High'].max()), 2),
            "low": round(float(df['Low'].min()), 2),
            "avg_volume": int(df['Volume'].mean())
        }


# Example usage
if __name__ == "__main__":
    fetcher = DataFetcher()
    
    # Fetch 5-minute data for Apple
    df = fetcher.fetch_stock_data('AAPL', interval='5m', period='1d')
    
    if df is not None:
        print("Data fetched successfully!")
        print(f"Shape: {df.shape}")
        print(f"\nLatest price: ${fetcher.get_latest_price(df)}")
        print(f"\nSummary: {fetcher.get_data_summary(df)}")
        print(f"\nFirst 5 rows:\n{df.head()}")
    else:
        print("Failed to fetch data")
