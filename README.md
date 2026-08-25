# Heart Disease in the U.S. Adult Population

An analysis of 253,680 survey responses from the CDC Behavioral Risk Factor Surveillance System (BRFSS), 2015.

[Open the interactive dashboard](https://victoria-chika-nwachukwu.github.io/heart-disease-analysis/dashboard.html)

## Why I chose this

I studied medical laboratory science, so healthcare data is what I know best. I wanted a project where I could ask real questions instead of just cleaning a file and making charts.

What surprised me most was the scale. 23,893 people in this survey reported coronary heart disease or a heart attack. That is 9.42% of everyone surveyed, and this is not a survey of hospital patients. It is ordinary adults.

## What I found

**Risk factors stack up fast.** I counted how many of six modifiable risk factors each person had. People with none had a 1.2% rate. People with all six had 42.0%. That is 36 times higher.

**Income matters more than I expected.** The rate is 15.8% in the lowest income bracket and 5.1% in the highest, and it drops steadily in between.

**Having insurance is not the same as being able to use it.** People who have coverage but skipped seeing a doctor because of cost had the highest rate of any group, at 13.2%. That is higher than people with no insurance at all, who came in at 7.0%.

That last one looked wrong to me, so I checked it. My first thought was age, because uninsured people tend to be younger and age drives heart disease. So I compared the groups within each age bracket separately. The cost-deterred group was still higher in all 13 brackets. They are also younger on average than the group reporting no barriers, which means the plain number was hiding the gap rather than creating it.

![Access barrier comparison](charts/06_access_paradox.png)

## Two things I decided differently

**I kept the duplicate rows.**

The file has 23,899 rows that are exact copies of another row. Most people who use this dataset delete them. I did not.

The survey has 22 columns and most of them are yes or no answers. With 253,680 people answering, two different people giving the same 22 answers is not strange. It is expected. There is no ID column, so there is no way to tell a genuine duplicate from two similar people. Deleting them would mean deleting real respondents.

The full reasoning is in [reports/data_quality_report.md](reports/data_quality_report.md).

**I used relative risk instead of correlation.**

Correlation does not work well when almost every column is a yes or no. Relative risk asks a simpler question: how many times more likely is someone with this factor to have heart disease?

It changed the ranking. Obesity came out near the bottom at 1.39 times. High blood pressure came out at 4.00 times, and it affects 43% of the people surveyed. So blood pressure is both the stronger signal and the far more common one.

## Files

```
dashboard.html             Interactive dashboard, opens in any browser
findings_report.md         Full written analysis
charts/                    Six figures
scripts/
  clean_brfss.py           Cleaning and decoding
  analysis_brfss.py        KPIs and charts
reports/
  data_quality_report.md
  kpi_summary.csv          21 metrics
data/                      Raw BRFSS 2015 file
```

## How I did it

**Cleaning.** The raw file is all numbers. Every answer is a code, so `Income = 6` means `$35,000-$49,999` and nothing in the file tells you that. I decoded every column against the BRFSS codebook. For the sex column I checked the data first instead of trusting the codebook, because a wrong assumption there would flip every result by sex. I range-checked all 22 columns and built four new ones, including the risk factor count and the healthcare access measure.

**Analysis.** 21 metrics covering relative risk, the risk factor curve, the income gradient, and the age-by-age access comparison.

**Dashboard.** I pre-aggregated the 253,680 rows into a 13,200 cell summary and embedded it in one HTML file, so it runs without a server. When you filter by age, the age chart still shows every bracket. Any group with fewer than 100 people is hidden, because a rate built on three respondents is not a rate.

## What this analysis cannot tell you

- People reported their own conditions. Anyone undiagnosed is invisible here, so the real rate is probably higher.
- This is one year of data with no follow-up. Nothing here shows cause.
- BRFSS provides survey weights for national estimates. I did not apply them. These are sample figures.
- Only 9.4% of the sample has heart disease. If anyone builds a model on this, accuracy would be the wrong measure.

## Tools

Python (pandas, numpy, matplotlib), SQL, HTML and JavaScript

## Source

CDC Behavioral Risk Factor Surveillance System, 2015. Public domain.
