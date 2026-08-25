"""
================================================================================
BRFSS 2015 — Heart Disease Health Indicators
Stage 2: KPI Calculation & Visualization
================================================================================

Input  : brfss_heart_clean.csv  (253,680 rows x 29 cols)
Outputs: kpi_summary.csv        — headline metrics table
         charts/*.png           — six figures
         findings_report.md     — the written analysis

Analytical spine of this project:
  1. Establish the baseline prevalence.
  2. Rank modifiable risk factors by relative risk, not raw correlation.
  3. Show the dose-response curve — the single most persuasive chart.
  4. Examine the socioeconomic gradient.
  5. Interrogate the healthcare-access finding, including the confounder test
     that most analyses of this dataset skip.

Author: [Your Name]
================================================================================
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from pathlib import Path

# ------------------------------------------------------------------ setup ---
DATA = "/mnt/user-data/outputs/brfss_heart_clean.csv"
OUT = Path("/mnt/user-data/outputs")
CHARTS = OUT / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

INK = "#1d2b36"
MUTED = "#8595a3"
ACCENT = "#c1502e"
BASE = "#3d6b7d"
LIGHT = "#cfdbe2"
GRID = "#e6ecf0"

plt.rcParams.update({
    "figure.dpi": 130,
    "savefig.dpi": 130,
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "text.color": INK,
    "axes.labelcolor": INK,
    "axes.edgecolor": GRID,
    "axes.linewidth": 1.0,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

df = pd.read_csv(DATA)
HD = df["heart_disease"].eq("Yes")
BASELINE = HD.mean()

kpis = []


def add_kpi(metric, value, unit, note):
    kpis.append({"metric": metric, "value": value, "unit": unit, "note": note})


def rate(mask):
    return df.loc[mask, "heart_disease"].eq("Yes").mean()


def style(ax, title, subtitle=None, xlab=None, ylab=None):
    ax.set_title(title, fontsize=13, fontweight="bold", loc="left",
                 pad=30 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.028, subtitle, transform=ax.transAxes,
                fontsize=9.5, color=MUTED, va="bottom")
    if xlab:
        ax.set_xlabel(xlab, fontsize=10, labelpad=8)
    if ylab:
        ax.set_ylabel(ylab, fontsize=10, labelpad=8)
    ax.grid(axis="y", color=GRID, linewidth=0.9)
    ax.set_axisbelow(True)


print("=" * 72)
print(f"BASELINE PREVALENCE: {BASELINE:.2%}  ({HD.sum():,} of {len(df):,} respondents)")
print("=" * 72)

add_kpi("Overall heart disease prevalence", round(BASELINE * 100, 2), "%",
        "Respondents reporting coronary heart disease or myocardial infarction")
add_kpi("Total respondents", len(df), "count", "BRFSS 2015 survey")
add_kpi("Cases identified", int(HD.sum()), "count", "")


# ==============================================================================
# KPI 1 — RELATIVE RISK OF EACH MODIFIABLE FACTOR
# ==============================================================================
# Relative risk answers the question a clinician actually asks: how many times
# more likely is a person WITH this factor to have heart disease? Raw
# correlation on binary data understates this badly.

factors = {
    "Difficulty walking": df["difficulty_walking"].eq("Yes"),
    "Stroke history": df["stroke_history"].eq("Yes"),
    "Diabetes": df["diabetes_status"].eq("Diabetes"),
    "High blood pressure": df["high_bp"].eq("Yes"),
    "High cholesterol": df["high_cholesterol"].eq("Yes"),
    "Physically inactive": df["physical_activity"].eq("No"),
    "Smoker": df["smoker"].eq("Yes"),
    "Obese (BMI 30+)": df["bmi"].ge(30),
    "Skipped doctor (cost)": df["skipped_doctor_due_to_cost"].eq("Yes"),
}

rr = []
for name, mask in factors.items():
    with_f, without_f = rate(mask), rate(~mask)
    rr.append({
        "factor": name,
        "prevalence_with": with_f,
        "prevalence_without": without_f,
        "relative_risk": with_f / without_f,
        "population_share": mask.mean(),
    })

rr_df = pd.DataFrame(rr).sort_values("relative_risk", ascending=True)

print("\nRelative risk by factor:")
for _, r in rr_df.iloc[::-1].iterrows():
    print(f"  {r.factor:<24} {r.relative_risk:>5.2f}x   "
          f"({r.prevalence_with:.1%} vs {r.prevalence_without:.1%})")

for _, r in rr_df.iterrows():
    add_kpi(f"Relative risk — {r.factor}", round(r.relative_risk, 2), "x",
            f"{r.prevalence_with:.1%} with vs {r.prevalence_without:.1%} without")

fig, ax = plt.subplots(figsize=(9.5, 5.6))
colors = [ACCENT if v >= 3 else BASE for v in rr_df["relative_risk"]]
bars = ax.barh(rr_df["factor"], rr_df["relative_risk"], color=colors, height=0.68)
ax.axvline(1, color=MUTED, linewidth=1.1, linestyle="--")
ax.text(1.02, -0.85, "no elevated risk", fontsize=8.5, color=MUTED)
for bar, v, share in zip(bars, rr_df["relative_risk"], rr_df["population_share"]):
    ax.text(v + 0.06, bar.get_y() + bar.get_height() / 2,
            f"{v:.2f}×", va="center", fontsize=9.5, fontweight="bold", color=INK)
    ax.text(0.06, bar.get_y() + bar.get_height() / 2,
            f"{share:.0%} of population", va="center", fontsize=8,
            color="white" if v > 1.6 else MUTED)
style(ax, "Five conditions triple the risk or more — behaviours rank lower",
      "Relative risk — how many times more likely a person with each factor is to report heart disease",
      xlab="Relative risk (×)")
ax.set_xlim(0, rr_df["relative_risk"].max() * 1.18)
fig.tight_layout()
fig.savefig(CHARTS / "01_relative_risk_by_factor.png", bbox_inches="tight")
plt.close(fig)


# ==============================================================================
# KPI 2 — DOSE-RESPONSE CURVE
# ==============================================================================
dose = (df.groupby("risk_factor_count")["heart_disease"]
          .agg(rate=lambda s: s.eq("Yes").mean(), n="size").reset_index())

print(f"\nDose-response: {dose.iloc[0]['rate']:.1%} at 0 factors "
      f"-> {dose.iloc[-1]['rate']:.1%} at 6 factors "
      f"({dose.iloc[-1]['rate'] / dose.iloc[0]['rate']:.0f}x)")

add_kpi("Prevalence at 0 risk factors", round(dose.iloc[0]["rate"] * 100, 2), "%", "")
add_kpi("Prevalence at 6 risk factors", round(dose.iloc[-1]["rate"] * 100, 2), "%", "")
add_kpi("Dose-response gradient", round(dose.iloc[-1]["rate"] / dose.iloc[0]["rate"], 1), "x",
        "Ratio of highest to lowest risk-factor burden")

fig, ax = plt.subplots(figsize=(9.5, 5.4))
bars = ax.bar(dose["risk_factor_count"], dose["rate"],
              color=[LIGHT if i < 4 else ACCENT for i in dose["risk_factor_count"]],
              width=0.68)
for x, y, n in zip(dose["risk_factor_count"], dose["rate"], dose["n"]):
    ax.text(x, y + 0.008, f"{y:.1%}", ha="center", fontsize=10,
            fontweight="bold", color=INK)
    ax.text(x, -0.022, f"n={n:,}", ha="center", fontsize=7.5, color=MUTED)
ax.axhline(BASELINE, color=BASE, linewidth=1.2, linestyle="--")
ax.text(6.35, BASELINE, f"  population\n  average {BASELINE:.1%}",
        va="center", fontsize=8.5, color=BASE)
style(ax, "Risk compounds sharply — each additional factor raises prevalence",
      "Heart disease prevalence by number of modifiable risk factors present (0–6)",
      xlab="Number of risk factors present", ylab="Heart disease prevalence")
ax.yaxis.set_major_formatter(PercentFormatter(1.0))
ax.set_ylim(-0.03, dose["rate"].max() * 1.16)
ax.set_xlim(-0.6, 7.9)
ax.set_xticks(range(7))
fig.tight_layout()
fig.savefig(CHARTS / "02_dose_response_curve.png", bbox_inches="tight")
plt.close(fig)


# ==============================================================================
# KPI 3 — SOCIOECONOMIC GRADIENT
# ==============================================================================
INCOME_ORDER = ["Under $10,000", "$10,000-$14,999", "$15,000-$19,999",
                "$20,000-$24,999", "$25,000-$34,999", "$35,000-$49,999",
                "$50,000-$74,999", "$75,000 or more"]

inc = (df.groupby("income_bracket")["heart_disease"]
         .agg(rate=lambda s: s.eq("Yes").mean(), n="size")
         .reindex(INCOME_ORDER).reset_index())

gradient = inc["rate"].iloc[0] / inc["rate"].iloc[-1]
print(f"\nIncome gradient: {inc['rate'].iloc[0]:.1%} (lowest) vs "
      f"{inc['rate'].iloc[-1]:.1%} (highest) = {gradient:.1f}x")

add_kpi("Income gradient", round(gradient, 2), "x",
        f"{inc['rate'].iloc[0]:.1%} in lowest bracket vs {inc['rate'].iloc[-1]:.1%} in highest")

fig, ax = plt.subplots(figsize=(9.5, 5.4))
shades = plt.cm.RdYlBu(np.linspace(0.12, 0.78, len(inc)))
ax.bar(range(len(inc)), inc["rate"], color=shades, width=0.7)
for i, v in enumerate(inc["rate"]):
    ax.text(i, v + 0.004, f"{v:.1%}", ha="center", fontsize=9.5,
            fontweight="bold", color=INK)
ax.set_xticks(range(len(inc)))
ax.set_xticklabels([b.replace("$", "$").replace(" or more", "+")
                    for b in inc["income_bracket"]], rotation=32, ha="right", fontsize=8.5)
style(ax, f"Heart disease is {gradient:.1f}× more common in the lowest income bracket",
      "Prevalence by annual household income — a near-monotonic gradient across all eight bands",
      ylab="Heart disease prevalence")
ax.yaxis.set_major_formatter(PercentFormatter(1.0))
ax.set_ylim(0, inc["rate"].max() * 1.16)
fig.tight_layout()
fig.savefig(CHARTS / "03_income_gradient.png", bbox_inches="tight")
plt.close(fig)


# ==============================================================================
# KPI 4 — SELF-RATED HEALTH
# ==============================================================================
GH_ORDER = ["Excellent", "Very good", "Good", "Fair", "Poor"]
gh = (df.groupby("general_health")["heart_disease"]
        .agg(rate=lambda s: s.eq("Yes").mean(), n="size")
        .reindex(GH_ORDER).reset_index())

add_kpi("Self-rated health gradient",
        round(gh["rate"].iloc[-1] / gh["rate"].iloc[0], 1), "x",
        f"{gh['rate'].iloc[-1]:.1%} (Poor) vs {gh['rate'].iloc[0]:.1%} (Excellent)")

fig, ax = plt.subplots(figsize=(8.6, 5.0))
ax.bar(gh["general_health"], gh["rate"],
       color=[LIGHT, LIGHT, BASE, ACCENT, ACCENT], width=0.62)
for i, (v, n) in enumerate(zip(gh["rate"], gh["n"])):
    ax.text(i, v + 0.007, f"{v:.1%}", ha="center", fontsize=10,
            fontweight="bold", color=INK)
    ax.text(i, -0.018, f"n={n:,}", ha="center", fontsize=7.5, color=MUTED)
style(ax, "A single survey question separates risk by 15×",
      "Prevalence by self-rated general health — one question, stronger signal than BMI or smoking",
      ylab="Heart disease prevalence")
ax.yaxis.set_major_formatter(PercentFormatter(1.0))
ax.set_ylim(-0.025, gh["rate"].max() * 1.15)
fig.tight_layout()
fig.savefig(CHARTS / "04_self_rated_health.png", bbox_inches="tight")
plt.close(fig)


# ==============================================================================
# KPI 5 — AGE CURVE BY SEX
# ==============================================================================
AGE_ORDER = ["18-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54",
             "55-59", "60-64", "65-69", "70-74", "75-79", "80+"]

age_sex = df.pivot_table(index="age_bracket", columns="sex",
                         values="heart_disease",
                         aggfunc=lambda s: s.eq("Yes").mean()).reindex(AGE_ORDER)

add_kpi("Male vs female prevalence",
        round(rate(df["sex"].eq("Male")) / rate(df["sex"].eq("Female")), 2), "x",
        f"{rate(df['sex'].eq('Male')):.1%} male vs {rate(df['sex'].eq('Female')):.1%} female")

fig, ax = plt.subplots(figsize=(9.5, 5.2))
ax.plot(age_sex.index, age_sex["Male"], marker="o", markersize=5,
        color=ACCENT, linewidth=2.2, label="Male")
ax.plot(age_sex.index, age_sex["Female"], marker="o", markersize=5,
        color=BASE, linewidth=2.2, label="Female")
ax.fill_between(age_sex.index, age_sex["Female"], age_sex["Male"],
                color=ACCENT, alpha=0.09)
ax.text(9.3, age_sex["Male"].iloc[9] + 0.012, "Male", color=ACCENT,
        fontweight="bold", fontsize=10)
ax.text(9.3, age_sex["Female"].iloc[9] - 0.028, "Female", color=BASE,
        fontweight="bold", fontsize=10)
style(ax, "The sex gap opens at 40 and never closes",
      "Prevalence by age bracket and sex — the shaded band is excess male risk",
      xlab="Age bracket", ylab="Heart disease prevalence")
ax.yaxis.set_major_formatter(PercentFormatter(1.0))
plt.setp(ax.get_xticklabels(), rotation=32, ha="right", fontsize=8.5)
fig.tight_layout()
fig.savefig(CHARTS / "05_age_sex_curve.png", bbox_inches="tight")
plt.close(fig)


# ==============================================================================
# KPI 6 — THE ACCESS PARADOX  (the finding that differentiates this project)
# ==============================================================================
crude = df.groupby("access_barrier")["heart_disease"].apply(lambda s: s.eq("Yes").mean())
mean_age = df.groupby("access_barrier")["age_midpoint"].mean()

print("\nAccess barrier — crude rates:")
for k in crude.index:
    print(f"  {k:<28} {crude[k]:.1%}   (mean age {mean_age[k]:.1f})")

strat = df.pivot_table(index="age_bracket", columns="access_barrier",
                       values="heart_disease",
                       aggfunc=lambda s: s.eq("Yes").mean()).reindex(AGE_ORDER)

add_kpi("Prevalence — insured but cost-deterred",
        round(crude["Insured but cost-deterred"] * 100, 2), "%",
        f"mean age {mean_age['Insured but cost-deterred']:.1f}")
add_kpi("Prevalence — no coverage",
        round(crude["No coverage"] * 100, 2), "%",
        f"mean age {mean_age['No coverage']:.1f}")
add_kpi("Prevalence — no access barrier",
        round(crude["No barrier reported"] * 100, 2), "%",
        f"mean age {mean_age['No barrier reported']:.1f}")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.4),
                               gridspec_kw={"width_ratios": [1, 1.5]})

order = ["No coverage", "No barrier reported", "Insured but cost-deterred"]
ax1.bar(range(3), [crude[k] for k in order], color=[LIGHT, BASE, ACCENT], width=0.6)
for i, k in enumerate(order):
    ax1.text(i, crude[k] + 0.003, f"{crude[k]:.1%}", ha="center",
             fontsize=10.5, fontweight="bold", color=INK)
    ax1.text(i, -0.011, f"avg age {mean_age[k]:.0f}", ha="center",
             fontsize=8, color=MUTED)
ax1.set_xticks(range(3))
ax1.set_xticklabels(["No\ncoverage", "No barrier\nreported",
                     "Insured but\ncost-deterred"], fontsize=9)
style(ax1, "Crude rates look backwards",
      "The uninsured appear healthiest", ylab="Heart disease prevalence")
ax1.yaxis.set_major_formatter(PercentFormatter(1.0))
ax1.set_ylim(-0.016, 0.155)

for col, colr, lw in [("Insured but cost-deterred", ACCENT, 2.4),
                      ("No coverage", MUTED, 1.9),
                      ("No barrier reported", BASE, 2.4)]:
    ax2.plot(strat.index, strat[col], marker="o", markersize=4.5,
             color=colr, linewidth=lw, label=col)
style(ax2, "…but the gap holds at every age",
      "Age-stratified prevalence — cost-deterred respondents lead in all 13 brackets",
      xlab="Age bracket")
ax2.yaxis.set_major_formatter(PercentFormatter(1.0))
ax2.legend(frameon=False, fontsize=9, loc="upper left")
plt.setp(ax2.get_xticklabels(), rotation=32, ha="right", fontsize=8.5)
fig.tight_layout()
fig.savefig(CHARTS / "06_access_paradox.png", bbox_inches="tight")
plt.close(fig)


# ==============================================================================
# EXPORT
# ==============================================================================
kpi_df = pd.DataFrame(kpis)
kpi_df.to_csv(OUT / "kpi_summary.csv", index=False)

# Aggregated tables for Power BI / SQL validation
(rr_df.assign(**{c: rr_df[c].round(4) for c in
                 ["prevalence_with", "prevalence_without", "relative_risk", "population_share"]})
 .to_csv(OUT / "agg_relative_risk.csv", index=False))
strat.round(4).to_csv(OUT / "agg_access_by_age.csv")

print(f"\n{len(kpi_df)} KPIs written to kpi_summary.csv")
print(f"6 charts written to charts/")
