-- ============================================================================
-- BRFSS 2015 Heart Disease Analysis
-- 01 - Schema
-- ============================================================================
-- Loads the cleaned output of scripts/clean_brfss.py into a relational table.
--
-- Tested on SQLite 3.45. Runs on PostgreSQL with two changes, noted inline.
--
-- Load (SQLite):
--   sqlite3 brfss.db
--   .mode csv
--   .import --skip 1 data/brfss_heart_clean.csv respondents
--
-- Load (PostgreSQL):
--   \copy respondents FROM 'data/brfss_heart_clean.csv' CSV HEADER
--
-- Author: Victoria Nwachukwu
-- ============================================================================

DROP TABLE IF EXISTS respondents;

CREATE TABLE respondents (
    respondent_id               INTEGER PRIMARY KEY,

    -- outcome
    heart_disease               TEXT    NOT NULL,   -- 'Yes' / 'No'

    -- diagnosed conditions
    high_bp                     TEXT,
    high_cholesterol            TEXT,
    cholesterol_checked_5yr     TEXT,
    stroke_history              TEXT,
    diabetes_status             TEXT,               -- 3 levels

    -- behaviour and measurement
    bmi                         REAL,
    smoker                      TEXT,
    physical_activity           TEXT,
    eats_fruit_daily            TEXT,
    eats_veg_daily              TEXT,
    heavy_drinker               TEXT,

    -- healthcare access
    has_healthcare_coverage     TEXT,
    skipped_doctor_due_to_cost  TEXT,

    -- self-reported health
    general_health              TEXT,               -- Excellent .. Poor
    poor_mental_health_days     INTEGER,            -- 0-30
    poor_physical_health_days   INTEGER,            -- 0-30
    difficulty_walking          TEXT,

    -- demographics
    sex                         TEXT,
    age_bracket                 TEXT,
    education_level             TEXT,
    income_bracket              TEXT,

    -- derived in cleaning
    is_duplicate_profile        TEXT,
    age_midpoint                INTEGER,
    bmi_category                TEXT,
    total_unhealthy_days        INTEGER,
    risk_factor_count           INTEGER,            -- 0-6
    access_barrier              TEXT                -- 3 levels
);

-- Indexes on the columns every query below groups or filters by.
CREATE INDEX idx_outcome   ON respondents (heart_disease);
CREATE INDEX idx_age       ON respondents (age_bracket);
CREATE INDEX idx_income    ON respondents (income_bracket);
CREATE INDEX idx_access    ON respondents (access_barrier);
CREATE INDEX idx_riskcount ON respondents (risk_factor_count);

-- ----------------------------------------------------------------------------
-- Ordering lookup.
-- age_bracket, income_bracket and general_health are text, so they sort
-- alphabetically by default, which is wrong: '$10,000-$14,999' would sort
-- before 'Under $10,000', and 'Excellent' before 'Fair'. This table gives
-- every ordered category an explicit position.
-- ----------------------------------------------------------------------------

DROP TABLE IF EXISTS category_order;

CREATE TABLE category_order (
    dimension   TEXT NOT NULL,
    label       TEXT NOT NULL,
    sort_order  INTEGER NOT NULL,
    PRIMARY KEY (dimension, label)
);

INSERT INTO category_order (dimension, label, sort_order) VALUES
    ('age_bracket', '18-24',  1), ('age_bracket', '25-29',  2),
    ('age_bracket', '30-34',  3), ('age_bracket', '35-39',  4),
    ('age_bracket', '40-44',  5), ('age_bracket', '45-49',  6),
    ('age_bracket', '50-54',  7), ('age_bracket', '55-59',  8),
    ('age_bracket', '60-64',  9), ('age_bracket', '65-69', 10),
    ('age_bracket', '70-74', 11), ('age_bracket', '75-79', 12),
    ('age_bracket', '80+',   13),

    ('income_bracket', 'Under $10,000',    1),
    ('income_bracket', '$10,000-$14,999',  2),
    ('income_bracket', '$15,000-$19,999',  3),
    ('income_bracket', '$20,000-$24,999',  4),
    ('income_bracket', '$25,000-$34,999',  5),
    ('income_bracket', '$35,000-$49,999',  6),
    ('income_bracket', '$50,000-$74,999',  7),
    ('income_bracket', '$75,000 or more',  8),

    ('general_health', 'Excellent', 1), ('general_health', 'Very good', 2),
    ('general_health', 'Good',      3), ('general_health', 'Fair',      4),
    ('general_health', 'Poor',      5);
