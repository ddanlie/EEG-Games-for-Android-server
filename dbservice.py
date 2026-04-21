import sqlite3
from uuid import uuid4
from datetime import datetime, timezone
from models import (
    UserIdentity
)
from config import (
    DB_PATH
)
from utils import (
    generate_infinite_jwt_token
)

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn 

def get_user_by_email(email: str) -> dict | None:
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
 
def get_user_by_id(user_id: str) -> dict | None:
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
 
def get_user_by_jwt(token: str) -> dict | None:
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE jwt_token = ?", (token,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
 
def get_user_by_bids_subject_number(number: int) -> dict | None:
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE bids_subject_number  = ?", (number,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_new_user(email: str) -> dict | None:
    conn = get_conn()
    try:
        user_id = str(uuid4())
        created_at = datetime.now(timezone.utc)
        token = generate_infinite_jwt_token()
 
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(MAX(bids_subject_number), 0) + 1 FROM users;
        """)
        autoincremented = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO users (
                id, email, created_at, jwt_token, role, bids_subject_number, login_code
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, email, created_at, token, "individual", autoincremented, "")
        )
        conn.commit()
        return get_user_by_id(user_id)
    except sqlite3.IntegrityError:
        # email already exists
        return None
    finally:
        conn.close()
 
def update_user_token(userId: str, token: str = generate_infinite_jwt_token()) -> str:
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET jwt_token = ? WHERE id = ?",
            (token, userId),
        )
        conn.commit()
        return token
    finally:
        conn.close()
 
def update_login_code(userId: str, code: str):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET login_code = ? WHERE id = ?",
            (code, userId),
        )
        conn.commit()
    finally:
        conn.close()

#TODO:
def add_eeg_game():
    pass

def delete_eeg_game():
    pass

def get_user_eeg_games():
    pass

# def get_user_by_email(email: str) -> dict | None:
#     pass

# def get_user_by_id() -> dict | None:
#     pass

# def get_user_by_jwt(token: str) -> dict | None:
#     pass

# def add_new_user(email: str) -> dict | None:
#     pass

# def update_user_token(userId: str, token: str=generate_infinite_jwt_token()) -> str: 
#     pass

# def update_login_code(userId: str, code: str):
#     pass


# def login(username: str, password: str) -> Optional[Dict]:
# with get_conn() as conn:
#     row = conn.execute(
#         "SELECT id, username FROM users WHERE username=? AND password=?",
#         (username, password)
#     ).fetchone()

#     return dict(row) if row else None