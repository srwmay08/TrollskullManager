import random
from fastapi import APIRouter
from bson.objectid import ObjectId

from models import RollRequest
from models import SaleItem
from models import InventoryItem
from models import LedgerEntry
from models import StaffItem
from models import SaveDayRequest

from database import db
from database import gc
from database import sales_sheet
from database import ledger_sheet

router = APIRouter()

@router.post("/api/roll")
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

    friendly_npcs = list(db.npcs.find({"bar_disposition": {"$gt": 0}}))
    neutral_npcs = list(db.npcs.find({"bar_disposition": 0}))
    
    daily_npcs = []
    total_visitors = patrons + vip_patrons
    for _ in range(total_visitors):
        if friendly_npcs and random.random() < 0.8:
            daily_npcs.append(random.choice(friendly_npcs))
        elif neutral_npcs:
            daily_npcs.append(random.choice(neutral_npcs))

    hours = ["12:00 PM", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM", "6:00 PM", "7:00 PM", "8:00 PM", "9:00 PM", "10:00 PM", "11:00 PM"]
    hour_assignments = {h: [] for h in hours}
    
    for npc in daily_npcs:
        arrive_hour = random.choice(hours)
        name = f"{npc.get('first_name', '')} {npc.get('last_name', '')}".strip()
        if not name:
            name = "Unknown Patron"
        hour_assignments[arrive_hour].append(name)

    hourly_breakdown = []
    for h in hours:
        hourly_breakdown.append({"hour": h, "patrons": hour_assignments[h]})

    ale_qty = 0
    food_qty = 0
    premium_qty = 0

    for npc in daily_npcs:
        lifestyle = npc.get("lifestyle", "Modest")
        if lifestyle == "Wealthy":
            premium_qty += random.randint(1, 3)
            food_qty += random.randint(0, 1)
        elif lifestyle == "Comfortable":
            ale_qty += random.randint(1, 2)
            food_qty += random.randint(0, 1)
            premium_qty += random.randint(0, 1)
        else:
            ale_qty += random.randint(1, 3)
            if random.random() > 0.5:
                food_qty += 1

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
        "auto_sales": generated_sales,
        "hourly_breakdown": hourly_breakdown
    }
    return result

@router.post("/api/save_day")
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

@router.get("/api/inventory")
def get_inventory():
    inventory_cursor = db.inventory.find()
    inventory_list = []
    for item in inventory_cursor:
        item["_id"] = str(item["_id"])
        inventory_list.append(item)
    return inventory_list

@router.post("/api/inventory")
def add_inventory(item: InventoryItem):
    item_dict = item.dict()
    db.inventory.insert_one(item_dict)
    item_dict["_id"] = str(item_dict["_id"])
    return item_dict

@router.put("/api/inventory/{item_id}")
def update_inventory(item_id: str, item: InventoryItem):
    obj_id = ObjectId(item_id)
    db.inventory.update_one({"_id": obj_id}, {"$set": item.dict()})
    return {"status": "Updated"}

@router.get("/api/staff")
def get_staff():
    staff_cursor = db.staff.find()
    staff_list = []
    for s in staff_cursor:
        s["_id"] = str(s["_id"])
        staff_list.append(s)
    return staff_list

@router.post("/api/staff")
def add_staff(staff: StaffItem):
    staff_dict = staff.dict()
    db.staff.insert_one(staff_dict)
    staff_dict["_id"] = str(staff_dict["_id"])
    return staff_dict

@router.get("/api/ledger")
def get_ledger():
    ledger_cursor = db.ledger.find()
    ledger_list = []
    for item in ledger_cursor:
        item["_id"] = str(item["_id"])
        ledger_list.append(item)
    return ledger_list

@router.post("/api/ledger")
def record_ledger_entry(entry: LedgerEntry):
    entry_dict = entry.dict()
    db.ledger.insert_one(entry_dict)
    if gc is not None:
        row = [entry.entry_date, entry.entry_type, entry.description, entry.amount]
        ledger_sheet.append_row(row)
    entry_dict["_id"] = str(entry_dict["_id"])
    return entry_dict

@router.get("/api/reports")
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