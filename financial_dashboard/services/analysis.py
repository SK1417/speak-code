import random
from ..utils.helpers import format_currency

def perform_deep_analysis(ticker: str) -> dict:
    """Top-level function to perform a deep financial analysis of a stock."""
    historical_data = _fetch_historical_data(ticker)
    moving_average = _calculate_moving_average(historical_data)
    volatility = _calculate_volatility(historical_data)
    report = _generate_report(ticker, moving_average, volatility)
    return report

def _fetch_historical_data(ticker: str) -> list[float]:
    """Simulates fetching historical price data for a stock."""
    # In a real app, this would be a database or API call
    print(f"Fetching historical data for {ticker}...")
    return [100 + i + random.uniform(-2, 2) for i in range(90)]

def _calculate_moving_average(data: list[float]) -> float:
    """Calculates the 30-day moving average."""
    print("Calculating moving average...")
    if len(data) < 30:
        return sum(data) / len(data)
    return sum(data[-30:]) / 30

def _calculate_volatility(data: list[float]) -> float:
    """Calculates the price volatility (standard deviation)."""
    print("Calculating volatility...")
    mean = sum(data) / len(data)
    variance = sum([(price - mean) ** 2 for price in data]) / len(data)
    return variance ** 0.5

def _generate_report(ticker: str, moving_average: float, volatility: float) -> dict:
    """Generates a final analysis report."""
    print("Generating final report...")
    return {
        "ticker": ticker,
        "30_day_moving_average": format_currency(moving_average),
        "volatility_index": f"{volatility:.2f}",
        "summary": f"Analysis for {ticker} shows a 30-day moving average of {format_currency(moving_average)} with a volatility of {volatility:.2f}."
    }
