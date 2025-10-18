from datetime import datetime, timedelta
import bcrypt
import secrets

class AuthManager:
    def __init__(self):
        # Store users in a dictionary (not a real DB)
        self.users = {}  
        # Store sessions: token -> user info and expiry time
        self.sessions = {}  
        # How long a session lasts
        self.session_duration = timedelta(hours=24)

    # Register a new user (hash password before storing)
    def register_user(self, username, password):
        if username in self.users:
            raise ValueError("Username already exists")

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_id = len(self.users) + 1
        self.users[username] = {
            'id': user_id,
            'username': username,
            'password_hash': hashed,
            'created_at': datetime.now()
        }
        return user_id

    # Login user and create a session token
    def login_user(self, username, password):
        if username not in self.users:
            raise ValueError("Invalid username or password")

        user = self.users[username]
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            raise ValueError("Invalid username or password")

        token = secrets.token_hex(32)
        expiry = datetime.now() + self.session_duration

        self.sessions[token] = {
            'user_id': user['id'],
            'username': username,
            'expiry': expiry
        }

        return token

    # Check if a session token is valid (exists and not expired)
    def validate_session(self, token):
        if token not in self.sessions:
            return False

        session = self.sessions[token]
        if datetime.now() > session['expiry']:
            del self.sessions[token]
            return False

        return True

    # Get user id for a given username
    def get_user_id(self, username):
        if username in self.users:
            return self.users[username]['id']
        return None

    # Remove expired sessions from the session dictionary
    def cleanup_expired_sessions(self):
        now = datetime.now()
        expired = [t for t, s in self.sessions.items() if now > s['expiry']]
        for token in expired:
            del self.sessions[token]
