---
# Written by worker/datatales/publish.py from the approved, verified story. Do not edit.
title: North West is the only English region where Covid deaths rose
description: Registered deaths involving Covid in a mid-April week rose from 4 to 6 in the North West
  between 2025 and 2026, while 7 of the 9 English regions saw a fall.
hook: In a mid-April week of 2026, the North West recorded 6 deaths involving Covid, more than any other
  English region and up from 4 a year earlier.
date: '2026-11-09'
updated: '2026-11-09'
source:
  name: Deaths registered weekly in England and Wales by region
  publisher: Office for National Statistics
  url: https://www.ons.gov.uk/datasets/weekly-deaths-region
  licence: Open Government Licence v3.0
fetchedAt: '2026-11-02'
recipeVersion: deaths-registered-weekly-in-england-and-wales-by-region.v1
datasetChecksum: d843c51202ed14ff3843a9be11a754417a974042701856f2b78849d7b79ac426
keyNumbers:
- label: Deaths due to respiratory disease, 2025
  value: '157'
  note: 'Next highest: South East, 131 (deaths)'
- label: Rank among 9 English regions (1st = highest)
  value: 7th → 1st
  note: Deaths involving COVID-19, 2025 to 2026
  kind: rank
- label: Deaths involving influenza or pneumonia, 2025
  value: '173'
  note: 'Next highest: South East, 161 (deaths)'
- label: Deaths involving COVID-19, 2026
  value: '6'
  note: From 4 in 2025 (deaths)
chart_spec:
  x: period
  y: value
  type: line
  title: Deaths involving Covid in a mid-April week, by English region
  series: geography
  yLabel: deaths
  highlight: North West
  annotation: Registered deaths in a mid-April week. Administrative counts. North West highlighted.
chart_data:
- code: E12000004
  lower: 2.97
  upper: 3.03
  value: 3.0
  period: '2025'
  geography: East Midlands
- code: E12000004
  lower: 2.97
  upper: 3.03
  value: 3.0
  period: '2026'
  geography: East Midlands
- code: E12000006
  lower: 5.94
  upper: 6.06
  value: 6.0
  period: '2025'
  geography: East of England
- code: E12000006
  lower: 1.98
  upper: 2.02
  value: 2.0
  period: '2026'
  geography: East of England
- code: E12000007
  lower: 8.91
  upper: 9.09
  value: 9.0
  period: '2025'
  geography: London
- code: E12000007
  lower: 1.98
  upper: 2.02
  value: 2.0
  period: '2026'
  geography: London
- code: E12000001
  lower: 5.94
  upper: 6.06
  value: 6.0
  period: '2025'
  geography: North East
- code: E12000001
  lower: 0.0
  upper: 0.0
  value: 0.0
  period: '2026'
  geography: North East
- code: E12000002
  lower: 3.96
  upper: 4.04
  value: 4.0
  period: '2025'
  geography: North West
- code: E12000002
  lower: 5.94
  upper: 6.06
  value: 6.0
  period: '2026'
  geography: North West
- code: E12000008
  lower: 7.92
  upper: 8.08
  value: 8.0
  period: '2025'
  geography: South East
- code: E12000008
  lower: 3.96
  upper: 4.04
  value: 4.0
  period: '2026'
  geography: South East
- code: E12000009
  lower: 7.92
  upper: 8.08
  value: 8.0
  period: '2025'
  geography: South West
- code: E12000009
  lower: 0.0
  upper: 0.0
  value: 0.0
  period: '2026'
  geography: South West
- code: E12000005
  lower: 6.93
  upper: 7.07
  value: 7.0
  period: '2025'
  geography: West Midlands
- code: E12000005
  lower: 1.98
  upper: 2.02
  value: 2.0
  period: '2026'
  geography: West Midlands
- code: E12000003
  lower: 3.96
  upper: 4.04
  value: 4.0
  period: '2025'
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 2.97
  upper: 3.03
  value: 3.0
  period: '2026'
  geography: Yorkshire and The Humber
numbers:
  cover:
    rank:
      noun: English regions
      groups: 9
      end_rank: 1
      end_period: '2026'
      start_rank: 7
      first_means: highest
      start_period: '2025'
    badge: 7th → 1st of 9 English regions
    group: North West
    label: Deaths involving COVID-19, 2026
    value: '6'
    change: Up from 4 in 2025
    measure_label: Deaths involving COVID-19
  series:
  - peak:
      low_value: 157.0
      low_period: '2025'
      peak_value: 157.0
      peak_period: '2025'
      latest_value: 157.0
      latest_period: '2025'
      latest_is_peak: true
      latest_below_peak_by: 0.0
      latest_well_below_peak: false
    unit: deaths
    week: Week 32
    points:
    - ci:
      - 155.43
      - 158.57
      value: 157.0
      period: '2025'
    geo_level: region
    geography: North West
    notable_moves: []
    cause_of_death: Deaths due to diseases of the respiratory system (J00 to J99)
    typical_yearly_change: 1.0
    moves_shared_by_most_geographies: []
  - peak:
      low_value: 173.0
      low_period: '2025'
      peak_value: 173.0
      peak_period: '2025'
      latest_value: 173.0
      latest_period: '2025'
      latest_is_peak: true
      latest_below_peak_by: 0.0
      latest_well_below_peak: false
    unit: deaths
    week: Week 32
    points:
    - ci:
      - 171.27
      - 174.73
      value: 173.0
      period: '2025'
    geo_level: region
    geography: North West
    notable_moves: []
    cause_of_death: Deaths involving influenza or pneumonia (J09 to J18)
    typical_yearly_change: 1.0
    moves_shared_by_most_geographies: []
  - peak:
      low_value: 254.0
      low_period: '2025'
      peak_value: 254.0
      peak_period: '2025'
      latest_value: 254.0
      latest_period: '2025'
      latest_is_peak: true
      latest_below_peak_by: 0.0
      latest_well_below_peak: false
    unit: deaths
    week: Week 50
    points:
    - ci:
      - 251.46
      - 256.54
      value: 254.0
      period: '2025'
    geo_level: region
    geography: North West
    notable_moves: []
    cause_of_death: Deaths involving influenza or pneumonia (J09 to J18)
    typical_yearly_change: 1.0
    moves_shared_by_most_geographies: []
  - peak:
      low_value: 183.0
      low_period: '2025'
      peak_value: 183.0
      peak_period: '2025'
      latest_value: 183.0
      latest_period: '2025'
      latest_is_peak: true
      latest_below_peak_by: 0.0
      latest_well_below_peak: false
    unit: deaths
    week: Week 31
    points:
    - ci:
      - 181.17
      - 184.83
      value: 183.0
      period: '2025'
    geo_level: region
    geography: North West
    notable_moves: []
    cause_of_death: Deaths involving influenza or pneumonia (J09 to J18)
    typical_yearly_change: 1.0
    moves_shared_by_most_geographies: []
  - peak:
      low_value: 4.0
      low_period: '2025'
      peak_value: 6.0
      peak_period: '2026'
      latest_value: 6.0
      latest_period: '2026'
      latest_is_peak: true
      latest_below_peak_by: 0.0
      latest_well_below_peak: false
    unit: deaths
    week: Week 16
    points:
    - ci:
      - 3.96
      - 4.04
      value: 4.0
      period: '2025'
    - ci:
      - 5.94
      - 6.06
      value: 6.0
      period: '2026'
    geo_level: region
    geography: North West
    notable_moves: []
    cause_of_death: Deaths involving COVID-19 (U07.1, U07.2, U09.9, U10.9)
    typical_yearly_change: 4.4478
    moves_shared_by_most_geographies:
    - of: 9
      groups: 7
      period: '2026'
      direction: fall
  - peak:
      low_value: 6.0
      low_period: '2025'
      peak_value: 8.0
      peak_period: '2026'
      latest_value: 8.0
      latest_period: '2026'
      latest_is_peak: true
      latest_below_peak_by: 0.0
      latest_well_below_peak: false
    unit: deaths
    week: Week 6
    points:
    - ci:
      - 5.94
      - 6.06
      value: 6.0
      period: '2025'
    - ci:
      - 7.92
      - 8.08
      value: 8.0
      period: '2026'
    geo_level: region
    geography: North West
    notable_moves: []
    cause_of_death: Deaths involving COVID-19 (U07.1, U07.2, U09.9, U10.9)
    typical_yearly_change: 5.9304
    moves_shared_by_most_geographies:
    - of: 9
      groups: 7
      period: '2026'
      direction: fall
  source:
    url: https://www.ons.gov.uk/datasets/weekly-deaths-region
    name: Deaths registered weekly in England and Wales by region
    licence: Open Government Licence v3.0
    publisher: Office for National Statistics
  caveats:
  - These are administrative counts, not survey estimates, so they have no margin of error; changes smaller
    than 2% are treated as no real change.
  findings:
  - ci:
    - 155.43
    - 158.57
    id: 33d8d3c7-7add-4cea-a46a-6a6c9bca8bda
    unit: deaths
    week: Week 32
    group: North West
    value: 157.0
    median: 93.0
    period: '2025'
    detector: outlier
    robust_z: 14.39
    slice_by:
    - cause_of_death
    - week
    - geo_level
    direction: above
    geo_level: region
    good_news: false
    group_code: E12000002
    nearest_ci:
    - 129.69
    - 132.31
    title_hint: North West stands out (above the rest) in Deaths due to diseases of the respiratory system
      (J00 to J99), Week 32, region
    effect_size: 14.3891
    score_parts:
      effect: 0.935
      surprise: 1.0
      freshness: 1.0
      relatability: 0.6
    gap_to_median: 64.0
    nearest_group: South East
    nearest_value: 131.0
    cause_of_death: Deaths due to diseases of the respiratory system (J00 to J99)
    gap_to_nearest: 26.0
    groups_compared: 9
    higher_is_better: false
  - ci:
    - 171.27
    - 174.73
    id: bcbf1ee0-ecd2-494d-be48-1381a32c7f0d
    unit: deaths
    week: Week 32
    group: North West
    value: 173.0
    median: 104.0
    period: '2025'
    detector: outlier
    robust_z: 9.31
    slice_by:
    - cause_of_death
    - week
    - geo_level
    direction: above
    geo_level: region
    good_news: false
    group_code: E12000002
    nearest_ci:
    - 159.39
    - 162.61
    title_hint: North West stands out (above the rest) in Deaths involving influenza or pneumonia (J09
      to J18), Week 32, region
    effect_size: 9.308
    score_parts:
      effect: 0.903
      surprise: 1.0
      freshness: 1.0
      relatability: 0.6
    gap_to_median: 69.0
    nearest_group: South East
    nearest_value: 161.0
    cause_of_death: Deaths involving influenza or pneumonia (J09 to J18)
    gap_to_nearest: 12.0
    groups_compared: 9
    higher_is_better: false
  - ci:
    - 251.46
    - 256.54
    id: eb5429b0-9b70-4985-9b38-0fb4792aa9fd
    unit: deaths
    week: Week 50
    group: North West
    value: 254.0
    median: 148.0
    period: '2025'
    detector: outlier
    robust_z: 8.94
    slice_by:
    - cause_of_death
    - week
    - geo_level
    direction: above
    geo_level: region
    good_news: false
    group_code: E12000002
    nearest_ci:
    - 221.76
    - 226.24
    title_hint: North West stands out (above the rest) in Deaths involving influenza or pneumonia (J09
      to J18), Week 50, region
    effect_size: 8.937
    score_parts:
      effect: 0.8994
      surprise: 1.0
      freshness: 1.0
      relatability: 0.6
    gap_to_median: 106.0
    nearest_group: South East
    nearest_value: 224.0
    cause_of_death: Deaths involving influenza or pneumonia (J09 to J18)
    gap_to_nearest: 30.0
    groups_compared: 9
    higher_is_better: false
  - ci:
    - 181.17
    - 184.83
    id: dca30552-4e2d-4da4-a9d9-c6a8824cadc7
    unit: deaths
    week: Week 31
    group: North West
    value: 183.0
    median: 112.0
    period: '2025'
    detector: outlier
    robust_z: 6.84
    slice_by:
    - cause_of_death
    - week
    - geo_level
    direction: above
    geo_level: region
    good_news: false
    group_code: E12000002
    nearest_ci:
    - 162.36
    - 165.64
    title_hint: North West stands out (above the rest) in Deaths involving influenza or pneumonia (J09
      to J18), Week 31, region
    effect_size: 6.8413
    score_parts:
      effect: 0.8725
      surprise: 1.0
      freshness: 1.0
      relatability: 0.6
    gap_to_median: 71.0
    nearest_group: South East
    nearest_value: 164.0
    cause_of_death: Deaths involving influenza or pneumonia (J09 to J18)
    gap_to_nearest: 19.0
    groups_compared: 9
    higher_is_better: false
  - id: 679978f9-e8ea-4231-a335-464a475a4f40
    unit: deaths
    week: Week 16
    group: North West
    end_ci:
    - 5.94
    - 6.06
    related:
    - numbers:
        ci:
        - 5.94
        - 6.06
        unit: deaths
        group: North West
        value: 6.0
        median: 2.0
        period: '2026'
        robust_z: 2.7
        direction: above
        good_news: false
        group_code: E12000002
        nearest_ci:
        - 3.96
        - 4.04
        gap_to_median: 4.0
        nearest_group: South East
        nearest_value: 4.0
        gap_to_nearest: 2.0
        groups_compared: 9
        higher_is_better: false
      detector: outlier
      title_hint: North West stands out (above the rest) in Deaths involving COVID-19 (U07.1, U07.2, U09.9,
        U10.9), Week 16, region
    - numbers:
        unit: deaths
        group: North West
        change: 2.0
        end_ci:
        - 5.94
        - 6.06
        improved: false
        start_ci:
        - 3.96
        - 4.04
        direction: rise
        end_value: 6.0
        good_news: false
        end_period: '2026'
        group_code: E12000002
        pct_change: 50.0
        change_rank: 7
        change_unit: deaths
        start_value: 4.0
        start_period: '2025'
        median_change: -4.0
        groups_compared: 9
        higher_is_better: false
        typical_yearly_change: 4.4478
      detector: biggest_change
      title_hint: 'North West: biggest rise in Deaths involving COVID-19 (U07.1, U07.2, U09.9, U10.9),
        Week 16, region'
    detector: rank_shift
    end_rank: 1
    overtook:
    - group: East of England
      end_ci:
      - 1.98
      - 2.02
      end_rank: 5
      start_ci:
      - 5.94
      - 6.06
      end_value: 2.0
      start_rank: 5
      start_value: 6.0
    - group: London
      end_ci:
      - 1.98
      - 2.02
      end_rank: 5
      start_ci:
      - 8.91
      - 9.09
      end_value: 2.0
      start_rank: 1
      start_value: 9.0
    - group: North East
      end_ci:
      - 0.0
      - 0.0
      end_rank: 8
      start_ci:
      - 5.94
      - 6.06
      end_value: 0.0
      start_rank: 5
      start_value: 6.0
    - group: South East
      end_ci:
      - 3.96
      - 4.04
      end_rank: 2
      start_ci:
      - 7.92
      - 8.08
      end_value: 4.0
      start_rank: 2
      start_value: 8.0
    - group: South West
      end_ci:
      - 0.0
      - 0.0
      end_rank: 8
      start_ci:
      - 7.92
      - 8.08
      end_value: 0.0
      start_rank: 2
      start_value: 8.0
    - group: West Midlands
      end_ci:
      - 1.98
      - 2.02
      end_rank: 5
      start_ci:
      - 6.93
      - 7.07
      end_value: 2.0
      start_rank: 4
      start_value: 7.0
    slice_by:
    - cause_of_death
    - week
    - geo_level
    start_ci:
    - 3.96
    - 4.04
    direction: up
    end_value: 6.0
    geo_level: region
    good_news: false
    end_period: '2026'
    group_code: E12000002
    start_rank: 7
    title_hint: North West climbed 6 place(s) in Deaths involving COVID-19 (U07.1, U07.2, U09.9, U10.9),
      Week 16, region
    effect_size: 6.75
    rank_change: 6
    score_parts:
      effect: 0.871
      surprise: 1.0
      freshness: 1.0
      relatability: 0.6
    start_value: 4.0
    overtaken_by: []
    rank_1_means: highest value
    start_period: '2025'
    groups_ranked: 9
    cause_of_death: Deaths involving COVID-19 (U07.1, U07.2, U09.9, U10.9)
    higher_is_better: false
  - id: dbb087fb-fe91-4b30-88e9-f57088383120
    unit: deaths
    week: Week 6
    group: North West
    end_ci:
    - 7.92
    - 8.08
    related:
    - numbers:
        unit: deaths
        group: North West
        change: 2.0
        end_ci:
        - 7.92
        - 8.08
        improved: false
        start_ci:
        - 5.94
        - 6.06
        direction: rise
        end_value: 8.0
        good_news: false
        end_period: '2026'
        group_code: E12000002
        pct_change: 33.33
        change_rank: 8
        change_unit: deaths
        start_value: 6.0
        start_period: '2025'
        median_change: -6.0
        groups_compared: 9
        higher_is_better: false
        typical_yearly_change: 5.9304
      detector: biggest_change
      title_hint: 'North West: biggest rise in Deaths involving COVID-19 (U07.1, U07.2, U09.9, U10.9),
        Week 6, region'
    detector: rank_shift
    end_rank: 2
    overtook:
    - group: East Midlands
      end_ci:
      - 1.98
      - 2.02
      end_rank: 9
      start_ci:
      - 9.9
      - 10.1
      end_value: 2.0
      start_rank: 5
      start_value: 10.0
    - group: East of England
      end_ci:
      - 3.96
      - 4.04
      end_rank: 5
      start_ci:
      - 13.86
      - 14.14
      end_value: 4.0
      start_rank: 3
      start_value: 14.0
    - group: London
      end_ci:
      - 5.94
      - 6.06
      end_rank: 3
      start_ci:
      - 15.84
      - 16.16
      end_value: 6.0
      start_rank: 2
      start_value: 16.0
    - group: North East
      end_ci:
      - 2.97
      - 3.03
      end_rank: 7
      start_ci:
      - 6.93
      - 7.07
      end_value: 3.0
      start_rank: 7
      start_value: 7.0
    - group: South West
      end_ci:
      - 3.96
      - 4.04
      end_rank: 5
      start_ci:
      - 9.9
      - 10.1
      end_value: 4.0
      start_rank: 5
      start_value: 10.0
    - group: West Midlands
      end_ci:
      - 5.94
      - 6.06
      end_rank: 3
      start_ci:
      - 11.88
      - 12.12
      end_value: 6.0
      start_rank: 4
      start_value: 12.0
    slice_by:
    - cause_of_death
    - week
    - geo_level
    start_ci:
    - 5.94
    - 6.06
    direction: up
    end_value: 8.0
    geo_level: region
    good_news: false
    end_period: '2026'
    group_code: E12000002
    start_rank: 8
    title_hint: North West climbed 6 place(s) in Deaths involving COVID-19 (U07.1, U07.2, U09.9, U10.9),
      Week 6, region
    effect_size: 6.75
    rank_change: 6
    score_parts:
      effect: 0.871
      surprise: 1.0
      freshness: 1.0
      relatability: 0.6
    start_value: 6.0
    overtaken_by: []
    rank_1_means: highest value
    start_period: '2025'
    groups_ranked: 9
    cause_of_death: Deaths involving COVID-19 (U07.1, U07.2, U09.9, U10.9)
    higher_is_better: false
  geo_level: region
  geography: North West
  good_news: false
  chart_facts:
    end: '2026'
    group: North West
    start: '2025'
    groups_rising: 1
    groups_falling: 7
    groups_compared: 9
    supported_checks:
    - kind: highest
      group: North West
      detail: North West 6 vs next South East 4 in 2026, clear
      period: '2026'
    - end: '2026'
      kind: only_rise
      group: North West
      start: '2025'
      detail: North West 2; all 8 others did not
    - end: '2026'
      kind: biggest_rise
      group: North West
      start: '2025'
      detail: North West 2, next 0
  data_period:
    last: '2026'
    first: '2025'
  exact_counts: true
  precision_pct: 2.0
more_charts:
- x: period
  y: value
  end: '2026'
  type: slope
  start: '2025'
  title: North West rose as most regions fell, 2025 to 2026
  series: geography
  yLabel: deaths
  highlight: North West
- x: period
  y: value
  type: map
  title: Deaths involving Covid by region, mid-April week of 2026
  period: '2026'
  series: geography
  yLabel: deaths
  highlight: North West
period: 2025 to 2026
---

The North West was the only English region where registered deaths involving Covid rose between a mid-April week in 2025 and the same week in 2026. The count went from 4 to 6, a rise of 2 deaths, which was also the biggest rise of the 9 regions. Over the same period, 7 of the 9 regions recorded a fall. That moved the North West from 7th of 9 regions to 1st, giving it the highest count of any region in that week of 2026.

The figures come from the Office for National Statistics release *Deaths registered weekly in England and Wales by region*, and cover the same mid-April week in 2025 and 2026. With data for just these years, there is no longer trend to describe, and the North West's 2026 figure is also its peak. Because the numbers are small, a difference of 2 deaths amounts to a 50.00% relative rise, so it should be read as a modest shift in absolute terms. The North West's 6 deaths was the highest regional figure in 2026, with the South East next on 4.

## How it compares

The picture elsewhere was mostly one of decline. London had the most deaths in this week of 2025, with 9, but recorded 2 in 2026. The South East fell from 8 to 4, and the South West from 8 to 0. The North East went from 6 to 0, the West Midlands from 7 to 2 and the East of England from 6 to 2. Yorkshire and The Humber moved from 4 to 3, while the East Midlands recorded 3 deaths in both years.

A similar pattern appears in an early-February week. There, the North West rose from 6 deaths involving Covid in 2025 to 8 in 2026, climbing from 8th to 2nd place, as 7 of the 9 regions recorded a fall. London went from 16 to 6 in that week and the East of England from 14 to 4.

The North West also stood out on other causes of death in 2025. In a late-summer week, it registered 157 deaths due to respiratory diseases, against a middle value of 93 across the 9 regions and 131 in the South East, the next closest region. In the same week, deaths involving influenza or pneumonia reached 173 in the North West, compared with 161 in the South East and a regional middle value of 104. In a neighbouring summer week the figures were 183 against 164, with a middle value of 112, and in a mid-December week they were 254 against 224, with a middle value of 148.

## What the data can't tell us

These are administrative counts of registered deaths, not survey estimates, so they have no margin of error. The source treats changes smaller than 2.00% as no real change, and the movements described here are larger than that. Even so, counts this small can swing from year to year, and a single week is a narrow window.

The figures are raw counts, not rates. Regions differ in population size and age profile, so a higher count does not by itself mean a higher risk for any individual.

The data do not explain causes. They cannot say why the North West rose while most regions fell, or whether this reflects local spread of the virus, testing, the timing of death registrations or chance. Involving Covid means Covid was mentioned on the death certificate, not necessarily as the main cause. Deaths are counted in the week they were registered, which can be some time after the death occurred. Finally, with figures for 2025 and 2026 alone, it is too early to call this a trend.
