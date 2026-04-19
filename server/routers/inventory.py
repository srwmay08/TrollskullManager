import csv
import math
from fastapi import APIRouter
from bson.objectid import ObjectId

from models import InventoryItem
from database import db

router = APIRouter()

# Global list to capture decorative headers dynamically
inventory_csv_headers = []


def clean_inventory_csv() -> list:
    global inventory_csv_headers
    items = []
    inventory_csv_headers.clear()
    try:
        with open("inventory.csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or all(cell.strip() == "" for cell in row):
                    continue
                
                is_data_row = False
                if len(row) >= 18 and row[0].strip():
                    try:
                        float(row[3].strip())
                        float(row[4].strip())
                        is_data_row = True
                    except ValueError:
                        is_data_row = False
                
                if is_data_row:
                    try:
                        # Mapping matches 18-column structure in provided CSV
                        items.append({
                            "category": row[0].strip(),
                            "item_name": row[1].strip(),
                            "order_unit": row[2].strip(),
                            "bottles_per_order_unit": int(float(row[3].strip() or 1)),
                            "unit_cost_copper": float(row[4].strip() or 0),
                            "servings_per_bottle": int(float(row[9].strip() or 1)),
                            "serve_size": str(row[8].strip()),
                            "cost_per_serving_copper": float(row[10].strip() or 0),
                            "sell_price_serving_copper": float(row[11].strip() or 0),
                            "sell_price_bottle_copper": float(row[6].strip() or 0),
                            "margin_serving_copper": float(row[12].strip() or 0),
                            "stock_bottle_quantity": float(row[13].strip() or 0),
                            "target_restock_bottles": int(float(row[14].strip() or 0)),
                            "reorder_level_bottles": int(float(row[15].strip() or 0)),
                            "status": row[16].strip() if len(row) > 16 else "OK",
                            "reorder_quantity_units": int(float(row[17].strip() or 0))
                        })
                    except (ValueError, IndexError) as e:
                        print(f"Skipping row due to mapping error: {row}. Error: {e}")
                else:
                    inventory_csv_headers.append(row)
    except Exception as e:
        print(f"CSV Load Error: {e}")
    return items


def sync_inventory_to_csv() -> None:
    items = list(db.inventory.find({}, {"_id": 0}))
    if not items:
        return
    
    with open("inventory.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        if inventory_csv_headers:
            for header_row in inventory_csv_headers:
                writer.writerow(header_row)
        else:
            writer.writerow([
                "CATEGORY", "ITEM", "UNIT NAME", "BOTTLES PER ORDER UNIT", 
                "COST IN COPPER", "CALCULATED UNIT COST", "SELL PRICE PER BOTTLE", 
                "BOTTLE MARGIN", "SERVING SIZE", "SERVINGS PER BOTTLE", 
                "CALCULATED SERVE COST", "SELL PRICE PER SERVING", "SERVING MARGIN", 
                "CURRENT STOCK ( IN BOTTLES)", "TARGET RESTOCK LEVEL", 
                "REORDER LEVEL ( IN BOTTLES )", "STATUS", "REORDER QUANTITY"
            ])
            
        items.sort(key=lambda x: (x.get("category", ""), x.get("item_name", "")))
        for item in items:
            cost_per_bottle = item.get("unit_cost_copper", 0) / max(item.get("bottles_per_order_unit", 1), 1)
            bottle_margin = item.get("sell_price_bottle_copper", 0) - cost_per_bottle
            
            writer.writerow([
                item.get("category", ""),
                item.get("item_name", ""),
                item.get("order_unit", ""),
                item.get("bottles_per_order_unit", 1),
                item.get("unit_cost_copper", 0.0),
                cost_per_bottle,
                item.get("sell_price_bottle_copper", 0.0),
                bottle_margin,
                str(item.get("serve_size", "")),
                item.get("servings_per_bottle", 1),
                item.get("cost_per_serving_copper", 0.0),
                item.get("sell_price_serving_copper", 0.0),
                item.get("margin_serving_copper", 0.0),
                item.get("stock_bottle_quantity", 0.0),
                item.get("target_restock_bottles", 0),
                item.get("reorder_level_bottles", 0),
                item.get("status", "OK"),
                item.get("reorder_quantity_units", 0)
            ])


@router.get("/api/inventory/sync")
def trigger_inventory_sync():
    items = clean_inventory_csv()
    if items:
        db.inventory.delete_many({})
        db.inventory.insert_many(items)
        return {"status": "Inventory re-synced from local CSV successfully.", "count": len(items)}
    return {"status": "No items found to sync."}


@router.get("/api/inventory")
def get_inventory():
    inventory_cursor = db.inventory.find()
    inventory_list = []
    for item in inventory_cursor:
        item["_id"] = str(item["_id"])
        inventory_list.append(item)
    return inventory_list


@router.put("/api/inventory/{item_id}")
def update_inventory(item_id: str, item: InventoryItem):
    db.inventory.update_one({"_id": ObjectId(item_id)}, {"$set": item.dict()})
    sync_inventory_to_csv()
    return {"status": "Updated"}