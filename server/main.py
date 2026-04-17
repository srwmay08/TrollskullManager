import contextlib
import uvicorn
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pydantic import Field
from pymongo import MongoClient
from bson.objectid import ObjectId
from typing import List
from typing import Optional
from typing import Dict
from typing import Any
import gspread
import random
import datetime
import csv
import os
import re

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["trollskull_tavern"]

try:
    gc = gspread.service_account(filename="creds.json")
    sheet = gc.open("Tavern_Ledger")
    sales_sheet = sheet.worksheet("Sales")
    ledger_sheet = sheet.worksheet("Ledger")
except Exception as e:
    print("Google Sheets connection failed. Operating with MongoDB only.")
    gc = None

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    if db.inventory.count_documents({}) == 0:
        seed_items = [
            {
                "item_name": "Moradin's Hammerfall (Heavy Pour)",
                "stock_on_hand": 60,
                "stock_on_order": 0,
                "units_per": 1,
                "unit_price": 2.0
            },
            {
                "item_name": "First Frost Art Wine (Bottle)",
                "stock_on_hand": 10,
                "stock_on_order": 5,
                "units_per": 5,
                "unit_price": 25.0
            },
            {
                "item_name": "Azun's Lament (Bottle)",
                "stock_on_hand": 12,
                "stock_on_order": 0,
                "units_per": 5,
                "unit_price": 15.0
            },
            {
                "item_name": "Black Wyvern Porter (Tankard)",
                "stock_on_hand": 200,
                "stock_on_order": 100,
                "units_per": 1,
                "unit_price": 0.04
            },
            {
                "item_name": "The 'Lif' Special (Glass)",
                "stock_on_hand": 50,
                "stock_on_order": 0,
                "units_per": 1,
                "unit_price": 0.8
            },
            {
                "item_name": "Gumpfish Stew (Bowl)",
                "stock_on_hand": 30,
                "stock_on_order": 0,
                "units_per": 1,
                "unit_price": 0.3
            }
        ]
        db.inventory.insert_many(seed_items)
    
    if db.staff.count_documents({}) == 0:
        seed_staff = [
            {
                "name": "Lif the Poltergeist",
                "wage": 0.0,
                "frequency": "Daily",
                "bonus": 5
            },
            {
                "name": "Bepis Honeymaker (Cook)",
                "wage": 0.0,
                "frequency": "Daily",
                "bonus": 2
            },
            {
                "name": "Spider (Warforged Security Tier II)",
                "wage": 2.0,
                "frequency": "Daily",
                "bonus": 4
            },
            {
                "name": "Amaryllis Thorne (Acrobat Guard Tier IV)",
                "wage": 1.5,
                "frequency": "Daily",
                "bonus": 3
            },
            {
                "name": "Myrnd Gundwynd (Black Boar Vanguard)",
                "wage": 3.0,
                "frequency": "Daily",
                "bonus": 5
            },
            {
                "name": "Istrid Horn (Treasury Security Tier I)",
                "wage": 5.0,
                "frequency": "Daily",
                "bonus": 6
            },
            {
                "name": "Tashlyn Yafeera (Head of Security Tier I)",
                "wage": 8.0,
                "frequency": "Daily",
                "bonus": 8
            }
        ]
        db.staff.insert_many(seed_staff)

    if db.ledger.count_documents({}) == 0:
        seed_ledger = [
            {
                "entry_type": "Income",
                "description": "Ransom of the Twelve",
                "amount": 11000.0,
                "frequency": "Once",
                "entry_date": "Ches 30"
            },
            {
                "entry_type": "Income",
                "description": "Volo's Sponsorship",
                "amount": 50.0,
                "frequency": "Monthly",
                "entry_date": "Ches 30"
            },
            {
                "entry_type": "Guild",
                "description": "Vintners' Guild Partnership",
                "amount": 300.0,
                "frequency": "Once",
                "entry_date": "Ches 30"
            }
        ]
        db.ledger.insert_many(seed_ledger)
        
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

class RollRequest(BaseModel):
    base_roll: int
    renown_bonus: int
    environmental_bonus: int

class SaleItem(BaseModel):
    item_name: str
    quantity: int
    total_price: float
    sale_date: str

class InventoryItem(BaseModel):
    item_name: str
    stock_on_hand: int
    stock_on_order: int
    units_per: int
    unit_price: float

class LedgerEntry(BaseModel):
    entry_type: str
    description: str
    amount: float
    frequency: str
    entry_date: str

class StaffItem(BaseModel):
    name: str
    wage: float
    frequency: str
    bonus: int

class SaveDayRequest(BaseModel):
    calendar_date: str
    sales: List[SaleItem]

class NPCData(BaseModel):
    first_name: str
    last_name: str
    affiliation: str
    occupation: str
    lifestyle: str
    bar_disposition: int
    party_disposition: int
    
class NPCDispositionUpdate(BaseModel):
    index: int
    delta: int

def get_csv_path():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "npcs.csv")
    if not os.path.exists(csv_path):
        csv_path = "npcs.csv"
    return csv_path

def load_clean_npcs(include_fieldnames=False):
    npcs = []
    csv_path = get_csv_path()
    fieldnames = []
    
    if not os.path.exists(csv_path):
        if include_fieldnames:
            return npcs, ["First Name", "Last Name", "Affiliation", "Occupation", "Lifestyle", "Bar Disposition", "Party Disposition"]
        return npcs
        
    with open(csv_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    clean_lines = []
    buffer = ""
    for line in lines:
        line = re.sub(r'\\s*', '', line).strip()
        if not line:
            continue
        if buffer:
            buffer += " " + line
        else:
            buffer = line
            
        if buffer.count(',') >= 6:
            clean_lines.append(buffer)
            buffer = ""
            
    if buffer:
        clean_lines.append(buffer)
        
    if not clean_lines:
        if include_fieldnames:
            return [], []
        return []

    reader = csv.DictReader(clean_lines)
    fieldnames = reader.fieldnames if reader.fieldnames else []
    
    for idx, row in enumerate(reader):
        row["_csv_index"] = idx
        npcs.append(row)
            
    if include_fieldnames:
        return npcs, fieldnames
    return npcs

def save_npcs_to_csv(npcs, fieldnames):
    csv_path = get_csv_path()
    if not fieldnames:
        fieldnames = ["First Name", "Last Name", "Affiliation", "Occupation", "Lifestyle", "Bar Disposition", "Party Disposition"]
        
    required_fields = ["First Name", "Last Name", "Affiliation", "Occupation", "Lifestyle", "Bar Disposition", "Party Disposition"]
    for req in required_fields:
        if req not in fieldnames:
            fieldnames.append(req)

    with open(csv_path, "w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[fn for fn in fieldnames if fn != "_csv_index"])
        writer.writeheader()
        for npc in npcs:
            clean_npc = {k: v for k, v in npc.items() if k != "_csv_index"}
            for fn in fieldnames:
                if fn not in clean_npc and fn != "_csv_index":
                    clean_npc[fn] = ""
            writer.writerow(clean_npc)

def simulate_npc_visitors():
    npcs = load_clean_npcs()
    if not npcs:
        return [], {}
        
    willing_npcs = []
    for n in npcs:
        try:
            b_val = str(n.get("Bar Disposition", "0")).strip()
            p_val = str(n.get("Party Disposition", "0")).strip()
            if not b_val: b_val = "0"
            if not p_val: p_val = "0"
            bar_disp = int(b_val)
            party_disp = int(p_val)
            if bar_disp + party_disp > -20:
                willing_npcs.append(n)
        except ValueError:
            continue
            
    num_groups = random.randint(1, 5)
    groups = []
    
    hourly_counts = {}
    for h in range(12, 24):
        hourly_counts[str(h)] = []
    
    random.shuffle(willing_npcs)
    used_names = set()
    
    for _ in range(num_groups):
        if not willing_npcs:
            break
            
        leader = willing_npcs.pop(0)
        leader_first = str(leader.get("First Name", "")).strip()
        leader_last = str(leader.get("Last Name", "")).strip()
        leader_name = f"{leader_first} {leader_last}".strip()
        if not leader_name:
            leader_name = "Unknown Patron"
            
        if leader_name in used_names:
            continue
            
        group_members = [leader]
        used_names.add(leader_name)
        
        group_size_target = random.randint(1, 5)
        members_to_remove = []
        
        for n in willing_npcs:
            if len(group_members) >= group_size_target:
                break
                
            n_first = str(n.get("First Name", "")).strip()
            n_last = str(n.get("Last Name", "")).strip()
            n_name = f"{n_first} {n_last}".strip()
            if not n_name or n_name in used_names:
                continue
                
            shared_last = (n_last != "" and n_last == leader_last)
            shared_affil = (n.get("Affiliation", "") != "" and n.get("Affiliation", "") == leader.get("Affiliation", ""))
            
            if shared_last or shared_affil:
                group_members.append(n)
                used_names.add(n_name)
                members_to_remove.append(n)
                
        for m in members_to_remove:
            willing_npcs.remove(m)
            
        arrival = random.randint(12, 21)
        stay = random.randint(1, 4)
        departure = min(23, arrival + stay)
        group_spend = 0.0
        member_data = []
        
        for m in group_members:
            m_first = str(m.get("First Name", "")).strip()
            m_last = str(m.get("Last Name", "")).strip()
            m_name = f"{m_first} {m_last}".strip()
            if not m_name:
                m_name = "Unknown Patron"
                
            lifestyle = str(m.get("Lifestyle", "")).lower()
            if "wealthy" in lifestyle or "aristocratic" in lifestyle or "noble" in lifestyle:
                spend = random.uniform(5.0, 15.0)
            elif "comfortable" in lifestyle:
                spend = random.uniform(2.0, 5.0)
            elif "modest" in lifestyle:
                spend = random.uniform(0.5, 2.0)
            else:
                spend = random.uniform(0.1, 0.5)
                
            group_spend += spend
            
            try:
                b_disp = int(m.get("Bar Disposition", 0))
            except:
                b_disp = 0
                
            member_data.append({
                "index": m.get("_csv_index", -1),
                "name": m_name,
                "affiliation": m.get("Affiliation", ""),
                "occupation": m.get("Occupation", ""),
                "lifestyle": m.get("Lifestyle", ""),
                "bar_disposition": b_disp
            })
            
            for hour in range(arrival, departure + 1):
                if str(hour) in hourly_counts:
                    hourly_counts[str(hour)].append(m_name)
                
        groups.append({
            "leader": leader_name,
            "size": len(group_members),
            "members_data": member_data,
            "arrival": arrival,
            "departure": departure,
            "stay_duration": stay,
            "group_spend": round(group_spend, 2),
            "location": "Unassigned"
        })
        
    return groups, hourly_counts

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    try:
        with open("index.html", "r") as file:
            html_content = file.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: index.html not found.</h1>", status_code=404)

@app.post("/api/roll")
def calculate_tavern_outcome(request: RollRequest):
    staff_cursor = db.staff.find()
    total_staff_bonus = 0
    for staff in staff_cursor:
        total_staff_bonus += staff.get("bonus", 0)

    total_roll = request.base_roll + total_staff_bonus + request.renown_bonus + request.environmental_bonus
    
    table_capacity = 44
    bar_capacity = 10
    vip_capacity = 10
    standing_capacity = random.randint(20, 40)
    
    patrons_main = 0
    patrons_standing = 0
    patrons_vip = 0
    outcome = "Standard Day"

    if total_roll <= 20:
        outcome = "Disaster: A brawl broke out. Empty tavern."
        patrons_main = random.randint(0, 10)
    elif total_roll <= 40:
        outcome = "Poor Day: Slow business."
        patrons_main = random.randint(10, 20)
    elif total_roll <= 60:
        outcome = "Average Day: Modest crowd."
        patrons_main = random.randint(20, 40)
    elif total_roll <= 80:
        outcome = "Good Day: Busy tavern."
        patrons_main = random.randint(40, 54)
    else:
        outcome = "Windfall: The tavern is packed!"
        patrons_main = 54
        patrons_standing = random.randint(5, standing_capacity)

    if total_roll > 60:
        vip_check = random.randint(1, 20)
        if vip_check >= 14:
            vip_fullness = random.randint(1, 100)
            patrons_vip = max(1, int((vip_fullness / 100.0) * vip_capacity))

    spots_available = {
        "VIP": patrons_vip,
        "Table": min(patrons_main, table_capacity),
        "Bar": max(0, patrons_main - table_capacity),
        "Standing": patrons_standing
    }

    npc_groups, npc_hourly = simulate_npc_visitors()
    
    total_npc_spend = 0.0
    total_named_visitors = 0
    
    for g in npc_groups:
        lifestyles = [str(m.get("lifestyle", "")).lower() for m in g["members_data"]]
        
        ideal = "Bar"
        if any(l in lifestyles for l in ["aristocratic", "wealthy", "noble"]):
            ideal = "VIP"
        elif any(l in lifestyles for l in ["comfortable"]):
            ideal = "Table"
            
        placed = False
        for pref in [ideal, "Table", "Bar", "Standing", "VIP"]:
            if spots_available[pref] >= g["size"]:
                spots_available[pref] -= g["size"]
                g["location"] = pref
                placed = True
                break
                
        if not placed:
            g["location"] = "Standing"
            
        total_npc_spend += g["group_spend"]
        total_named_visitors += g["size"]

    ale_qty = int((patrons_main + patrons_standing) * random.uniform(1.0, 2.5))
    food_qty = int(patrons_main * random.uniform(0.2, 0.8))
    premium_qty = int(patrons_vip * random.uniform(2.0, 4.0))

    generated_sales = []
    if ale_qty > 0:
        generated_sales.append({"item_name": "Standard Ale/Drinks", "quantity": ale_qty, "total_price": round(ale_qty * 0.5, 2)})
    if food_qty > 0:
        generated_sales.append({"item_name": "Tavern Fare", "quantity": food_qty, "total_price": round(food_qty * 1.5, 2)})
    if premium_qty > 0:
        generated_sales.append({"item_name": "Premium VIP Drinks", "quantity": premium_qty, "total_price": round(premium_qty * 5.0, 2)})
        
    if total_npc_spend > 0:
        generated_sales.append({
            "item_name": "Named NPC Group Spend",
            "quantity": total_named_visitors,
            "total_price": round(total_npc_spend, 2)
        })

    result = {
        "total_roll": total_roll,
        "staff_bonus_applied": total_staff_bonus,
        "outcome": outcome,
        "main_patrons": patrons_main,
        "standing_patrons": patrons_standing,
        "vip_patrons": patrons_vip,
        "max_standing": standing_capacity,
        "auto_sales": generated_sales,
        "npc_groups": npc_groups,
        "npc_hourly": npc_hourly
    }
    return result

@app.post("/api/save_day")
def save_day_data(request: SaveDayRequest):
    date_str = request.calendar_date
    for sale in request.sales:
        sale.sale_date = date_str
        sale_dict = sale.dict()
        db.sales.insert_one(sale_dict)
        if gc is not None:
            sales_sheet.append_row([sale.sale_date, sale.item_name, sale.quantity, sale.total_price])

    daily_staff = db.staff.find({"frequency": "Daily"})
    for staff in daily_staff:
        if staff.get("wage", 0) > 0:
            wage_entry = {
                "entry_type": "Expense",
                "description": f"Daily Wage: {staff['name']}",
                "amount": staff["wage"],
                "frequency": "Daily",
                "entry_date": date_str
            }
            db.ledger.insert_one(wage_entry)
            if gc is not None:
                ledger_sheet.append_row([date_str, "Expense", wage_entry["description"], wage_entry["amount"]])

    return {"status": "Day Saved Successfully"}

@app.get("/api/inventory")
def get_inventory():
    return [{**i, "_id": str(i["_id"])} for i in db.inventory.find()]

@app.post("/api/inventory")
def add_inventory(item: InventoryItem):
    item_dict = item.dict()
    db.inventory.insert_one(item_dict)
    item_dict["_id"] = str(item_dict["_id"])
    return item_dict

@app.put("/api/inventory/{item_id}")
def update_inventory(item_id: str, item: InventoryItem):
    db.inventory.update_one({"_id": ObjectId(item_id)}, {"$set": item.dict()})
    return {"status": "Updated"}

@app.get("/api/staff")
def get_staff():
    return [{**s, "_id": str(s["_id"])} for s in db.staff.find()]

@app.post("/api/staff")
def add_staff(staff: StaffItem):
    staff_dict = staff.dict()
    db.staff.insert_one(staff_dict)
    staff_dict["_id"] = str(staff_dict["_id"])
    return staff_dict

@app.put("/api/staff/{staff_id}")
def update_staff(staff_id: str, staff: StaffItem):
    db.staff.update_one({"_id": ObjectId(staff_id)}, {"$set": staff.dict()})
    return {"status": "Updated"}

@app.get("/api/ledger")
def get_ledger():
    return [{**l, "_id": str(l["_id"])} for l in db.ledger.find()]

@app.post("/api/ledger")
def record_ledger_entry(entry: LedgerEntry):
    entry_dict = entry.dict()
    db.ledger.insert_one(entry_dict)
    if gc is not None:
        ledger_sheet.append_row([entry.entry_date, entry.entry_type, entry.description, entry.amount])
    entry_dict["_id"] = str(entry_dict["_id"])
    return entry_dict

@app.put("/api/ledger/{entry_id}")
def update_ledger(entry_id: str, entry: LedgerEntry):
    db.ledger.update_one({"_id": ObjectId(entry_id)}, {"$set": entry.dict()})
    return {"status": "Updated"}

@app.get("/api/reports")
def get_reports():
    sales = [{**s, "_id": str(s["_id"])} for s in db.sales.find()]
    ledger = [{**l, "_id": str(l["_id"])} for l in db.ledger.find()]
    return {"sales": sales, "ledger": ledger}

@app.get("/api/npcs")
def get_npcs():
    npcs = load_clean_npcs()
    return npcs

@app.post("/api/npcs")
def create_npc(npc: NPCData):
    npcs, fieldnames = load_clean_npcs(include_fieldnames=True)
    new_row = {
        "First Name": npc.first_name,
        "Last Name": npc.last_name,
        "Affiliation": npc.affiliation,
        "Occupation": npc.occupation,
        "Lifestyle": npc.lifestyle,
        "Bar Disposition": str(npc.bar_disposition),
        "Party Disposition": str(npc.party_disposition)
    }
    npcs.append(new_row)
    save_npcs_to_csv(npcs, fieldnames)
    return {"status": "Added NPC"}

@app.put("/api/npcs/{index}")
def update_npc(index: int, npc: NPCData):
    npcs, fieldnames = load_clean_npcs(include_fieldnames=True)
    for row in npcs:
        if row.get("_csv_index") == index:
            row["First Name"] = npc.first_name
            row["Last Name"] = npc.last_name
            row["Affiliation"] = npc.affiliation
            row["Occupation"] = npc.occupation
            row["Lifestyle"] = npc.lifestyle
            row["Bar Disposition"] = str(npc.bar_disposition)
            row["Party Disposition"] = str(npc.party_disposition)
            break
    save_npcs_to_csv(npcs, fieldnames)
    return {"status": "Updated NPC"}

@app.put("/api/npcs/disposition/adjust")
def adjust_npc_disposition(req: NPCDispositionUpdate):
    npcs, fieldnames = load_clean_npcs(include_fieldnames=True)
    for row in npcs:
        if row.get("_csv_index") == req.index:
            try:
                curr = int(row.get("Bar Disposition", 0))
            except:
                curr = 0
            row["Bar Disposition"] = str(curr + req.delta)
            break
    save_npcs_to_csv(npcs, fieldnames)
    return {"status": "Disposition adjusted"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)