from dotenv import load_dotenv
import os

load_dotenv() 


JWT_SECRET = os.getenv("JWT_SECRET")
DB_PATH = os.getenv("DB_PATH", "./app.db")
GOOGLE_SMTP_APP_PASSWORD = os.getenv("GOOGLE_SMTP_APP_PASSWORD", "")
BIDS_DB_PATH = os.getenv("BIDS_DB_PATH", "")
EEG_SAMPLING_RATE = int(os.getenv("EEG_SAMPLING_RATE", 0))