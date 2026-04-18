import contextlib
import uvicorn
import csv
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from database import db
from routers import router

def parse_int(val):
    try:
        return int(val)
    except Exception:
        return 0

def parse_float(val):
    try:
        return float(val)
    except Exception:
        return 0.0

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    if db.inventory.count_documents({}) == 0:
        if os.path.exists("inventory.csv"):
            inv_list = []
            with open("inventory.csv", mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    inv_list.append({
                        "item_name": row.get("Item Name", row.get("item_name", "")),
                        "stock_on_hand": parse_int(row.get("Stock on Hand", row.get("stock_on_hand", "0"))),
                        "size_per_unit": row.get("Size per Unit", "Unit"),
                        "qty_per_unit": parse_int(row.get("Qty per Unit", "1")),
                        "order_cost": parse_float(row.get("Order Cost", "0.0")),
                        "cost_per_item": parse_float(row.get("Cost per Item", "0.0")),
                        "base_stock": parse_int(row.get("Base Stock", "0")),
                        "restock_level": parse_int(row.get("Restock Level", "0")),
                        "unit_price": parse_float(row.get("Sale Price", row.get("unit_price", "0.0")))
                    })
            if inv_list:
                db.inventory.insert_many(inv_list)
        else:
            seed_items = [
                {"item_name": "Moradin's Hammerfall", "stock_on_hand": 120, "size_per_unit": "Keg", "qty_per_unit": 60, "order_cost": 30.0, "cost_per_item": 0.5, "base_stock": 240, "restock_level": 40, "unit_price": 2.0},
                {"item_name": "First Frost Art Wine", "stock_on_hand": 10, "size_per_unit": "Case", "qty_per_unit": 6, "order_cost": 60.0, "cost_per_item": 10.0, "base_stock": 24, "restock_level": 6, "unit_price": 25.0},
                {"item_name": "Black Wyvern Porter", "stock_on_hand": 200, "size_per_unit": "Large Keg", "qty_per_unit": 100, "order_cost": 1.0, "cost_per_item": 0.01, "base_stock": 300, "restock_level": 50, "unit_price": 0.04},
                {"item_name": "Gumpfish Stew", "stock_on_hand": 30, "size_per_unit": "Pot", "qty_per_unit": 20, "order_cost": 2.0, "cost_per_item": 0.1, "base_stock": 60, "restock_level": 10, "unit_price": 0.3}
            ]
            db.inventory.insert_many(seed_items)
            
            keys = ["Item Name", "Stock on Hand", "Size per Unit", "Qty per Unit", "Order Cost", "Cost per Item", "Base Stock", "Restock Level", "Sale Price"]
            with open("inventory.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for item in seed_items:
                    writer.writerow({
                        "Item Name": item["item_name"],
                        "Stock on Hand": item["stock_on_hand"],
                        "Size per Unit": item["size_per_unit"],
                        "Qty per Unit": item["qty_per_unit"],
                        "Order Cost": item["order_cost"],
                        "Cost per Item": item["cost_per_item"],
                        "Base Stock": item["base_stock"],
                        "Restock Level": item["restock_level"],
                        "Sale Price": item["unit_price"]
                    })
    
    if db.staff.count_documents({}) == 0:
        seed_staff = [
            {"name": "Lif the Poltergeist", "wage": 0.0, "frequency": "Daily", "bonus": 5},
            {"name": "Bepis Honeymaker (Cook)", "wage": 0.0, "frequency": "Daily", "bonus": 2},
            {"name": "Spider (Warforged Security Tier II)", "wage": 2.0, "frequency": "Daily", "bonus": 4},
            {"name": "Tashlyn Yafeera (Head of Security Tier I)", "wage": 8.0, "frequency": "Daily", "bonus": 8}
        ]
        db.staff.insert_many(seed_staff)

    if db.ledger.count_documents({}) == 0:
        seed_ledger = [
            {"entry_type": "Income", "description": "Ransom of the Twelve", "amount": 11000.0, "frequency": "Once", "entry_date": "Ches 30"}
        ]
        db.ledger.insert_many(seed_ledger)

    if db.npcs.count_documents({}) == 0:
        if os.path.exists("npcs.csv"):
            npc_list = []
            with open("npcs.csv", mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    npc_list.append({
                        "first_name": row.get("First Name", ""),
                        "last_name": row.get("Last Name", ""),
                        "occupation": row.get("Occupation", ""),
                        "lifestyle": row.get("Lifestyle", ""),
                        "faction": row.get("Faction", ""),
                        "age": parse_int(row.get("Age", "")),
                        "bar_disposition": parse_int(row.get("Bar Disposition", "")),
                        "party_disposition": parse_int(row.get("Party Disposition", "")),
                        "nobility_status": row.get("Nobility Status", "Civilian"),
                        "noble_house": row.get("Noble House", ""),
                        "story_connection": row.get("Story Connection", "None"),
                        "pc_affiliation": row.get("PC Affiliation", "None")
                    })
            if npc_list:
                db.npcs.insert_many(npc_list)
        
    print("\n" + "="*50)
    print("TROLLSKULL MANOR SERVER IS RUNNING")
    print("Frontend URL: http://127.0.0.1:8000/")
    print("API Base URL: http://127.0.0.1:8000/api")
    print("="*50 + "\n")
    
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(router)

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    try:
        with open("index.html", "r") as file:
            html_content = file.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        error_html = "<h1>Error: index.html not found.</h1>"
        return HTMLResponse(content=error_html, status_code=404)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)