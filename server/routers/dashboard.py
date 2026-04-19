import random
import csv
import math
from typing import Dict
from typing import List
from typing import Any

from fastapi import APIRouter

from models import RollRequest
from models import SaveDayRequest
from database import db
from database import gc
from database import sales_sheet
from database import ledger_sheet

router = APIRouter()


def get_fallback_npcs() -> List[Dict[str, Any]]:
    """Failsafe: If the MongoDB collection is empty, read directly from the CSV."""
    fallback: List[Dict[str, Any]] = []
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
        fallback = [{"first_name": "Mysterious", "last_name": "Stranger", "lifestyle": "Modest"}]
    return fallback


@router.post("/api/roll")
def simulate_tavern_day(request: RollRequest) -> Dict[str, Any]:
    if request.is_closed:
        return {
            "total_roll": 0, 
            "auto_sales": [], 
            "receipts": [], 
            "hourly_feedback": {}, 
            "total_gross": 0.0, 
            "total_profit": 0.0, 
            "is_closed": True
        }

    staff_cursor = db.staff.find()
    total_staff_bonus: int = sum(staff.get("bonus", 0) for staff in staff_cursor)
    total_roll: int = request.base_roll + total_staff_bonus + request.renown_bonus + request.environmental_bonus
    
    demand_multiplier: float = 1.0
    winter_penalty: int = 0
    if request.current_date:
        if request.current_date.month in [1, 2]:
            winter_penalty = 10
        if request.current_date.is_holiday:
            demand_multiplier = 2.0
        if request.current_date.is_shieldmeet:
            demand_multiplier = random.uniform(3.0, 4.0)

    total_expected_patrons: int = 0
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

    strategy: str = request.price_strategy
    allowed_lifestyles: List[str] = []
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

    all_npcs: List[Dict[str, Any]] = list(db.npcs.find())
    if not all_npcs:
        all_npcs = get_fallback_npcs()
        
    valid_npcs: List[Dict[str, Any]] = [npc for npc in all_npcs if npc.get("lifestyle", "Modest") in allowed_lifestyles]
    if not valid_npcs:
        valid_npcs = all_npcs 
        
    daily_visitors: List[Dict[str, Any]] = [random.choice(valid_npcs) for _ in range(total_expected_patrons)]
    
    inventory_db = list(db.inventory.find({"stock_bottle_quantity": {"$gt": 0}}))
    inventory_state: Dict[str, Any] = {str(item["_id"]): item for item in inventory_db}

    hours_range: List[int] = []
    if request.close_hour <= request.open_hour:
        hours_range = list(range(request.open_hour, 24)) + list(range(0, request.close_hour))
    else:
        hours_range = list(range(request.open_hour, request.close_hour))

    if not hours_range:
        hours_range = [request.open_hour]

    active_patrons: List[Dict[str, Any]] = []
    customer_receipts: List[Dict[str, Any]] = []
    consolidated_sales: Dict[str, Any] = {}
    hourly_feedback: Dict[str, Any] = {}
    
    total_gross_sales: float = 0.0
    total_cost_of_goods: float = 0.0

    for current_hour_idx, hr_val in enumerate(hours_range):
        hr_label: str = f"{hr_val}:00"
        active_patrons = [p for p in active_patrons if p["departure_idx"] > current_hour_idx]
        arrivals_count: int = max(0, int(total_expected_patrons / len(hours_range)) + random.randint(-2, 5))
        
        for _ in range(arrivals_count):
            if not daily_visitors:
                break
            visitor: Dict[str, Any] = daily_visitors.pop(0)
            duration: int = random.randint(1, 3)
            customer_name: str = f"{visitor.get('first_name', '')} {visitor.get('last_name', '')}".strip()
            lifestyle: str = visitor.get("lifestyle", "Modest")
            
            active_patrons.append({
                "name": customer_name,
                "departure_idx": current_hour_idx + duration
            })
            
            available_items: List[Dict[str, Any]] = [item for item in inventory_state.values() if item["stock_bottle_quantity"] > 0]
            affordable_items: List[Dict[str, Any]] = []
            
            if lifestyle in ["Squalid", "Poor"]:
                affordable_items = [i for i in available_items if (i.get("sell_price_serving_copper", 0) / 100.0) <= 0.5]
            elif lifestyle == "Modest":
                affordable_items = [i for i in available_items if 0.1 <= (i.get("sell_price_serving_copper", 0) / 100.0) <= 2.0]
            elif lifestyle == "Comfortable":
                affordable_items = [i for i in available_items if 1.0 <= (i.get("sell_price_serving_copper", 0) / 100.0) <= 10.0]
            else: 
                affordable_items = [i for i in available_items if (i.get("sell_price_serving_copper", 0) / 100.0) >= 5.0]

            if not affordable_items and available_items:
                affordable_items = available_items

            receipt_items: List[Dict[str, Any]] = []
            receipt_total: float = 0.0
            num_items_to_buy: int = random.randint(1, 3)
            
            for _ in range(num_items_to_buy):
                if affordable_items:
                    chosen_item: Dict[str, Any] = random.choice(affordable_items)
                    
                    is_buying_bottle: bool = False
                    if lifestyle in ["Aristocratic", "Wealthy"] and random.random() < 0.3:
                        is_buying_bottle = True
                    elif lifestyle == "Comfortable" and random.random() < 0.1:
                        is_buying_bottle = True

                    if is_buying_bottle:
                        stock_deduction: float = 1.0
                        item_label: str = f"{chosen_item['item_name']} (Bottle)"
                        price_in_gp: float = (chosen_item.get("sell_price_bottle_copper", 0) / 100.0)
                        cost_in_gp: float = (chosen_item.get("unit_cost_copper", 0) / max(1, chosen_item.get("bottles_per_order_unit", 1))) / 100.0
                    else:
                        stock_deduction = 1.0 / max(1, chosen_item.get("servings_per_bottle", 1))
                        item_label = f"{chosen_item['item_name']} ({chosen_item.get('serve_size', 'Serve')})"
                        price_in_gp = (chosen_item.get("sell_price_serving_copper", 0) / 100.0)
                        cost_in_gp = (chosen_item.get("cost_per_serving_copper", 0) / 100.0)
                        
                    if chosen_item["stock_bottle_quantity"] >= stock_deduction:
                        chosen_item["stock_bottle_quantity"] -= stock_deduction
                        
                        receipt_items.append({"name": item_label, "qty": 1, "price": price_in_gp})
                        receipt_total += price_in_gp
                        
                        total_gross_sales += price_in_gp
                        total_cost_of_goods += cost_in_gp
                        
                        if item_label not in consolidated_sales:
                            consolidated_sales[item_label] = {
                                "qty": 0, 
                                "total": 0.0, 
                                "id": str(chosen_item["_id"]),
                                "original_item_name": chosen_item["item_name"],
                                "stock_deduction": 0.0
                            }
                        consolidated_sales[item_label]["qty"] += 1
                        consolidated_sales[item_label]["total"] += price_in_gp
                        consolidated_sales[item_label]["stock_deduction"] += stock_deduction
                        
                        affordable_items = [i for i in affordable_items if i["stock_bottle_quantity"] > 0]

            if receipt_items:
                customer_receipts.append({
                    "name": customer_name,
                    "lifestyle": lifestyle,
                    "hour": hr_label,
                    "items": receipt_items,
                    "total": receipt_total
                })

        hourly_feedback[hr_label] = [p["name"] for p in active_patrons]

    final_auto_sales: List[Dict[str, Any]] = []
    for item_label, data in consolidated_sales.items():
        final_auto_sales.append({
            "item_name": item_label, 
            "original_item_name": data["original_item_name"],
            "quantity": data["qty"], 
            "stock_deduction": data["stock_deduction"],
            "total_price": data["total"], 
            "inv_id": data["id"]
        })

    total_profit: float = total_gross_sales - total_cost_of_goods

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
def save_day_data(request: SaveDayRequest) -> Dict[str, Any]:
    date_str: str = request.calendar_date
    if request.is_closed:
        closed_entry: Dict[str, Any] = {
            "entry_type": "Expense", 
            "description": "Closed for Day", 
            "amount": 0.0, 
            "frequency": "Once", 
            "entry_date": date_str
        }
        db.ledger.insert_one(closed_entry)
        return {"status": "Day Saved (Closed)", "restocks": []}

    total_income: float = 0.0
    for sale in request.sales:
        total_income += sale.total_price
        db.sales.insert_one(sale.dict())
        inv_item = db.inventory.find_one({"item_name": sale.original_item_name})
        if inv_item:
            new_stock: float = max(0, inv_item["stock_bottle_quantity"] - sale.stock_deduction)
            db.inventory.update_one({"_id": inv_item["_id"]}, {"$set": {"stock_bottle_quantity": new_stock}})

    if total_income > 0:
        ledger_income: Dict[str, Any] = {
            "entry_type": "Income", 
            "description": f"Daily Bar Sales - {date_str}", 
            "amount": total_income, 
            "frequency": "Once", 
            "entry_date": date_str
        }
        db.ledger.insert_one(ledger_income)
        if gc is not None:
            ledger_sheet.append_row([date_str, "Income", ledger_income["description"], total_income])

    restock_messages: List[str] = []
    all_inventory: List[Dict[str, Any]] = list(db.inventory.find())
    for inv in all_inventory:
        current_stock: float = inv.get("stock_bottle_quantity", 0)
        restock_lvl: int = inv.get("reorder_level_bottles", 0)
        
        if current_stock <= restock_lvl:
            target_stock: int = inv.get("target_restock_bottles", restock_lvl * 3)
            bottles_needed: float = target_stock - current_stock
            bottles_per_unit: int = inv.get("bottles_per_order_unit", 1)
            
            units_to_order: int = int(math.ceil(bottles_needed / bottles_per_unit))
            items_received: int = units_to_order * bottles_per_unit
            total_order_cost_gp: float = (units_to_order * inv.get("unit_cost_copper", 0.0)) / 100.0
            
            db.inventory.update_one({"_id": inv["_id"]}, {"$inc": {"stock_bottle_quantity": items_received}})
            desc: str = f"Auto-Restock: {units_to_order}x {inv.get('order_unit', 'Unit')} of {inv['item_name']}"
            db.ledger.insert_one({
                "entry_type": "Expense", 
                "description": desc, 
                "amount": total_order_cost_gp, 
                "frequency": "Once", 
                "entry_date": date_str
            })
            restock_messages.append(f"{desc} (Cost: {total_order_cost_gp} gp)")

    from routers.inventory import sync_inventory_to_csv
    sync_inventory_to_csv()
    
    return {"status": "Day Saved Successfully", "restocks": restock_messages}