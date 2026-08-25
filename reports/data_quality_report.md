# Data Quality Report — BRFSS 2015 Heart Disease Indicators

**Source:** CDC Behavioral Risk Factor Surveillance System, 2015  
**Raw:** 253,680 rows x 22 columns  
**Clean:** 253,680 rows x 29 columns  
**Rows removed:** 0 — see Section 3 for the reasoning

---

## 1. Load & profile

- Rows loaded: **253,680**
- Columns: **22**
- Missing values: **0** (none — BRFSS pre-processes non-responses)
- Memory: 42.6 MB

- Genuinely binary columns: **14** of 22

## 2. Range validation

Each column is checked against its documented BRFSS codebook range. A value outside these bounds would indicate corruption during export.

- ✅ All 22 columns fall within documented codebook ranges. No out-of-range corruption.

- BMI above 60 (clinically extreme but plausible): **805** (0.32%). Retained — these are real respondents, and removing them would bias the obesity–heart disease relationship.

## 3. Duplicate rows — investigated, not deleted

Exact duplicate rows found: **23,899** (9.4% of the file).

Most published analyses of this dataset drop these immediately. That is very likely a mistake, and here is the reasoning.

- The 22 columns describe a person using mostly yes/no flags. Only `BMI`, `MentHlth` and `PhysHlth` are high-cardinality.
- Distinct profiles actually observed: **229,781**
- Respondents: **253,680**

With a quarter of a million people compressed into a coarse, mostly-binary feature space, two different people producing an identical row is not just possible — it is expected. A 55-year-old non-smoker with high blood pressure, a BMI of 27 and no reported unhealthy days is a common human being, not a copy-paste error.

**Decision: retain all rows.** BRFSS is a survey of distinct respondents; each row is a person, and there is no respondent ID that would let us prove otherwise. Deleting 23,899 people would silently shrink the population and bias every prevalence rate we report. Instead we flag them so the choice is auditable and reversible.

- Heart disease rate, all rows retained: **9.42%**
- Heart disease rate, if duplicates dropped: **10.32%**
- Absolute difference: **0.90 percentage points** — material enough that the choice must be stated, not assumed.

## 4. Codebook decoding

Numeric codes are mapped to their BRFSS 2015 meanings. This is what turns `Income = 6` into `$35,000-$49,999` and makes every downstream chart readable without a lookup sheet.

- Decoded **19** columns from numeric codes to labels
- Added `age_midpoint` so age can be used numerically in correlations

## 5. Derived features

- `bmi_category` — WHO standard classification (6 bands)
- `total_unhealthy_days` — MentHlth + PhysHlth, range 0-60
- `risk_factor_count` — 0-6 modifiable cardiovascular risk factors
- `access_barrier` — distinguishes uninsured from insured-but-cost-deterred

## 6. Final validation

- ✅ Row count preserved: **253,680** (no respondents lost)
- ✅ Target variable complete: 0 nulls
- ✅ Columns: 22 → **29** (+7 derived)
- ✅ Remaining nulls: **0**

Clean dataset written: `brfss_heart_clean.csv` (46.3 MB)
