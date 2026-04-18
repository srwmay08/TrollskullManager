from fastapi import APIRouter
from bson.objectid import ObjectId

from models import StaffItem
from database import db

router = APIRouter()


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
    return {"status": "Staff Updated"}