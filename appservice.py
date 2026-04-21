# Connects endpoints and dbservice module
from typing import Union
from uuid import uuid4
import jwt
from config import (
    JWT_SECRET
)

from models import (
    UserIdentity,
    EmailRequest,
    EmailCodeRequest
)
from dbservice import (
    get_user_by_email,
    get_user_by_id,
    add_new_user,
    update_user_token,
    update_login_code,
    get_user_by_jwt,
)
from utils import (
    send_code_to_email,
)

def app_login_request(req: EmailRequest) -> bool:
    # check if there such email
    user = get_user_by_email(req.email)
    if user is None:
        user = add_new_user(req.email)
    code = send_code_to_email(req.email)
    if code is None:
        return False
    update_login_code(user["id"], str(code)) # type: ignore
    return True


def app_login(eqrequest: EmailCodeRequest) -> UserIdentity | None:
    user = get_user_by_email(eqrequest.email)
    if user is None:
        return None
    if eqrequest.code != user["login_code"]:
        return None
    token = update_user_token(user["id"])
    update_login_code(user["id"], "") # forget the code
    return UserIdentity(token=token, userId=user["id"])
    

def app_login_token(token:str) -> UserIdentity | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None
    user = get_user_by_jwt(token)
    if user is None:
        return None
    update_login_code(user["id"], "") # forget the code
    return UserIdentity(token=token, userId=user["id"])