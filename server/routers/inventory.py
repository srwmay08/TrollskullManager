import csv
import os
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

def seed_from_csv_if_empty():
    """Reads the CSV and populates the DB if the DB is currently empty."""
    if db.inventory.count_documents({}) == 0 and os.path.exists("inventory.csv"):
        with open("inventory.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                for row in rows:
                    for k, v in row.items():
                        if v is None:
                            row[k] = ""
                            continue
                        val_str = str(v).strip()
                        if val_str.lower() == 'true': row[k] = True
                        elif val_str.lower() == 'false': row[k] = False
                        else:
                            try:
                                row[k] = float(val_str) if '.' in val_str else int(val_str)
                            except ValueError:
                                row[k] = val_str
                db.inventory.insert_many(rows)

@router.get("/api/inventory")
def get_inventory():
    seed_from_csv_if_empty()
    cursor = db.inventory.find()
    data_list = []
    for item in cursor:
        item["_id"] = str(item["_id"])
        data_list.append(item)
    return data_list

@router.post("/api/inventory")
def create_inventory(item: Dict[str, Any]):
    item.pop("_id", None)
    result = db.inventory.insert_one(item)
    sync_collection_to_csv(db.inventory, "inventory.csv")
    return {"status": "Created", "id": str(result.inserted_id)}

@router.put("/api/inventory/{item_id}")
def update_inventory(item_id: str, item: Dict[str, Any]):
    item.pop("_id", None)
    db.inventory.update_one({"_id": ObjectId(item_id)}, {"$set": item})
    sync_collection_to_csv(db.inventory, "inventory.csv")
    return {"status": "Updated"}

@router.delete("/api/inventory/{item_id}")
def delete_inventory(item_id: str):
    db.inventory.delete_one({"_id": ObjectId(item_id)})
    sync_collection_to_csv(db.inventory, "inventory.csv")
    return {"status": "Deleted"}