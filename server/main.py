from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from typing import List
from typing import Optional
import gspread
import random
import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["trollskull_tavern"]

try:
    gc = gspread.service_account(filename="cred.json")
    sheet = gc.open("Tavern_Ledger")
    sales_sheet = sheet.worksheet("Sales")
    ledger_sheet = sheet.worksheet("Ledger")
except Exception as e:
    print("Google Sheets connection failed. Operating with MongoDB only.")
    gc = None

class RollRequest(BaseModel):
    base_roll: int
    staff_bonus: int
    renown_bonus: int
    environmental_bonus: int

class SaleItem(BaseModel):
    item_name: str
    quantity: int
    total_price: float
    sale_date: str

class InventoryItem(BaseModel):
    item_name: str
    stock_on_hand: int
    stock_on_order: int
    units_per: int
    unit_price: float

class LedgerEntry(BaseModel):
    entry_type: str
    description: str
    amount: float
    entry_date: str

@app.post("/api/roll")
def calculate_tavern_outcome(request: RollRequest):
    total_roll = request.base_roll + request.staff_bonus + request.renown_bonus + request.environmental_bonus
    outcome = "Standard Day"
    profit_multiplier = 1.0

    if total_roll <= 20:
        outcome = "Disaster: Pay 1.5x maintenance costs. A brawl broke out."
        profit_multiplier = -1.5
    elif total_roll <= 40:
        outcome = "Poor Day: Pay half maintenance costs."
        profit_multiplier = -0.5
    elif total_roll <= 60:
        outcome = "Average Day: Costs are covered, no extra profit."
        profit_multiplier = 0.0
    elif total_roll <= 80:
        outcome = "Good Day: You made a modest profit."
        profit_multiplier = 1.5
    elif total_roll <= 100:
        outcome = "Great Day: The tavern is bustling."
        profit_multiplier = 2.5
    else:
        outcome = "Windfall: Nobles visited and tipped highly!"
        profit_multiplier = 5.0

    result = {
        "total_roll": total_roll,
        "outcome": outcome,
        "profit_multiplier": profit_multiplier
    }
    return result

@app.post("/api/sales")
def record_sale(sale: SaleItem):
    sale_dict = sale.dict()
    db.sales.insert_one(sale_dict)
    
    if gc is not None:
        row = [sale.sale_date, sale.item_name, sale.quantity, sale.total_price]
        sales_sheet.append_row(row)
        
    sale_dict["_id"] = str(sale_dict["_id"])
    return sale_dict

@app.get("/api/inventory")
def get_inventory():
    inventory_cursor = db.inventory.find()
    inventory_list = []
    for item in inventory_cursor:
        item["_id"] = str(item["_id"])
        inventory_list.append(item)
    return inventory_list

@app.post("/api/inventory")
def add_inventory(item: InventoryItem):
    item_dict = item.dict()
    db.inventory.insert_one(item_dict)
    item_dict["_id"] = str(item_dict["_id"])
    return item_dict

@app.post("/api/ledger")
def record_ledger_entry(entry: LedgerEntry):
    entry_dict = entry.dict()
    db.ledger.insert_one(entry_dict)
    
    if gc is not None:
        row = [entry.entry_date, entry.entry_type, entry.description, entry.amount]
        ledger_sheet.append_row(row)
        
    entry_dict["_id"] = str(entry_dict["_id"])
    return entry_dict

@app.on_event("startup")
def seed_initial_data():
    if db.inventory.count_documents({}) == 0:
        seed_items = [
            {
                "item_name": "Dragon's Breath Ale",
                "stock_on_hand": 5,
                "stock_on_order": 2,
                "units_per": 40,
                "unit_price": 2.5
            },
            {
                "item_name": "Small-Batch Sweet Rolls",
                "stock_on_hand": 24,
                "stock_on_order": 0,
                "units_per": 1,
                "unit_price": 0.5
            },
            {
                "item_name": "Cast Iron Baked Rye",
                "stock_on_hand": 10,
                "stock_on_order": 0,
                "units_per": 1,
                "unit_price": 1.0
            }
        ]
        db.inventory.insert_many(seed_items)