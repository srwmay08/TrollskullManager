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
                if not row or not any(row):
                    continue
                
                # Pad the row to 14 columns to avoid IndexErrors if some columns are empty
                row += [""] * (14 - len(row))
                
                category = row[0].strip()
                item_name = row[1].strip()
                
                # A true data row should have an Item Name that isn't the header title
                is_data_row = bool(item_name) and item_name != "ITEM" and item_name != "ITEMS / UNIT DETAILS"
                
                if is_data_row:
                    try:
                        items.append({
                            "category": category or "Uncategorized",
                            "item_name": item_name,
                            "order_unit": row[2].strip() or "Unit",
                            "order_quantity": int(row[3].strip() or 1),
                            "unit_cost_copper": float(row[4].strip() or 0.0),
                            "qty_per_unit": int(row[5].strip() or 1),
                            "serve_size": row[6].strip(),
                            "cost_per_item_copper": float(row[7].strip() or 0.0),
                            "sell_price_copper": float(row[8].strip() or 0.0),
                            "margin_copper": float(row[9].strip() or 0.0),
                            "stock_unit_quantity": int(row[10].strip() or 0),
                            "reorder_level": int(row[11].strip() or 0),
                            "status": row[12].strip() or "OK",
                            "reorder_quantity": int(row[13].strip() or 0)
                        })
                    except ValueError as e:
                        print(f"Skipping row due to number parsing error: {row}. Error: {e}")
                        inventory_csv_headers.append(row)
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
            
        items.sort(key=lambda x: x.get("category", ""))
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

# --- STARTUP HOOK ---
# Auto-load the CSV if the database is currently empty
if db.inventory.count_documents({}) == 0:
    print("Inventory database is empty. Attempting to load from inventory.csv...")
    initial_items = clean_inventory_csv()
    if initial_items:
        db.inventory.insert_many(initial_items)
        print(f"Successfully loaded {len(initial_items)} items from CSV.")
    else:
        print("No items could be parsed from inventory.csv.")