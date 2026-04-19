from typing import Dict
from typing import List
from typing import Any

from fastapi import APIRouter
from bson.objectid import ObjectId

from database import db

router = APIRouter()


@router.get("/api/ledger")
def get_ledger() -> List[Dict[str, Any]]:
    """Retrieves all ledger entries to populate the frontend table."""
    ledger_cursor = db.ledger.find()
    ledger_list: List[Dict[str, Any]] = []
    
    for item in ledger_cursor:
        item["_id"] = str(item["_id"])
        ledger_list.append(item)
        
    return ledger_list