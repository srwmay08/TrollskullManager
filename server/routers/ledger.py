import csv
from typing import Dict, Any
from fastapi import APIRouter
from bson.objectid import ObjectId
from database import db

router = APIRouter()

def sync_collection_to_csv(collection_obj, filepath: str) -> None:
    items = list(collection_obj.find({}, {"_id": 0}))
    if not items:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            f.write("")
        return
        
    keys = []
    for item in items:
        for k in item.keys():
            if k not in keys:
                keys.append(k)
                
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for item in items:
            writer.writerow(item)

@router.get("/api/ledger")
def get_ledger():
    cursor = db.ledger.find()
    data_list = []
    for item in cursor:
        item["_id"] = str(item["_id"])
        data_list.append(item)
    return data_list

@router.post("/api/ledger")
def create_ledger(item: Dict[str, Any]):
    item.pop("_id", None)
    result = db.ledger.insert_one(item)
    sync_collection_to_csv(db.ledger, "ledger.csv")
    return {"status": "Created", "id": str(result.inserted_id)}

@router.put("/api/ledger/{item_id}")
def update_ledger(item_id: str, item: Dict[str, Any]):
    item.pop("_id", None)
    db.ledger.update_one({"_id": ObjectId(item_id)}, {"$set": item})
    sync_collection_to_csv(db.ledger, "ledger.csv")
    return {"status": "Updated"}

@router.delete("/api/ledger/{item_id}")
def delete_ledger(item_id: str):
    db.ledger.delete_one({"_id": ObjectId(item_id)})
    sync_collection_to_csv(db.ledger, "ledger.csv")
    return {"status": "Deleted"}