import os
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from pydantic import UploadFile
from config import (
    BIDS_DB_PATH
)
from utils import (
    csv_to_tsv
)


def bids_subject_exists(label: str) -> bool:
    return (Path(BIDS_DB_PATH) / f"sub-{label}").is_dir()

def add_bids_subject(label: str) -> bool:
    path = Path(BIDS_DB_PATH) / f"sub-{label}"
    if path.exists():
        return True
    path.mkdir(parents=True)
    return True

# returns complete session label like "<game_name><session_number>" 
# or empty string "" if subject doesn't exist
def add_bids_single_run_session(subject_label: str, session_label: str) -> str:
    if not bids_subject_exists(subject_label):
        return ""
    full_session_label = f"{session_label}_{datetime.now(timezone.utc)}"
    path = Path(BIDS_DB_PATH) / f"sub-{subject_label}" / f"ses-{full_session_label}"
    if path.exists():
        return full_session_label
    path.mkdir(parents=True)
    return full_session_label

def delete_bids_single_run_session(subject_label: str,  session_label: str):
    session_path = Path(BIDS_DB_PATH) / f"sub-{subject_label}" / f"ses-{session_label}" 
    shutil.rmtree(session_path)
    
async def save_raw_file(file: UploadFile, subject_label: str, session_label: str, filename: str) -> Path:
    # session folder
    session_path = Path(BIDS_DB_PATH) / f"sub-{subject_label}" / f"ses-{session_label}"
    if not session_path.exists():
        return Path("")
    raw_path = session_path / "raw"
    raw_path.mkdir(exist_ok=True)

    # path
    try:
        dest = raw_path / filename
        with open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)
    except Exception as e:
        #file save fail
        delete_bids_single_run_session(subject_label, session_label)


    return dest

# datatype ="eeg"|"events"|"gameSettings"
async def convert_raw_data(input_filename_with_extension: str, subject_label: str, session_label: str, datatype:str):
    t = {
        "eeg": True,
        "events": True,
        "gameSettings": False
    }
    input_path = Path(BIDS_DB_PATH) / f"sub-{subject_label}" / f"ses-{session_label}" / "raw" / input_filename_with_extension
    output_path = Path(BIDS_DB_PATH) / get_clean_data_prefix(subject_label, session_label, datatype)
    if datatype == "eeg" or datatype == "events":
        return await asyncio.to_thread(csv_to_tsv, input_path, output_path)
    if datatype == "gameSettings":
        shutil.copy(input_path, output_path)

def get_subject_label(patientId: str):
    return f"{patientId}"

def get_session_label(experiment_name: str, session_number: str):
    return f"{experiment_name}_{session_number}"

# datatype ="eeg"|"events"|"gameSettings"
def get_clean_data_prefix(subject_label:str, session_label:str, datatype:str) -> str:
    t = {
        "eeg": "eeg.eeg",
        "events": "events.tsv",
        "gameSettings": "eeg.json"
    }
    return f"sub-{subject_label}_ses-{session_label}_task-{session_label}_run-01_{t[datatype]}"


#TODO: processes files, puts eeg data results into <session folder>/results
def process_files_job(subject_label:str, session_label:str):
    pass