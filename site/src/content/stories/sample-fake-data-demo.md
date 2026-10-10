---
# SAMPLE STORY - ALL NUMBERS ARE MADE UP.
# Used only to develop and preview the story template (`npm run dev`).
# `sample: true` keeps it out of every production build, the sitemap and the RSS feed.
sample: true
title: "[SAMPLE] Fictional wellbeing scores in four made-up regions, 2015–2023"
description: "A layout test using invented numbers. Not real data."
hook: "In this invented dataset, Northvale overtook Eastmoor to finish with the highest score, rising from 6.1 to 7.4."
date: 2026-10-01
updated: 2026-10-05
source:
  name: "Fictional test dataset (not real)"
  publisher: "DataTales test fixtures"
  url: "https://datatales.co.uk/about"
  licence: "Test data only"
fetchedAt: 2026-10-01
recipeVersion: "sample.v1"
datasetChecksum: "0000000000000000000000000000000000000000000000000000000000000000"
period: "2015 to 2023"
keyNumbers:
  - label: "Northvale score in 2023 (fake)"
    value: "7.4"
    note: "Up from 6.1 in 2015"
  - label: "Rise in Northvale's score (fake)"
    value: "+1.3"
  - label: "Gap between highest and lowest region in 2023 (fake)"
    value: "1.6"
chart_spec:
  type: line
  x: year
  y: score
  series: region
  highlight: [Northvale, Eastmoor]
  title: "Average score by made-up region, 2015–2023 (fake data)"
  yLabel: "Average score (0–10)"
  annotation: "Fake data for layout testing. Northvale and Eastmoor are highlighted; the other regions are shown in grey."
chart_data:
  - { region: Northvale, year: 2015, score: 6.1 }
  - { region: Northvale, year: 2017, score: 6.5 }
  - { region: Northvale, year: 2019, score: 6.9 }
  - { region: Northvale, year: 2021, score: 7.0 }
  - { region: Northvale, year: 2023, score: 7.4 }
  - { region: Eastmoor, year: 2015, score: 6.8 }
  - { region: Eastmoor, year: 2017, score: 6.9 }
  - { region: Eastmoor, year: 2019, score: 7.0 }
  - { region: Eastmoor, year: 2021, score: 6.7 }
  - { region: Eastmoor, year: 2023, score: 7.1 }
  - { region: Southmere, year: 2015, score: 6.0 }
  - { region: Southmere, year: 2017, score: 6.1 }
  - { region: Southmere, year: 2019, score: 6.2 }
  - { region: Southmere, year: 2021, score: 5.9 }
  - { region: Southmere, year: 2023, score: 5.8 }
  - { region: Westford, year: 2015, score: 6.4 }
  - { region: Westford, year: 2017, score: 6.4 }
  - { region: Westford, year: 2019, score: 6.6 }
  - { region: Westford, year: 2021, score: 6.3 }
  - { region: Westford, year: 2023, score: 6.5 }
numbers:
  northvale_2015: 6.1
  northvale_2023: 7.4
  northvale_change: 1.3
  gap_2023: 1.6
---

**This is a sample story with invented numbers.** It exists only to test the story layout.

In this fictional dataset, Northvale's average score rose from 6.1 in 2015 to 7.4 in 2023, a rise of 1.3 points. Eastmoor started highest but ended second, on 7.1.

Southmere was the only region to finish lower than it started, ending on 5.8. That leaves a gap of 1.6 points between the highest and lowest regions in 2023.

## What this sample is for

It checks the headline, hook, chart, key-number cards, body text and the "Source & method" box on desktop and mobile, in light and dark themes.
