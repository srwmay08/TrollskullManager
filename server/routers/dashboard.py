import random
import csv
import math
import re
from typing import Dict
from typing import List
from typing import Any
from typing import Tuple

from fastapi import APIRouter

from models import RollRequest
from models import SaveDayRequest
from database import db
from database import gc
from database import sales_sheet
from database import ledger_sheet

router = APIRouter()

def get_fallback_npcs() -> List[Dict[str, Any]]:
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

def get_harptos_date(date_str: str) -> Tuple[int, int, int]:
    months = [
        "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn",
        "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"
    ]
    day = 1
    year = 1492
    month_idx = 1
    
    year_match = re.search(r'\b(\d{4})\b', date_str)
    if year_match:
        year = int(year_match.group(1))
    
    clean_str = date_str
    if year_match:
        clean_str = clean_str.replace(str(year), '')
        
    day_match = re.search(r'\b([1-9]|[12][0-9]|30)\b', clean_str)
    if day_match:
        day = int(day_match.group(1))
        
    for idx, m in enumerate(months):
        if m.lower() in date_str.lower():
            month_idx = idx + 1
            break
            
    return month_idx, day, year

def add_harptos_days(month: int, day: int, year: int, days: int) -> Tuple[int, int, int]:
    new_day = day + days
    new_month = month
    new_year = year
    
    while new_day > 30:
        new_day -= 30
        new_month += 1
        if new_month > 12:
            new_month = 1
            new_year += 1
            
    return new_month, new_day, new_year

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
            "daily_events": [],
            "is_closed": True
        }

    staff_cursor = list(db.staff.find())
    
    total_staff_bonus: int = 0
    entertainer_active: bool = False
    bouncer_active: bool = False
    
    for staff in staff_cursor:
        staff_keys = {k.lower().strip(): k for k in staff.keys()}
        
        for key in staff_keys:
            if 'service' in key or 'security' in key:
                try:
                    total_staff_bonus += int(staff[staff_keys[key]])
                except (ValueError, TypeError):
                    pass
                    
        if "role" in staff_keys:
            role_str = str(staff[staff_keys["role"]]).lower().strip()
            if "entertainer" in role_str:
                entertainer_active = True
            elif any(x in role_str for x in ["bouncer", "guard", "security"]):
                bouncer_active = True

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

    if entertainer_active and "Comfortable" not in allowed_lifestyles:
        allowed_lifestyles.append("Comfortable")

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
    triggered_events: List[str] = []
    
    total_gross_sales: float = 0.0
    total_cost_of_goods: float = 0.0
    breakage_costs: float = 0.0

    for current_hour_idx, hr_val in enumerate(hours_range):
        hr_label: str = f"{hr_val}:00"
        active_patrons = [p for p in active_patrons if p["departure_idx"] > current_hour_idx]
        arrivals_count: int = max(0, int(total_expected_patrons / len(hours_range)) + random.randint(-2, 5))
        
        for _ in range(arrivals_count):
            if not daily_visitors:
                break
            visitor: Dict[str, Any] = daily_visitors.pop(0)
            duration: int = random.randint(1, 3)
            
            v_keys = {k.lower(): k for k in visitor.keys()}
            f_name = visitor[v_keys["first_name"]] if "first_name" in v_keys else ""
            l_name = visitor[v_keys["last_name"]] if "last_name" in v_keys else ""
            customer_name: str = f"{f_name} {l_name}".strip()
            lifestyle: str = visitor.get("lifestyle", "Modest")
            
            if visitor.get("is_quest_giver") and visitor.get("quest_hook_text"):
                trigger_chance = float(visitor.get("quest_trigger_chance", 0.05))
                if random.random() <= trigger_chance:
                    hook = f"{hr_label} - EVENT: {customer_name} has arrived. {visitor.get('quest_hook_text')}"
                    if hook not in triggered_events:
                        triggered_events.append(hook)

            if strategy == "Dive" and random.random() < 0.02:
                if bouncer_active:
                    triggered_events.append(f"{hr_label} - Bouncer prevented a brawl involving {customer_name}.")
                else:
                    breakage_penalty = random.uniform(1.0, 5.0)
                    breakage_costs += breakage_penalty
                    triggered_events.append(f"{hr_label} - A brawl broke out near {customer_name}. {round(breakage_penalty, 2)} gp in damages.")

            active_patrons.append({
                "name": customer_name,
                "departure_idx": current_hour_idx + duration
            })
            
            available_items: List[Dict[str, Any]] = [item for item in inventory_state.values() if item.get("stock_bottle_quantity", 0) > 0]
            affordable_items: List[Dict[str, Any]] = []
            
            if lifestyle in ["Squalid", "Poor"]:
                affordable_items = [i for i in available_items if (float(i.get("sell_price_serving_copper", 0)) / 100.0) <= 0.5]
            elif lifestyle == "Modest":
                affordable_items = [i for i in available_items if 0.1 <= (float(i.get("sell_price_serving_copper", 0)) / 100.0) <= 2.0]
            elif lifestyle == "Comfortable":
                affordable_items = [i for i in available_items if 1.0 <= (float(i.get("sell_price_serving_copper", 0)) / 100.0) <= 10.0]
            else: 
                affordable_items = [i for i in available_items if (float(i.get("sell_price_serving_copper", 0)) / 100.0) >= 5.0]

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
                        item_label: str = f"{chosen_item.get('item_name', 'Unknown')} (Bottle)"
                        price_in_gp: float = (float(chosen_item.get("sell_price_bottle_copper", 0)) / 100.0)
                        cost_in_gp: float = (float(chosen_item.get("unit_cost_copper", 0)) / max(1, float(chosen_item.get("bottles_per_order_unit", 1)))) / 100.0
                    else:
                        stock_deduction = 1.0 / max(1, float(chosen_item.get("servings_per_bottle", 1)))
                        item_label = f"{chosen_item.get('item_name', 'Unknown')} ({chosen_item.get('serve_size', 'Serve')})"
                        price_in_gp = (float(chosen_item.get("sell_price_serving_copper", 0)) / 100.0)
                        cost_in_gp = (float(chosen_item.get("cost_per_serving_copper", 0)) / 100.0)
                        
                    if float(chosen_item.get("stock_bottle_quantity", 0)) >= stock_deduction:
                        chosen_item["stock_bottle_quantity"] = float(chosen_item["stock_bottle_quantity"]) - stock_deduction
                        
                        receipt_items.append({"name": item_label, "qty": 1, "price": price_in_gp})
                        receipt_total += price_in_gp
                        
                        total_gross_sales += price_in_gp
                        total_cost_of_goods += cost_in_gp
                        
                        if item_label not in consolidated_sales:
                            consolidated_sales[item_label] = {
                                "qty": 0, 
                                "total": 0.0, 
                                "id": str(chosen_item["_id"]),
                                "original_item_name": chosen_item.get("item_name", "Unknown"),
                                "stock_deduction": 0.0
                            }
                        consolidated_sales[item_label]["qty"] += 1
                        consolidated_sales[item_label]["total"] += price_in_gp
                        consolidated_sales[item_label]["stock_deduction"] += stock_deduction
                        
                        affordable_items = [i for i in affordable_items if float(i.get("stock_bottle_quantity", 0)) > 0]

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

    total_profit: float = total_gross_sales - total_cost_of_goods - breakage_costs

    return {
        "total_roll": total_roll, 
        "auto_sales": final_auto_sales, 
        "receipts": customer_receipts, 
        "hourly_feedback": hourly_feedback, 
        "total_gross": round(total_gross_sales, 2),
        "total_profit": round(total_profit, 2),
        "daily_events": triggered_events,
        "is_closed": False
    }

@router.post("/api/save_day")
def save_day_data(request: SaveDayRequest) -> Dict[str, Any]:
    date_str: str = request.calendar_date
    c_month, c_day, c_year = get_harptos_date(date_str)
    
    if request.is_closed:
        closed_entry: Dict[str, Any] = {
            "entry_type": "Expense", 
            "description": "Closed for Day", 
            "amount": 0.0, 
            "frequency": "Once", 
            "entry_date": date_str
        }
        db.ledger.insert_one(closed_entry)
        return {"status": "Day Saved (Closed)", "restocks": [], "payroll": []}

    shipment_messages: List[str] = []
    pending_shipments = list(db.shipments.find({"status": "Pending"}))
    
    for shipment in pending_shipments:
        s_year = int(shipment.get("arrival_year", 1492))
        s_month = int(shipment.get("arrival_month", 1))
        s_day = int(shipment.get("arrival_day", 1))
        
        is_arrived = False
        if s_year < c_year:
            is_arrived = True
        elif s_year == c_year and s_month < c_month:
            is_arrived = True
        elif s_year == c_year and s_month == c_month and s_day <= c_day:
            is_arrived = True
            
        if is_arrived:
            total_cost = float(shipment.get("total_cost", 0.0))
            vendor_name = shipment.get("vendor_name", "Unknown Vendor")
            
            items_received_list = []
            for item in shipment.get("items", []):
                item_name = item.get("item_name")
                qty = float(item.get("quantity_bottles", 0))
                
                if item_name and qty > 0:
                    db.inventory.update_one(
                        {"item_name": item_name},
                        {"$inc": {"stock_bottle_quantity": qty}}
                    )
                    items_received_list.append(f"{qty}x {item_name}")
            
            desc = f"Delivery Arrived: {vendor_name} (" + ", ".join(items_received_list) + ")"
            db.ledger.insert_one({
                "entry_type": "Expense",
                "description": desc,
                "amount": total_cost,
                "frequency": "Once",
                "entry_date": date_str
            })
            
            if gc is not None and ledger_sheet is not None:
                try:
                    ledger_sheet.append_row([date_str, "Expense", desc, total_cost])
                except Exception:
                    pass
                    
            db.shipments.update_one({"_id": shipment["_id"]}, {"$set": {"status": "Delivered"}})
            shipment_messages.append(f"Received delivery from {vendor_name} for {round(total_cost, 2)} gp.")

    total_income: float = 0.0
    for sale in request.sales:
        total_income += sale.total_price
        db.sales.insert_one(sale.dict())
        
        all_inv = list(db.inventory.find())
        for inv_doc in all_inv:
            inv_keys = {k.lower(): k for k in inv_doc.keys()}
            if "item_name" in inv_keys and str(inv_doc[inv_keys["item_name"]]) == sale.original_item_name:
                stock_key = inv_keys.get("stock_bottle_quantity", "stock_bottle_quantity")
                new_stock: float = max(0, float(inv_doc.get(stock_key, 0)) - sale.stock_deduction)
                db.inventory.update_one({"_id": inv_doc["_id"]}, {"$set": {stock_key: new_stock}})
                break

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
    orders_by_vendor: Dict[str, List[Dict[str, Any]]] = {}
    
    for inv in all_inventory:
        inv_keys = {k.lower(): k for k in inv.keys()}
        stock_key = inv_keys.get("stock_bottle_quantity", "stock_bottle_quantity")
        reorder_key = inv_keys.get("reorder_level_bottles", "reorder_level_bottles")
        target_key = inv_keys.get("target_restock_bottles", "target_restock_bottles")
        b_per_u_key = inv_keys.get("bottles_per_order_unit", "bottles_per_order_unit")
        cost_key = inv_keys.get("unit_cost_copper", "unit_cost_copper")
        name_key = inv_keys.get("item_name", "item_name")

        current_stock: float = float(inv.get(stock_key, 0))
        restock_lvl: int = int(inv.get(reorder_key, 0))
        
        pending_orders = list(db.shipments.find({"status": "Pending", "items.item_name": inv.get(name_key)}))
        incoming_stock = 0.0
        for po in pending_orders:
            for item in po.get("items", []):
                if item.get("item_name") == inv.get(name_key):
                    incoming_stock += float(item.get("quantity_bottles", 0))
                    
        effective_stock = current_stock + incoming_stock
        
        if effective_stock <= restock_lvl and restock_lvl > 0:
            target_stock: int = int(inv.get(target_key, restock_lvl * 3))
            bottles_needed: float = target_stock - current_stock
            bottles_per_unit: int = int(inv.get(b_per_u_key, 1))
            
            units_to_order: int = int(math.ceil(bottles_needed / bottles_per_unit))
            items_received: int = units_to_order * bottles_per_unit
            base_cost_gp: float = (units_to_order * float(inv.get(cost_key, 0.0))) / 100.0
            
            vendor_name = inv.get("vendor_name", "Local Supplier")
            if not vendor_name:
                vendor_name = "Local Supplier"
                
            if vendor_name not in orders_by_vendor:
                orders_by_vendor[vendor_name] = []
                
            orders_by_vendor[vendor_name].append({
                "inv": inv,
                "units": units_to_order,
                "bottles": items_received,
                "cost": base_cost_gp
            })
            
    for v_name, items in orders_by_vendor.items():
        vendor = db.vendors.find_one({"name": v_name})
        delivery_days = 3
        holiday_multiplier = 1.0
        
        if vendor:
            delivery_days = int(vendor.get("base_delivery_days", 3))
            holiday_multiplier = float(vendor.get("holiday_premium_multiplier", 1.0))
            
        a_month, a_day, a_year = add_harptos_days(c_month, c_day, c_year, delivery_days)
        
        shipment_items = []
        total_shipment_cost = 0.0
        
        for order in items:
            final_cost = order["cost"] * holiday_multiplier
            total_shipment_cost += final_cost
            shipment_items.append({
                "item_name": order["inv"].get("item_name", "Unknown Item"),
                "quantity_bottles": order["bottles"],
                "cost": final_cost
            })
            
        db.shipments.insert_one({
            "vendor_name": v_name,
            "items": shipment_items,
            "arrival_month": a_month,
            "arrival_day": a_day,
            "arrival_year": a_year,
            "total_cost": total_shipment_cost,
            "status": "Pending"
        })
        
        restock_messages.append(f"Ordered {len(items)} item(s) from {v_name} for {round(total_shipment_cost, 2)} gp. (Arrives: {a_month}/{a_day}/{a_year})")

    payroll_messages: List[str] = []
    if request.pay_wages:
        staff_cursor = db.staff.find()
        for staff in staff_cursor:
            s_keys = {k.lower(): k for k in staff.keys()}
            wage_key = s_keys.get("wage", "wage")
            name_key = s_keys.get("name", "name")
            role_key = s_keys.get("role", "role")
            
            wage: float = float(staff.get(wage_key, 0.0))
            if wage > 0:
                desc = f"Payroll: {staff.get(name_key, 'Unknown Staff')} ({staff.get(role_key, 'Staff')})"
                db.ledger.insert_one({
                    "entry_type": "Expense",
                    "description": desc,
                    "amount": wage,
                    "frequency": "Once",
                    "entry_date": date_str
                })
                payroll_messages.append(f"Paid {wage} gp to {staff.get(name_key, 'Unknown Staff')}")

    from routers.inventory import sync_collection_to_csv
    sync_collection_to_csv(db.inventory, "inventory.csv")
    
    return {
        "status": "Day Saved Successfully", 
        "restocks": shipment_messages + restock_messages,
        "payroll": payroll_messages
    }