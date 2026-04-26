import os
import sys
from pathlib import Path

# Insert this dir (must contain pipeline_config_base.py) so pipeline module can see it
base_config_dir = Path(__name__).parent.resolve()
sys.path.insert(0, str(base_config_dir))
from mne_bids_pipeline_config_base import *

# Below are essential customizations the server should do to choose what to process
# The rest of pipeline_config_base.py settings is treated as generic and doesn't need to be changed 


# ----------- Data samples selection ----------- #
# BIDS folder
bids_root = "./test_data2"
# Derivatives (analysis results) root
deriv_root = "./test_data2/derivatives/mne-bids-pipeline" 
# Process specific session (e.g. specify new sessions arrived after processing request from app)
sessions = ["01"]
# Process specific task (same approach as for session)
task = "fist"
# Process specific run (same approach as for session)
runs = ["01"] # list[str]
# Users (same approach as for session)
subjects = ["01"] # list[str]
# Force to process ERPs and do some other steps

# ----------- Some sample specific config ----------- #

task_is_rest = False
# Crop your data if there are some specifications
crop_runs = None
# Define eye close channels to be able to remove blinks artifacts etc

# ----------- Denoising, cleaning, filtering ----------- #

# Channels Montage
# Check it with print(mne.channels.get_builtin_montages())
eeg_template_montage = "standard_1020"# "biosemi64" # 
# MNE Reader extra params
reader_extra_params = {
    #"units": "uV",
}
# Channels of higher ocular activity
eog_channels = []#['Fp1', 'Fp2'] 
# Time for automatically detected breaks to be spotted
min_break_duration = 15.0 # [Seconds]
# Padding of breaks in the start <useful data>|<5 seconds included> ------ long break -----|<useful data>
t_break_annot_start_after_previous_event = 5.0
# Padding of breaks in the end   <useful data>|------ long break ----- <5 seconds included>|<useful data>
t_break_annot_stop_before_next_event = 5.0
# High-pass (filter all what is lower than l_freq) [Hz]
l_freq = 1.0
# Low-pass (filter all twhat is higher than h_freq)  [Hz]
h_freq = None#120.0
# Notch frequency 50hz and its sub harmionics
notch_freq = [25, 50]#[25, 50, 100, 150]

# ----------- Epoching ----------- #

# What to do if more than one event occurred at the exact same time point
event_repeated = "drop" # "error", "drop" - drop one of them, "merge" - not  tested, dangerous
# Events to analyse around
conditions = ["T0", "T1", "T2"]#["stimulus"]
# Epochs min and max [seconds]
epochs_tmin = -0.2
epochs_tmax = 4
# How to compute baseline
baseline = (None, 0) # see more in config
# Contrasts of ERPs
contrasts = []

# ----------- Computations ----------- #

# How many subjects to process in parallel
n_jobs = 5
# Pipeline log level
log_level = "info"

# ----------- Validations ----------- # 
# Config validation
on_error = "abort"#"continue", "abort", "debug"