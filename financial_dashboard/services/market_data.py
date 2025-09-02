from ..models.instrument import Stock
from ..utils.helpers import generate_random_price_change

def get_stock_price(ticker: str) -> float:
    """Simulates fetching the current price of a stock."""
    base_prices = {
        "AAPL": 150.0,
        "GOOGL": 2800.0,
        "MSFT": 300.0,
        "AMZN": 3400.0
    }
    base_price = base_prices.get(ticker, 200.0)
    return base_price + generate_random_price_change()

def get_market_overview() -> list[Stock]:
    """Provides an overview of the market with some example stocks."""
    stocks = [
        Stock(ticker="AAPL", name="Apple Inc.", current_price=get_stock_price("AAPL"), market_cap=2.4e12),
        Stock(ticker="GOOGL", name="Alphabet Inc.", current_price=get_stock_price("GOOGL"), market_cap=1.9e12),
        Stock(ticker="MSFT", name="Microsoft Corporation", current_price=get_stock_price("MSFT"), market_cap=2.2e12),
        Stock(ticker="AMZN", name="Amazon.com, Inc.", current_price=get_stock_price("AMZN"), market_cap=1.7e12),
    ]
    return stocks
