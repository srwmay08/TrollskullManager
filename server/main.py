import contextlib
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from database import db
from routers import router

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
                "description": "Ransom of the Twelve (Lord Lorahmar Djinni Rescue)",
                "amount": 11000.0,
                "frequency": "Once",
                "entry_date": "Ches 30"
            },
            {
                "entry_type": "Income",
                "description": "Volo's Sponsorship (Brand Ambassador)",
                "amount": 50.0,
                "frequency": "Monthly",
                "entry_date": "Ches 30"
            },
            {
                "entry_type": "Guild",
                "description": "Vintners' Guild Partnership (Mertyn Bottlewick) Upfront",
                "amount": 300.0,
                "frequency": "Once",
                "entry_date": "Ches 30"
            },
            {
                "entry_type": "Renovation",
                "description": "Tally Fellbranch Ironwood Restoration",
                "amount": 1200.0,
                "frequency": "Once",
                "entry_date": "Ches 30"
            },
            {
                "entry_type": "Guild",
                "description": "Dungsweepers' Guild (Grubach) Contract",
                "amount": 20.0,
                "frequency": "Weekly",
                "entry_date": "Ches 30"
            },
            {
                "entry_type": "Guild",
                "description": "Vintners' Guild Weekly Fee",
                "amount": 5.0,
                "frequency": "Weekly",
                "entry_date": "Ches 30"
            },
            {
                "entry_type": "Tuition",
                "description": "Murkledorn's Education (7 Urchins/Appleton Boys)",
                "amount": 14.0,
                "frequency": "Weekly",
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