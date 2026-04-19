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
                # Skip empty rows
                if not row or all(cell.strip() == "" for cell in row):
                    continue
                
                # Data row detection: 
                # 1. Must have at least 18 columns.
                # 2. Column A (Category) must not be empty.
                # 3. Column D (Bottles per unit) must be a digit.
                is_data_row = False
                if len(row) >= 18 and row[0].strip():
                    val_d = row[3].strip().replace('.', '', 1)
                    if val_d.isdigit():
                        is_data_row = True
                
                if is_data_row:
                    try:
                        # MAPPING BASED ON YOUR LOG OUTPUT:
                        # 0: Category, 1: Item, 2: Unit Name, 3: Bottles per Order Unit
                        # 4: Cost Copper, 5: Calc Unit Cost, 6: Sell Price Bottle, 7: Bottle Margin
                        # 8: SERVING SIZE (String), 9: Servings Per Bottle
                        # 10: Calc Serve Cost, 11: Sell Price Serving, 12: Serving Margin
                        # 13: Current Stock, 14: Target Restock, 15: Reorder Level
                        # 16: Status, 17: Reorder Quantity
                        
                        items.append({
                            "category": row[0].strip(),
                            "item_name": row[1].strip(),
                            "order_unit": row[2].strip(),
                            "order_quantity": int(float(row[3] or 1)),
                            "unit_cost_copper": float(row[4] or 0),
                            "qty_per_unit": int(float(row[9] or 1)),
                            "serve_size": str(row[8].strip()),  # Explicitly string
                            "cost_per_item_copper": float(row[10] or 0),
                            "sell_price_copper": float(row[11] or 0),
                            "margin_copper": float(row[12] or 0),
                            "stock_unit_quantity": int(float(row[13] or 0)),
                            "reorder_level": int(float(row[15] or 0)),
                            "status": row[16].strip() if len(row) > 16 else "OK",
                            "reorder_quantity": int(float(row[17] or 0)) if len(row) > 17 else 0
                        })
                    except (ValueError, IndexError) as e:
                        print(f"Skipping row due to parsing error: {row}. Error: {e}")
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
            # Fallback 18-column header
            writer.writerow(["CATEGORY", "ITEM", "UNIT NAME", "BOTTLES PER ORDER UNIT", "COST IN COPPER", "CALCULATED UNIT COST", "SELL PRICE PER BOTTLE", "BOTTLE MARGIN", "SERVING SIZE", "SERVINGS PER BOTTLE", "CALCULATED SERVE COST", "SELL PRICE PER SERVING", "SERVING MARGIN", "CURRENT STOCK ( IN BOTTLES)", "TARGET RESTOCK LEVEL", "REORDER LEVEL ( IN BOTTLES )", "STATUS", "REORDER QUANTITY"])
            
        items.sort(key=lambda x: (x.get("category", ""), x.get("item_name", "")))
        for item in items:
            writer.writerow([
                item.get("category", ""),
                item.get("item_name", ""),
                item.get("order_unit", ""),
                item.get("order_quantity", 1),
                item.get("unit_cost_copper", 0.0),
                0,  # placeholder index 5
                0,  # placeholder index 6
                0,  # placeholder index 7
                str(item.get("serve_size", "")),
                item.get("qty_per_unit", 1),
                item.get("cost_per_item_copper", 0.0),
                item.get("sell_price_copper", 0.0),
                item.get("margin_copper", 0.0),
                item.get("stock_unit_quantity", 0),
                0,  # placeholder index 14
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