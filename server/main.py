import contextlib
import uvicorn
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pymongo import MongoClient
from bson.objectid import ObjectId
from typing import List
import gspread
import random
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

def get_inventory_csv_path():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "inventory.csv")
    if not os.path.exists(csv_path):
        csv_path = "inventory.csv"
    return csv_path

def load_inventory_csv(include_fieldnames=False):
    inv = []
    csv_path = get_inventory_csv_path()
    fieldnames = []
    if not os.path.exists(csv_path):
        if include_fieldnames:
            return inv, ["Item Name", "Stock on Hand", "Stock on Order", "Units Per", "Unit Price"]
        return inv
        
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames if reader.fieldnames else []
        for idx, row in enumerate(reader):
            row["_csv_index"] = idx
            inv.append(row)
            
    if include_fieldnames:
        return inv, fieldnames
    return inv

def save_inventory_csv(inv, fieldnames):
    csv_path = get_inventory_csv_path()
    if not fieldnames:
        fieldnames = ["Item Name", "Stock on Hand", "Stock on Order", "Units Per", "Unit Price"]
        
    with open(csv_path, "w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[fn for fn in fieldnames if fn != "_csv_index"])
        writer.writeheader()
        for item in inv:
            clean_item = {k: v for k, v in item.items() if k != "_csv_index"}
            for fn in fieldnames:
                if fn not in clean_item:
                    clean_item[fn] = ""
            writer.writerow(clean_item)

def init_inventory_csv():
    csv_path = get_inventory_csv_path()
    if not os.path.exists(csv_path):
        seed_data = [
            {"Item Name": "Moradin-Anaz (\"Moradin's Hammerfall\")", "Stock on Hand": 60, "Stock on Order": 0, "Units Per": 1, "Unit Price": 2.0},
            {"Item Name": "Ironforge Reserve", "Stock on Hand": 60, "Stock on Order": 0, "Units Per": 1, "Unit Price": 1.0},
            {"Item Name": "Stone-Hearth Malt", "Stock on Hand": 60, "Stock on Order": 0, "Units Per": 1, "Unit Price": 0.5},
            {"Item Name": "First Frost", "Stock on Hand": 50, "Stock on Order": 0, "Units Per": 5, "Unit Price": 5.0},
            {"Item Name": "Azun's Lament", "Stock on Hand": 50, "Stock on Order": 0, "Units Per": 5, "Unit Price": 3.0},
            {"Item Name": "Silver Spring", "Stock on Hand": 50, "Stock on Order": 0, "Units Per": 5, "Unit Price": 2.0},
            {"Item Name": "Manycherries Bold", "Stock on Hand": 50, "Stock on Order": 0, "Units Per": 5, "Unit Price": 1.0},
            {"Item Name": "Harbor White", "Stock on Hand": 50, "Stock on Order": 0, "Units Per": 5, "Unit Price": 0.8},
            {"Item Name": "Pulass", "Stock on Hand": 50, "Stock on Order": 0, "Units Per": 5, "Unit Price": 1.0},
            {"Item Name": "Best Old Mintarn Whisky", "Stock on Hand": 50, "Stock on Order": 0, "Units Per": 1, "Unit Price": 1.0},
            {"Item Name": "Wyvern Whiskey", "Stock on Hand": 50, "Stock on Order": 0, "Units Per": 1, "Unit Price": 0.8},
            {"Item Name": "Amberjack Whiskey", "Stock on Hand": 50, "Stock on Order": 0, "Units Per": 1, "Unit Price": 0.6},
            {"Item Name": "Waterdhavian Zzar", "Stock on Hand": 50, "Stock on Order": 0, "Units Per": 1, "Unit Price": 0.5},
            {"Item Name": "Lieutenant Talbot's Moonshine", "Stock on Hand": 50, "Stock on Order": 0, "Units Per": 1, "Unit Price": 0.4},
            {"Item Name": "Shadowdale Brandy", "Stock on Hand": 50, "Stock on Order": 0, "Units Per": 1, "Unit Price": 1.0},
            {"Item Name": "Neverwinter Black Icewine", "Stock on Hand": 50, "Stock on Order": 0, "Units Per": 1, "Unit Price": 2.0},
            {"Item Name": "The \"Lif\" Special", "Stock on Hand": 100, "Stock on Order": 0, "Units Per": 1, "Unit Price": 0.8},
            {"Item Name": "Aftermath Abbey Ale", "Stock on Hand": 100, "Stock on Order": 0, "Units Per": 1, "Unit Price": 0.1},
            {"Item Name": "Hell's Teeth Cider", "Stock on Hand": 100, "Stock on Order": 0, "Units Per": 1, "Unit Price": 0.05},
            {"Item Name": "Black Wyvern Porter", "Stock on Hand": 100, "Stock on Order": 0, "Units Per": 1, "Unit Price": 0.04},
            {"Item Name": "Goat's Head Ale", "Stock on Hand": 100, "Stock on Order": 0, "Units Per": 1, "Unit Price": 0.03}
        ]
        save_inventory_csv(seed_data, ["Item Name", "Stock on Hand", "Stock on Order", "Units Per", "Unit Price"])

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    init_inventory_csv()
    if db.staff.count_documents({}) == 0:
        seed_staff = [
            {"name": "Lif the Poltergeist", "wage": 0.0, "frequency": "Daily", "bonus": 5},
            {"name": "Bepis Honeymaker (Cook)", "wage": 0.0, "frequency": "Daily", "bonus": 2},
            {"name": "Spider (Warforged Security Tier II)", "wage": 2.0, "frequency": "Daily", "bonus": 4},
            {"name": "Amaryllis Thorne (Acrobat Guard Tier IV)", "wage": 1.5, "frequency": "Daily", "bonus": 3},
            {"name": "Myrnd Gundwynd (Black Boar Vanguard)", "wage": 3.0, "frequency": "Daily", "bonus": 5},
            {"name": "Istrid Horn (Treasury Security Tier I)", "wage": 5.0, "frequency": "Daily", "bonus": 6},
            {"name": "Tashlyn Yafeera (Head of Security Tier I)", "wage": 8.0, "frequency": "Daily", "bonus": 8}
        ]
        db.staff.insert_many(seed_staff)

    if db.ledger.count_documents({}) == 0:
        seed_ledger = [
            {"entry_type": "Income", "description": "Ransom of the Twelve", "amount": 11000.0, "frequency": "Once", "entry_date": "Ches 30"},
            {"entry_type": "Income", "description": "Volo's Sponsorship", "amount": 50.0, "frequency": "Monthly", "entry_date": "Ches 30"},
            {"entry_type": "Guild", "description": "Vintners' Guild Partnership", "amount": 300.0, "frequency": "Once", "entry_date": "Ches 30"}
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
    main_quest: int
    side_quest: int
    
class NPCDispositionUpdate(BaseModel):
    index: int
    delta: int
    disp_type: str 

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
            return npcs, ["First Name", "Last Name", "Affiliation", "Occupation", "Lifestyle", "Bar Disposition", "Party Disposition", "MAIN QUEST NPC", "SIDE QUEST NPC"]
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
        fieldnames = ["First Name", "Last Name", "Affiliation", "Occupation", "Lifestyle", "Bar Disposition", "Party Disposition", "MAIN QUEST NPC", "SIDE QUEST NPC"]
        
    required_fields = ["First Name", "Last Name", "Affiliation", "Occupation", "Lifestyle", "Bar Disposition", "Party Disposition", "MAIN QUEST NPC", "SIDE QUEST NPC"]
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

def simulate_npc_visitors(target_vip, target_table, target_bar, target_standing, temp_stock, item_prices):
    npcs = load_clean_npcs()
    willing_npcs = []
    
    for n in npcs:
        try:
            b_val = str(n.get("Bar Disposition", "0")).strip()
            p_val = str(n.get("Party Disposition", "0")).strip()
            if not b_val: b_val = "0"
            if not p_val: p_val = "0"
            if int(b_val) + int(p_val) > -20:
                willing_npcs.append(n)
        except ValueError:
            continue
            
    random.shuffle(willing_npcs)
    
    quest_npcs = []
    drinkers = []
    for n in willing_npcs:
        try: mq = int(n.get("MAIN QUEST NPC", 0))
        except: mq = 0
        try: sq = int(n.get("SIDE QUEST NPC", 0))
        except: sq = 0
        
        if mq == 1 or sq == 1:
            quest_npcs.append(n)
        else:
            drinkers.append(n)
            
    num_guaranteed_quests = min(len(quest_npcs), random.randint(1, 3))
    guaranteed = quest_npcs[:num_guaranteed_quests]
    rest = quest_npcs[num_guaranteed_quests:] + drinkers
    random.shuffle(rest)
    willing_npcs = guaranteed + rest
    
    generics = [
        "Merchant", "City Guard", "Traveler", "Artisan", "Laborer", 
        "Sailor", "Nobleman", "Beggar", "Mercenary", "Guildsman"
    ]
    
    hourly_counts = {str(h): {"VIP": [], "Table": [], "Bar": [], "Standing": []} for h in range(12, 24)}
    groups = []
    
    def build_groups_for_location(target_size, loc_name):
        cat_groups = []
        current_count = 0
        while current_count < target_size:
            g_size = random.randint(1, min(5, target_size - current_count))
            if g_size <= 0: break
            
            members = []
            
            for _ in range(g_size):
                if willing_npcs:
                    n = willing_npcs.pop(0)
                    first = str(n.get("First Name", "")).strip()
                    last = str(n.get("Last Name", "")).strip()
                    name = f"{first} {last}".strip()
                    if not name: name = "Unknown Patron"
                    affil = n.get("Affiliation", "")
                    occ = n.get("Occupation", "")
                    life = n.get("Lifestyle", "")
                    try: b_disp = int(n.get("Bar Disposition", 0))
                    except: b_disp = 0
                    try: p_disp = int(n.get("Party Disposition", 0))
                    except: p_disp = 0
                    try: mq = int(n.get("MAIN QUEST NPC", 0))
                    except: mq = 0
                    try: sq = int(n.get("SIDE QUEST NPC", 0))
                    except: sq = 0
                    idx = n.get("_csv_index", -1)
                else:
                    title = random.choice(generics)
                    name = f"Anonymous {title}"
                    affil = "None"
                    occ = title
                    life = "Modest"
                    if title in ["Nobleman", "Merchant", "Guildsman"]: life = "Wealthy"
                    elif title in ["Beggar"]: life = "Squalid"
                    b_disp, p_disp, mq, sq, idx = 0, 0, 0, 0, -1
                    
                members.append({
                    "index": idx,
                    "name": name,
                    "affiliation": affil,
                    "occupation": occ,
                    "lifestyle": life,
                    "bar_disposition": b_disp,
                    "party_disposition": p_disp,
                    "main_quest": mq,
                    "side_quest": sq
                })
            
            current_count += g_size
            arrival = random.randint(12, 21)
            stay = random.randint(1, 4)
            departure = min(23, arrival + stay)
            
            receipt_dict = {}
            g_spend = 0.0
            
            for m in members:
                m_life = str(m.get("lifestyle", "")).lower()
                mult = 1.0
                if "wealthy" in m_life or "aristocratic" in m_life or "noble" in m_life: mult = 2.5
                elif "modest" in m_life: mult = 0.8
                elif "squalid" in m_life: mult = 0.5
                    
                num_items = random.randint(1, 3)
                for _ in range(num_items):
                    avail = [k for k, v in temp_stock.items() if v > 0]
                    if not avail: break
                    choice = random.choice(avail)
                    temp_stock[choice] -= 1
                    cost = item_prices[choice] * mult
                    g_spend += cost
                    
                    if choice in receipt_dict:
                        receipt_dict[choice]["qty"] += 1
                        receipt_dict[choice]["cost"] += cost
                    else:
                        receipt_dict[choice] = {"qty": 1, "cost": cost}
                        
            formatted_receipt = [{"item_name": k, "quantity": v["qty"], "total_price": round(v["cost"], 2)} for k, v in receipt_dict.items()]
                    
            cat_groups.append({
                "leader": members[0]["name"],
                "size": g_size,
                "members_data": members,
                "arrival": arrival,
                "departure": departure,
                "stay_duration": stay,
                "group_spend": round(g_spend, 2),
                "location": loc_name,
                "receipt": formatted_receipt
            })
            
            for m in members:
                for hour in range(arrival, departure + 1):
                    if str(hour) in hourly_counts:
                        hourly_counts[str(hour)][loc_name].append(m)
                        
        return cat_groups

    groups.extend(build_groups_for_location(target_vip, "VIP"))
    groups.extend(build_groups_for_location(target_table, "Table"))
    groups.extend(build_groups_for_location(target_bar, "Bar"))
    groups.extend(build_groups_for_location(target_standing, "Standing"))
    
    return groups, hourly_counts

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    try:
        with open("index.html", "r") as file:
            html_content = file.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: index.html not found.</h1>", status_code=404)

@app.get("/{filename}.png")
def serve_image(filename: str):
    file_path = f"{filename}.png"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return HTTPException(status_code=404, detail="Image not found")

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

    target_table = min(patrons_main, table_capacity)
    target_bar = max(0, patrons_main - table_capacity)
    target_vip = patrons_vip
    target_standing = patrons_standing

    inv = load_inventory_csv()
    temp_stock = {i["Item Name"]: int(i.get("Stock on Hand", 0)) for i in inv}
    item_prices = {i["Item Name"]: float(i.get("Unit Price", 0.0)) for i in inv}

    npc_groups, npc_hourly = simulate_npc_visitors(target_vip, target_table, target_bar, target_standing, temp_stock, item_prices)
    
    all_auto_sales = []
    sales_agg = {}
    
    def add_to_agg(receipt_list):
        for r in receipt_list:
            name = r["item_name"]
            if name in sales_agg:
                sales_agg[name]["quantity"] += r["quantity"]
                sales_agg[name]["total_price"] += r["total_price"]
            else:
                sales_agg[name] = {"item_name": name, "quantity": r["quantity"], "total_price": r["total_price"]}
                
    for g in npc_groups:
        add_to_agg(g["receipt"])

    for k, v in sales_agg.items():
        all_auto_sales.append({"item_name": v["item_name"], "quantity": v["quantity"], "total_price": round(v["total_price"], 2)})

    result = {
        "total_roll": total_roll,
        "staff_bonus_applied": total_staff_bonus,
        "outcome": outcome,
        "main_patrons": patrons_main,
        "table_patrons": target_table,
        "bar_patrons": target_bar,
        "standing_patrons": target_standing,
        "vip_patrons": target_vip,
        "max_standing": standing_capacity,
        "auto_sales": all_auto_sales,
        "npc_groups": npc_groups,
        "npc_hourly": npc_hourly
    }
    return result

@app.post("/api/save_day")
def save_day_data(request: SaveDayRequest):
    date_str = request.calendar_date
    inv_list, fieldnames = load_inventory_csv(include_fieldnames=True)

    # 1. Fetch old sales to revert inventory if this is a resave/edit of an existing day
    old_sales = list(db.sales.find({"sale_date": date_str}))
    is_new_day = len(old_sales) == 0
    
    for old_sale in old_sales:
        for row in inv_list:
            if row["Item Name"] == old_sale["item_name"]:
                try: curr = int(row.get("Stock on Hand", 0))
                except: curr = 0
                row["Stock on Hand"] = str(curr + old_sale["quantity"])
                break
                
    # Wipe the old records for this day completely
    db.sales.delete_many({"sale_date": date_str})
    db.ledger.delete_many({"entry_date": date_str, "description": {"$regex": "^Daily Wage:"}})

    # 2. If it's a completely NEW day, process arrivals of pending "Stock on Order"
    if is_new_day:
        for row in inv_list:
            try: on_order = int(row.get("Stock on Order", 0))
            except: on_order = 0
            if on_order > 0:
                try: curr = int(row.get("Stock on Hand", 0))
                except: curr = 0
                row["Stock on Hand"] = str(curr + on_order)
                row["Stock on Order"] = "0"

    # 3. Apply the newly generated sales
    for sale in request.sales:
        sale.sale_date = date_str
        db.sales.insert_one(sale.dict())
        
        for row in inv_list:
            if row["Item Name"] == sale.item_name:
                try: curr = int(row.get("Stock on Hand", 0))
                except: curr = 0
                new_qty = curr - sale.quantity
                row["Stock on Hand"] = str(new_qty)
                
                # Auto-Replenishment Logic: If we ran out, order 50 automatically
                try: pending_order = int(row.get("Stock on Order", 0))
                except: pending_order = 0
                
                if new_qty <= 0 and pending_order == 0:
                    row["Stock on Order"] = "50"
                break
                
        if gc is not None:
            sales_sheet.append_row([sale.sale_date, sale.item_name, sale.quantity, sale.total_price])

    save_inventory_csv(inv_list, fieldnames)

    # 4. Re-apply daily wages
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
    inv = load_inventory_csv()
    return inv

@app.post("/api/inventory")
def add_inventory(item: InventoryItem):
    inv, fieldnames = load_inventory_csv(include_fieldnames=True)
    new_row = {
        "Item Name": item.item_name,
        "Stock on Hand": str(item.stock_on_hand),
        "Stock on Order": str(item.stock_on_order),
        "Units Per": str(item.units_per),
        "Unit Price": str(item.unit_price)
    }
    inv.append(new_row)
    save_inventory_csv(inv, fieldnames)
    return {"status": "Added Inventory"}

@app.put("/api/inventory/{index}")
def update_inventory(index: int, item: InventoryItem):
    inv, fieldnames = load_inventory_csv(include_fieldnames=True)
    for row in inv:
        if row.get("_csv_index") == index:
            row["Item Name"] = item.item_name
            row["Stock on Hand"] = str(item.stock_on_hand)
            row["Stock on Order"] = str(item.stock_on_order)
            row["Units Per"] = str(item.units_per)
            row["Unit Price"] = str(item.unit_price)
            break
    save_inventory_csv(inv, fieldnames)
    return {"status": "Updated Inventory"}

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
        "Party Disposition": str(npc.party_disposition),
        "MAIN QUEST NPC": str(npc.main_quest),
        "SIDE QUEST NPC": str(npc.side_quest)
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
            row["MAIN QUEST NPC"] = str(npc.main_quest)
            row["SIDE QUEST NPC"] = str(npc.side_quest)
            break
    save_npcs_to_csv(npcs, fieldnames)
    return {"status": "Updated NPC"}

@app.put("/api/npcs/disposition/adjust")
def adjust_npc_disposition(req: NPCDispositionUpdate):
    npcs, fieldnames = load_clean_npcs(include_fieldnames=True)
    for row in npcs:
        if row.get("_csv_index") == req.index:
            target_col = "Bar Disposition" if req.disp_type == 'bar' else "Party Disposition"
            try: curr = int(row.get(target_col, 0))
            except: curr = 0
            row[target_col] = str(curr + req.delta)
            break
    save_npcs_to_csv(npcs, fieldnames)
    return {"status": "Disposition adjusted"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)