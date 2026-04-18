from fastapi import APIRouter
from database import db

router = APIRouter()

@router.get("/api/ledger")
def get_ledger():
    ledger_cursor = db.ledger.find()
    ledger_list = []
    for item in ledger_cursor:
        item["_id"] = str(item["_id"])
        ledger_list.append(item)
    return ledger_list