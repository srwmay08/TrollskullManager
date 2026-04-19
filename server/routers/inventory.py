import csv
from fastapi import APIRouter
from bson.objectid import ObjectId

from models import InventoryItem
from database import db

router = APIRouter()

# Global list to capture your decorative headers dynamically
inventory_csv_headers = []


def clean_inventory_csv() -> list:
    global inventory_csv_headers
    items = []
    inventory_csv_headers.clear()
    try:
        with open("inventory.csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                
                is_data_row = False
                if len(row) > 4 and row[3].strip().isdigit():
                    try:
                        float(row[4] or 0)
                        is_data_row = True
                    except ValueError:
                        pass
                
                if is_data_row:
                    items.append({
                        "category": row[0],
                        "item_name": row[1],
                        "order_unit": row[2],
                        "order_quantity": int(row[3] or 1),
                        "unit_cost_copper": float(row[4] or 0),
                        "qty_per_unit": int(row[5] or 1),
                        "serve_size": row[6] if len(row) > 6 else "",
                        "cost_per_item_copper": float(row[7] or 0) if len(row) > 7 else 0.0,
                        "sell_price_copper": float(row[8] or 0) if len(row) > 8 else 0.0,
                        "margin_copper": float(row[9] or 0) if len(row) > 9 else 0.0,
                        "stock_unit_quantity": int(row[10] or 0) if len(row) > 10 else 0,
                        "reorder_level": int(row[11] or 0) if len(row) > 11 else 0,
                        "status": row[12] if len(row) > 12 else "OK",
                        "reorder_quantity": int(row[13] or 0) if len(row) > 13 else 0
                    })
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
            writer.writerow(["", "", "ORDER BY", "", "", "ITEMS / UNIT DETAILS", "", "COST PER ITEM", "SELL PRICE IN COPPER", "MARGIN IN COPPER", "STOCK UNIT QUANTITY", "REORDER LEVEL", "STATUS", "REORDER QUANTITY"])
            writer.writerow(["CATEGORY", "ITEM", "UNIT", "QUANTITY", "UNIT COST IN COPPER", "QUANTITY per UNIT", "SERVE SIZE", "", "", "", "", "", "", ""])
            writer.writerow([""] * 14)
            
        items.sort(key=lambda x: (x.get("category", ""), x.get("item_name", "")))
        for item in items:
            writer.writerow([
                item.get("category", ""),
                item.get("item_name", ""),
                item.get("order_unit", ""),
                item.get("order_quantity", 1),
                item.get("unit_cost_copper", 0.0),
                item.get("qty_per_unit", 1),
                item.get("serve_size", ""),
                item.get("cost_per_item_copper", 0.0),
                item.get("sell_price_copper", 0.0),
                item.get("margin_copper", 0.0),
                item.get("stock_unit_quantity", 0),
                item.get("reorder_level", 0),
                item.get("status", "OK"),
                item.get("reorder_quantity", 0)
            ])


@router.get("/api/inventory/sync")
def trigger_inventory_sync():
    items = clean_inventory_csv()
    if items:
        db.inventory.delete_many({})
        db.inventory.insert_many(items)
    return {"status": "Inventory re-synced from local CSV successfully."}


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