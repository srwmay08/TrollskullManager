import random
from fastapi import APIRouter
from bson.objectid import ObjectId

from models import RollRequest
from models import SaleItem
from models import InventoryItem
from models import LedgerEntry
from models import StaffItem
from models import SaveDayRequest
from models import NpcItem

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
    
    demand_multiplier = 1.0
    winter_penalty = 0
    is_shieldmeet = False
    is_feast_of_moon = False
    is_winter = False
    
    if request.current_date:
        if request.current_date.month in [1, 2]:
            winter_penalty = 10
            is_winter = True
        if request.current_date.is_holiday:
            demand_multiplier = 2.0
            if request.current_date.holiday_name == "Feast of the Moon":
                is_feast_of_moon = True
        if request.current_date.is_shieldmeet:
            demand_multiplier = random.uniform(3.0, 4.0)
            is_shieldmeet = True

    outcome = "Standard Day"
    total_expected_patrons = 0

    if total_roll <= 20:
        outcome = "Disaster: Poor word of mouth."
        total_expected_patrons = random.randint(5, 20)
    elif total_roll <= 40:
        outcome = "Poor Day: Slow business."
        total_expected_patrons = random.randint(20, 40)
    elif total_roll <= 60:
        outcome = "Average Day: Modest crowd."
        total_expected_patrons = random.randint(40, 80)
    elif total_roll <= 80:
        outcome = "Good Day: Busy tavern."
        total_expected_patrons = random.randint(80, 120)
    else:
        outcome = "Windfall: The tavern is packed!"
        total_expected_patrons = random.randint(120, 180)

    total_expected_patrons = int((total_expected_patrons * demand_multiplier) - winter_penalty)
    if total_expected_patrons < 0:
        total_expected_patrons = 0

    if is_shieldmeet:
        outcome = "SHIELDMEET: Absolute chaos, maximum capacity!"
    elif is_feast_of_moon:
        outcome = f"{outcome} (Feast of the Moon Event)"

    # Pricing Strategy Adjustments
    strategy = request.price_strategy
    brawl_chance = 0.05
    allowed_lifestyles = []
    
    if strategy == "Dive":
        outcome += " (Dive Pricing: High volume, high friction)"
        total_expected_patrons = int(total_expected_patrons * 1.5)
        allowed_lifestyles = ["Squalid", "Poor", "Modest"]
        brawl_chance = 0.25
    elif strategy == "Standard":
        allowed_lifestyles = ["Poor", "Modest", "Comfortable", "Wealthy"]
    elif strategy == "Premium":
        outcome += " (Premium Pricing: Reduced volume, higher margins)"
        total_expected_patrons = int(total_expected_patrons * 0.7)
        allowed_lifestyles = ["Comfortable", "Wealthy", "Aristocratic"]
    elif strategy == "Exclusive":
        outcome += " (Exclusive Pricing: Very low volume, extreme margins)"
        total_expected_patrons = int(total_expected_patrons * 0.4)
        allowed_lifestyles = ["Wealthy", "Aristocratic"]

    all_npcs = list(db.npcs.find())
    valid_npcs = [npc for npc in all_npcs if npc.get("lifestyle", "Modest") in allowed_lifestyles]
    if not valid_npcs:
        valid_npcs = all_npcs # Fallback if database is misconfigured
        
    daily_visitors = []
    for _ in range(total_expected_patrons):
        daily_visitors.append(random.choice(valid_npcs))

    hours = ["12 PM", "1 PM", "2 PM", "3 PM", "4 PM", "5 PM", "6 PM", "7 PM", "8 PM", "9 PM", "10 PM", "11 PM"]
    
    cap_tables = 44
    cap_bar = 10
    cap_vip = 10
    cap_stand = random.randint(20, 40)
    
    active_patrons = []
    hourly_logs = []
    total_sales_generated = []
    
    total_revenue_pool = 0.0

    for current_hour_idx, hr in enumerate(hours):
        # Remove patrons whose duration is up
        active_patrons = [p for p in active_patrons if p["departure_idx"] > current_hour_idx]
        
        # Determine arrivals for this hour
        arrivals_count = int(total_expected_patrons / len(hours))
        # Add some variance
        arrivals_count = max(0, arrivals_count + random.randint(-2, 5))
        
        arrivals_this_hour = []
        for _ in range(arrivals_count):
            if daily_visitors:
                visitor = daily_visitors.pop(0)
                duration = random.randint(1, 3)
                
                # Try to seat them
                seated_at = "Bounced"
                lifestyle = visitor.get("lifestyle", "Modest")
                
                current_vips = len([p for p in active_patrons if p["seat"] == "VIP"])
                current_tables = len([p for p in active_patrons if p["seat"] == "Table"])
                current_bars = len([p for p in active_patrons if p["seat"] == "Bar"])
                current_stands = len([p for p in active_patrons if p["seat"] == "Standing"])
                
                if lifestyle in ["Wealthy", "Aristocratic"] and current_vips < cap_vip:
                    seated_at = "VIP"
                elif lifestyle in ["Wealthy", "Aristocratic"] and current_tables < cap_tables:
                    seated_at = "Table"
                elif lifestyle in ["Wealthy", "Aristocratic"]:
                    seated_at = "Bounced" # Rich refuse to stand or sit at bar
                elif current_tables < cap_tables:
                    seated_at = "Table"
                elif current_bars < cap_bar:
                    seated_at = "Bar"
                elif current_stands < cap_stand:
                    seated_at = "Standing"
                
                if seated_at != "Bounced":
                    active_patrons.append({
                        "name": f"{visitor.get('first_name', '')} {visitor.get('last_name', '')}".strip(),
                        "lifestyle": lifestyle,
                        "seat": seated_at,
                        "departure_idx": current_hour_idx + duration
                    })
                    arrivals_this_hour.append(visitor)
                    
                    # Calculate spend
                    spend = 0.0
                    if lifestyle == "Squalid" or lifestyle == "Poor":
                        spend = random.uniform(0.1, 0.3)
                    elif lifestyle == "Modest":
                        spend = random.uniform(0.5, 1.5)
                    elif lifestyle == "Comfortable":
                        spend = random.uniform(2.0, 4.0)
                    elif lifestyle == "Wealthy":
                        spend = random.uniform(5.0, 10.0)
                    elif lifestyle == "Aristocratic":
                        spend = random.uniform(15.0, 50.0)
                        
                    total_revenue_pool += spend

        # Compile hour stats
        log_entry = {
            "hour": hr,
            "arrivals": len(arrivals_this_hour),
            "table_used": len([p for p in active_patrons if p["seat"] == "Table"]),
            "bar_used": len([p for p in active_patrons if p["seat"] == "Bar"]),
            "vip_used": len([p for p in active_patrons if p["seat"] == "VIP"]),
            "stand_used": len([p for p in active_patrons if p["seat"] == "Standing"]),
            "brawls": 1 if random.random() < brawl_chance and len(active_patrons) > 20 else 0
        }
        hourly_logs.append(log_entry)

    # Condense sales into categories
    total_sales_generated.append({
        "item_name": f"{strategy} Service Food & Drink", 
        "quantity": total_expected_patrons, 
        "total_price": total_revenue_pool
    })

    result = {
        "total_roll": total_roll,
        "staff_bonus_applied": total_staff_bonus,
        "outcome": outcome,
        "main_patrons": total_expected_patrons,
        "vip_patrons": 0, # integrated into hourly logs
        "auto_sales": total_sales_generated,
        "hourly_breakdown": hourly_logs
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

@router.get("/api/npcs")
def get_npcs():
    npc_cursor = db.npcs.find()
    npc_list = []
    for item in npc_cursor:
        item["_id"] = str(item["_id"])
        npc_list.append(item)
    return npc_list

@router.put("/api/npcs/{item_id}")
def update_npc(item_id: str, item: NpcItem):
    obj_id = ObjectId(item_id)
    db.npcs.update_one({"_id": obj_id}, {"$set": item.dict()})
    return {"status": "Updated"}