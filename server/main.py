import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routers import dashboard
from routers import inventory
from routers import staff
from routers import npcs
from routers import ledger
from routers import analytics

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(inventory.router)
app.include_router(staff.router)
app.include_router(npcs.router)
app.include_router(ledger.router)
app.include_router(analytics.router)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("index.html")

if __name__ == "__main__":
    # Add reload_excludes to ignore the data files!
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_excludes=["*.csv"])