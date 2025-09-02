import random

def format_currency(value: float) -> str:
    return f"${value:,.2f}"

def generate_random_price_change() -> float:
    return random.uniform(-5.0, 5.0)
