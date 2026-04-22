from typing import Dict
from typing import Any
from typing import List
from fastapi import APIRouter
from database import db

router = APIRouter()

@router.get("/api/analytics")
def get_business_analytics() -> Dict[str, Any]:
    ledger_cursor = db.ledger.find()
    profit_by_date: Dict[str, Dict[str, float]] = {}
    
    for entry in ledger_cursor:
        date_str = str(entry.get("entry_date", "Unknown"))
        if date_str not in profit_by_date:
            profit_by_date[date_str] = {"income": 0.0, "expense": 0.0, "profit": 0.0}
            
        amt = float(entry.get("amount", 0.0))
        if entry.get("entry_type") == "Income":
            profit_by_date[date_str]["income"] += amt
            profit_by_date[date_str]["profit"] += amt
        else:
            profit_by_date[date_str]["expense"] += amt
            profit_by_date[date_str]["profit"] -= amt
            
    sales_cursor = db.sales.find()
    items_stats: Dict[str, Dict[str, float]] = {}
    
    for sale in sales_cursor:
        name = str(sale.get("original_item_name", "Unknown"))
        if name not in items_stats:
            items_stats[name] = {"volume": 0.0, "revenue": 0.0, "cost": 0.0, "margin": 0.0}
            
        qty = float(sale.get("quantity", 0.0))
        rev = float(sale.get("total_price", 0.0))
        cost = float(sale.get("total_cost", 0.0))
        
        items_stats[name]["volume"] += qty
        items_stats[name]["revenue"] += rev
        items_stats[name]["cost"] += cost
        items_stats[name]["margin"] += (rev - cost)
        
    receipts_cursor = db.receipts.find()
    lifestyle_stats: Dict[str, int] = {}
    
    for r in receipts_cursor:
        ls = str(r.get("lifestyle", "Unknown"))
        if ls not in lifestyle_stats:
            lifestyle_stats[ls] = 0
            
        lifestyle_stats[ls] += 1
        
    return {
        "financials": profit_by_date,
        "items": items_stats,
        "lifestyles": lifestyle_stats
    }