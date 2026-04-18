import csv
from fastapi import APIRouter
from bson.objectid import ObjectId
from models import NpcItem
from database import db

router = APIRouter()

def sync_npcs_to_csv() -> None:
    items = list(db.npcs.find({}, {"_id": 0}))
    if not items:
        return
    keys = ["First Name", "Last Name", "Occupation", "Lifestyle", "Faction", "Age", "Bar Disposition", "Party Disposition", "Nobility Status", "Noble House", "Story Connection", "PC Affiliation"]
    with open("npcs.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for item in items:
            writer.writerow({
                "First Name": item.get("first_name", ""),
                "Last Name": item.get("last_name", ""),
                "Occupation": item.get("occupation", ""),
                "Lifestyle": item.get("lifestyle", ""),
                "Faction": item.get("faction", ""),
                "Age": item.get("age", 0),
                "Bar Disposition": item.get("bar_disposition", 0),
                "Party Disposition": item.get("party_disposition", 0),
                "Nobility Status": item.get("nobility_status", ""),
                "Noble House": item.get("noble_house", ""),
                "Story Connection": item.get("story_connection", ""),
                "PC Affiliation": item.get("pc_affiliation", "")
            })

@router.get("/api/npcs")
def get_npcs():
    npc_cursor = db.npcs.find()
    npc_list = []
    for item in npc_cursor:
        item["_id"] = str(item["_id"])
        npc_list.append(item)
    return npc_list

@router.put("/api/npcs/{item_id}")
def update_npc(item_id: str, item: NpcItem):
    db.npcs.update_one({"_id": ObjectId(item_id)}, {"$set": item.dict()})
    sync_npcs_to_csv()
    return {"status": "Updated"}