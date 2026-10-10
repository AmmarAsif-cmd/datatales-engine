---
title: "Wellbeing in the UK (2011–2023): Data Trends and Insights"
seoTitle: "UK Wellbeing Data (2011–2023): Trends and Insights Across Regions"
description: "Explore how happiness, life satisfaction, feelings of purpose and anxiety have shifted across the UK from 2011 to 2023."
date: 2025-08-09T23:00:00.000Z
updated: 2025-08-13T02:25:42.281Z
cover: /images/posts/wellbeing-in-the-uk/cover.jpeg
coverAlt: "Cover image for Wellbeing in the UK (2011–2023): Data Trends and Insights"
tags: ["UKWellbeing", "wellbeingdata", "wellbeingtrends", "ukdata", "mentalhealthuk", "life satisfaction", "ONSData", "wellbeing", "Data Science", "data analysis", "data analytics", "data storytelling", "PowerBI", "Mental Health", "Happiness"]
originalUrl: https://datatales.co.uk/wellbeing-in-the-uk
---
## Introduction – Why look at wellbeing now?

Over the past decade the UK has gone through major changes that have touched almost every aspect of daily life. From the long shadow of the financial crisis to Brexit, the Covid-19 pandemic, and the more recent cost of living pressures, each event has shaped how people feel about their lives.

Wellbeing is more than just the absence of illness. It reflects how satisfied people are with their lives, how happy they feel, whether they believe what they do is worthwhile, and how often they experience anxiety. The Office for National Statistics collects this information every year from people all over the UK, providing a unique view into the emotional and mental health of the nation.

For this project I worked with ONS wellbeing data from 2011 to 2023. After cleaning and transforming the data, I built an interactive Power BI dashboard to explore how these measures have changed over time, where the highest and lowest scores are found, and how wellbeing is spread across different regions. The aim is to turn over a decade of numbers into a story about how life in the UK has been experienced and felt.

<div class="embed">
  <iframe src="https://app.powerbi.com/view?r=eyJrIjoiZDhlMzA3NmMtMTkwYy00M2E2LTk2NzQtNGVkOGZlOGEwN2NmIiwidCI6IjU0MDIxNjJhLTM0ZTQtNGQ2NC1hMDMyLWRjNzUwYTJjYWU3YSJ9&amp;pageName=66dce9339123a3b9549f" title="Interactive Power BI dashboard" loading="lazy" allowfullscreen></iframe>
</div>

## Dashboard Walkthrough

The wellbeing dashboard is designed to be simple enough to navigate at a glance but detailed enough to give meaningful insights. It’s divided into three main pages, each focusing on a different angle of the data.

The first page provides an overall picture of wellbeing across the UK. Here you’ll find key performance indicators (KPIs) like the highest and lowest scoring regions, the most improved areas over time, and the overall score change since the earliest year in the dataset. This page acts as a “big picture” summary so you can quickly see who is doing well and who might be struggling.

The second page focuses on trends over time. This is where you can compare different regions and wellbeing measures year by year, spotting patterns like gradual improvements or sudden drops. It’s especially useful for identifying whether certain regions are consistently improving or stuck at the same level.

The third page is all about score distribution. Instead of looking only at averages, this view spreads out the data to show how scores are distributed across regions and measures. It helps uncover whether differences between places are small and consistent or wide and uneven.

Each page has filters for year, measure of wellbeing, and region, allowing you to tailor the view to your specific interest.

## Data Overview

The data for this project comes from the Office for National Statistics’ annual survey on personal wellbeing. Every year thousands of people across the UK are asked four key questions:

- How satisfied are you with your life?
- To what extent do you feel the things you do in your life are worthwhile?
- How happy did you feel yesterday?
- How anxious did you feel yesterday?

The answers are given on a scale from 0 to 10, where higher scores indicate greater satisfaction, happiness, or sense of worth, and lower anxiety. For reporting purposes, the ONS groups these responses into categories such as “very good”, “good”, “fair”, and “poor”.

The dataset covers the period from 2011–12 to 2022–23 and includes results for every local authority and region in the UK. It also includes additional details such as the statistical confidence ranges for each measure, which help in understanding the reliability of the scores.

While the raw dataset is large and complex, it provides a rich foundation for analysis, allowing us to examine changes over time, regional differences, and how each wellbeing measure compares to the others.

## Data Source

The data for this analysis comes from the UK’s official wellbeing statistics, collected and published by the Office for National Statistics (ONS). These figures are based on large-scale surveys where people across the UK rate their wellbeing in four key areas: life satisfaction, feeling that what they do is worthwhile, happiness, and anxiety.

The dataset covers more than a decade, from 2011–12 to 2022–23, and includes results for different administrative areas across England, Wales, Scotland, and Northern Ireland. Each record contains a score, as well as the lower and upper confidence limits, which show the possible range of the estimate. The data also includes codes for each geography, making it easier to group areas by region or country.

You can access the original dataset on the Office for National Statistics website.

To support transparency, I’ve made both versions of the dataset publicly available:

- 📁 [**Raw Dataset (CSV)**](https://github.com/AmmarAsif-cmd/Wellbeing-Dataset/blob/main/Wellbeing_Dataset_Raw.xlsx)
- 📁 [**Cleaned Dataset (CSV)**](https://github.com/AmmarAsif-cmd/Wellbeing-Dataset/blob/main/Wellbeing_Dataset_Cleaned.xlsx)

## Data Cleaning and Preparation

The original dataset was not ready for direct analysis in Power BI. It included multiple columns for confidence intervals, long text labels, and some formatting that made it tricky to work with right away. The first step was to simplify and structure it in a way that would allow clear, meaningful comparisons.

One challenge was that the “Year” column was formatted like “2011–12” instead of a standard numeric year, so it had to be cleaned into a consistent format for filtering and visualizing trends. Another key step was to standardize the geographic codes (such as those starting with E, W, S, and N) so we could add a “Region” column. This allowed grouping results into England, Wales, Scotland, and Northern Ireland, as well as breaking them down by local authority.

For the wellbeing measures themselves, the dataset provided both the raw average scores and the categorical breakdowns (e.g., “good”, “poor”). We kept both, as the averages allow for precise calculations while the categories are helpful for storytelling.

Finally, we removed duplicate or irrelevant entries and reshaped the data so that each row represented one wellbeing measure for a specific place and year. This tidy structure made it much easier to create the visuals in Power BI without having to do repetitive manual fixes.

## Findings at a Glance

When you explore the wellbeing data over the last twelve years, certain stories start to take shape. On the whole, people’s sense of life satisfaction and feeling that what they do is worthwhile have held steady. There have been gentle rises and falls, but nothing dramatic in those measures. Anxiety is the one that wobbles more. It seems to respond quickly to bigger social and economic shifts.

Regional differences are clear, too. Some parts of England consistently report high levels of wellbeing, while places in the North East and parts of Wales often lag behind. These differences have persisted over the years, suggesting that local circumstances play a big role in how content or anxious people feel.

Not every area moves in the same direction. A handful of local authorities have seen their scores fall since the early years of this data. The drops are most noticeable in how happy and how satisfied people say they are with their lives. Those pockets of decline could point to new or growing challenges that deserve more attention.

If you look at how the scores are spread, you see there is more to the picture than the averages suggest. Even within high-scoring regions, there are places where people feel a lot less satisfied or happy than their neighbours. And in some areas that rank lower overall, there are communities with surprisingly strong scores. This spread shows that averages can mask real differences on the ground.

Finally, the way anxiety behaves stands apart. Lower anxiety is better, and it doesn’t always follow the same pattern as the positive measures. Regions that score well in life satisfaction aren’t always the ones with the least anxiety, which suggests that different factors are at work.

In short, the data paints a picture of a country where overall wellbeing has stayed fairly steady, but with real and persistent gaps between different regions and communities. It also reminds us that what helps people feel happy and fulfilled isn’t always the same as what helps them feel calm and free from anxiety.

## How to Use the Dashboard

This dashboard has been built so you can explore the wellbeing data from different angles without getting lost in the numbers.

On the **Summary** page, you can see the big picture — the latest national averages, how they compare over time, and which regions stand out at the top or bottom. This page is great for a quick overview.

The **Wellbeing Trends** page lets you dive deeper into regional differences and track how scores have shifted since 2011–12. You can see which areas are improving, which are holding steady, and which are showing declines.

The **Score Distribution** page is where you explore how scores are spread out. It shows you whether the wellbeing in a region is mostly similar or if there’s a wide gap between its highest and lowest scoring areas.

You can use the slicers at the top of each page to filter the data by year, measure of wellbeing, and region. This means you can focus on just one aspect, like Happiness in 2020–21, or compare several measures side by side.

Tip: If you’re not sure where to start, set the filters to the most recent year and explore each measure one at a time — this often reveals the clearest patterns.

## Caveats and Limitations

While this dashboard provides a clear view of wellbeing trends across the UK, it’s important to remember what the data can and cannot tell us.

First, the wellbeing scores are based on survey responses, which means they reflect how people feel rather than any objective measurement. This makes them valuable for understanding public sentiment, but it also means they can be influenced by short-term events, seasonal effects, or even the way questions are asked.

Second, the data is aggregated to local authority and regional levels. This is great for spotting patterns and comparing areas, but it also hides variation within those areas. A region with a “good” average score could still have communities facing serious challenges.

Third, not all changes in scores over time are necessarily linked to policy or social shifts. Sometimes differences can be due to sampling changes, differences in survey participation, or broader events like the pandemic that affect everyone in some way.

Lastly, although the dataset is quite comprehensive, it does not include every possible factor that influences wellbeing. Things like employment rates, housing quality, healthcare access, and social connections all play a role but are not directly measured here.

This dashboard should be seen as a starting point as a way to guide deeper conversations and more targeted analysis, not as the final word on wellbeing in the UK.

## Conclusion

Working with this dataset taught me that even clean numbers hide messy stories. From a purely analytical view, it is satisfying to see clear lines of stability in life satisfaction and happiness over the past decade, modest upticks and declines, and obvious regional patterns. Yet it is also a bit jarring when those charts show certain places consistently lagging behind or sudden dips around 2020.

What struck me most as I dug into the data is how much variance there is beneath the surface. An average score can look fine, but when you break it down by local authority or measure, the picture changes completely. In some communities, people are becoming more anxious while happiness stays unchanged. In others, feelings of worthwhileness drop even as life satisfaction rises. This complexity is where the data comes alive, because it reflects how differently people experience their lives depending on where they live and what they value.

As an analyst, it is tempting to focus only on the metrics and on how a line trends up or down, or which region tops the ranking. But the real takeaway is that these numbers represent people. The consistent stability hides personal struggles and successes. The regional gaps hint at the influence of local economies, support networks and services. The patterns in anxiety remind us that feeling calm is not just about being happy or satisfied, it’s about deeper factors we cannot see in the data.

In short, this project reminded me that data analysis is not just about finding trends; it is about telling the stories behind them. And the biggest story here is that wellbeing in the UK is a mosaic of experiences. Some areas are thriving, others are stuck or declining, and many places show a mix of both. By paying attention to these nuances, we can better understand where help is needed and where positive practices are working well.
