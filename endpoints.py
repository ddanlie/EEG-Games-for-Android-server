from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from pathlib import Path
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
    app_login_token
)
from eeg_service import (
    bids_subject_exists,
    add_bids_subject,
    add_bids_single_run_session,
    save_raw_file,
    get_subject_label,
    get_session_label,
    convert_raw_data,
    process_files_job
)
from config import (
    BIDS_DB_PATH
)
from utils import (
    csv_to_tsv,
)

router = APIRouter(prefix="/api/v1")
security = HTTPBearer()


@router.post("/auth/login/request", status_code=status.HTTP_204_NO_CONTENT)
def login_request(erequest: EmailRequest):
    if(app_login_request(erequest)):
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    raise HTTPException(status_code=404, detail="Failed sending the code") 


@router.post("/auth/login", response_model=UserIdentity)
def login_first_time(eqrequest: EmailCodeRequest):
    user = app_login(eqrequest)
    if user is None:
        raise HTTPException(status_code=404, detail="Login failed, likely the wrong code from email pasted")
    return user

@router.post("/auth/login", response_model=UserIdentity)
def login_with_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    user = app_login_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Failed to login, token might be expired or user does not exist")
    return user

@router.post("/recorded-run-send", status_code=status.HTTP_204_NO_CONTENT)
async def accept_recorded_run_data(   
    background_tasks: BackgroundTasks,
    events: UploadFile = File(...),
    eegData: UploadFile = File(...),
    gameSettings: UploadFile = File(...),
    patientId: str = Form(...),
    experimentName: str = Form(...),
    sessionNumber: str = Form(...),
):
    # save events_T001.csv to  
    # eeg_data_T001.csv
    if not add_bids_subject:
        raise HTTPException(status_code=500, detail="Couldn't add bids subject")

    subject_label = get_subject_label(patientId)
    session_label = get_session_label(experimentName, sessionNumber)
    
    try:
        await save_raw_file(events, subject_label, session_label, "events.csv")
        await save_raw_file(eegData, subject_label, session_label, "eeg_data.csv")
        await save_raw_file(gameSettings, subject_label, session_label, "game_settings.json")

        # await your conversion
        await convert_raw_data("events.csv", subject_label, session_label, "eeg")
        await convert_raw_data("events.csv", subject_label, session_label, "events")
        await convert_raw_data("events.csv", subject_label, session_label, "gameSettings")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Server error: Couldn't convert or copy files on disk")
        pass
    # background processing (non-blocking)
    background_tasks.add_task(process_files_job, subject_label, session_label)

    return

# # --- Routes ---

# @router.get("/items", response_model=list[ItemResponse])
# def get_items():
#     """Return all items."""
#     return [
#         {"id": 1, "name": "Example item", "description": "A sample item"},
#     ]


# @router.get("/items/{item_id}", response_model=ItemResponse)
# def get_item(item_id: int):
#     """Return a single item by ID."""
#     if item_id != 1:
#         raise HTTPException(status_code=404, detail="Item not found")
#     return {"id": item_id, "name": "Example item", "description": "A sample item"}


# @router.post("/items", response_model=ItemResponse, status_code=201)
# def create_item(item: Item):
#     """Create a new item."""
#     return {"id": 2, **item.model_dump()}


# @router.delete("/items/{item_id}", status_code=204)
# def delete_item(item_id: int):
#     """Delete an item by ID."""
#     if item_id != 1:
#         raise HTTPException(status_code=404, detail="Item not found")