import contextlib
import uvicorn
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pymongo import MongoClient
from bson.objectid import ObjectId
from typing import List
from typing import Optional
import gspread
import random
import datetime

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

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    if db.inventory.count_documents({}) == 0:
        seed_items = [
            {
                "item_name": "Moradin's Hammerfall (Heavy Pour)",
                "stock_on_hand": 60,
                "stock_on_order": 0,
                "units_per": 1,
                "unit_price": 2.0
            },
            {
                "item_name": "First Frost Art Wine (Bottle)",
                "stock_on_hand": 10,
                "stock_on_order": 5,
                "units_per": 5,
                "unit_price": 25.0
            },
            {
                "item_name": "Azun's Lament (Bottle)",
                "stock_on_hand": 12,
                "stock_on_order": 0,
                "units_per": 5,
                "unit_price": 15.0
            },
            {
                "item_name": "Black Wyvern Porter (Tankard)",
                "stock_on_hand": 200,
                "stock_on_order": 100,
                "units_per": 1,
                "unit_price": 0.04
            },
            {
                "item_name": "The 'Lif' Special (Glass)",
                "stock_on_hand": 50,
                "stock_on_order": 0,
                "units_per": 1,
                "unit_price": 0.8
            },
            {
                "item_name": "Gumpfish Stew (Bowl)",
                "stock_on_hand": 30,
                "stock_on_order": 0,
                "units_per": 1,
                "unit_price": 0.3
            }
        ]
        db.inventory.insert_many(seed_items)
    
    if db.staff.count_documents({}) == 0:
        seed_staff = [
            {
                "name": "Lif the Poltergeist",
                "wage": 0.0,
                "frequency": "Daily",
                "bonus": 5
            },
            {
                "name": "Bepis Honeymaker (Cook)",
                "wage": 0.0,
                "frequency": "Daily",
                "bonus": 2
            },
            {
                "name": "Spider (Warforged Security Tier II)",
                "wage": 2.0,
                "frequency": "Daily",
                "bonus": 4
            },
            {
                "name": "Amaryllis Thorne (Acrobat Guard Tier IV)",
                "wage": 1.5,
                "frequency": "Daily",
                "bonus": 3
            },
            {
                "name": "Myrnd Gundwynd (Black Boar Vanguard)",
                "wage": 3.0,
                "frequency": "Daily",
                "bonus": 5
            },
            {
                "name": "Istrid Horn (Treasury Security Tier I)",
                "wage": 5.0,
                "frequency": "Daily",
                "bonus": 6
            },
            {
                "name": "Tashlyn Yafeera (Head of Security Tier I)",
                "wage": 8.0,
                "frequency": "Daily",
                "bonus": 8
            }
        ]
        db.staff.insert_many(seed_staff)

    if db.ledger.count_documents({}) == 0:
        seed_ledger = [
            {
                "entry_type": "Income",
                "description": "Ransom of the Twelve (Lord Lorahmar Djinni Rescue)",
                "amount": 11000.0,
                "frequency": "Once",
                "entry_date": "Ches 30"
            },
            {
                "entry_type": "Income",
                "description": "Volo's Sponsorship (Brand Ambassador)",
                "amount": 50.0,
                "frequency": "Monthly",
                "entry_date": "Ches 30"
            },
            {
                "entry_type": "Guild",
                "description": "Vintners' Guild Partnership (Mertyn Bottlewick) Upfront",
                "amount": 300.0,
                "frequency": "Once",
                "entry_date": "Ches 30"
            },
            {
                "entry_type": "Renovation",
                "description": "Tally Fellbranch Ironwood Restoration",
                "amount": 1200.0,
                "frequency": "Once",
                "entry_date": "Ches 30"
            },
            {
                "entry_type": "Guild",
                "description": "Dungsweepers' Guild (Grubach) Contract",
                "amount": 20.0,
                "frequency": "Weekly",
                "entry_date": "Ches 30"
            },
            {
                "entry_type": "Guild",
                "description": "Vintners' Guild Weekly Fee",
                "amount": 5.0,
                "frequency": "Weekly",
                "entry_date": "Ches 30"
            },
            {
                "entry_type": "Tuition",
                "description": "Murkledorn's Education (7 Urchins/Appleton Boys)",
                "amount": 14.0,
                "frequency": "Weekly",
                "entry_date": "Ches 30"
            }
        ]
        db.ledger.insert_many(seed_ledger)
        
    print("\n" + "="*50)
    print("TROLLSKULL MANOR SERVER IS RUNNING")
    print("Frontend URL: http://127.0.0.1:8000/")
    print("API Base URL: http://127.0.0.1:8000/api")
    print("="*50 + "\n")
    
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RollRequest(BaseModel):
    base_roll: int
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
    frequency: str
    entry_date: str

class StaffItem(BaseModel):
    name: str
    wage: float
    frequency: str
    bonus: int

class SaveDayRequest(BaseModel):
    calendar_date: str
    sales: List[SaleItem]

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    try:
        with open("index.html", "r") as file:
            html_content = file.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        error_html = "<h1>Error: index.html not found.</h1>"
        return HTMLResponse(content=error_html, status_code=404)

@app.post("/api/roll")
def calculate_tavern_outcome(request: RollRequest):
    staff_cursor = db.staff.find()
    total_staff_bonus = 0
    for staff in staff_cursor:
        total_staff_bonus += staff.get("bonus", 0)

    total_roll = request.base_roll + total_staff_bonus + request.renown_bonus + request.environmental_bonus
    outcome = "Standard Day"
    
    patrons = 0
    vip_patrons = 0

    if total_roll <= 20:
        outcome = "Disaster: A brawl broke out. Empty tavern."
        patrons = random.randint(0, 10)
    elif total_roll <= 40:
        outcome = "Poor Day: Slow business."
        patrons = random.randint(10, 20)
    elif total_roll <= 60:
        outcome = "Average Day: Modest crowd."
        patrons = random.randint(20, 40)
    elif total_roll <= 80:
        outcome = "Good Day: Busy tavern."
        patrons = random.randint(40, 54)
    else:
        outcome = "Windfall: The tavern is packed!"
        patrons = 54

    if total_roll > 60:
        vip_check = random.randint(1, 20)
        if vip_check >= 14:
            vip_fullness = random.randint(1, 100)
            vip_patrons = max(1, int((vip_fullness / 100.0) * 10))

    ale_qty = int(patrons * random.uniform(1.0, 2.5))
    food_qty = int(patrons * random.uniform(0.2, 0.8))
    premium_qty = int(vip_patrons * random.uniform(2.0, 4.0))

    generated_sales = []
    if ale_qty > 0:
        generated_sales.append({"item_name": "Standard Ale/Drinks", "quantity": ale_qty, "total_price": ale_qty * 0.5})
    if food_qty > 0:
        generated_sales.append({"item_name": "Tavern Fare", "quantity": food_qty, "total_price": food_qty * 1.5})
    if premium_qty > 0:
        generated_sales.append({"item_name": "Premium VIP Drinks", "quantity": premium_qty, "total_price": premium_qty * 5.0})

    result = {
        "total_roll": total_roll,
        "staff_bonus_applied": total_staff_bonus,
        "outcome": outcome,
        "main_patrons": patrons,
        "vip_patrons": vip_patrons,
        "auto_sales": generated_sales
    }
    return result

@app.post("/api/save_day")
def save_day_data(request: SaveDayRequest):
    date_str = request.calendar_date
    
    for sale in request.sales:
        sale.sale_date = date_str
        sale_dict = sale.dict()
        db.sales.insert_one(sale_dict)
        if gc is not None:
            row = [sale.sale_date, sale.item_name, sale.quantity, sale.total_price]
            sales_sheet.append_row(row)

    daily_staff = db.staff.find({"frequency": "Daily"})
    for staff in daily_staff:
        if staff.get("wage", 0) > 0:
            wage_entry = {
                "entry_type": "Expense",
                "description": f"Daily Wage: {staff['name']}",
                "amount": staff["wage"],
                "frequency": "Daily",
                "entry_date": date_str
            }
            db.ledger.insert_one(wage_entry)
            if gc is not None:
                row = [date_str, "Expense", wage_entry["description"], wage_entry["amount"]]
                ledger_sheet.append_row(row)

    return {"status": "Day Saved Successfully"}

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

@app.put("/api/inventory/{item_id}")
def update_inventory(item_id: str, item: InventoryItem):
    obj_id = ObjectId(item_id)
    db.inventory.update_one({"_id": obj_id}, {"$set": item.dict()})
    return {"status": "Updated"}

@app.get("/api/staff")
def get_staff():
    staff_cursor = db.staff.find()
    staff_list = []
    for s in staff_cursor:
        s["_id"] = str(s["_id"])
        staff_list.append(s)
    return staff_list

@app.post("/api/staff")
def add_staff(staff: StaffItem):
    staff_dict = staff.dict()
    db.staff.insert_one(staff_dict)
    staff_dict["_id"] = str(staff_dict["_id"])
    return staff_dict

@app.get("/api/ledger")
def get_ledger():
    ledger_cursor = db.ledger.find()
    ledger_list = []
    for item in ledger_cursor:
        item["_id"] = str(item["_id"])
        ledger_list.append(item)
    return ledger_list

@app.post("/api/ledger")
def record_ledger_entry(entry: LedgerEntry):
    entry_dict = entry.dict()
    db.ledger.insert_one(entry_dict)
    if gc is not None:
        row = [entry.entry_date, entry.entry_type, entry.description, entry.amount]
        ledger_sheet.append_row(row)
    entry_dict["_id"] = str(entry_dict["_id"])
    return entry_dict

@app.get("/api/reports")
def get_reports():
    sales_cursor = db.sales.find()
    sales = []
    for s in sales_cursor:
        s["_id"] = str(s["_id"])
        sales.append(s)
        
    ledger_cursor = db.ledger.find()
    ledger = []
    for l in ledger_cursor:
        l["_id"] = str(l["_id"])
        ledger.append(l)
        
    return {"sales": sales, "ledger": ledger}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)