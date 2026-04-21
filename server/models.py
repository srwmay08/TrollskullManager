from pydantic import BaseModel
from typing import List
from typing import Optional


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
    open_hour: int = 12
    close_hour: int = 24
    is_closed: bool = False


class SaleItem(BaseModel):
    item_name: str
    original_item_name: str
    quantity: int
    stock_deduction: float
    total_price: float
    sale_date: str
    serve_size: Optional[str] = None


class InventoryItem(BaseModel):
    category: str
    item_name: str
    order_unit: str
    bottles_per_order_unit: int
    unit_cost_copper: float
    servings_per_bottle: int
    serve_size: str
    cost_per_serving_copper: float
    sell_price_serving_copper: float
    sell_price_bottle_copper: float
    margin_serving_copper: float
    stock_bottle_quantity: float
    reorder_level_bottles: int
    target_restock_bottles: int
    status: str
    reorder_quantity_units: int


class LedgerEntry(BaseModel):
    entry_type: str
    description: str
    amount: float
    frequency: str
    entry_date: str


class StaffItem(BaseModel):
    name: str
    role: str = "General"
    wage: float
    frequency: str
    bonus: int


class SaveDayRequest(BaseModel):
    calendar_date: str
    sales: List[SaleItem]
    is_closed: bool = False
    pay_wages: bool = False


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
    is_quest_giver: bool = False
    quest_trigger_chance: float = 0.0
    quest_hook_text: Optional[str] = None