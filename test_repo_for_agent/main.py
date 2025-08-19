from utils import greet
from models import User

def main():
    print(greet("World"))
    user = User("Alice", "alice@example.com")
    print(f"User: {user.name}, Email: {user.email}")

if __name__ == "__main__":
    main()
