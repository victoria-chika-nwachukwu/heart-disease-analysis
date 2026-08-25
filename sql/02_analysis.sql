-- ============================================================================
-- BRFSS 2015 Heart Disease Analysis
-- 02 - Analysis queries
-- ============================================================================
-- Each query reproduces a result reported in findings_report.md. Running these
-- against the loaded database should return the same numbers as the Python
-- pipeline; that agreement is the point, since two independent routes to the
-- same figure is a real check on both.
--
-- Tested on SQLite 3.45.
-- Author: Victoria Nwachukwu
-- ============================================================================


-- ----------------------------------------------------------------------------
-- Q1. Baseline prevalence
-- Expected: 253,680 respondents, 23,893 cases, 9.42%
-- ----------------------------------------------------------------------------
SELECT
    COUNT(*)                                                   AS respondents,
    SUM(CASE WHEN heart_disease = 'Yes' THEN 1 ELSE 0 END)     AS cases,
    ROUND(100.0 * AVG(CASE WHEN heart_disease = 'Yes' THEN 1.0 ELSE 0.0 END), 2)
                                                               AS prevalence_pct
FROM respondents;


-- ----------------------------------------------------------------------------
-- Q2. Relative risk by factor
--
-- Relative risk needs two rates per factor -- with and without -- which is
-- awkward in a single GROUP BY. The approach here is to unpivot: build one row
-- per (factor, present/absent) pair with a UNION ALL, then pivot the two rates
-- back onto one row with conditional aggregation.
--
-- Expected: stroke 4.67x, high BP 4.00x, difficulty walking 3.51x,
--           obesity second-to-last at 1.39x
-- ----------------------------------------------------------------------------
WITH flagged AS (
    SELECT 'Stroke history'       AS factor, stroke_history = 'Yes'      AS has_factor, heart_disease FROM respondents
    UNION ALL
    SELECT 'High blood pressure', high_bp = 'Yes',                       heart_disease FROM respondents
    UNION ALL
    SELECT 'Difficulty walking',  difficulty_walking = 'Yes',            heart_disease FROM respondents
    UNION ALL
    SELECT 'High cholesterol',    high_cholesterol = 'Yes',              heart_disease FROM respondents
    UNION ALL
    SELECT 'Diabetes',            diabetes_status = 'Diabetes',          heart_disease FROM respondents
    UNION ALL
    SELECT 'Smoker',              smoker = 'Yes',                        heart_disease FROM respondents
    UNION ALL
    SELECT 'Physically inactive', physical_activity = 'No',              heart_disease FROM respondents
    UNION ALL
    SELECT 'Obese (BMI 30+)',     bmi >= 30,                             heart_disease FROM respondents
    UNION ALL
    SELECT 'Skipped doctor (cost)', skipped_doctor_due_to_cost = 'Yes',  heart_disease FROM respondents
),
rates AS (
    SELECT
        factor,
        has_factor,
        COUNT(*)                                                          AS n,
        AVG(CASE WHEN heart_disease = 'Yes' THEN 1.0 ELSE 0.0 END)        AS rate
    FROM flagged
    GROUP BY factor, has_factor
),
paired AS (
    SELECT
        factor,
        MAX(CASE WHEN has_factor THEN rate END)     AS rate_with,
        MAX(CASE WHEN NOT has_factor THEN rate END) AS rate_without,
        MAX(CASE WHEN has_factor THEN n END)        AS n_with,
        SUM(n)                                      AS n_total
    FROM rates
    GROUP BY factor
)
SELECT
    factor,
    ROUND(100.0 * rate_with,    1) AS prevalence_with_pct,
    ROUND(100.0 * rate_without, 1) AS prevalence_without_pct,
    ROUND(rate_with / rate_without, 2) AS relative_risk,
    ROUND(100.0 * n_with / n_total, 0) AS population_share_pct
FROM paired
ORDER BY relative_risk DESC;


-- ----------------------------------------------------------------------------
-- Q3. Dose-response curve, with the step change between levels
--
-- LAG() gives each row access to the previous risk level's rate, so the
-- marginal effect of adding one more factor can be read directly instead of
-- being eyeballed off a chart.
--
-- Expected: 1.2% at 0 factors rising to 42.0% at 6
-- ----------------------------------------------------------------------------
WITH by_count AS (
    SELECT
        risk_factor_count,
        COUNT(*)                                                    AS n,
        AVG(CASE WHEN heart_disease = 'Yes' THEN 1.0 ELSE 0.0 END)  AS rate
    FROM respondents
    GROUP BY risk_factor_count
)
SELECT
    risk_factor_count,
    n,
    ROUND(100.0 * rate, 1)                                          AS prevalence_pct,
    ROUND(100.0 * (rate - LAG(rate) OVER (ORDER BY risk_factor_count)), 1)
                                                                    AS pp_added,
    ROUND(rate / LAG(rate) OVER (ORDER BY risk_factor_count), 2)    AS multiple_of_previous,
    ROUND(rate / FIRST_VALUE(rate) OVER (ORDER BY risk_factor_count), 1)
                                                                    AS multiple_of_zero
FROM by_count
ORDER BY risk_factor_count;


-- ----------------------------------------------------------------------------
-- Q4. Income gradient, ranked and compared to the population baseline
--
-- The cross join to a single-row CTE puts the overall rate on every row, so
-- each bracket can be expressed as a ratio to the population average.
--
-- Expected: 15.8% lowest vs 5.1% highest. Note the one break in the pattern:
--           $10-15k (18.6%) is higher than Under $10k (15.8%).
-- ----------------------------------------------------------------------------
WITH baseline AS (
    SELECT AVG(CASE WHEN heart_disease = 'Yes' THEN 1.0 ELSE 0.0 END) AS overall_rate
    FROM respondents
),
by_income AS (
    SELECT
        r.income_bracket,
        c.sort_order,
        COUNT(*)                                                      AS n,
        AVG(CASE WHEN r.heart_disease = 'Yes' THEN 1.0 ELSE 0.0 END)  AS rate
    FROM respondents r
    JOIN category_order c
      ON c.dimension = 'income_bracket'
     AND c.label     = r.income_bracket
    GROUP BY r.income_bracket, c.sort_order
)
SELECT
    b.income_bracket,
    b.n,
    ROUND(100.0 * b.rate, 1)                    AS prevalence_pct,
    ROUND(b.rate / base.overall_rate, 2)        AS vs_baseline,
    RANK() OVER (ORDER BY b.rate DESC)          AS risk_rank
FROM by_income b
CROSS JOIN baseline base
ORDER BY b.sort_order;


-- ----------------------------------------------------------------------------
-- Q5. The access paradox -- crude rates
--
-- Taken alone this table is misleading, which is the reason Q6 exists.
-- Expected: cost-deterred 13.2%, no barrier 9.3%, no coverage 7.0%
-- ----------------------------------------------------------------------------
SELECT
    access_barrier,
    COUNT(*)                                                     AS n,
    ROUND(100.0 * AVG(CASE WHEN heart_disease = 'Yes' THEN 1.0 ELSE 0.0 END), 1)
                                                                 AS prevalence_pct,
    ROUND(AVG(age_midpoint), 1)                                  AS mean_age
FROM respondents
GROUP BY access_barrier
ORDER BY prevalence_pct DESC;


-- ----------------------------------------------------------------------------
-- Q6. The access paradox -- stratified by age
--
-- The uninsured group is the youngest, and age dominates cardiac risk, so the
-- crude comparison in Q5 confounds the two. This holds age constant by
-- comparing within each bracket.
--
-- Expected: the cost-deterred group is higher than 'no barrier' in all 13
--           brackets, so the gap is not an age artefact.
-- ----------------------------------------------------------------------------
WITH stratified AS (
    SELECT
        r.age_bracket,
        c.sort_order,
        r.access_barrier,
        COUNT(*)                                                      AS n,
        AVG(CASE WHEN r.heart_disease = 'Yes' THEN 1.0 ELSE 0.0 END)  AS rate
    FROM respondents r
    JOIN category_order c
      ON c.dimension = 'age_bracket'
     AND c.label     = r.age_bracket
    GROUP BY r.age_bracket, c.sort_order, r.access_barrier
    HAVING COUNT(*) >= 100          -- suppress groups too small to be a rate
),
pivoted AS (
    SELECT
        age_bracket,
        sort_order,
        MAX(CASE WHEN access_barrier = 'Insured but cost-deterred' THEN rate END) AS cost_deterred,
        MAX(CASE WHEN access_barrier = 'No barrier reported'       THEN rate END) AS no_barrier,
        MAX(CASE WHEN access_barrier = 'No coverage'               THEN rate END) AS no_coverage
    FROM stratified
    GROUP BY age_bracket, sort_order
)
SELECT
    age_bracket,
    ROUND(100.0 * cost_deterred, 1)                 AS cost_deterred_pct,
    ROUND(100.0 * no_barrier,    1)                 AS no_barrier_pct,
    ROUND(100.0 * no_coverage,   1)                 AS no_coverage_pct,
    ROUND(cost_deterred / no_barrier, 2)            AS cost_deterred_vs_no_barrier,
    CASE WHEN cost_deterred > no_barrier THEN 'yes' ELSE 'no' END
                                                    AS cost_deterred_higher
FROM pivoted
ORDER BY sort_order;


-- ----------------------------------------------------------------------------
-- Q7. Where the cases actually are
--
-- Prevalence answers "how likely", not "how many". A group can carry high risk
-- and still be a small share of total cases. The running total shows how few
-- segments account for most of the burden.
-- ----------------------------------------------------------------------------
WITH by_segment AS (
    SELECT
        age_bracket,
        sex,
        COUNT(*)                                                   AS n,
        SUM(CASE WHEN heart_disease = 'Yes' THEN 1 ELSE 0 END)     AS cases
    FROM respondents
    GROUP BY age_bracket, sex
)
SELECT
    age_bracket,
    sex,
    n,
    cases,
    ROUND(100.0 * cases / n, 1)                                    AS prevalence_pct,
    ROUND(100.0 * cases / SUM(cases) OVER (), 1)                   AS pct_of_all_cases,
    ROUND(100.0 * SUM(cases) OVER (ORDER BY cases DESC
                                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
          / SUM(cases) OVER (), 1)                                 AS running_pct_of_cases
FROM by_segment
ORDER BY cases DESC
LIMIT 10;


-- ----------------------------------------------------------------------------
-- Q8. Data quality check -- the duplicate decision, quantified
--
-- Documents in SQL what data_quality_report.md argues in prose: how much the
-- headline figure moves if the duplicate rows are dropped.
--
-- A subtlety worth being careful about. The is_duplicate_profile flag marks
-- every row belonging to a duplicated profile, including the first occurrence,
-- so filtering it out removes 35,086 rows -- more than the 23,899 redundant
-- copies. To measure the real effect of deduplication, one row per distinct
-- profile has to be kept, which is what ROW_NUMBER does here.
--
-- Expected: 253,680 rows at 9.42%, versus 229,781 rows at 10.32% deduplicated
--           -- a shift of 0.9 percentage points.
-- ----------------------------------------------------------------------------
WITH deduped AS (
    SELECT
        heart_disease,
        ROW_NUMBER() OVER (
            PARTITION BY
                heart_disease, high_bp, high_cholesterol, cholesterol_checked_5yr,
                bmi, smoker, stroke_history, diabetes_status, physical_activity,
                eats_fruit_daily, eats_veg_daily, heavy_drinker,
                has_healthcare_coverage, skipped_doctor_due_to_cost,
                general_health, poor_mental_health_days, poor_physical_health_days,
                difficulty_walking, sex, age_bracket, education_level, income_bracket
            ORDER BY respondent_id
        ) AS occurrence
    FROM respondents
)
SELECT
    'All rows retained' AS treatment,
    COUNT(*)            AS respondents,
    ROUND(100.0 * AVG(CASE WHEN heart_disease = 'Yes' THEN 1.0 ELSE 0.0 END), 2) AS prevalence_pct
FROM respondents

UNION ALL

SELECT
    'One row per distinct profile',
    COUNT(*),
    ROUND(100.0 * AVG(CASE WHEN heart_disease = 'Yes' THEN 1.0 ELSE 0.0 END), 2)
FROM deduped
WHERE occurrence = 1;
