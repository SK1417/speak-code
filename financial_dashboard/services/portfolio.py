from ..models.instrument import Stock, Portfolio
from .market_data import get_stock_price

def get_user_portfolio(user_id: str) -> Portfolio:
    """Simulates fetching a user's portfolio."""
    # In a real app, you'd fetch this from a database
    holdings = [
        Stock(ticker="AAPL", name="Apple Inc.", current_price=get_stock_price("AAPL"), market_cap=2.4e12),
        Stock(ticker="MSFT", name="Microsoft Corporation", current_price=get_stock_price("MSFT"), market_cap=2.2e12),
    ]
    return Portfolio(name=f"{user_id}'s Portfolio", holdings=holdings)

def calculate_portfolio_value(portfolio: Portfolio) -> float:
    """Calculates the total value of a portfolio."""
    total_value = 0.0
    for stock in portfolio.holdings:
        total_value += stock.current_price
    return total_value
