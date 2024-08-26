import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

import json
import time
import pyotp
import pandas as pd
import numpy as np
import requests
from dotenv import load_dotenv
from SmartApi import SmartConnect

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
# Load environment variables
load_dotenv()

class AngelOneConnector:
    def __init__(self):
        self.api_key = os.getenv('ANGEL_ONE_APP_KEY')
        self.client_id = os.getenv('ANGEL_ONE_CLIENT_ID')
        self.totp_secret = os.getenv('ANGEL_ONE_TOTP_SECRET')
        self.pin = os.getenv('ANGEL_ONE_PIN')
        self.api = None
        self.auth_token = None
        self.feed_token = None

    def connect(self) -> bool:
        try:
            self.api = SmartConnect(api_key=self.api_key)
            totp = pyotp.TOTP(self.totp_secret)
            data = self.api.generateSession(self.client_id, self.pin, totp.now())
            self.auth_token = data['data']['jwtToken']
            self.feed_token = data['data']['feedToken']
            logger.info("Successfully connected to Angel One API")
            return True
        except Exception as e:
            logger.error(f"Error connecting to Angel One API: {str(e)}")
            return False

    def get_historical_data(self, symbol_token: str, interval: str, from_date: str, to_date: str) -> Optional[pd.DataFrame]:
        try:
            params = {
                "exchange": "NSE",
                "symboltoken": symbol_token,
                "interval": interval,
                "fromdate": from_date,
                "todate": to_date
            }
            data = self.api.getCandleData(params)
            
            if 'data' not in data or not isinstance(data['data'], list):
                logger.error(f"Unexpected response format: {data}")
                return None
            
            if not data['data']:
                logger.warning(f"No data returned for symbol token {symbol_token}")
                return None
            
            df = pd.DataFrame(data['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            return df
        except Exception as e:
            logger.error(f"Error fetching historical data: {str(e)}")
            return None

    def close(self):
        if self.api:
            self.api.terminateSession(self.client_id)
        logger.info("Closed AngelOne connection")

class InstrumentManager:
    def __init__(self):
        self.instruments_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        self.instruments_file = "instruments.json"
        self.csv_file = "instruments.csv"
        self.instruments = None

    def fetch_instruments(self) -> None:
        if self._should_update_file():
            self._download_instruments()
        else:
            self._load_instruments()

    def _download_instruments(self) -> None:
        response = requests.get(self.instruments_url)
        if response.status_code == 200:
            self.instruments = response.json()
            self._save_instruments()
            logger.info("Instruments data fetched and saved successfully.")
        else:
            logger.error(f"Failed to fetch instruments. Status code: {response.status_code}")

    def _save_instruments(self) -> None:
        with open(self.instruments_file, 'w') as f:
            json.dump(self.instruments, f)
        df = pd.DataFrame(self.instruments)
        df.to_csv(self.csv_file, index=False)

    def _load_instruments(self) -> None:
        if os.path.exists(self.csv_file):
            self.instruments = pd.read_csv(self.csv_file)
            logger.info("Instruments data loaded successfully from CSV.")
        elif os.path.exists(self.instruments_file):
            with open(self.instruments_file, 'r') as f:
                self.instruments = json.load(f)
            logger.info("Instruments data loaded successfully from JSON.")
        else:
            logger.error("Instruments file not found. Please run fetch_instruments() to download the data.")

    def _should_update_file(self) -> bool:
        if not os.path.exists(self.instruments_file) and not os.path.exists(self.csv_file):
            return True
        file_to_check = self.csv_file if os.path.exists(self.csv_file) else self.instruments_file
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_to_check))
        return file_mod_time.date() < datetime.now().date()

    def get_symbol_token(self, symbol: str) -> Optional[str]:
        if self.instruments is None:
            self._load_instruments()
        
        if isinstance(self.instruments, pd.DataFrame):
            instrument = self.instruments[self.instruments['symbol'] == symbol]
            return instrument.iloc[0]['token'] if not instrument.empty else None
        elif isinstance(self.instruments, list):
            return next((instrument['token'] for instrument in self.instruments if instrument['symbol'] == symbol), None)
        return None

def prepare_stocks_to_scan(instruments_file: str, output_file: str) -> None:
    df = pd.read_csv(instruments_file)

    # 1. Filter data for exch_seg="NFO" and instrumenttype="FUTSTK"
    futures_df = df[(df['exch_seg'] == 'NFO') & (df['instrumenttype'] == 'FUTSTK')]

    # 2. Filter for nearest expiry
    today = datetime.now()
    futures_df['expiry_date'] = pd.to_datetime(futures_df['expiry'], format='%d%b%Y')
    futures_df = futures_df[futures_df['expiry_date'] >= today]
    nearest_expiry = futures_df['expiry_date'].min()
    futures_df = futures_df[futures_df['expiry_date'] == nearest_expiry]

    # 3. Take just the name column
    stock_names = futures_df['name'].unique()

    # 4. Append "-EQ" to the names
    stock_symbols = [f"{name}-EQ" for name in stock_names]

    # 5. Search instrument universe for these symbols in NSE
    nse_stocks = df[(df['exch_seg'] == 'NSE') & (df['symbol'].isin(stock_symbols))]

    # 6. Take columns - token, symbol, name
    result = nse_stocks[['token', 'symbol', 'name']]

    # 7. Save as stocks_to_scan.csv
    result.to_csv(output_file, index=False)

    logger.info(f"Saved {len(result)} stocks to {output_file}")

def identify_breakout(df: pd.DataFrame, symbol: str, lookback: int = 20) -> Tuple[bool, str, Dict[str, float]]:
    if len(df) < lookback:
        logger.debug(f"{symbol}: Not enough data for lookback period. Data points: {len(df)}")
        return False, "Insufficient Data", {}

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    df['highest_high'] = df['high'].rolling(window=lookback, min_periods=1).max()

    current_close = df['close'].iloc[-1]
    previous_high = df['highest_high'].iloc[-2]

    logger.debug(f"{symbol}: Data points: {len(df)}, Current close: {current_close}, Previous high: {previous_high}")

    if pd.notna(previous_high) and current_close > previous_high:
        logger.debug(f"{symbol}: Potential breakout detected")
        
        df['tr'] = np.maximum(df['high'] - df['low'], 
                              np.maximum(abs(df['high'] - df['close'].shift(1)),
                                         abs(df['low'] - df['close'].shift(1))))
        df['atr'] = df['tr'].rolling(window=14, min_periods=1).mean()

        atr = df['atr'].iloc[-1]
        breakout_size = current_close - previous_high
        logger.debug(f"{symbol}: Breakout size: {breakout_size}, ATR: {atr}")

        avg_volume = df['volume'].rolling(window=lookback, min_periods=1).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]
        
        details = {
            "current_close": current_close,
            "previous_high": previous_high,
            "breakout_size": breakout_size,
            "atr": atr,
            "current_volume": current_volume,
            "avg_volume": avg_volume
        }

        if breakout_size > atr:
            if current_volume > 1.5 * avg_volume:
                logger.info(f"{symbol}: Full breakout confirmed")
                return True, "Full Breakout", details
            else:
                logger.debug(f"{symbol}: Partial breakout - Volume not significant enough")
                return True, "Partial Breakout - Low Volume", details
        else:
            logger.debug(f"{symbol}: Partial breakout - Not significant enough")
            return True, "Partial Breakout - Small Size", details
    else:
        logger.debug(f"{symbol}: No breakout detected")
        return False, "No Breakout", {}

def scan_for_breakouts(connector: AngelOneConnector, instrument_manager: InstrumentManager, symbols: List[str]) -> List[Dict[str, any]]:
    breakout_stocks = []
    delay = 1  # Start with a 1 second delay

    for symbol in symbols:
        logger.info(f"Scanning {symbol}")
        symbol_token = instrument_manager.get_symbol_token(symbol)
        if symbol_token:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            for _ in range(3):  # Max 3 retries
                try:
                    df = connector.get_historical_data(
                        symbol_token,
                        "ONE_DAY",
                        start_date.strftime("%Y-%m-%d %H:%M"),
                        end_date.strftime("%Y-%m-%d %H:%M")
                    )
                    
                    if df is not None and not df.empty:
                        logger.debug(f"{symbol}: Retrieved {len(df)} days of data")
                        is_breakout, breakout_type, details = identify_breakout(df, symbol)
                        if is_breakout:
                            breakout_stocks.append({
                                "symbol": symbol,
                                "breakout_type": breakout_type,
                                **details
                            })
                    else:
                        logger.warning(f"{symbol}: No data retrieved")
                    break  # Successful, exit the retry loop
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {str(e)}")
                    delay *= 2  # Exponential backoff
                    time.sleep(delay)
            else:
                logger.error(f"Failed to process {symbol} after 3 attempts")
        else:
            logger.warning(f"Symbol token not found for {symbol}")
        
        time.sleep(delay)  # Wait before the next request

    return breakout_stocks

def save_breakout_results(breakout_stocks: List[Dict[str, any]]):
    if not breakout_stocks:
        logger.info("No breakout stocks to save.")
        return

    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"breakout_stocks_{current_time}.csv"
    
    df = pd.DataFrame(breakout_stocks)
    df.to_csv(filename, index=False)
    logger.info(f"Saved breakout results to {filename}")

def main():
    instrument_manager = InstrumentManager()
    instrument_manager.fetch_instruments()

    prepare_stocks_to_scan("instruments.csv", "stocks_to_scan.csv")

    connector = AngelOneConnector()
    if not connector.connect():
        logger.error("Failed to connect to Angel One API. Exiting.")
        return

    try:
        stocks_to_scan = pd.read_csv("stocks_to_scan.csv")['symbol'].tolist()

        breakout_stocks = scan_for_breakouts(connector, instrument_manager, stocks_to_scan)

        save_breakout_results(breakout_stocks)

        full_breakouts = [stock for stock in breakout_stocks if stock['breakout_type'] == "Full Breakout"]
        partial_breakouts = [stock for stock in breakout_stocks if stock['breakout_type'].startswith("Partial Breakout")]

        logger.info(f"Total stocks scanned: {len(stocks_to_scan)}")
        logger.info(f"Full breakouts detected: {len(full_breakouts)}")
        logger.info(f"Partial breakouts detected: {len(partial_breakouts)}")

        if full_breakouts:
            logger.info("Full breakout stocks detected:")
            for stock in full_breakouts:
                print(f"{stock['symbol']} - {stock['breakout_type']}")

        if partial_breakouts:
            logger.info("Partial breakout stocks detected:")
            for stock in partial_breakouts:
                print(f"{stock['symbol']} - {stock['breakout_type']}")

    finally:
        connector.close()

if __name__ == "__main__":
    main()