from pydantic import BaseModel
from typing import List, Optional

class HarptosState(BaseModel):
    month: int
    day: int
    year: int
    is_holiday: bool = False
    holiday_name: Optional[str] = None
    is_shieldmeet: bool = False

class RollRequest(BaseModel):
    base_roll: int
    renown_bonus: int
    environmental_bonus: int
    current_date: Optional[HarptosState] = None
    price_strategy: str = "Standard"

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
    occupation: str
    lifestyle: str
    faction: str
    age: int
    bar_disposition: int
    party_disposition: int
    nobility_status: str
    noble_house: str
    story_connection: str
    pc_affiliation: str