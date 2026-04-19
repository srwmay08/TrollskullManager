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
                if not row or all(cell.strip() == "" for cell in row):
                    continue
                
                # Check if it's a data row: Category (0) must have text, 
                # and Bottles Per Unit (3) must be numeric.
                is_data_row = False
                if len(row) >= 18 and row[0].strip():
                    try:
                        # Validate that Column D (index 3) is numeric (Bottles Per Unit)
                        float(row[3] or 0)
                        # Validate that Column E (index 4) is numeric (Cost in Copper)
                        float(row[4] or 0)
                        is_data_row = True
                    except ValueError:
                        is_data_row = False
                
                if is_data_row:
                    try:
                        # Aligned mapping for the 18-column "Bottle Focus" structure
                        items.append({
                            "category": row[0].strip(),
                            "item_name": row[1].strip(),
                            "order_unit": row[2].strip(),
                            "order_quantity": int(float(row[3] or 1)),
                            "unit_cost_copper": float(row[4] or 0),
                            "qty_per_unit": int(float(row[9] or 1)),      # index 9: Servings Per Bottle
                            "serve_size": str(row[8].strip()),            # index 8: Serving Size (Explicit String)
                            "cost_per_item_copper": float(row[10] or 0),  # index 10: Calc Serve Cost
                            "sell_price_copper": float(row[11] or 0),     # index 11: Sell Price Serving
                            "margin_copper": float(row[12] or 0),         # index 12: Serving Margin
                            "stock_unit_quantity": int(float(row[13] or 0)), # index 13: Current Stock
                            "reorder_level": int(float(row[15] or 0)),    # index 15: Reorder Level
                            "status": row[16] if len(row) > 16 else "OK", # index 16: Status
                            "reorder_quantity": int(float(row[17] or 0)) if len(row) > 17 else 0 # index 17: Reorder Qty
                        })
                    except (ValueError, IndexError) as e:
                        print(f"Skipping row due to number parsing error: {row}. Error: {e}")
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
            # Reconstruct the 18-column header if metadata is lost
            writer.writerow(["CATEGORY", "ITEM", "UNIT NAME", "BOTTLES PER ORDER UNIT", "COST IN COPPER", "CALCULATED UNIT COST", "SELL PRICE PER BOTTLE", "BOTTLE MARGIN", "SERVING SIZE", "SERVINGS PER BOTTLE", "CALCULATED SERVE COST", "SELL PRICE PER SERVING", "SERVING MARGIN", "CURRENT STOCK ( IN BOTTLES)", "TARGET RESTOCK LEVEL", "REORDER LEVEL ( IN BOTTLES )", "STATUS", "REORDER QUANTITY"])
            
        # Grouping by category and name to maintain simulation structure
        items.sort(key=lambda x: (x.get("category", ""), x.get("item_name", "")))
        for item in items:
            writer.writerow([
                item.get("category", ""),
                item.get("item_name", ""),
                item.get("order_unit", ""),
                item.get("order_quantity", 1),
                item.get("unit_cost_copper", 0.0),
                0,  # index 5: Calculated Unit Cost placeholder
                0,  # index 6: Bottle Sell placeholder
                0,  # index 7: Bottle Margin placeholder
                str(item.get("serve_size", "")),
                item.get("qty_per_unit", 1),
                item.get("cost_per_item_copper", 0.0),
                item.get("sell_price_copper", 0.0),
                item.get("margin_copper", 0.0),
                item.get("stock_unit_quantity", 0),
                0,  # index 14: Target Restock Level placeholder
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