import csv
from fastapi import APIRouter
from bson.objectid import ObjectId

from models import StaffItem
from database import db

router = APIRouter()

def sync_staff_to_csv() -> None:
    items = list(db.staff.find({}, {"_id": 0}))
    if not items:
        return
    keys = ["Name", "Role", "Wage", "Wage Timing", "Bonus"]
    with open("staff.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for item in items:
            writer.writerow({
                "Name": item.get("name", ""),
                "Role": item.get("role", "General"),
                "Wage": item.get("wage", 0.0),
                "Wage Timing": item.get("frequency", "Weekly"),
                "Bonus": item.get("bonus", 0)
            })

@router.get("/api/staff")
def get_staff():
    staff_cursor = db.staff.find()
    staff_list = []
    for s in staff_cursor:
        s["_id"] = str(s["_id"])
        staff_list.append(s)
    return staff_list

@router.put("/api/staff/{staff_id}")
def update_staff(staff_id: str, staff: StaffItem):
    db.staff.update_one({"_id": ObjectId(staff_id)}, {"$set": staff.dict()})
    sync_staff_to_csv()
    return {"status": "Staff Updated"}