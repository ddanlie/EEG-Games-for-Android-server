from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from pathlib import Path
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import (
    APIRouter, HTTPException,  Response, 
    status, Depends, Form, BackgroundTasks,
    UploadFile, File,
)
from models import (
    UserIdentity,
    EmailRequest,
    EmailCodeRequest,
)
from appservice import (
    app_login_request,
    app_login,
    app_login_token,
    app_accept_recorded_run_data,
)
from eeg_service import (
    bids_subject_exists,
    add_bids_subject,
    add_bids_single_run_session,
    save_raw_file,
    get_subject_label,
    get_session_label,
    convert_raw_data_and_save_clean,
    analyse_files
)
from dbservice import (
    get_user_by_jwt,
    get_user_by_id,
)
from config import (
    BIDS_DB_PATH
)
from utils import (
    csv_to_tsv,
)

router = APIRouter(prefix="/api/v1")
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if not get_user_by_jwt(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

@router.post("/auth/login/request", status_code=status.HTTP_204_NO_CONTENT)
def login_request(erequest: EmailRequest):
    if(app_login_request(erequest)):
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Failed sending the code") 


@router.post("/auth/login", response_model=UserIdentity)
def login_first_time(eqrequest: EmailCodeRequest):
    user = app_login(eqrequest)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Login failed, likely the wrong code from email pasted")
    return user

@router.post("/auth/login", response_model=UserIdentity)
def login_with_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    user = app_login_token(token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to login, token might be expired or user does not exist")
    return user

@router.post("/recorded-run-send", status_code=status.HTTP_204_NO_CONTENT)
async def accept_recorded_run_data(   
    background_tasks: BackgroundTasks,
    events: UploadFile = File(...),
    eegData: UploadFile = File(...),
    gameSettings: UploadFile = File(...),
    patientId: str = Form(...), # this is a bids_subject_number
    experimentName: str = Form(...),
    sessionNumber: str = Form(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    user = get_user_by_jwt(token)
 
    subject_label = get_subject_label(user["id"], patientId) #type: ignore
    session_label = get_session_label(experimentName, sessionNumber)

    if not await app_accept_recorded_run_data(subject_label, session_label, events, eegData, gameSettings):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server error: Couldn't convert or copy files on disk")    

    background_tasks.add_task(analyse_files, subject_label, session_label)
    # try:
    #     await save_raw_file(events, subject_label, session_label, "events.csv")
    #     await save_raw_file(eegData, subject_label, session_label, "eeg_data.csv")
    #     await save_raw_file(gameSettings, subject_label, session_label, "game_settings.json")

    #     # await your conversion
    #     await convert_raw_data_and_save_clean("events.csv", subject_label, session_label, "eeg")
    #     await convert_raw_data_and_save_clean("eeg_data.csv", subject_label, session_label, "events")
    #     await convert_raw_data_and_save_clean("game_settings.json", subject_label, session_label, "gameSettings")
    # except Exception as e:
    #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server error: Couldn't convert or copy files on disk")
    #     pass


    return