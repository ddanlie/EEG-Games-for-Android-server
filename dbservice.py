import sqlite3
import json
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

def delete_eeg_game():
    pass

def get_user_eeg_games():
    pass


def create_signle_run_session(
    user_id, 
    session_name, 
    session_bids_number
):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE bids_session_number = ?", (session_bids_number,))
        row = cursor.fetchone()
        if row: #such session already exists
            return
        session_id = str(uuid4())
        cursor.execute(
            """
            INSERT INTO sessions (
                id, user_id, bids_session_number, created_at, description
            )
            VALUES (?,?,?,?,?)
            """,
            (session_id, user_id, session_bids_number, datetime.now(timezone.utc), ""),
        )

        cursor.execute(
            """
            INSERT INTO runs (
                id, game_id, session_id, bids_run_number, created_at, is_valid, notes
            )
            VALUES (?,?,?,?,?,?,?)
            """,
            (str(uuid4()), get_game_by_name(session_name)["id"], session_id, 1, datetime.now(timezone.utc), 1, "") # number is always 01 here
        )
        conn.commit()
    finally:
        conn.close()

def delete_signle_run_session(session_id:str):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM runs WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    finally:
        conn.close()

def create_game(name:str, description:str, attention_domain:str, attention_subdomain:str, other_info_json:dict):
    conn = get_conn()
    try:
        game_id = str(uuid4())
        
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO games (
                id, name, description, attention_domain, attention_subdomain, other_info_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (game_id, name, description, attention_domain, attention_subdomain, json.dumps(other_info_json))
        )
        conn.commit()
    finally:
        conn.close()


def delete_game(id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM games WHERE id = ?", (id,))
        conn.commit()
    finally:
        conn.close()


def create_observation(run_id:str, biomarkers_json_data: dict):
    conn = get_conn()
    try:
        observation_id = str(uuid4())
        
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO observations (
                id, run_id, biomarkers_json_data
            )
            VALUES (?, ?, ?)
            """,
            (observation_id, run_id, json.dumps(biomarkers_json_data))
        )
        conn.commit()
    finally:
        conn.close()


def get_session_by_bids_number(session_bids_number: str) -> dict | None:
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE bids_session_number = ?", (session_bids_number,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        return None
    finally:
        conn.close()
    

def get_game_by_name(game_name: str) -> dict | None:
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM games WHERE name = ?", (game_name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        return None
    finally:
        conn.close()

def get_single_session_run(game_id: str, session_id: str):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM runs WHERE game_id = ? AND session_id = ?", (game_id, session_id))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        return None
    finally:
        conn.close()

def get_user_session_runs(user_id: str) -> list[dict]:
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT runs.* FROM runs
            JOIN sessions ON runs.session_id = sessions.id
            WHERE sessions.user_id = ?
            """,
            (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows] if rows else []
    except Exception as e:
        return []
    finally:
        conn.close()
