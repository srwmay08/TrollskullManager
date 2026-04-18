from pydantic import BaseModel
from typing import List

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

class NpcItem(BaseModel):
    first_name: str
    last_name: str
    type: str
    lifestyle: str
    affiliation: str
    age: int
    bar_disposition: int
    party_disposition: int