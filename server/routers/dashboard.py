import random
import csv
from fastapi import APIRouter
from models import RollRequest
from models import SaveDayRequest
from database import db
from database import gc
from database import sales_sheet
from database import ledger_sheet

router = APIRouter()


def get_fallback_npcs():
    """Failsafe: If the MongoDB collection is empty, read directly from the CSV."""
    fallback = []
    try:
        with open("npcs.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fallback.append({
                    "first_name": row.get("First Name", ""),
                    "last_name": row.get("Last Name", ""),
                    "lifestyle": row.get("Lifestyle", "Modest"),
                })
    except Exception as e:
        print(f"Fallback CSV read failed: {e}")
        
    if not fallback:
        # Absolute failsafe if CSV is missing
        fallback = [{"first_name": "Mysterious", "last_name": "Stranger", "lifestyle": "Modest"}]
    return fallback


@router.post("/api/roll")
def simulate_tavern_day(request: RollRequest):
    if request.is_closed:
        return {"total_roll": 0, "auto_sales": [], "receipts": [], "hourly_feedback": {}, "total_gross": 0.0, "total_profit": 0.0, "is_closed": True}

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
    if total_roll <= 20:
        total_expected_patrons = random.randint(5, 20)
    elif total_roll <= 40:
        total_expected_patrons = random.randint(20, 40)
    elif total_roll <= 60:
        total_expected_patrons = random.randint(40, 80)
    elif total_roll <= 80:
        total_expected_patrons = random.randint(80, 120)
    else:
        total_expected_patrons = random.randint(120, 180)

    total_expected_patrons = int((total_expected_patrons * demand_multiplier) - winter_penalty)
    if total_expected_patrons < 0:
        total_expected_patrons = 0

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
    if not all_npcs:
        all_npcs = get_fallback_npcs()
        
    valid_npcs = [npc for npc in all_npcs if npc.get("lifestyle", "Modest") in allowed_lifestyles]
    if not valid_npcs:
        valid_npcs = all_npcs 
        
    daily_visitors = [random.choice(valid_npcs) for _ in range(total_expected_patrons)]
    inventory_db = list(db.inventory.find({"stock_unit_quantity": {"$gt": 0}}))
    inventory_state = {str(item["_id"]): item for item in inventory_db}

    hours_range = list(range(request.open_hour, request.close_hour))
    if not hours_range:
        hours_range = [request.open_hour]

    active_patrons = []
    customer_receipts = []
    consolidated_sales = {}
    hourly_feedback = {}
    
    total_gross_sales = 0.0
    total_cost_of_goods = 0.0

    for current_hour_idx, hr_val in enumerate(hours_range):
        hr_label = f"{hr_val}:00"
        active_patrons = [p for p in active_patrons if p["departure_idx"] > current_hour_idx]
        arrivals_count = max(0, int(total_expected_patrons / len(hours_range)) + random.randint(-2, 5))
        
        for _ in range(arrivals_count):
            if not daily_visitors:
                break
            visitor = daily_visitors.pop(0)
            duration = random.randint(1, 3)
            
            lifestyle = visitor.get("lifestyle", "Modest")
            customer_name = f"{visitor.get('first_name', '')} {visitor.get('last_name', '')}".strip()
            
            active_patrons.append({
                "name": customer_name,
                "departure_idx": current_hour_idx + duration
            })
            
            available_items = [item for item in inventory_state.values() if item["stock_unit_quantity"] > 0]
            affordable_items = []
            
            if lifestyle in ["Squalid", "Poor"]:
                affordable_items = [i for i in available_items if (i.get("sell_price_copper", 0) / 100.0) <= 0.5]
            elif lifestyle == "Modest":
                affordable_items = [i for i in available_items if 0.1 <= (i.get("sell_price_copper", 0) / 100.0) <= 2.0]
            elif lifestyle == "Comfortable":
                affordable_items = [i for i in available_items if 1.0 <= (i.get("sell_price_copper", 0) / 100.0) <= 10.0]
            else: 
                affordable_items = [i for i in available_items if (i.get("sell_price_copper", 0) / 100.0) >= 5.0]

            if not affordable_items and available_items:
                affordable_items = available_items

            receipt_items = []
            receipt_total = 0.0
            num_items_to_buy = random.randint(1, 3)
            
            for _ in range(num_items_to_buy):
                if affordable_items:
                    chosen_item = random.choice(affordable_items)
                    qty = 1
                    if chosen_item["stock_unit_quantity"] >= qty:
                        chosen_item["stock_unit_quantity"] -= qty
                        
                        price_in_gp = (chosen_item.get("sell_price_copper", 0) / 100.0)
                        cost_in_gp = (chosen_item.get("cost_per_item_copper", 0) / 100.0)
                        
                        receipt_items.append({"name": chosen_item["item_name"], "qty": qty, "price": price_in_gp * qty})
                        receipt_total += (price_in_gp * qty)
                        
                        total_gross_sales += (price_in_gp * qty)
                        total_cost_of_goods += (cost_in_gp * qty)
                        
                        if chosen_item["item_name"] not in consolidated_sales:
                            consolidated_sales[chosen_item["item_name"]] = {"qty": 0, "total": 0.0, "id": str(chosen_item["_id"])}
                        consolidated_sales[chosen_item["item_name"]]["qty"] += qty
                        consolidated_sales[chosen_item["item_name"]]["total"] += (price_in_gp * qty)
                        
                        affordable_items = [i for i in affordable_items if i["stock_unit_quantity"] > 0]

            if receipt_items:
                customer_receipts.append({
                    "name": customer_name,
                    "lifestyle": lifestyle,
                    "hour": hr_label,
                    "items": receipt_items,
                    "total": receipt_total
                })

        hourly_feedback[hr_label] = [p["name"] for p in active_patrons]

    final_auto_sales = []
    for item_name, data in consolidated_sales.items():
        final_auto_sales.append({"item_name": item_name, "quantity": data["qty"], "total_price": data["total"], "inv_id": data["id"]})

    total_profit = total_gross_sales - total_cost_of_goods

    return {
        "total_roll": total_roll, 
        "auto_sales": final_auto_sales, 
        "receipts": customer_receipts, 
        "hourly_feedback": hourly_feedback, 
        "total_gross": round(total_gross_sales, 2),
        "total_profit": round(total_profit, 2),
        "is_closed": False
    }


@router.post("/api/save_day")
def save_day_data(request: SaveDayRequest):
    date_str = request.calendar_date
    if request.is_closed:
        closed_entry = {"entry_type": "Expense", "description": "Closed for Day", "amount": 0.0, "frequency": "Once", "entry_date": date_str}
        db.ledger.insert_one(closed_entry)
        return {"status": "Day Saved (Closed)", "restocks": []}

    total_income = 0.0
    for sale in request.sales:
        total_income += sale.total_price
        db.sales.insert_one(sale.dict())
        inv_item = db.inventory.find_one({"item_name": sale.item_name})
        if inv_item:
            new_stock = max(0, inv_item["stock_unit_quantity"] - sale.quantity)
            db.inventory.update_one({"_id": inv_item["_id"]}, {"$set": {"stock_unit_quantity": new_stock}})

    if total_income > 0:
        ledger_income = {"entry_type": "Income", "description": f"Daily Bar Sales - {date_str}", "amount": total_income, "frequency": "Once", "entry_date": date_str}
        db.ledger.insert_one(ledger_income)
        if gc is not None:
            ledger_sheet.append_row([date_str, "Income", ledger_income["description"], total_income])

    restock_messages = []
    all_inventory = list(db.inventory.find())
    for inv in all_inventory:
        current_stock = inv.get("stock_unit_quantity", 0)
        restock_lvl = inv.get("reorder_level", 0)
        if current_stock <= restock_lvl:
            units_to_order = inv.get("reorder_quantity", 1)
            items_received = units_to_order * inv.get("qty_per_unit", 1)
            total_order_cost_gp = (units_to_order * inv.get("unit_cost_copper", 0.0)) / 100.0
            db.inventory.update_one({"_id": inv["_id"]}, {"$inc": {"stock_unit_quantity": items_received}})
            desc = f"Auto-Restock: {units_to_order}x {inv.get('order_unit', 'Unit')} of {inv['item_name']}"
            db.ledger.insert_one({"entry_type": "Expense", "description": desc, "amount": total_order_cost_gp, "frequency": "Once", "entry_date": date_str})
            restock_messages.append(f"{desc} (Cost: {total_order_cost_gp} gp)")

    # Deferred import: Solves load order crashing on startup
    from routers.inventory import sync_inventory_to_csv
    sync_inventory_to_csv()
    
    return {"status": "Day Saved Successfully", "restocks": restock_messages}