from pathlib import Path
import os
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

# Testnet base URL by default. Public market-data endpoints do not need API keys.
BASE_URL = os.getenv("BINANCE_BASE_URL", "https://demo-fapi.binance.com").rstrip("/")
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
TIMEFRAMES = ["15m", "1h"]
KLINE_LIMIT = 500
REQUEST_TIMEOUT = 15
DATA_DIR = PROJECT_ROOT / "data" / "raw"
