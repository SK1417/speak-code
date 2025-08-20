from .logic import process_data
from ..models import User

def api_call():
    user = User("Bob", "bob@example.com")
    return process_data(user.name)
