import gspread
from pymongo import MongoClient

mongo_client = MongoClient("mongodb://localhost:27017/")
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