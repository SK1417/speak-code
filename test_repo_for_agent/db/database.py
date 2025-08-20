class Database:
    def __init__(self, connection_string):
        self.connection_string = connection_string

    def connect(self):
        print(f"Connecting to {self.connection_string}")

    def get_user(self, user_id):
        return {"id": user_id, "name": "Test User"}
