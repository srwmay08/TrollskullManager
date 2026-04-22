import gspread
from pymongo import MongoClient

# CHANGE THIS LINE: Use 127.0.0.1 instead of localhost
mongo_client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=2000)
db = mongo_client["trollskull_tavern"]

try:
    gc = gspread.service_account(filename="creds.json")
    sheet = gc.open("Tavern_Ledger")
    sales_sheet = sheet.worksheet("Sales")
    ledger_sheet = sheet.worksheet("Ledger")
except Exception as e:
    print("Google Sheets connection failed. Operating with MongoDB only.")
    gc = None
    sales_sheet = None
    ledger_sheet = None