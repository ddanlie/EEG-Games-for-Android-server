import mne_bids_pipeline_config_current
import pandas as pd
import os
import sys
import shutil
import asyncio

import subprocess
from pathlib import Path
from datetime import datetime, timezone
import mne
import pandas as pd
from mne_bids import BIDSPath, write_raw_bids
import numpy as np
from fastapi import UploadFile
from config import (
    BIDS_DB_PATH,
    EEG_SAMPLING_RATE
)
from utils import (
    csv_to_tsv
)
from dbservice import (
    create_observation,
    get_user_by_id,
    get_session_by_bids_number,
    get_game_by_name,
    get_single_session_run,
)

EXG_LSB = 0.045

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
        "name": "C5",
        "region_approx": "parietal" # least relevant
    },
    "channel_4":{
        "name": "C1",
        "region_approx": "parietal" # least relevant
    },
    "channel_5":{
        "name": "C2",
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

# tmin, tmax [seconds] - see mne confing definitions
CONDITIONS = {
  "ERP_P1": {
    #"region_approx": ["occipital"],
    "tmin": 0.08,
    "tmax": 0.13
  },

  "ERP_N1": {
    #"region_approx": ["occipital", "frontal"],
    "tmin": 0.10,
    "tmax": 0.15
  },

  "ERP_N170": {
    #"region_approx": ["temporo-occipital"] # (right > left),
    "tmin": 0.14,
    "tmax": 0.20
  },

  "ERP_N2": {
    #"region_approx": "fronto-central",
    "tmin": 0.20,
    "tmax": 0.35
  },

  "ERP_P2": {
    #"region_approx": "fronto-central",
    "tmin": 0.15,
    "tmax": 0.28
  },

  # same as P2, only for the second stimuli (e.g. in Attentional Blink test)
  "ERP_P2_2": {
    #"region_approx": "fronto-central",
    "tmin": 0.15,
    "tmax": 0.28
  },
  
  "ERP_P3B": {
    #"region_approx": "parietal (Pz)",
    "tmin": 0.30,
    "tmax": 0.60
  },

  "ERP_P200": {
    #"region_approx": "fronto-central",
    "tmin": 0.15,
    "tmax": 0.25
  },

  "ERP_MMN": {
    #"region_approx": "fronto-central (with temporal sources)",
    "tmin": 0.10,
    "tmax": 0.25
  }
}


def bids_subject_exists(subject_label: str) -> bool:
    return (Path(BIDS_DB_PATH) / f"sub-{subject_label}").is_dir()

def bids_single_run_session_exists(subject_label: str, session_label: str) -> bool:
    path = Path(BIDS_DB_PATH) / f"sub-{subject_label}" / f"ses-{session_label}"
    return path.exists()

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
    subpaths = [path / "raw", path / "eeg"]

    if path.exists():
        return True
    path.mkdir(parents=True)
    for sbpth in subpaths:
        sbpth.mkdir()
 
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
    if not input_path.exists():
        return False
    if datatype == "eeg":
        eeg_tsv_path = Path(str(input_path).replace(".csv", ".tsv"))
        events_tsv_path = Path(BIDS_DB_PATH) \
            / f"sub-{subject_label}" / f"ses-{session_label}" / "eeg" / \
            get_bids_filename_with_extension(subject_label, session_label, "events")
        await asyncio.to_thread(csv_to_tsv, input_path, eeg_tsv_path)
        await asyncio.to_thread(eeg_tsv_map_channels_set_cols, eeg_tsv_path, events_tsv_path, output_path, subject_label, session_label)
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
        "resultProcCleanEpo": "proc-clean_epo.fif",
        "resultProcFiltRaw": "proc-filt_raw.fif",
        #reference
        "microstatesReference": "microstates_reference.mat",
    }
    if datatype == "microstatesReference":
        return t["microstatesReference"]
    if datatype == "resultProcCleanEpo":
        return f"sub-{subject_label}_ses-{session_label}_task-common_{t[datatype]}" 
    return f"sub-{subject_label}_ses-{session_label}_task-common_run-01_{t[datatype]}"

def eeg_tsv_map_channels_set_cols(eeg_tsv_path, eeg_events_tsv_path, output_path, subject_label, session_label):
    eeg = pd.read_csv(eeg_tsv_path, sep="\t")[CHANNELS.keys()]
    events = pd.read_csv(eeg_events_tsv_path, sep="\t")
    annotations = mne.Annotations(
        onset=events["onset"].values,
        duration=events["duration"].values,
        description=events["trial_type"].astype(str).values
    )
    info = mne.create_info(
        ch_names=[data["name"] for ch, data in CHANNELS.items()],
        sfreq=EEG_SAMPLING_RATE,
        ch_types="eeg"
    )
    raw = mne.io.RawArray(eeg.T.values * EXG_LSB / float(1e6), info)# [Volts]
    raw.set_annotations(annotations)
    # raw.save(output_path, overwrite=True)


    bids_path = BIDSPath(
        subject=subject_label,
        session=session_label,
        task="common",             
        run="01",
        datatype="eeg",
        root=BIDS_DB_PATH
    )

    write_raw_bids(
        raw,
        bids_path=bids_path,
        overwrite=True,
        format="EDF",
        allow_preload=True,
    )



# MNE BIDS PIPELINE
def analyse_files(subject_label:str, session_label:str) -> bool:
    # modify config
    derivatives_root = f"{BIDS_DB_PATH}\\derivatives\\mne-bids-pipeline"

    configs_path = Path(f"{BIDS_DB_PATH}") / f"sub-{subject_label}" / f"ses-{session_label}" / "eeg"
    base_config_path = configs_path / "mne_config_base.py"
    current_config_path = configs_path / "mne_config.py"

    shutil.copy("./mne_bids_pipeline_config_base.py", base_config_path)

    events_tsv_path = Path(BIDS_DB_PATH) \
            / f"sub-{subject_label}" / f"ses-{session_label}" / "eeg" / \
            get_bids_filename_with_extension(subject_label, session_label, "events")
    events = pd.read_csv(events_tsv_path, sep="\t")
    conditions = sorted(events["trial_type"].unique())

    current_config_path.write_text(f"""
import os
import sys
from pathlib import Path

# Insert this dir so pipeline module can see it
base_config_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(base_config_dir))

from mne_config_base import *

bids_root = r"{BIDS_DB_PATH}"
deriv_root = r"{derivatives_root}"
sessions = ["{session_label}"]
task = "common"
runs = ["01"]
subjects = ["{subject_label}"]
conditions = {conditions}
notch_freq = [25, 50, 100, 150]
epochs_tmin = -0.2
epochs_tmax = 1.2 # max + some padding for any ERP
""", encoding="utf-8"
)

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    # run the pipeline
    with open("pipeline.output", "w") as out_file, open("pipeline.error", "w") as err_file:
        result = subprocess.run(
            ["mne_bids_pipeline", f"--config={str(current_config_path)}"],
            stdout=out_file,
            stderr=err_file,
            text=True,
            env=env
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

    for erp_event, event_avg_samples_per_channel in evokeds.items():
        cropped = event_avg_samples_per_channel.copy().crop(
            CONDITIONS[erp_event]["tmin"], 
            CONDITIONS[erp_event]["tmax"]
        ).data # shape: (channels, timepoints)
        result_erp_amplitudes[erp_event] = {
            "positive": cropped.max(),
            "negative": cropped.min(),
            "channels-mean": cropped.mean() # mean value across channels 
        }
            


    
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
    for _, device_ch_data in CHANNELS.items():
        region = device_ch_data["region_approx"]
        
        if device_ch_data["name"] in ch_names:
            idx = ch_names.index(device_ch_data["name"])
            region_map.setdefault(region, []).append(idx)

    psd = epochs.compute_psd(fmin=1, fmax=60)
    data = psd.get_data()  # shape: (epochs, channels, freqs)
    freqs = psd.freqs

    for epoch_idx in range(data.shape[0]):
        epoch_data = data[epoch_idx]  # shape: (channels, freqs)
        result_band_powers[epoch_idx] = {}

        for band, (fmin, fmax) in bands.items():
            freq_idx = (freqs >= fmin) & (freqs <= fmax)
            band_ch = epoch_data[:, freq_idx].mean(axis=1)  # (channels, )
            result_band_powers[epoch_idx][band] = {}

            for region, ch_indices in region_map.items():
                result_band_powers[epoch_idx][band][region] = band_ch[ch_indices].mean()
    


    result_microstates_stats = {}
    # Check if reference map file exists
    subject_folder_path = Path(f"{BIDS_DB_PATH}\\sub-{subject_label}")
    reference_file_path = subject_folder_path / get_bids_filename_with_extension(subject_label, session_label, "microstatesReference")
    if reference_file_path.exists():
        # Analyse Microstates
        raw = mne.io.read_raw_fif(results_path / get_bids_filename_with_extension(subject_label, session_label, "resultProcFiltRaw"))
        raw.set_eeg_reference("average")
        gfp_peaks = extract_gfp_peaks(raw)
        # TODO: finish using read_results.ipynb in mne tests folder

    # result_erp_amplitudes - dict # result: erp event name -> mean value
    # result_band_powers - dict # result: band -> region -> single value
    biomarkers_json_data = {
        "erp_amplitudes": result_erp_amplitudes,
        "band_powers": result_band_powers,
        "microstates_stats": result_microstates_stats
    }
    db_user_id = get_user_id_bids_number(subject_label)[0]
    game_name, db_session_bids_number = get_session_name_bids_number(session_label)
    session  = get_session_by_bids_number(db_session_bids_number)
    game = get_game_by_name(game_name)
    session_run = get_single_session_run(game["id"], session["id"]) #type: ignore
    create_observation(session_run["id"], biomarkers_json_data) #type: ignore


# TODO: finish using read_results.ipynb in mne tests folder
def process_microstates_reference():
    pass