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
                # 1. Skip truly empty rows or rows that are just commas
                if not row or all(cell.strip() == "" for cell in row):
                    continue
                
                # 2. Strict Data Row Validation
                # We only process the row as data if:
                # - It has at least 18 columns.
                # - Column A (Category) is not empty.
                # - Column D (index 3) and Column E (index 4) are strictly numeric.
                is_data_row = False
                if len(row) >= 18 and row[0].strip():
                    try:
                        # Attempt to parse key numeric columns to confirm this is data
                        float(row[3].strip())
                        float(row[4].strip())
                        # Also ensure Column I (index 8) isn't accidentally being parsed as a number
                        is_data_row = True
                    except ValueError:
                        is_data_row = False
                
                if is_data_row:
                    try:
                        # 3. Explicit Mapping with individual float/int protection
                        # Index Mapping for 18-column format:
                        # 0: Category, 1: Item, 2: Unit Name, 3: Bottles/Order Unit, 4: Cost Copper
                        # 5: Calc Unit Cost, 6: Sell Price Bottle, 7: Bottle Margin
                        # 8: SERVING SIZE (String), 9: Servings Per Bottle, 10: Calc Serve Cost
                        # 11: Sell Price Serving, 12: Serving Margin, 13: Current Stock
                        # 14: Target Restock, 15: Reorder Level, 16: Status, 17: Reorder Qty
                        
                        items.append({
                            "category": row[0].strip(),
                            "item_name": row[1].strip(),
                            "order_unit": row[2].strip(),
                            "order_quantity": int(float(row[3].strip() or 1)),
                            "unit_cost_copper": float(row[4].strip() or 0),
                            "qty_per_unit": int(float(row[9].strip() or 1)),
                            "serve_size": str(row[8].strip()),  # Explicitly keep as string
                            "cost_per_item_copper": float(row[10].strip() or 0),
                            "sell_price_copper": float(row[11].strip() or 0),
                            "margin_copper": float(row[12].strip() or 0),
                            "stock_unit_quantity": int(float(row[13].strip() or 0)),
                            "reorder_level": int(float(row[15].strip() or 0)),
                            "status": row[16].strip() if len(row) > 16 else "OK",
                            "reorder_quantity": int(float(row[17].strip() or 0)) if len(row) > 17 else 0
                        })
                    except (ValueError, IndexError) as e:
                        print(f"Skipping row due to mapping error: {row}. Error: {e}")
                else:
                    # Capture headers and decorative rows to maintain structure for syncing
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
        
        # Write preserved headers/decorative rows first
        if inventory_csv_headers:
            for header_row in inventory_csv_headers:
                writer.writerow(header_row)
        else:
            # Fallback 18-column header structure
            writer.writerow(["CATEGORY", "ITEM", "UNIT NAME", "BOTTLES PER ORDER UNIT", "COST IN COPPER", "CALCULATED UNIT COST", "SELL PRICE PER BOTTLE", "BOTTLE MARGIN", "SERVING SIZE", "SERVINGS PER BOTTLE", "CALCULATED SERVE COST", "SELL PRICE PER SERVING", "SERVING MARGIN", "CURRENT STOCK ( IN BOTTLES)", "TARGET RESTOCK LEVEL", "REORDER LEVEL ( IN BOTTLES )", "STATUS", "REORDER QUANTITY"])
            
        # Group and sort by category then item name to keep simulation structure
        items.sort(key=lambda x: (x.get("category", ""), x.get("item_name", "")))
        for item in items:
            writer.writerow([
                item.get("category", ""),
                item.get("item_name", ""),
                item.get("order_unit", ""),
                item.get("order_quantity", 1),
                item.get("unit_cost_copper", 0.0),
                0,  # index 5 placeholder
                0,  # index 6 placeholder
                0,  # index 7 placeholder
                str(item.get("serve_size", "")),
                item.get("qty_per_unit", 1),
                item.get("cost_per_item_copper", 0.0),
                item.get("sell_price_copper", 0.0),
                item.get("margin_copper", 0.0),
                item.get("stock_unit_quantity", 0),
                0,  # index 14 placeholder
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