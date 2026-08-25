"""
================================================================================
BRFSS 2015 — Heart Disease Health Indicators
Stage 1: Data Cleaning & Preparation
================================================================================

Source : CDC Behavioral Risk Factor Surveillance System (BRFSS), 2015
Input  : heart_disease_health_indicators_BRFSS2015.csv  (253,680 rows x 22 cols)
Output : brfss_heart_clean.csv  — analysis-ready, human-readable labels
         data_quality_report.md — before/after audit trail

The raw file arrives fully numeric-encoded. Every value is a code that means
nothing without the BRFSS codebook (e.g. Income = 6 means "$35,000-$49,999").
Decoding these is the core work of this stage: it makes every downstream chart
and SQL query self-explanatory instead of requiring a lookup table.

Author: [Your Name]
================================================================================
"""

import pandas as pd
import numpy as np
from pathlib import Path

RAW_PATH = "/home/claude/peek3/heart_disease_health_indicators_BRFSS2015.csv"
OUT_DIR = Path("/mnt/user-data/outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

audit = []          # collects findings for the data quality report


def log(msg):
    print(msg)
    audit.append(msg)


# ==============================================================================
# 1. LOAD & PROFILE
# ==============================================================================
log("## 1. Load & profile\n")

df = pd.read_csv(RAW_PATH)
raw_shape = df.shape

log(f"- Rows loaded: **{raw_shape[0]:,}**")
log(f"- Columns: **{raw_shape[1]}**")
log(f"- Missing values: **{df.isna().sum().sum()}** (none — BRFSS pre-processes non-responses)")
log(f"- Memory: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB\n")

# Every column loaded as float64 despite most being 0/1 flags — wasteful and
# misleading. Confirm which are genuinely binary before downcasting.
binary_cols = [c for c in df.columns if set(df[c].dropna().unique()) <= {0.0, 1.0}]
log(f"- Genuinely binary columns: **{len(binary_cols)}** of {raw_shape[1]}\n")


# ==============================================================================
# 2. RANGE VALIDATION
# ==============================================================================
log("## 2. Range validation\n")
log("Each column is checked against its documented BRFSS codebook range. "
    "A value outside these bounds would indicate corruption during export.\n")

EXPECTED_RANGES = {
    "HeartDiseaseorAttack": (0, 1), "HighBP": (0, 1), "HighChol": (0, 1),
    "CholCheck": (0, 1), "BMI": (12, 98), "Smoker": (0, 1), "Stroke": (0, 1),
    "Diabetes": (0, 2), "PhysActivity": (0, 1), "Fruits": (0, 1),
    "Veggies": (0, 1), "HvyAlcoholConsump": (0, 1), "AnyHealthcare": (0, 1),
    "NoDocbcCost": (0, 1), "GenHlth": (1, 5), "MentHlth": (0, 30),
    "PhysHlth": (0, 30), "DiffWalk": (0, 1), "Sex": (0, 1),
    "Age": (1, 13), "Education": (1, 6), "Income": (1, 8),
}

violations = 0
for col, (lo, hi) in EXPECTED_RANGES.items():
    bad = ((df[col] < lo) | (df[col] > hi)).sum()
    if bad:
        log(f"- ⚠️ `{col}`: {bad:,} values outside [{lo}, {hi}]")
        violations += bad

if violations == 0:
    log("- ✅ All 22 columns fall within documented codebook ranges. "
        "No out-of-range corruption.\n")

# BMI deserves a second look: 98 is the codebook ceiling, not a data error,
# but values that extreme are clinically rare and worth flagging, not deleting.
extreme_bmi = (df["BMI"] > 60).sum()
log(f"- BMI above 60 (clinically extreme but plausible): **{extreme_bmi:,}** "
    f"({extreme_bmi/len(df):.2%}). Retained — these are real respondents, "
    "and removing them would bias the obesity–heart disease relationship.\n")


# ==============================================================================
# 3. THE DUPLICATE QUESTION  ← the key analytical decision in this project
# ==============================================================================
log("## 3. Duplicate rows — investigated, not deleted\n")

n_dupes = df.duplicated().sum()
log(f"Exact duplicate rows found: **{n_dupes:,}** ({n_dupes/len(df):.1%} of the file).\n")

log("Most published analyses of this dataset drop these immediately. "
    "That is very likely a mistake, and here is the reasoning.\n")

# 20 of 22 columns are binary or low-cardinality. Estimate how many distinct
# respondent "profiles" the schema can even express.
distinct_profiles = 1
for col in df.columns:
    distinct_profiles *= df[col].nunique()

unique_rows = len(df.drop_duplicates())
log(f"- The 22 columns describe a person using mostly yes/no flags. "
    f"Only `BMI`, `MentHlth` and `PhysHlth` are high-cardinality.")
log(f"- Distinct profiles actually observed: **{unique_rows:,}**")
log(f"- Respondents: **{len(df):,}**\n")

log("With a quarter of a million people compressed into a coarse, mostly-binary "
    "feature space, two different people producing an identical row is not just "
    "possible — it is expected. A 55-year-old non-smoker with high blood "
    "pressure, a BMI of 27 and no reported unhealthy days is a common human "
    "being, not a copy-paste error.\n")

log("**Decision: retain all rows.** BRFSS is a survey of distinct respondents; "
    "each row is a person, and there is no respondent ID that would let us prove "
    "otherwise. Deleting 23,899 people would silently shrink the population and "
    "bias every prevalence rate we report. Instead we flag them so the choice is "
    "auditable and reversible.\n")

df["is_duplicate_profile"] = df.duplicated(keep=False)

# Quantify the impact of the alternative choice, so the decision is defensible.
rate_kept = df["HeartDiseaseorAttack"].mean()
rate_dropped = df.drop_duplicates(subset=df.columns[:22])["HeartDiseaseorAttack"].mean()
log(f"- Heart disease rate, all rows retained: **{rate_kept:.2%}**")
log(f"- Heart disease rate, if duplicates dropped: **{rate_dropped:.2%}**")
log(f"- Absolute difference: **{abs(rate_kept - rate_dropped)*100:.2f} percentage points** "
    "— material enough that the choice must be stated, not assumed.\n")


# ==============================================================================
# 4. CODEBOOK DECODING
# ==============================================================================
log("## 4. Codebook decoding\n")
log("Numeric codes are mapped to their BRFSS 2015 meanings. This is what turns "
    "`Income = 6` into `$35,000-$49,999` and makes every downstream chart "
    "readable without a lookup sheet.\n")

clean = df.copy()

YES_NO = {0.0: "No", 1.0: "Yes"}

binary_map = {
    "HeartDiseaseorAttack": YES_NO, "HighBP": YES_NO, "HighChol": YES_NO,
    "CholCheck": YES_NO, "Smoker": YES_NO, "Stroke": YES_NO,
    "PhysActivity": YES_NO, "Fruits": YES_NO, "Veggies": YES_NO,
    "HvyAlcoholConsump": YES_NO, "AnyHealthcare": YES_NO,
    "NoDocbcCost": YES_NO, "DiffWalk": YES_NO,
}

AGE_BRACKETS = {
    1: "18-24", 2: "25-29", 3: "30-34", 4: "35-39", 5: "40-44", 6: "45-49",
    7: "50-54", 8: "55-59", 9: "60-64", 10: "65-69", 11: "70-74",
    12: "75-79", 13: "80+",
}
# Bracket midpoints let us compute correlations and trend lines that a text
# label cannot support.
AGE_MIDPOINTS = {
    1: 21, 2: 27, 3: 32, 4: 37, 5: 42, 6: 47, 7: 52, 8: 57,
    9: 62, 10: 67, 11: 72, 12: 77, 13: 85,
}

EDUCATION = {
    1: "Never attended / Kindergarten only",
    2: "Elementary (Grades 1-8)",
    3: "Some high school (Grades 9-11)",
    4: "High school graduate / GED",
    5: "Some college / Technical school",
    6: "College graduate (4+ years)",
}

INCOME = {
    1: "Under $10,000", 2: "$10,000-$14,999", 3: "$15,000-$19,999",
    4: "$20,000-$24,999", 5: "$25,000-$34,999", 6: "$35,000-$49,999",
    7: "$50,000-$74,999", 8: "$75,000 or more",
}

GEN_HEALTH = {1: "Excellent", 2: "Very good", 3: "Good", 4: "Fair", 5: "Poor"}

DIABETES = {0: "No diabetes", 1: "Prediabetes / Gestational", 2: "Diabetes"}

# Sex encoding verified empirically before trusting the codebook:
# code 0 = 141,974 respondents at 7.2% heart disease; code 1 = 111,706 at 12.3%.
# Higher male prevalence and female over-representation both match known BRFSS
# patterns, confirming 0 = Female, 1 = Male.
SEX = {0.0: "Female", 1.0: "Male"}

for col, mapping in binary_map.items():
    clean[col] = clean[col].map(mapping)

clean["Sex"] = clean["Sex"].map(SEX)
clean["Diabetes"] = clean["Diabetes"].map(DIABETES)
clean["GenHlth"] = clean["GenHlth"].map(GEN_HEALTH)
clean["age_midpoint"] = clean["Age"].map(AGE_MIDPOINTS)
clean["Age"] = clean["Age"].map(AGE_BRACKETS)
clean["Education"] = clean["Education"].map(EDUCATION)
clean["Income"] = clean["Income"].map(INCOME)

log(f"- Decoded **{len(binary_map) + 6}** columns from numeric codes to labels")
log("- Added `age_midpoint` so age can be used numerically in correlations\n")


# ==============================================================================
# 5. DERIVED FEATURES
# ==============================================================================
log("## 5. Derived features\n")

# Standard WHO BMI classification
clean["bmi_category"] = pd.cut(
    clean["BMI"],
    bins=[0, 18.5, 25, 30, 35, 40, 200],
    labels=["Underweight", "Healthy weight", "Overweight",
            "Obese Class I", "Obese Class II", "Obese Class III"],
    right=False,
)

# Total days of poor health in the last 30 — combines the two survey items
clean["total_unhealthy_days"] = clean["MentHlth"] + clean["PhysHlth"]

# Count of modifiable cardiovascular risk factors present
risk_flags = ["HighBP", "HighChol", "Smoker", "DiffWalk"]
clean["risk_factor_count"] = (
    sum((clean[c] == "Yes").astype(int) for c in risk_flags)
    + (clean["Diabetes"] == "Diabetes").astype(int)
    + (clean["PhysActivity"] == "No").astype(int)
)

# Healthcare access barrier: insured status combined with cost-avoidance
clean["access_barrier"] = np.select(
    [
        (clean["AnyHealthcare"] == "No"),
        (clean["AnyHealthcare"] == "Yes") & (clean["NoDocbcCost"] == "Yes"),
    ],
    ["No coverage", "Insured but cost-deterred"],
    default="No barrier reported",
)

log("- `bmi_category` — WHO standard classification (6 bands)")
log("- `total_unhealthy_days` — MentHlth + PhysHlth, range 0-60")
log("- `risk_factor_count` — 0-6 modifiable cardiovascular risk factors")
log("- `access_barrier` — distinguishes uninsured from insured-but-cost-deterred\n")


# ==============================================================================
# 6. RENAME TO ANALYSIS-FRIENDLY COLUMN NAMES
# ==============================================================================
clean = clean.rename(columns={
    "HeartDiseaseorAttack": "heart_disease",
    "HighBP": "high_bp",
    "HighChol": "high_cholesterol",
    "CholCheck": "cholesterol_checked_5yr",
    "BMI": "bmi",
    "Smoker": "smoker",
    "Stroke": "stroke_history",
    "Diabetes": "diabetes_status",
    "PhysActivity": "physical_activity",
    "Fruits": "eats_fruit_daily",
    "Veggies": "eats_veg_daily",
    "HvyAlcoholConsump": "heavy_drinker",
    "AnyHealthcare": "has_healthcare_coverage",
    "NoDocbcCost": "skipped_doctor_due_to_cost",
    "GenHlth": "general_health",
    "MentHlth": "poor_mental_health_days",
    "PhysHlth": "poor_physical_health_days",
    "DiffWalk": "difficulty_walking",
    "Sex": "sex",
    "Age": "age_bracket",
    "Education": "education_level",
    "Income": "income_bracket",
})

clean.insert(0, "respondent_id", range(1, len(clean) + 1))


# ==============================================================================
# 7. FINAL VALIDATION & EXPORT
# ==============================================================================
log("## 6. Final validation\n")

assert len(clean) == raw_shape[0], "Row count changed unexpectedly"
assert clean["heart_disease"].isna().sum() == 0, "Target has nulls"
assert clean["respondent_id"].is_unique, "respondent_id not unique"

log(f"- ✅ Row count preserved: **{len(clean):,}** (no respondents lost)")
log(f"- ✅ Target variable complete: 0 nulls")
log(f"- ✅ Columns: {raw_shape[1]} → **{clean.shape[1]}** "
    f"(+{clean.shape[1]-raw_shape[1]} derived)")

remaining_nulls = clean.isna().sum().sum()
log(f"- ✅ Remaining nulls: **{remaining_nulls}**\n")

out_csv = OUT_DIR / "brfss_heart_clean.csv"
clean.to_csv(out_csv, index=False)
log(f"Clean dataset written: `{out_csv.name}` "
    f"({out_csv.stat().st_size / 1024**2:.1f} MB)\n")

# ------------------------------------------------------------------ report ---
report = [
    "# Data Quality Report — BRFSS 2015 Heart Disease Indicators\n",
    "**Source:** CDC Behavioral Risk Factor Surveillance System, 2015  ",
    f"**Raw:** {raw_shape[0]:,} rows x {raw_shape[1]} columns  ",
    f"**Clean:** {clean.shape[0]:,} rows x {clean.shape[1]} columns  ",
    "**Rows removed:** 0 — see Section 3 for the reasoning\n",
    "---\n",
] + audit

(OUT_DIR / "data_quality_report.md").write_text("\n".join(report))

print("\n" + "=" * 70)
print("CLEANING COMPLETE")
print("=" * 70)
print(clean[["age_bracket", "sex", "income_bracket", "general_health",
             "risk_factor_count", "heart_disease"]].head(5).to_string(index=False))
