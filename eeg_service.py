import mne_bids_pipeline_config_current
import os
import shutil
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime, timezone
import mne
import pandas as pd
import numpy as np
from pydantic import UploadFile
from config import (
    BIDS_DB_PATH,
    EEG_SAMPLING_RATE
)
from utils import (
    csv_to_tsv
)
from dbservice import (
    create_signle_run_session,
    create_run_observation,
    get_user_by_id,
)


CHANNELS = {
    "channel_1":{
        "name": "Fp1",
        "region_approx": "frontal"
    },
    "channel_2":{
        "name": "Fp2",
        "region_approx": "frontal"
    },
    "channel_3":{
        "name": "C1",
        "region_approx": "parietal" # least relevant
    },
    "channel_4":{
        "name": "C2",
        "region_approx": "parietal" # least relevant
    },
    "channel_5":{
        "name": "C5",
        "region_approx": "temporal" 
    },
    "channel_6":{
        "name": "C6",
        "region_approx": "temporal" 
    },
    "channel_7":{
        "name": "O1",
        "region_approx": "occipital"
    },
    "channel_8":{
        "name": "O2",
        "region_approx": "occipital"
    },
}

CONDITIONS = {
    "ERP_P1": {
        
    },

    "ERP_N1": {
        
    },

    "ERP_P300": {

    },

    "ERP_N170": {

    },

    "ERP_N2": {

    },

    "ERP_P2": {
    },

    "ERP_P3B": {

    }, 

    "ERP_P200": {

    },

    "ERP_MMN": {

    }
}


def bids_subject_exists(subject_label: str) -> bool:
    return (Path(BIDS_DB_PATH) / f"sub-{subject_label}").is_dir()


def add_bids_subject(subject_label: str) -> bool:
    path = Path(BIDS_DB_PATH) / f"sub-{subject_label}"
    if path.exists():
        return True
    path.mkdir(parents=True)
    return True

def add_bids_single_run_session(subject_label: str, session_label: str) -> bool:
    if not bids_subject_exists(subject_label):
        return False
    
    # Folders
    path = Path(BIDS_DB_PATH) / f"sub-{subject_label}" / f"ses-{session_label}"
    if path.exists():
        return True
    path.mkdir(parents=True)
 
    # Database
    user_id, user_bids_number = get_user_id_bids_number(subject_label)
    session_name, session_bids_number = get_session_name_bids_number(session_label)
    create_signle_run_session(user_id, session_name, session_bids_number)
    

    return True

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
async def convert_raw_data_and_save_clean(input_filename_with_extension: str, subject_label: str, session_label: str, datatype:str) -> bool:
    t = {
        "eeg": True,
        "events": True,
        "gameSettings": False
    }
    input_path = Path(BIDS_DB_PATH) / f"sub-{subject_label}" / f"ses-{session_label}" / "raw" / input_filename_with_extension
    output_path = Path(BIDS_DB_PATH) / f"sub-{subject_label}" / f"ses-{session_label}" / "eeg" / get_bids_filename_with_extension(subject_label, session_label, datatype)
    if not input_path.exists() or not output_path.exists():
        return False
    if datatype == "eeg":
        eeg_tsv_path = Path(str(input_path).replace(".csv", ".tsv"))
        await asyncio.to_thread(csv_to_tsv, input_path, eeg_tsv_path)
        await asyncio.to_thread(eeg_tsv_map_channels_set_cols, eeg_tsv_path, output_path)
    elif datatype == "events":
        await asyncio.to_thread(csv_to_tsv, input_path, output_path)
    elif datatype == "gameSettings":
        shutil.copy(input_path, output_path)
    return True

def get_user_id_bids_number(subject_label: str) -> list[str]:
    return subject_label.split("@")

def get_session_name_bids_number(session_label:str) -> list[str]:
    return session_label.split("@")

def get_subject_label(userId: str, bids_subject_number: str):
    return f"{userId}@{bids_subject_number}"

def get_session_label(experiment_name: str, session_number: str):
    return f"{experiment_name}@{session_number}"

# datatype ="eeg"|"events"|"gameSettings"|"resultProcCleanEpo"|"resultProcFiltRaw"|"microstatesReference"
def get_bids_filename_with_extension(subject_label:str, session_label:str, datatype:str) -> str:
    t = {
        #input
        "eeg": "eeg.fif",
        "events": "events.tsv",
        "gameSettings": "eeg.json",
        #output
        "resultProcCleanEpo": "proc_clean_epo.fif",
        "resultProcFiltRaw": "proc-filt_raw.fif",
        #reference
        "microstatesReference": "microstates_reference.mat"
    }
    if datatype == "microstatesReference":
        return t["microstatesReference"]
    return f"sub-{subject_label}_ses-{session_label}_task-{session_label}_run-01_{t[datatype]}"

def eeg_tsv_map_channels_set_cols(eeg_tsv_path, output_path):
    eeg = pd.read_csv(eeg_tsv_path, sep="\t")[CHANNELS.keys()]

    info = mne.create_info(
        ch_names=list(eeg.columns),
        sfreq=EEG_SAMPLING_RATE,
        ch_types="eeg"
    )
    raw = mne.io.RawArray(eeg.T.values, info)
    raw.save(output_path, overwrite=True)

# MNE BIDS PIPELINE
def analyse_files(subject_label:str, session_label:str) -> bool:
    # modify config
    derivatives_root = f"{BIDS_DB_PATH}\\derivatives\\mne-bids-pipeline"
    mne_bids_pipeline_config_current.bids_root = BIDS_DB_PATH
    mne_bids_pipeline_config_current.deriv_root = derivatives_root
    mne_bids_pipeline_config_current.sessions = [session_label]
    mne_bids_pipeline_config_current.task = session_label
    mne_bids_pipeline_config_current.runs = ["01"]
    mne_bids_pipeline_config_current.subjects = [subject_label]
    mne_bids_pipeline_config_current.conditions = CONDITIONS.keys()

    # run the pipeline
    with open("pipeline.output", "w") as out_file, open("pipeline.error", "w") as err_file:
        result = subprocess.run(
            ["mne_bids_pipeline", "--config=./pipeline_config_current.py"],
            stdout=out_file,
            stderr=err_file,
            text=True
        )

    print("PIPELINE Return code:", result.returncode)
    if result.returncode != 0:
        return False

    # gather results
    mne_pipeline_results_analysis(
        subject_label, 
        session_label, 
        Path(derivatives_root) / f"sub-{subject_label}" / f"ses-{session_label}" / "eeg"
    )

    return True


def mne_pipeline_results_analysis(subject_label:str, session_label:str, results_path:Path):
    import mne
    import matplotlib.pyplot as plt
    from pycrostates.preprocessing import extract_gfp_peaks
    from pycrostates.cluster import ModKMeans
    import pycrostates

    
    # Analyse ERPs amplitudes
    result_erp_amplitudes = {} # result: erp event name -> mean value

    epochs = mne.read_epochs(results_path / get_bids_filename_with_extension(subject_label, session_label, "resultProcCleanEpo"))
    # Get average - how average ERP looks like
    evokeds = {}
    for erp_event in epochs.event_id:
        evokeds[erp_event] = epochs[erp_event].average() 
    tmin, tmax = 0.1, 0.6 # [seconds] (safe window for all ERPs)

    # Average amplitudes per event shape: (event_count, )
    for erp_event, event_avg_samples_per_channel in evokeds.items():
        result_erp_amplitudes[erp_event] = event_avg_samples_per_channel.copy().crop(tmin, tmax).data.mean()


    
    # Analyse Band Power

    result_band_powers = {} # result: band -> region -> single value

    bands = {
        "delta": (1, 4), #[Hz]
        "theta": (4, 8),
        "alpha": (8, 13),
        "beta": (13, 30),
        "gamma": (30, 60)
    }

    region_map = {}
    ch_names = epochs.ch_names
    for file_ch_name, device_ch_data in CHANNELS.items():
        region = device_ch_data["region_approx"]

        if file_ch_name in ch_names:
            idx = ch_names.index(file_ch_name)
            region_map.setdefault(region, []).append(idx)

    psd = epochs.compute_psd(fmin=1, fmax=60)
    data = psd.get_data()  # shape: (epochs, channels, freqs)
    freqs = psd.freqs


    for band, (fmin, fmax) in bands.items():
        idx = (freqs >= fmin) & (freqs <= fmax)

        # collapse everything except channels
        band_ch = data[:, :, idx].mean(axis=(0, 2))  # (channels, )

        result_band_powers[band] = {}

        for region, ch_indices in region_map.items():
            result_band_powers[band][region] = band_ch[ch_indices].mean()

    


    
    # Check if reference map file exists
    subject_folder_path = Path(f"{BIDS_DB_PATH}\\sub-{subject_label}")
    reference_file_path = subject_folder_path / get_bids_filename_with_extension(subject_label, session_label, "microstatesReference")
    if reference_file_path.exists():
        # Analyse Microstates
        raw = mne.io.read_raw_fif(results_path / get_bids_filename_with_extension(subject_label, session_label, "resultProcFiltRaw"))
        raw.set_eeg_reference("average")
        gfp_peaks = extract_gfp_peaks(raw)
        # TODO: finish using read_results.ipynb in mne tests folder

    biomarkers_json_data = {

    }
    db_user_id = get_user_id_bids_number(subject_label)[0]
    db_session_bids_number = get_session_name_bids_number(session_label)[1]
    create_run_observation()
    # result_erp_amplitudes = {} # result: erp event name -> mean value
    # result_band_powers = {} # result: band -> region -> single value


# TODO: finish using read_results.ipynb in mne tests folder
def process_microstates_reference():
    pass