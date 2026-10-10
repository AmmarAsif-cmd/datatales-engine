---
title: "Are Petrol Cars still King in UK 2024?"
seoTitle: "Are Petrol Cars Still King in the UK? Data Analysis of Fuel Trends"
description: "Discover whether petrol cars still dominate UK roads through real data. This interactive analysis compares petrol vs electric car trends."
date: 2025-07-12T04:52:25.571Z
updated: 2025-07-23T01:14:23.222Z
cover: /images/posts/are-petrol-cars-still-king-in-uk/cover.jpeg
coverAlt: "Cover image for Are Petrol Cars still King in UK 2024?"
tags: ["Power BI", "data analysis", "electric vehicles", "petrol cars", "Interactive Dashboards", "UK Market"]
originalUrl: https://datatales.co.uk/are-petrol-cars-still-king-in-uk
---
## Introduction

Over the past ten years, the UK automobile market has seen significant change, particularly in response to growing concerns about sustainability, emissions, and government-sponsored EV subsidies. — **how dominant are petrol cars today?**

This dashboard examines the data reported by DVLA from 2014 - 2024 thoroughly with an emphasis on fuel type trends, vehicles declared SORN, Most popular models of vehicles over the years.

<div class="embed">
  <iframe src="https://app.powerbi.com/view?r=eyJrIjoiOGM4NThhM2UtODg1NS00ZDMyLWE5NDgtZDIxZjJmMzM2NTg4IiwidCI6IjU0MDIxNjJhLTM0ZTQtNGQ2NC1hMDMyLWRjNzUwYTJjYWU3YSJ9" title="Interactive Power BI dashboard" loading="lazy" allowfullscreen></iframe>
</div>

## Dashboard Overview

The Power BI dashboard is structured to answer key questions like:

- Which **fuel types** dominate the UK roads?
- How has the **trend changed over time**?
- What is the **most popular car model**?
- What proportion of vehicles are **SORN vs Licensed**?
- How do fuel types contribute to this licensing split?

## Key Highlights

#### 1. Petrol Still Leads, But EV adoption is rising

In the default view , the data shows **Petrol** is leading but in trends you can see that **EVs** are increasing like crazy every year.

- **Petrol vehicles remain the largest group**, but their lead is shrinking.
- **Electric and hybrid vehicles** have grown significantly post-2020.

#### 2. Most Popular Model in 2024: Ford FIESTA

The **Ford Fiesta** continues to be the most licensed model, closely followed by the **Volkswagen Golf** and **Ford Focus**.

This trend reflects strong demand for commercial and reliable mid-size vehicles in the UK market.

Moreover, if you check the most licensed model over the years from 2014 - 2024 in different categories you’ll find different models and companies. Like if we talk about petrol and diesel, in the UK Ford is the most dominant vehicle.But for Hybrid electric (Petrol) people rely on Toyota and Hybrid electric (Diesel) Mercedes and BMW have been seen being used by people.

#### 3. SORN Rate: 11.25% of Vehicles

Across the full dataset, around **54 million vehicles** are marked as SORN (Statutory Off Road Notification), representing:

- 11.25% of the total vehicle count

#### 4. Fuel Type Trends Over Time

Between 2014 and 2024:

- **Diesel vehicles grew** until about 2018–2019, then started declining
- **Electric vehicles** began rising significantly post-2020

The **overall fleet** expanded until 2019 before plateauing

## How to Use the Dashboard

You can filter by:

- **Year** (2014–2024)
- **Fuel Type** (Petrol, Diesel, EVs, Hybrids, etc.)
- **Licence Status** (Licensed or SORN)

Each visual updates dynamically to reflect the selected filters — offering a highly interactive view into the UK vehicle population.

## Insights & Takeaways

- **Petrol is still king**, but the crown is slipping.
- **Diesel’s popularity has peaked**, and its decline may continue.
- **Electric vehicles are on the rise**, but still lag behind in raw numbers.
- **SORN rates are useful** for understanding vehicle usage trends — such as seasonal vehicles or fleet retirements.

## Data Source & Tools

- **Source:** UK government car licensing statistics (processed in Excel)
- **Tool Used:** Power BI
- **Visuals Included:** Donut charts, bar graphs, time-series line graphs, and KPI cards

## Data Credibility & Processing

\*\*Data Source  
\*\*The dataset used in this analysis is sourced from the UK Government’s open data platform — specifically from the DVLA vehicle licensing statistics. It includes anonymized records of vehicles registered in the UK, their **fuel type**, **licence status** (Licensed or SORN), and **model details**, recorded yearly from 2014 to 2024.

\*\*Cleaning & Preparation  
\*\*The raw dataset contained multiple tables across years. Key preparation steps:

- **Merged yearly sheets** into one master dataset
- Filtered only **active (Licensed) and SORN** vehicles
- Grouped fuel types (e.g., Plug-in hybrids, range-extended electric)
- Removed blank/null entries in model and fuel type columns
- Created **custom fields** such as:
  - Total Vehicle Count
  - Fuel Type Grouping
  - Most Popular Model by Year
  - % Share of Each Fuel Type

**Limitations**

- This dashboard reflects **licensing counts**, not **vehicle usage** (i.e., miles driven)
- SORN data does not indicate why a vehicle was taken off-road
- **Model popularity** is based on total active records, not new registrations

## Future Improvements

- Add more **granular date data** (e.g. monthly trends)
- Include **emission data** or **regional breakdowns**
- Integrate **EV charging infrastructure** trends for added context

## Conclusion

Petrol cars still hold the lead in the UK — but they are no longer the unchallenged champions. As the push for greener transport continues, **electric and hybrid models are rising**, with policies and infrastructure expected to accelerate the shift. This dashboard captures a pivotal moment in that transition.
