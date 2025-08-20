from ..utils import greet
from ..db.database import Database

def process_data(data):
    db = Database("sqlite:///:memory:")
    db.connect()
    user = db.get_user(1)
    return greet(user['name'])
