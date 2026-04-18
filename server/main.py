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
        if val is None or str(val).strip() == "": return 0
        return int(float(val))
    except Exception:
        return 0

def parse_float(val):
    try:
        if val is None or str(val).strip() == "": return 0.0
        return float(val)
    except Exception:
        return 0.0

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    if db.inventory.count_documents({}) == 0:
        if os.path.exists("inventory.csv"):
            inv_list = []
            with open("inventory.csv", mode="r", encoding="utf-8") as f:
                reader = csv.reader(f)
                lines = list(reader)
                current_category = "Uncategorized"
                
                # Skip the two complex header rows
                for row in lines[2:]:
                    if not row or not any(row): continue
                    
                    # If column 1 is filled, but others are mostly empty, it's a category header
                    if row[0].strip() and all(cell.strip() == "" for cell in row[1:5]):
                        current_category = row[0].strip()
                        continue
                    
                    if len(row) >= 13:
                        inv_list.append({
                            "item_name": row[0].strip(),
                            "category": current_category,
                            "order_unit": row[1].strip(),
                            "order_quantity": parse_int(row[2]),
                            "unit_cost_copper": parse_float(row[3]),
                            "qty_per_unit": parse_int(row[4]),
                            "serve_size": row[5].strip(),
                            "cost_per_item_copper": parse_float(row[6]),
                            "sell_price_copper": parse_float(row[7]),
                            "margin_copper": parse_float(row[8]),
                            "stock_unit_quantity": parse_int(row[9]),
                            "reorder_level": parse_int(row[10]),
                            "status": row[11].strip(),
                            "reorder_quantity": parse_int(row[12])
                        })
            if inv_list:
                db.inventory.insert_many(inv_list)
        else:
            print("inventory.csv not found to rebuild database!")
    
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