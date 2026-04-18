import random
import csv
import math
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

def sync_inventory_to_csv():
    items = list(db.inventory.find({}, {"_id": 0}))
    if not items: return
    keys = ["Item Name", "Category", "Order Unit", "Order Cost", "Qty per Unit", "Cost per Item", "Base Stock", "Restock Level", "Stock on Hand", "Sale Price"]
    with open("inventory.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for item in items:
            writer.writerow({
                "Item Name": item.get("item_name", ""),
                "Category": item.get("category", "Uncategorized"),
                "Order Unit": item.get("order_unit", "Unit"),
                "Order Cost": item.get("order_cost", 0.0),
                "Qty per Unit": item.get("qty_per_unit", 1),
                "Cost per Item": item.get("cost_per_item", 0.0),
                "Base Stock": item.get("base_stock", 0),
                "Restock Level": item.get("restock_level", 0),
                "Stock on Hand": item.get("stock_on_hand", 0),
                "Sale Price": item.get("unit_price", 0.0)
            })

def sync_npcs_to_csv():
    items = list(db.npcs.find({}, {"_id": 0}))
    if not items: return
    keys = ["First Name", "Last Name", "Occupation", "Lifestyle", "Faction", "Age", "Bar Disposition", "Party Disposition", "Nobility Status", "Noble House", "Story Connection", "PC Affiliation"]
    with open("npcs.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for item in items:
            writer.writerow({
                "First Name": item.get("first_name", ""),
                "Last Name": item.get("last_name", ""),
                "Occupation": item.get("occupation", ""),
                "Lifestyle": item.get("lifestyle", ""),
                "Faction": item.get("faction", ""),
                "Age": item.get("age", 0),
                "Bar Disposition": item.get("bar_disposition", 0),
                "Party Disposition": item.get("party_disposition", 0),
                "Nobility Status": item.get("nobility_status", ""),
                "Noble House": item.get("noble_house", ""),
                "Story Connection": item.get("story_connection", ""),
                "PC Affiliation": item.get("pc_affiliation", "")
            })

@router.post("/api/roll")
def simulate_tavern_day(request: RollRequest):
    staff_cursor = db.staff.find()
    total_staff_bonus = sum(staff.get("bonus", 0) for staff in staff_cursor)
    total_roll = request.base_roll + total_staff_bonus + request.renown_bonus + request.environmental_bonus
    
    demand_multiplier = 1.0
    winter_penalty = 0
    if request.current_date:
        if request.current_date.month in [1, 2]:
            winter_penalty = 10
        if request.current_date.is_holiday:
            demand_multiplier = 2.0
        if request.current_date.is_shieldmeet:
            demand_multiplier = random.uniform(3.0, 4.0)

    total_expected_patrons = 0
    if total_roll <= 20: total_expected_patrons = random.randint(5, 20)
    elif total_roll <= 40: total_expected_patrons = random.randint(20, 40)
    elif total_roll <= 60: total_expected_patrons = random.randint(40, 80)
    elif total_roll <= 80: total_expected_patrons = random.randint(80, 120)
    else: total_expected_patrons = random.randint(120, 180)

    total_expected_patrons = int((total_expected_patrons * demand_multiplier) - winter_penalty)
    if total_expected_patrons < 0: total_expected_patrons = 0

    strategy = request.price_strategy
    allowed_lifestyles = []
    if strategy == "Dive":
        total_expected_patrons = int(total_expected_patrons * 1.5)
        allowed_lifestyles = ["Squalid", "Poor", "Modest"]
    elif strategy == "Standard":
        allowed_lifestyles = ["Poor", "Modest", "Comfortable", "Wealthy"]
    elif strategy == "Premium":
        total_expected_patrons = int(total_expected_patrons * 0.7)
        allowed_lifestyles = ["Comfortable", "Wealthy", "Aristocratic"]
    elif strategy == "Exclusive":
        total_expected_patrons = int(total_expected_patrons * 0.4)
        allowed_lifestyles = ["Wealthy", "Aristocratic"]

    all_npcs = list(db.npcs.find())
    valid_npcs = [npc for npc in all_npcs if npc.get("lifestyle", "Modest") in allowed_lifestyles]
    if not valid_npcs: valid_npcs = all_npcs 
        
    daily_visitors = [random.choice(valid_npcs) for _ in range(total_expected_patrons)]

    inventory_db = list(db.inventory.find({"stock_on_hand": {"$gt": 0}}))
    inventory_state = {str(item["_id"]): item for item in inventory_db}

    hours = ["12 PM", "1 PM", "2 PM", "3 PM", "4 PM", "5 PM", "6 PM", "7 PM", "8 PM", "9 PM", "10 PM", "11 PM"]
    cap_tables = 44
    cap_bar = 10
    cap_vip = 10
    cap_stand = random.randint(20, 40)
    
    active_patrons = []
    customer_receipts = []
    consolidated_sales = {}

    for current_hour_idx, hr in enumerate(hours):
        active_patrons = [p for p in active_patrons if p["departure_idx"] > current_hour_idx]
        arrivals_count = max(0, int(total_expected_patrons / len(hours)) + random.randint(-2, 5))
        
        for _ in range(arrivals_count):
            if not daily_visitors: break
            visitor = daily_visitors.pop(0)
            duration = random.randint(1, 3)
            
            lifestyle = visitor.get("lifestyle", "Modest")
            seated_at = "Bounced"
            
            current_vips = len([p for p in active_patrons if p["seat"] == "VIP"])
            current_tables = len([p for p in active_patrons if p["seat"] == "Table"])
            current_bars = len([p for p in active_patrons if p["seat"] == "Bar"])
            current_stands = len([p for p in active_patrons if p["seat"] == "Standing"])
            
            if lifestyle in ["Wealthy", "Aristocratic"] and current_vips < cap_vip:
                seated_at = "VIP"
            elif lifestyle in ["Wealthy", "Aristocratic"] and current_tables < cap_tables:
                seated_at = "Table"
            elif lifestyle in ["Wealthy", "Aristocratic"]:
                seated_at = "Bounced" 
            elif current_tables < cap_tables:
                seated_at = "Table"
            elif current_bars < cap_bar:
                seated_at = "Bar"
            elif current_stands < cap_stand:
                seated_at = "Standing"
            
            if seated_at != "Bounced":
                active_patrons.append({"seat": seated_at, "departure_idx": current_hour_idx + duration})
                
                available_items = [item for item in inventory_state.values() if item["stock_on_hand"] > 0]
                affordable_items = []
                
                if lifestyle in ["Squalid", "Poor"]:
                    affordable_items = [i for i in available_items if i["unit_price"] <= 0.5]
                elif lifestyle == "Modest":
                    affordable_items = [i for i in available_items if 0.1 <= i["unit_price"] <= 2.0]
                elif lifestyle == "Comfortable":
                    affordable_items = [i for i in available_items if 1.0 <= i["unit_price"] <= 10.0]
                else: 
                    affordable_items = [i for i in available_items if i["unit_price"] >= 5.0]

                if not affordable_items and available_items:
                    affordable_items = available_items

                receipt_items = []
                receipt_total = 0.0
                
                num_items_to_buy = random.randint(1, 3)
                for _ in range(num_items_to_buy):
                    if affordable_items:
                        chosen_item = random.choice(affordable_items)
                        qty = 1
                        
                        if chosen_item["stock_on_hand"] >= qty:
                            chosen_item["stock_on_hand"] -= qty
                            receipt_items.append({"name": chosen_item["item_name"], "qty": qty, "price": chosen_item["unit_price"] * qty})
                            receipt_total += (chosen_item["unit_price"] * qty)
                            
                            if chosen_item["item_name"] not in consolidated_sales:
                                consolidated_sales[chosen_item["item_name"]] = {"qty": 0, "total": 0.0, "id": str(chosen_item["_id"])}
                            consolidated_sales[chosen_item["item_name"]]["qty"] += qty
                            consolidated_sales[chosen_item["item_name"]]["total"] += (chosen_item["unit_price"] * qty)
                            
                            affordable_items = [i for i in affordable_items if i["stock_on_hand"] > 0]

                if receipt_items:
                    customer_name = f"{visitor.get('first_name', '')} {visitor.get('last_name', '')}".strip()
                    customer_receipts.append({
                        "name": customer_name,
                        "lifestyle": lifestyle,
                        "seat": seated_at,
                        "hour": hr,
                        "items": receipt_items,
                        "total": receipt_total
                    })

    final_auto_sales = []
    for item_name, data in consolidated_sales.items():
        final_auto_sales.append({"item_name": item_name, "quantity": data["qty"], "total_price": data["total"], "inv_id": data["id"]})

    return {"total_roll": total_roll, "auto_sales": final_auto_sales, "receipts": customer_receipts}

@router.post("/api/save_day")
def save_day_data(request: SaveDayRequest):
    date_str = request.calendar_date
    
    for sale in request.sales:
        sale_dict = sale.dict()
        db.sales.insert_one(sale_dict)
        
        inv_item = db.inventory.find_one({"item_name": sale.item_name})
        if inv_item:
            new_stock = max(0, inv_item["stock_on_hand"] - sale.quantity)
            db.inventory.update_one({"_id": inv_item["_id"]}, {"$set": {"stock_on_hand": new_stock}})

        if gc is not None:
            row = [sale.sale_date, sale.item_name, sale.quantity, sale.total_price]
            sales_sheet.append_row(row)

    restock_messages = []

    all_inventory = list(db.inventory.find())
    for inv in all_inventory:
        current_stock = inv.get("stock_on_hand", 0)
        restock_lvl = inv.get("restock_level", 0)
        base_stock = inv.get("base_stock", 0)
        
        if current_stock <= restock_lvl and base_stock > current_stock:
            qty_per_unit = inv.get("qty_per_unit", 1)
            if qty_per_unit <= 0: qty_per_unit = 1
            
            items_needed = base_stock - current_stock
            units_to_order = math.ceil(items_needed / qty_per_unit)
            total_order_cost = units_to_order * inv.get("order_cost", 0.0)
            items_received = units_to_order * qty_per_unit
            
            db.inventory.update_one({"_id": inv["_id"]}, {"$inc": {"stock_on_hand": items_received}})
            
            desc = f"Auto-Restock: {units_to_order}x {inv.get('order_unit', 'Unit')} of {inv['item_name']}"
            ledger_entry = {"entry_type": "Expense", "description": desc, "amount": total_order_cost, "frequency": "Once", "entry_date": date_str}
            db.ledger.insert_one(ledger_entry)
            
            if gc is not None:
                row = [date_str, "Expense", desc, total_order_cost]
                ledger_sheet.append_row(row)
                
            restock_messages.append(f"{desc} (Cost: {total_order_cost} gp)")

    sync_inventory_to_csv()

    daily_staff = db.staff.find({"frequency": "Daily"})
    for staff in daily_staff:
        if staff.get("wage", 0) > 0:
            wage_entry = {"entry_type": "Expense", "description": f"Daily Wage: {staff['name']}", "amount": staff["wage"], "frequency": "Daily", "entry_date": date_str}
            db.ledger.insert_one(wage_entry)
            if gc is not None:
                row = [date_str, "Expense", wage_entry["description"], wage_entry["amount"]]
                ledger_sheet.append_row(row)

    return {"status": "Day Saved Successfully", "restocks": restock_messages}

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
    sync_inventory_to_csv()
    return item_dict

@router.put("/api/inventory/{item_id}")
def update_inventory(item_id: str, item: InventoryItem):
    obj_id = ObjectId(item_id)
    db.inventory.update_one({"_id": obj_id}, {"$set": item.dict()})
    sync_inventory_to_csv()
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
    sync_npcs_to_csv()
    return {"status": "Updated"}