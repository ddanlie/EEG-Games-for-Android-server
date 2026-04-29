# Connects endpoints and dbservice module
from typing import Union
from uuid import uuid4
import jwt
import traceback
from config import (
    JWT_SECRET
)

from models import (
    UserIdentity,
    EmailRequest,
    EmailCodeRequest
)
from dbservice import (
    create_signle_run_session,
    delete_signle_run_session,
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
from eeg_service import (
    get_user_id_bids_number,
    get_session_name_bids_number,
    bids_subject_exists,
    add_bids_subject,
    add_bids_single_run_session,
    bids_single_run_session_exists,
    delete_bids_single_run_session,
    save_raw_file,
    convert_raw_data_and_save_clean,
    get_subject_label,
    get_session_label,
    get_bids_filename_with_extension,
    analyse_files,
)

def app_login_request(req: EmailRequest) -> bool:
    # check if there is such email
    user = get_user_by_email(req.email)
    if user is None:
        user = add_new_user(req.email)
    code = send_code_to_email(req.email)
    if code is None:
        return False
    update_login_code(user["id"], str(code)) # type: ignore

    # BIDS db:
    add_bids_subject(get_subject_label(user["id"], user["bids_subject_number"])) #type: ignore
    return True


def app_login(eqrequest: EmailCodeRequest) -> UserIdentity | None:
    user = get_user_by_email(eqrequest.email)
    if user is None:
        return None
    if eqrequest.code != user["login_code"]:
        return None
    token = update_user_token(user["id"])
    update_login_code(user["id"], "") # forget the code
    return UserIdentity(token=token, userId=user["bids_subject_number"])
    

def app_login_token(token:str) -> UserIdentity | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None
    user = get_user_by_jwt(token)
    if user is None:
        return None
    update_login_code(user["id"], "") # forget the code
    return UserIdentity(token=token, userId=user["bids_subject_number"])


async def app_accept_recorded_run_data(subject_label, session_label, events, eegData, gameSettings) -> bool:
    
    add_bids_subject(subject_label)
    if bids_single_run_session_exists(subject_label, session_label):
        # Database
        user_id, user_bids_number = get_user_id_bids_number(subject_label)
        session_name, session_bids_number = get_session_name_bids_number(session_label)
        create_signle_run_session(user_id, session_name, session_bids_number)
    # BIDS
    add_bids_single_run_session(subject_label, session_label)

    try:
        await save_raw_file(events, subject_label, session_label, "events.csv")
        await save_raw_file(eegData, subject_label, session_label, "eeg_data.csv")
        await save_raw_file(gameSettings, subject_label, session_label, "game_settings.json")

        # await your conversion
        await convert_raw_data_and_save_clean("events.csv", subject_label, session_label, "eeg")
        await convert_raw_data_and_save_clean("eeg_data.csv", subject_label, session_label, "events")
        await convert_raw_data_and_save_clean("game_settings.json", subject_label, session_label, "gameSettings")
    except Exception as e:
        return False

    return True

async def app_process_recorded_run_data(subject_label, session_label) -> bool:
    add_bids_subject(subject_label)
    # Database
    user_id, user_bids_number = get_user_id_bids_number(subject_label)
    session_name, session_bids_number = get_session_name_bids_number(session_label)
    create_signle_run_session(user_id, session_name, session_bids_number)
    add_bids_single_run_session(subject_label, session_label)
    try: #will fail if first time run, need to add those files
        #events first, then eeg data!
        await convert_raw_data_and_save_clean("events.csv", subject_label, session_label, "events")
        print(f"APP: events OK")
        await convert_raw_data_and_save_clean("eeg_data.csv", subject_label, session_label, "eeg")
        print(f"APP: EEG OK")
        await convert_raw_data_and_save_clean("game_settings.json", subject_label, session_label, "gameSettings")
        print(f"APP: SETTINGS OK")
    except Exception as e:
        print(f"APP: exception {e}")
        print(traceback.print_exc())
        return False
    
    return True

async def app_process_and_analyse_single_session(subject_label, session_label) -> bool:
    if not await app_process_recorded_run_data(subject_label, session_label):
        print("APP: process run data failed")
        return False
    
    return analyse_files(subject_label, session_label)
    