# Heart Disease in the U.S. Adult Population

An end-to-end analysis of **253,680 respondents** from the CDC Behavioral Risk Factor Surveillance System (BRFSS), 2015.

**[→ Open the interactive dashboard](https://victoria-chika-nwachukwu.github.io/heart-disease-analysis/dashboard.html)**

---

## What this project shows

**Baseline prevalence: 9.42%** — 23,893 respondents reported coronary heart disease or a heart attack.

Three findings:

**1. Risk compounds, it doesn't add.**
People carrying all six modifiable risk factors have **42.0%** prevalence, against **1.2%** for those with none — a 36× spread.

**2. Poverty behaves like a cardiac risk factor.**
Prevalence is **3.1× higher** in the lowest income bracket than the highest (15.8% vs 5.1%), falling almost monotonically across all eight bands.

**3. Insurance is not the same as access.**
Respondents who *have* coverage but skipped a doctor over cost show the **highest prevalence of any access group — 13.2%**, above both the uninsured (7.0%) and those reporting no barrier (9.3%).

That third result looks backwards, so I tested it. Age was the obvious confounder — the uninsured are the youngest group. Re-running the comparison **within each age bracket**, the cost-deterred group still leads in **all 13 brackets**, and they are younger on average than the no-barrier group. The crude figure was understating the gap, not inflating it.

![Access paradox](charts/06_access_paradox.png)

---

## Two decisions worth explaining

**Duplicate rows were kept, not dropped.**
The raw file contains 23,899 exact duplicate rows. Most published analyses delete them. With 22 mostly-binary columns describing a quarter-million people, identical rows are statistically expected — two different respondents can easily produce the same answers. There is no respondent ID to prove otherwise, so deleting them would remove real people and bias every rate. They were retained and flagged in `is_duplicate_profile`. Dropping them would shift the headline rate by 0.9pp; the reasoning is documented in [`reports/data_quality_report.md`](reports/data_quality_report.md).

**Relative risk was used instead of correlation.**
Correlation coefficients compress badly on binary survey data. Relative risk answers the question that actually matters: how many times more likely is someone with this factor to have heart disease? It also reorders the story — obesity ranks second-to-last at 1.39×, while high blood pressure reaches 4.00× and affects 43% of the population.

---

## Repository structure

```
├── dashboard.html          Interactive dashboard (self-contained, no install)
├── findings_report.md      Full written analysis
├── charts/                 Six figures
├── scripts/
│   ├── clean_brfss.py      Stage 1 — cleaning and codebook decoding
│   └── analysis_brfss.py   Stage 2 — KPIs and visualization
├── reports/
│   ├── data_quality_report.md
│   └── kpi_summary.csv     21 headline metrics
└── data/                   Raw BRFSS 2015 file
```

---

## Method

**Cleaning** — the raw file is fully numeric-encoded, so every column was decoded against the BRFSS codebook (`Income = 6` → `$35,000–$49,999`). The `Sex` encoding was verified empirically before trusting the codebook. All 22 columns were range-checked; four features were derived, including a 0–6 risk factor count and a three-level healthcare access measure.

**Analysis** — 21 KPIs covering relative risk, dose-response, socioeconomic gradient, and age-stratified access comparison.

**Dashboard** — 253,680 rows pre-aggregated into a 13,200-cell cube embedded in a single HTML file. Cross-filtering excludes each chart's own dimension, so filtering by age still shows the full age distribution. Cohorts under 100 respondents are suppressed.

## Tools

Python (pandas, numpy, matplotlib) · SQL · HTML/JavaScript

## Limitations

- Self-reported data; undiagnosed cases cannot appear, so prevalence is likely underestimated
- Cross-sectional single year — **no causal claims**
- BRFSS survey weights not applied; figures are sample prevalence, not weighted national estimates
- 9.4% positive class — accuracy would be a misleading metric for any predictive modelling

## Source

CDC Behavioral Risk Factor Surveillance System, 2015. Public domain.
