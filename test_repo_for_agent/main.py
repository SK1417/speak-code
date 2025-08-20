from utils import greet
from models import User
from services.api import api_call

def main():
    print(greet("World"))
    user = User("Alice", "alice@example.com")
    print(f"User: {user.name}, Email: {user.email}")
    print(f"API Call Response: {api_call()}")

if __name__ == "__main__":
    main()
