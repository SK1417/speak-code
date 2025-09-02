from pydantic import BaseModel
from typing import List, Optional

class Stock(BaseModel):
    ticker: str
    name: str
    current_price: float
    market_cap: float

class Portfolio(BaseModel):
    name: str
    holdings: List[Stock]
