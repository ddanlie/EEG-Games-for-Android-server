import csv
import sqlite3
import jwt
from uuid import uuid4
from datetime import datetime, timedelta, timezone
import secrets
import random
import smtplib
from email.mime.text import MIMEText
from config import (
    JWT_SECRET,
    GOOGLE_SMTP_APP_PASSWORD,
)

# Call example: sv_to_tsv("input.csv", "output.tsv")
def csv_to_tsv(input_path, output_path):
    with open(input_path, newline='', encoding='utf-8') as fin, \
         open(output_path, 'w', newline='', encoding='utf-8') as fout:

        reader = csv.reader(fin)
        writer = csv.writer(fout, delimiter='\t')

        for row in reader:
            writer.writerow(row)

def create_db_from_schema(schema_name="schema.sql", dbname="app.db"):
    # cli alternative: sqlite3 app.db < schema.sql
    with sqlite3.connect(dbname) as conn:
        with open(schema_name, "r", encoding="utf-8-sig") as f:
            conn.executescript(f.read())

def generate_login_code() -> int:
    return random.randint(100000, 999999) 

def send_code_to_email(email: str, code: int|None=None) -> bool:
    if code is None:
        code = generate_login_code()
    html = f"""
    <html>
      <body style="margin:0; padding:0; font-family: Arial;">
        <div style="
            display:flex;
            height:100vh;
            justify-content:center;
            align-items:center;
            font-size:28px;
            font-weight:bold;
        ">
            Your Code: {code}
        </div>
      </body>
    </html>
    """
    me = "danildomrachev111@gmail.com"
    msg = MIMEText(html, "html")
    msg["Subject"] = "Login Code"
    msg["From"] = me 
    msg["To"] = email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login("danildomrachev111@gmail.com", GOOGLE_SMTP_APP_PASSWORD)
            server.sendmail(me, [email], msg.as_string())
        return True
    except Exception as e:
        print(e)
        return False

def generate_infinite_jwt_token(data: dict={}) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(days=365 * 100)
    payload["iat"] = datetime.now(timezone.utc)
    payload["jti"] = str(uuid4())
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token

def generate_jwt_secret() -> str:
    return secrets.token_hex(32)

