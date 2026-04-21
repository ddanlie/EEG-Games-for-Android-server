PRAGMA foreign_keys = ON;

-- USERS
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    bids_subject_number INTEGER,
    role TEXT, -- individual, coordinator, admin
    email TEXT UNIQUE,
    created_at TEXT,
    login_code TEXT,
    jwt_token TEXT
);

-- INDIVIDUAL INFO
CREATE TABLE individual_info (
    id TEXT PRIMARY KEY,
    user_id TEXT UNIQUE,
    name TEXT,
    surname TEXT,
    smoking_status TEXT, -- Non-Smoker, Current Smoker, Ex-Smoker
    alcohol_use TEXT,    -- None, Moderate, Heavy
    age_years INTEGER,
    sex TEXT,            -- Male, Female
    weight_kg REAL,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- SESSION-SPECIFIC INDIVIDUAL INFO
CREATE TABLE individual_info_session (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    session_id TEXT UNIQUE,
    last_meal TEXT,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- SESSIONS
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    bids_session_number INTEGER,
    created_at TEXT,
    description TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- GAMES
CREATE TABLE games (
    id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    attention_domain TEXT,
    attention_subdomain TEXT,
    other_info_json TEXT
);

-- RUNS
CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    game_id TEXT,
    session_id TEXT,
    bids_run_number INTEGER,
    created_at TEXT,
    eeg_datafile_path TEXT,
    eeg_rest_datafile_path TEXT,
    is_vaild INTEGER,
    notes TEXT,
    FOREIGN KEY (game_id) REFERENCES games(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- OBSERVATIONS
CREATE TABLE observation (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    biomarkers_json_data TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);