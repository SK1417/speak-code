from fastapi import APIRouter
from typing import List
from ..models.instrument import Stock, Portfolio
from ..services import market_data, portfolio, analysis

router = APIRouter()

@router.get("/market", response_model=List[Stock])
def get_market_overview():
    """Get an overview of the current market."""
    return market_data.get_market_overview()

@router.get("/portfolio/{user_id}", response_model=Portfolio)
def get_portfolio(user_id: str):
    """Get the portfolio for a specific user."""
    user_portfolio = portfolio.get_user_portfolio(user_id)
    return user_portfolio

@router.get("/portfolio/{user_id}/value")
def get_portfolio_value(user_id: str):
    """Calculate the total value of a user's portfolio."""
    user_portfolio = portfolio.get_user_portfolio(user_id)
    total_value = portfolio.calculate_portfolio_value(user_portfolio)
    return {"user_id": user_id, "total_value": total_value}

@router.get("/analysis/{ticker}")
def get_deep_analysis(ticker: str):
    """Perform a deep analysis of a stock."""
    return analysis.perform_deep_analysis(ticker)
