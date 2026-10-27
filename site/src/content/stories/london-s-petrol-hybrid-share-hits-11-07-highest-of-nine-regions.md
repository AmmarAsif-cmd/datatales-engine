---
# Written by worker/datatales/publish.py from the approved, verified story. Do not edit.
title: London's petrol hybrid share hits 11.07%, highest of nine regions
description: London's share of private cars that are petrol hybrids rose from 1.38% in 2014 Q3 to 11.07%
  in 2026 Q2, the biggest rise of England's nine regions at 9.69 percentage points.
hook: At the end of June 2026, 11.07% of privately kept cars in London were petrol hybrids, up from 1.38%
  in 2014 Q3.
date: '2026-10-27'
updated: '2026-10-27'
source:
  name: Vehicle licensing statistics (VEH tables)
  publisher: Department for Transport
  url: https://www.gov.uk/government/statistical-data-sets/vehicle-licensing-statistics-data-tables
  licence: Open Government Licence v3.0
fetchedAt: '2026-10-12'
recipeVersion: vehicle-licensing-statistics-veh-tables.v2
datasetChecksum: 242fa118bb25226ffa44797072d66bbcd07ecdcdec2fadb4a39853b4cc847d26
keyNumbers:
- label: 'Share of private cars: petrol hybrids, 2026 Q2'
  value: 11.07%
  note: 'Next highest: North West, 7.96%'
- label: 'Share of private cars: other fuel types, 2026 Q2'
  value: 7.99%
  note: 'Next highest: South East, 6.05%'
- label: 'Share of private cars: diesel, 2026 Q2'
  value: 14.33%
  note: 'Next lowest: South East, 25.95%'
chart_spec:
  x: period
  y: value
  type: line
  title: Share of private cars that are petrol hybrids, by English region
  series: geography
  yLabel: '% of privately kept cars'
  highlight: London
  annotation: 'Cars kept by private individuals, end of each quarter. Source: DfT Vehicle licensing statistics.'
chart_data:
- code: E12000006
  lower: 0.4586
  upper: 0.4679
  value: 0.4633
  period: 2014 Q3
  geography: East
- code: E12000006
  lower: 0.4733
  upper: 0.4829
  value: 0.4781
  period: 2014 Q4
  geography: East
- code: E12000006
  lower: 0.4961
  upper: 0.5061
  value: 0.5011
  period: 2015 Q1
  geography: East
- code: E12000006
  lower: 0.5163
  upper: 0.5267
  value: 0.5215
  period: 2015 Q2
  geography: East
- code: E12000006
  lower: 0.5397
  upper: 0.5506
  value: 0.5451
  period: 2015 Q3
  geography: East
- code: E12000006
  lower: 0.561
  upper: 0.5723
  value: 0.5667
  period: 2015 Q4
  geography: East
- code: E12000006
  lower: 0.5835
  upper: 0.5953
  value: 0.5894
  period: 2016 Q1
  geography: East
- code: E12000006
  lower: 0.6104
  upper: 0.6227
  value: 0.6165
  period: 2016 Q2
  geography: East
- code: E12000006
  lower: 0.6439
  upper: 0.6569
  value: 0.6504
  period: 2016 Q3
  geography: East
- code: E12000006
  lower: 0.667
  upper: 0.6805
  value: 0.6737
  period: 2016 Q4
  geography: East
- code: E12000006
  lower: 0.7112
  upper: 0.7255
  value: 0.7183
  period: 2017 Q1
  geography: East
- code: E12000006
  lower: 0.7466
  upper: 0.7617
  value: 0.7541
  period: 2017 Q2
  geography: East
- code: E12000006
  lower: 0.7957
  upper: 0.8118
  value: 0.8038
  period: 2017 Q3
  geography: East
- code: E12000006
  lower: 0.8327
  upper: 0.8495
  value: 0.8411
  period: 2017 Q4
  geography: East
- code: E12000006
  lower: 0.8838
  upper: 0.9016
  value: 0.8927
  period: 2018 Q1
  geography: East
- code: E12000006
  lower: 0.928
  upper: 0.9468
  value: 0.9374
  period: 2018 Q2
  geography: East
- code: E12000006
  lower: 0.988
  upper: 1.008
  value: 0.998
  period: 2018 Q3
  geography: East
- code: E12000006
  lower: 1.0311
  upper: 1.0519
  value: 1.0415
  period: 2018 Q4
  geography: East
- code: E12000006
  lower: 1.0876
  upper: 1.1096
  value: 1.0986
  period: 2019 Q1
  geography: East
- code: E12000006
  lower: 1.1335
  upper: 1.1564
  value: 1.1449
  period: 2019 Q2
  geography: East
- code: E12000006
  lower: 1.188
  upper: 1.212
  value: 1.2
  period: 2019 Q3
  geography: East
- code: E12000006
  lower: 1.2369
  upper: 1.2619
  value: 1.2494
  period: 2019 Q4
  geography: East
- code: E12000006
  lower: 1.3022
  upper: 1.3285
  value: 1.3154
  period: 2020 Q1
  geography: East
- code: E12000006
  lower: 1.3307
  upper: 1.3576
  value: 1.3442
  period: 2020 Q2
  geography: East
- code: E12000006
  lower: 1.4462
  upper: 1.4754
  value: 1.4608
  period: 2020 Q3
  geography: East
- code: E12000006
  lower: 1.5292
  upper: 1.56
  value: 1.5446
  period: 2020 Q4
  geography: East
- code: E12000006
  lower: 1.6439
  upper: 1.6771
  value: 1.6605
  period: 2021 Q1
  geography: East
- code: E12000006
  lower: 1.8048
  upper: 1.8413
  value: 1.8231
  period: 2021 Q2
  geography: East
- code: E12000006
  lower: 1.9681
  upper: 2.0078
  value: 1.988
  period: 2021 Q3
  geography: East
- code: E12000006
  lower: 2.0822
  upper: 2.1242
  value: 2.1032
  period: 2021 Q4
  geography: East
- code: E12000006
  lower: 2.2788
  upper: 2.3249
  value: 2.3019
  period: 2022 Q1
  geography: East
- code: E12000006
  lower: 2.4749
  upper: 2.5249
  value: 2.4999
  period: 2022 Q2
  geography: East
- code: E12000006
  lower: 2.6721
  upper: 2.7261
  value: 2.6991
  period: 2022 Q3
  geography: East
- code: E12000006
  lower: 2.8342
  upper: 2.8915
  value: 2.8629
  period: 2022 Q4
  geography: East
- code: E12000006
  lower: 3.0565
  upper: 3.1183
  value: 3.0874
  period: 2023 Q1
  geography: East
- code: E12000006
  lower: 3.2658
  upper: 3.3318
  value: 3.2988
  period: 2023 Q2
  geography: East
- code: E12000006
  lower: 3.5488
  upper: 3.6205
  value: 3.5846
  period: 2023 Q3
  geography: East
- code: E12000006
  lower: 3.8293
  upper: 3.9066
  value: 3.8679
  period: 2023 Q4
  geography: East
- code: E12000006
  lower: 4.1584
  upper: 4.2424
  value: 4.2004
  period: 2024 Q1
  geography: East
- code: E12000006
  lower: 4.4533
  upper: 4.5433
  value: 4.4983
  period: 2024 Q2
  geography: East
- code: E12000006
  lower: 4.7945
  upper: 4.8913
  value: 4.8429
  period: 2024 Q3
  geography: East
- code: E12000006
  lower: 5.1325
  upper: 5.2362
  value: 5.1844
  period: 2024 Q4
  geography: East
- code: E12000006
  lower: 5.5526
  upper: 5.6648
  value: 5.6087
  period: 2025 Q1
  geography: East
- code: E12000006
  lower: 5.8688
  upper: 5.9873
  value: 5.928
  period: 2025 Q2
  geography: East
- code: E12000006
  lower: 6.2393
  upper: 6.3654
  value: 6.3023
  period: 2025 Q3
  geography: East
- code: E12000006
  lower: 6.5933
  upper: 6.7265
  value: 6.6599
  period: 2025 Q4
  geography: East
- code: E12000006
  lower: 7.0531
  upper: 7.1956
  value: 7.1244
  period: 2026 Q1
  geography: East
- code: E12000006
  lower: 7.4151
  upper: 7.5649
  value: 7.49
  period: 2026 Q2
  geography: East
- code: E12000004
  lower: 0.4269
  upper: 0.4355
  value: 0.4312
  period: 2014 Q3
  geography: East Midlands
- code: E12000004
  lower: 0.4401
  upper: 0.449
  value: 0.4446
  period: 2014 Q4
  geography: East Midlands
- code: E12000004
  lower: 0.4658
  upper: 0.4753
  value: 0.4705
  period: 2015 Q1
  geography: East Midlands
- code: E12000004
  lower: 0.481
  upper: 0.4907
  value: 0.4859
  period: 2015 Q2
  geography: East Midlands
- code: E12000004
  lower: 0.5017
  upper: 0.5119
  value: 0.5068
  period: 2015 Q3
  geography: East Midlands
- code: E12000004
  lower: 0.5201
  upper: 0.5306
  value: 0.5253
  period: 2015 Q4
  geography: East Midlands
- code: E12000004
  lower: 0.5444
  upper: 0.5554
  value: 0.5499
  period: 2016 Q1
  geography: East Midlands
- code: E12000004
  lower: 0.5732
  upper: 0.5848
  value: 0.579
  period: 2016 Q2
  geography: East Midlands
- code: E12000004
  lower: 0.603
  upper: 0.6152
  value: 0.6091
  period: 2016 Q3
  geography: East Midlands
- code: E12000004
  lower: 0.6259
  upper: 0.6386
  value: 0.6322
  period: 2016 Q4
  geography: East Midlands
- code: E12000004
  lower: 0.6724
  upper: 0.6859
  value: 0.6792
  period: 2017 Q1
  geography: East Midlands
- code: E12000004
  lower: 0.7062
  upper: 0.7205
  value: 0.7133
  period: 2017 Q2
  geography: East Midlands
- code: E12000004
  lower: 0.7508
  upper: 0.766
  value: 0.7584
  period: 2017 Q3
  geography: East Midlands
- code: E12000004
  lower: 0.7888
  upper: 0.8047
  value: 0.7967
  period: 2017 Q4
  geography: East Midlands
- code: E12000004
  lower: 0.8354
  upper: 0.8523
  value: 0.8438
  period: 2018 Q1
  geography: East Midlands
- code: E12000004
  lower: 0.8715
  upper: 0.8891
  value: 0.8803
  period: 2018 Q2
  geography: East Midlands
- code: E12000004
  lower: 0.9236
  upper: 0.9423
  value: 0.9329
  period: 2018 Q3
  geography: East Midlands
- code: E12000004
  lower: 0.965
  upper: 0.9845
  value: 0.9747
  period: 2018 Q4
  geography: East Midlands
- code: E12000004
  lower: 1.0076
  upper: 1.028
  value: 1.0178
  period: 2019 Q1
  geography: East Midlands
- code: E12000004
  lower: 1.0463
  upper: 1.0674
  value: 1.0569
  period: 2019 Q2
  geography: East Midlands
- code: E12000004
  lower: 1.0977
  upper: 1.1198
  value: 1.1087
  period: 2019 Q3
  geography: East Midlands
- code: E12000004
  lower: 1.1413
  upper: 1.1644
  value: 1.1529
  period: 2019 Q4
  geography: East Midlands
- code: E12000004
  lower: 1.1997
  upper: 1.2239
  value: 1.2118
  period: 2020 Q1
  geography: East Midlands
- code: E12000004
  lower: 1.2272
  upper: 1.2519
  value: 1.2395
  period: 2020 Q2
  geography: East Midlands
- code: E12000004
  lower: 1.3283
  upper: 1.3551
  value: 1.3417
  period: 2020 Q3
  geography: East Midlands
- code: E12000004
  lower: 1.4073
  upper: 1.4357
  value: 1.4215
  period: 2020 Q4
  geography: East Midlands
- code: E12000004
  lower: 1.5096
  upper: 1.5401
  value: 1.5248
  period: 2021 Q1
  geography: East Midlands
- code: E12000004
  lower: 1.6623
  upper: 1.6959
  value: 1.6791
  period: 2021 Q2
  geography: East Midlands
- code: E12000004
  lower: 1.8196
  upper: 1.8563
  value: 1.8379
  period: 2021 Q3
  geography: East Midlands
- code: E12000004
  lower: 1.9233
  upper: 1.9622
  value: 1.9428
  period: 2021 Q4
  geography: East Midlands
- code: E12000004
  lower: 2.0934
  upper: 2.1357
  value: 2.1145
  period: 2022 Q1
  geography: East Midlands
- code: E12000004
  lower: 2.269
  upper: 2.3148
  value: 2.2919
  period: 2022 Q2
  geography: East Midlands
- code: E12000004
  lower: 2.4359
  upper: 2.4851
  value: 2.4605
  period: 2022 Q3
  geography: East Midlands
- code: E12000004
  lower: 2.5785
  upper: 2.6306
  value: 2.6046
  period: 2022 Q4
  geography: East Midlands
- code: E12000004
  lower: 2.7768
  upper: 2.8329
  value: 2.8048
  period: 2023 Q1
  geography: East Midlands
- code: E12000004
  lower: 2.9635
  upper: 3.0234
  value: 2.9934
  period: 2023 Q2
  geography: East Midlands
- code: E12000004
  lower: 3.2236
  upper: 3.2888
  value: 3.2562
  period: 2023 Q3
  geography: East Midlands
- code: E12000004
  lower: 3.4744
  upper: 3.5446
  value: 3.5095
  period: 2023 Q4
  geography: East Midlands
- code: E12000004
  lower: 3.7636
  upper: 3.8396
  value: 3.8016
  period: 2024 Q1
  geography: East Midlands
- code: E12000004
  lower: 4.0404
  upper: 4.1221
  value: 4.0812
  period: 2024 Q2
  geography: East Midlands
- code: E12000004
  lower: 4.3561
  upper: 4.4441
  value: 4.4001
  period: 2024 Q3
  geography: East Midlands
- code: E12000004
  lower: 4.6631
  upper: 4.7573
  value: 4.7102
  period: 2024 Q4
  geography: East Midlands
- code: E12000004
  lower: 5.049
  upper: 5.151
  value: 5.1
  period: 2025 Q1
  geography: East Midlands
- code: E12000004
  lower: 5.3596
  upper: 5.4679
  value: 5.4138
  period: 2025 Q2
  geography: East Midlands
- code: E12000004
  lower: 5.7108
  upper: 5.8262
  value: 5.7685
  period: 2025 Q3
  geography: East Midlands
- code: E12000004
  lower: 6.0662
  upper: 6.1887
  value: 6.1275
  period: 2025 Q4
  geography: East Midlands
- code: E12000004
  lower: 6.509
  upper: 6.6405
  value: 6.5748
  period: 2026 Q1
  geography: East Midlands
- code: E12000004
  lower: 6.8779
  upper: 7.0169
  value: 6.9474
  period: 2026 Q2
  geography: East Midlands
- code: E12000007
  lower: 1.3613
  upper: 1.3888
  value: 1.3751
  period: 2014 Q3
  geography: London
- code: E12000007
  lower: 1.4227
  upper: 1.4515
  value: 1.4371
  period: 2014 Q4
  geography: London
- code: E12000007
  lower: 1.5035
  upper: 1.5339
  value: 1.5187
  period: 2015 Q1
  geography: London
- code: E12000007
  lower: 1.5868
  upper: 1.6189
  value: 1.6029
  period: 2015 Q2
  geography: London
- code: E12000007
  lower: 1.6851
  upper: 1.7191
  value: 1.7021
  period: 2015 Q3
  geography: London
- code: E12000007
  lower: 1.7729
  upper: 1.8088
  value: 1.7909
  period: 2015 Q4
  geography: London
- code: E12000007
  lower: 1.8569
  upper: 1.8944
  value: 1.8757
  period: 2016 Q1
  geography: London
- code: E12000007
  lower: 1.9601
  upper: 1.9997
  value: 1.9799
  period: 2016 Q2
  geography: London
- code: E12000007
  lower: 2.0652
  upper: 2.1069
  value: 2.086
  period: 2016 Q3
  geography: London
- code: E12000007
  lower: 2.1482
  upper: 2.1916
  value: 2.1699
  period: 2016 Q4
  geography: London
- code: E12000007
  lower: 2.2567
  upper: 2.3023
  value: 2.2795
  period: 2017 Q1
  geography: London
- code: E12000007
  lower: 2.3503
  upper: 2.3978
  value: 2.3741
  period: 2017 Q2
  geography: London
- code: E12000007
  lower: 2.4577
  upper: 2.5074
  value: 2.4825
  period: 2017 Q3
  geography: London
- code: E12000007
  lower: 2.5577
  upper: 2.6093
  value: 2.5835
  period: 2017 Q4
  geography: London
- code: E12000007
  lower: 2.6755
  upper: 2.7295
  value: 2.7025
  period: 2018 Q1
  geography: London
- code: E12000007
  lower: 2.7904
  upper: 2.8468
  value: 2.8186
  period: 2018 Q2
  geography: London
- code: E12000007
  lower: 2.9387
  upper: 2.998
  value: 2.9684
  period: 2018 Q3
  geography: London
- code: E12000007
  lower: 3.0762
  upper: 3.1383
  value: 3.1072
  period: 2018 Q4
  geography: London
- code: E12000007
  lower: 3.2258
  upper: 3.291
  value: 3.2584
  period: 2019 Q1
  geography: London
- code: E12000007
  lower: 3.3755
  upper: 3.4437
  value: 3.4096
  period: 2019 Q2
  geography: London
- code: E12000007
  lower: 3.5341
  upper: 3.6055
  value: 3.5698
  period: 2019 Q3
  geography: London
- code: E12000007
  lower: 3.6885
  upper: 3.7631
  value: 3.7258
  period: 2019 Q4
  geography: London
- code: E12000007
  lower: 3.8103
  upper: 3.8873
  value: 3.8488
  period: 2020 Q1
  geography: London
- code: E12000007
  lower: 3.8972
  upper: 3.9759
  value: 3.9366
  period: 2020 Q2
  geography: London
- code: E12000007
  lower: 4.089
  upper: 4.1716
  value: 4.1303
  period: 2020 Q3
  geography: London
- code: E12000007
  lower: 4.273
  upper: 4.3594
  value: 4.3162
  period: 2020 Q4
  geography: London
- code: E12000007
  lower: 4.5037
  upper: 4.5947
  value: 4.5492
  period: 2021 Q1
  geography: London
- code: E12000007
  lower: 4.7719
  upper: 4.8683
  value: 4.8201
  period: 2021 Q2
  geography: London
- code: E12000007
  lower: 5.0986
  upper: 5.2016
  value: 5.1501
  period: 2021 Q3
  geography: London
- code: E12000007
  lower: 5.3052
  upper: 5.4124
  value: 5.3588
  period: 2021 Q4
  geography: London
- code: E12000007
  lower: 5.564
  upper: 5.6764
  value: 5.6202
  period: 2022 Q1
  geography: London
- code: E12000007
  lower: 5.8173
  upper: 5.9348
  value: 5.8761
  period: 2022 Q2
  geography: London
- code: E12000007
  lower: 6.0818
  upper: 6.2046
  value: 6.1432
  period: 2022 Q3
  geography: London
- code: E12000007
  lower: 6.3071
  upper: 6.4345
  value: 6.3708
  period: 2022 Q4
  geography: London
- code: E12000007
  lower: 6.5953
  upper: 6.7286
  value: 6.6619
  period: 2023 Q1
  geography: London
- code: E12000007
  lower: 6.909
  upper: 7.0486
  value: 6.9788
  period: 2023 Q2
  geography: London
- code: E12000007
  lower: 7.3189
  upper: 7.4667
  value: 7.3928
  period: 2023 Q3
  geography: London
- code: E12000007
  lower: 7.6325
  upper: 7.7867
  value: 7.7096
  period: 2023 Q4
  geography: London
- code: E12000007
  lower: 7.9575
  upper: 8.1183
  value: 8.0379
  period: 2024 Q1
  geography: London
- code: E12000007
  lower: 8.2527
  upper: 8.4195
  value: 8.3361
  period: 2024 Q2
  geography: London
- code: E12000007
  lower: 8.5725
  upper: 8.7457
  value: 8.6591
  period: 2024 Q3
  geography: London
- code: E12000007
  lower: 8.8783
  upper: 9.0576
  value: 8.9679
  period: 2024 Q4
  geography: London
- code: E12000007
  lower: 9.2282
  upper: 9.4146
  value: 9.3214
  period: 2025 Q1
  geography: London
- code: E12000007
  lower: 9.5323
  upper: 9.7249
  value: 9.6286
  period: 2025 Q2
  geography: London
- code: E12000007
  lower: 9.8762
  upper: 10.0757
  value: 9.9759
  period: 2025 Q3
  geography: London
- code: E12000007
  lower: 10.2124
  upper: 10.4187
  value: 10.3156
  period: 2025 Q4
  geography: London
- code: E12000007
  lower: 10.6019
  upper: 10.8161
  value: 10.709
  period: 2026 Q1
  geography: London
- code: E12000007
  lower: 10.9591
  upper: 11.1805
  value: 11.0698
  period: 2026 Q2
  geography: London
- code: E12000001
  lower: 0.2655
  upper: 0.2709
  value: 0.2682
  period: 2014 Q3
  geography: North East
- code: E12000001
  lower: 0.2737
  upper: 0.2793
  value: 0.2765
  period: 2014 Q4
  geography: North East
- code: E12000001
  lower: 0.2875
  upper: 0.2933
  value: 0.2904
  period: 2015 Q1
  geography: North East
- code: E12000001
  lower: 0.2983
  upper: 0.3044
  value: 0.3014
  period: 2015 Q2
  geography: North East
- code: E12000001
  lower: 0.3135
  upper: 0.3198
  value: 0.3166
  period: 2015 Q3
  geography: North East
- code: E12000001
  lower: 0.3268
  upper: 0.3334
  value: 0.3301
  period: 2015 Q4
  geography: North East
- code: E12000001
  lower: 0.3406
  upper: 0.3474
  value: 0.344
  period: 2016 Q1
  geography: North East
- code: E12000001
  lower: 0.3574
  upper: 0.3646
  value: 0.361
  period: 2016 Q2
  geography: North East
- code: E12000001
  lower: 0.3754
  upper: 0.3829
  value: 0.3791
  period: 2016 Q3
  geography: North East
- code: E12000001
  lower: 0.39
  upper: 0.3979
  value: 0.3939
  period: 2016 Q4
  geography: North East
- code: E12000001
  lower: 0.4194
  upper: 0.4279
  value: 0.4237
  period: 2017 Q1
  geography: North East
- code: E12000001
  lower: 0.4402
  upper: 0.4491
  value: 0.4446
  period: 2017 Q2
  geography: North East
- code: E12000001
  lower: 0.4703
  upper: 0.4798
  value: 0.475
  period: 2017 Q3
  geography: North East
- code: E12000001
  lower: 0.4925
  upper: 0.5025
  value: 0.4975
  period: 2017 Q4
  geography: North East
- code: E12000001
  lower: 0.5189
  upper: 0.5294
  value: 0.5241
  period: 2018 Q1
  geography: North East
- code: E12000001
  lower: 0.549
  upper: 0.5601
  value: 0.5546
  period: 2018 Q2
  geography: North East
- code: E12000001
  lower: 0.5904
  upper: 0.6023
  value: 0.5964
  period: 2018 Q3
  geography: North East
- code: E12000001
  lower: 0.6176
  upper: 0.6301
  value: 0.6238
  period: 2018 Q4
  geography: North East
- code: E12000001
  lower: 0.6606
  upper: 0.674
  value: 0.6673
  period: 2019 Q1
  geography: North East
- code: E12000001
  lower: 0.6875
  upper: 0.7014
  value: 0.6944
  period: 2019 Q2
  geography: North East
- code: E12000001
  lower: 0.7281
  upper: 0.7428
  value: 0.7354
  period: 2019 Q3
  geography: North East
- code: E12000001
  lower: 0.7572
  upper: 0.7725
  value: 0.7648
  period: 2019 Q4
  geography: North East
- code: E12000001
  lower: 0.8011
  upper: 0.8173
  value: 0.8092
  period: 2020 Q1
  geography: North East
- code: E12000001
  lower: 0.8244
  upper: 0.841
  value: 0.8327
  period: 2020 Q2
  geography: North East
- code: E12000001
  lower: 0.925
  upper: 0.9437
  value: 0.9344
  period: 2020 Q3
  geography: North East
- code: E12000001
  lower: 0.988
  upper: 1.0079
  value: 0.9979
  period: 2020 Q4
  geography: North East
- code: E12000001
  lower: 1.0916
  upper: 1.1137
  value: 1.1027
  period: 2021 Q1
  geography: North East
- code: E12000001
  lower: 1.2414
  upper: 1.2665
  value: 1.2539
  period: 2021 Q2
  geography: North East
- code: E12000001
  lower: 1.4024
  upper: 1.4308
  value: 1.4166
  period: 2021 Q3
  geography: North East
- code: E12000001
  lower: 1.4978
  upper: 1.528
  value: 1.5129
  period: 2021 Q4
  geography: North East
- code: E12000001
  lower: 1.6669
  upper: 1.7006
  value: 1.6838
  period: 2022 Q1
  geography: North East
- code: E12000001
  lower: 1.8456
  upper: 1.8829
  value: 1.8642
  period: 2022 Q2
  geography: North East
- code: E12000001
  lower: 2.0096
  upper: 2.0502
  value: 2.0299
  period: 2022 Q3
  geography: North East
- code: E12000001
  lower: 2.1703
  upper: 2.2142
  value: 2.1923
  period: 2022 Q4
  geography: North East
- code: E12000001
  lower: 2.3778
  upper: 2.4258
  value: 2.4018
  period: 2023 Q1
  geography: North East
- code: E12000001
  lower: 2.6005
  upper: 2.6531
  value: 2.6268
  period: 2023 Q2
  geography: North East
- code: E12000001
  lower: 2.8576
  upper: 2.9154
  value: 2.8865
  period: 2023 Q3
  geography: North East
- code: E12000001
  lower: 3.1082
  upper: 3.171
  value: 3.1396
  period: 2023 Q4
  geography: North East
- code: E12000001
  lower: 3.4188
  upper: 3.4879
  value: 3.4533
  period: 2024 Q1
  geography: North East
- code: E12000001
  lower: 3.7535
  upper: 3.8293
  value: 3.7914
  period: 2024 Q2
  geography: North East
- code: E12000001
  lower: 4.124
  upper: 4.2073
  value: 4.1657
  period: 2024 Q3
  geography: North East
- code: E12000001
  lower: 4.4507
  upper: 4.5406
  value: 4.4956
  period: 2024 Q4
  geography: North East
- code: E12000001
  lower: 4.8875
  upper: 4.9862
  value: 4.9368
  period: 2025 Q1
  geography: North East
- code: E12000001
  lower: 5.2546
  upper: 5.3608
  value: 5.3077
  period: 2025 Q2
  geography: North East
- code: E12000001
  lower: 5.6633
  upper: 5.7777
  value: 5.7205
  period: 2025 Q3
  geography: North East
- code: E12000001
  lower: 6.0338
  upper: 6.1557
  value: 6.0948
  period: 2025 Q4
  geography: North East
- code: E12000001
  lower: 6.5624
  upper: 6.6949
  value: 6.6286
  period: 2026 Q1
  geography: North East
- code: E12000001
  lower: 7.0181
  upper: 7.1598
  value: 7.089
  period: 2026 Q2
  geography: North East
- code: E12000002
  lower: 0.4243
  upper: 0.4328
  value: 0.4285
  period: 2014 Q3
  geography: North West
- code: E12000002
  lower: 0.4417
  upper: 0.4506
  value: 0.4462
  period: 2014 Q4
  geography: North West
- code: E12000002
  lower: 0.4632
  upper: 0.4726
  value: 0.4679
  period: 2015 Q1
  geography: North West
- code: E12000002
  lower: 0.4853
  upper: 0.4951
  value: 0.4902
  period: 2015 Q2
  geography: North West
- code: E12000002
  lower: 0.5129
  upper: 0.5232
  value: 0.518
  period: 2015 Q3
  geography: North West
- code: E12000002
  lower: 0.5333
  upper: 0.5441
  value: 0.5387
  period: 2015 Q4
  geography: North West
- code: E12000002
  lower: 0.5587
  upper: 0.57
  value: 0.5644
  period: 2016 Q1
  geography: North West
- code: E12000002
  lower: 0.5912
  upper: 0.6032
  value: 0.5972
  period: 2016 Q2
  geography: North West
- code: E12000002
  lower: 0.6242
  upper: 0.6368
  value: 0.6305
  period: 2016 Q3
  geography: North West
- code: E12000002
  lower: 0.65
  upper: 0.6632
  value: 0.6566
  period: 2016 Q4
  geography: North West
- code: E12000002
  lower: 0.6966
  upper: 0.7107
  value: 0.7037
  period: 2017 Q1
  geography: North West
- code: E12000002
  lower: 0.7319
  upper: 0.7467
  value: 0.7393
  period: 2017 Q2
  geography: North West
- code: E12000002
  lower: 0.7782
  upper: 0.7939
  value: 0.7861
  period: 2017 Q3
  geography: North West
- code: E12000002
  lower: 0.813
  upper: 0.8294
  value: 0.8212
  period: 2017 Q4
  geography: North West
- code: E12000002
  lower: 0.8551
  upper: 0.8723
  value: 0.8637
  period: 2018 Q1
  geography: North West
- code: E12000002
  lower: 0.8983
  upper: 0.9164
  value: 0.9074
  period: 2018 Q2
  geography: North West
- code: E12000002
  lower: 0.9531
  upper: 0.9723
  value: 0.9627
  period: 2018 Q3
  geography: North West
- code: E12000002
  lower: 0.9952
  upper: 1.0153
  value: 1.0052
  period: 2018 Q4
  geography: North West
- code: E12000002
  lower: 1.0405
  upper: 1.0615
  value: 1.051
  period: 2019 Q1
  geography: North West
- code: E12000002
  lower: 1.0792
  upper: 1.101
  value: 1.0901
  period: 2019 Q2
  geography: North West
- code: E12000002
  lower: 1.1234
  upper: 1.1461
  value: 1.1347
  period: 2019 Q3
  geography: North West
- code: E12000002
  lower: 1.1683
  upper: 1.1919
  value: 1.1801
  period: 2019 Q4
  geography: North West
- code: E12000002
  lower: 1.2219
  upper: 1.2466
  value: 1.2343
  period: 2020 Q1
  geography: North West
- code: E12000002
  lower: 1.2548
  upper: 1.2802
  value: 1.2675
  period: 2020 Q2
  geography: North West
- code: E12000002
  lower: 1.3592
  upper: 1.3867
  value: 1.373
  period: 2020 Q3
  geography: North West
- code: E12000002
  lower: 1.4413
  upper: 1.4704
  value: 1.4559
  period: 2020 Q4
  geography: North West
- code: E12000002
  lower: 1.561
  upper: 1.5926
  value: 1.5768
  period: 2021 Q1
  geography: North West
- code: E12000002
  lower: 1.7134
  upper: 1.7481
  value: 1.7307
  period: 2021 Q2
  geography: North West
- code: E12000002
  lower: 1.8798
  upper: 1.9177
  value: 1.8988
  period: 2021 Q3
  geography: North West
- code: E12000002
  lower: 1.9935
  upper: 2.0337
  value: 2.0136
  period: 2021 Q4
  geography: North West
- code: E12000002
  lower: 2.1937
  upper: 2.238
  value: 2.2159
  period: 2022 Q1
  geography: North West
- code: E12000002
  lower: 2.4032
  upper: 2.4518
  value: 2.4275
  period: 2022 Q2
  geography: North West
- code: E12000002
  lower: 2.603
  upper: 2.6556
  value: 2.6293
  period: 2022 Q3
  geography: North West
- code: E12000002
  lower: 2.7677
  upper: 2.8236
  value: 2.7956
  period: 2022 Q4
  geography: North West
- code: E12000002
  lower: 2.9926
  upper: 3.053
  value: 3.0228
  period: 2023 Q1
  geography: North West
- code: E12000002
  lower: 3.2176
  upper: 3.2826
  value: 3.2501
  period: 2023 Q2
  geography: North West
- code: E12000002
  lower: 3.5036
  upper: 3.5744
  value: 3.539
  period: 2023 Q3
  geography: North West
- code: E12000002
  lower: 3.7873
  upper: 3.8638
  value: 3.8256
  period: 2023 Q4
  geography: North West
- code: E12000002
  lower: 4.149
  upper: 4.2328
  value: 4.1909
  period: 2024 Q1
  geography: North West
- code: E12000002
  lower: 4.4977
  upper: 4.5886
  value: 4.5431
  period: 2024 Q2
  geography: North West
- code: E12000002
  lower: 4.8858
  upper: 4.9845
  value: 4.9352
  period: 2024 Q3
  geography: North West
- code: E12000002
  lower: 5.2337
  upper: 5.3395
  value: 5.2866
  period: 2024 Q4
  geography: North West
- code: E12000002
  lower: 5.6953
  upper: 5.8104
  value: 5.7529
  period: 2025 Q1
  geography: North West
- code: E12000002
  lower: 6.0823
  upper: 6.2052
  value: 6.1438
  period: 2025 Q2
  geography: North West
- code: E12000002
  lower: 6.5093
  upper: 6.6408
  value: 6.575
  period: 2025 Q3
  geography: North West
- code: E12000002
  lower: 6.9209
  upper: 7.0607
  value: 6.9908
  period: 2025 Q4
  geography: North West
- code: E12000002
  lower: 7.4487
  upper: 7.5991
  value: 7.5239
  period: 2026 Q1
  geography: North West
- code: E12000002
  lower: 7.8815
  upper: 8.0407
  value: 7.9611
  period: 2026 Q2
  geography: North West
- code: E12000008
  lower: 0.5537
  upper: 0.5649
  value: 0.5593
  period: 2014 Q3
  geography: South East
- code: E12000008
  lower: 0.5726
  upper: 0.5842
  value: 0.5784
  period: 2014 Q4
  geography: South East
- code: E12000008
  lower: 0.5961
  upper: 0.6082
  value: 0.6021
  period: 2015 Q1
  geography: South East
- code: E12000008
  lower: 0.6177
  upper: 0.6302
  value: 0.6239
  period: 2015 Q2
  geography: South East
- code: E12000008
  lower: 0.645
  upper: 0.658
  value: 0.6515
  period: 2015 Q3
  geography: South East
- code: E12000008
  lower: 0.6678
  upper: 0.6813
  value: 0.6745
  period: 2015 Q4
  geography: South East
- code: E12000008
  lower: 0.697
  upper: 0.7111
  value: 0.7041
  period: 2016 Q1
  geography: South East
- code: E12000008
  lower: 0.7272
  upper: 0.7419
  value: 0.7345
  period: 2016 Q2
  geography: South East
- code: E12000008
  lower: 0.7636
  upper: 0.779
  value: 0.7713
  period: 2016 Q3
  geography: South East
- code: E12000008
  lower: 0.7926
  upper: 0.8087
  value: 0.8007
  period: 2016 Q4
  geography: South East
- code: E12000008
  lower: 0.84
  upper: 0.857
  value: 0.8485
  period: 2017 Q1
  geography: South East
- code: E12000008
  lower: 0.8774
  upper: 0.8952
  value: 0.8863
  period: 2017 Q2
  geography: South East
- code: E12000008
  lower: 0.9309
  upper: 0.9498
  value: 0.9403
  period: 2017 Q3
  geography: South East
- code: E12000008
  lower: 0.9723
  upper: 0.9919
  value: 0.9821
  period: 2017 Q4
  geography: South East
- code: E12000008
  lower: 1.0228
  upper: 1.0434
  value: 1.0331
  period: 2018 Q1
  geography: South East
- code: E12000008
  lower: 1.0633
  upper: 1.0848
  value: 1.074
  period: 2018 Q2
  geography: South East
- code: E12000008
  lower: 1.1179
  upper: 1.1405
  value: 1.1292
  period: 2018 Q3
  geography: South East
- code: E12000008
  lower: 1.1631
  upper: 1.1866
  value: 1.1748
  period: 2018 Q4
  geography: South East
- code: E12000008
  lower: 1.2138
  upper: 1.2383
  value: 1.2261
  period: 2019 Q1
  geography: South East
- code: E12000008
  lower: 1.257
  upper: 1.2824
  value: 1.2697
  period: 2019 Q2
  geography: South East
- code: E12000008
  lower: 1.3154
  upper: 1.342
  value: 1.3287
  period: 2019 Q3
  geography: South East
- code: E12000008
  lower: 1.3677
  upper: 1.3954
  value: 1.3816
  period: 2019 Q4
  geography: South East
- code: E12000008
  lower: 1.4326
  upper: 1.4616
  value: 1.4471
  period: 2020 Q1
  geography: South East
- code: E12000008
  lower: 1.4657
  upper: 1.4953
  value: 1.4805
  period: 2020 Q2
  geography: South East
- code: E12000008
  lower: 1.5776
  upper: 1.6094
  value: 1.5935
  period: 2020 Q3
  geography: South East
- code: E12000008
  lower: 1.6689
  upper: 1.7026
  value: 1.6857
  period: 2020 Q4
  geography: South East
- code: E12000008
  lower: 1.7903
  upper: 1.8265
  value: 1.8084
  period: 2021 Q1
  geography: South East
- code: E12000008
  lower: 1.954
  upper: 1.9935
  value: 1.9737
  period: 2021 Q2
  geography: South East
- code: E12000008
  lower: 2.1256
  upper: 2.1685
  value: 2.147
  period: 2021 Q3
  geography: South East
- code: E12000008
  lower: 2.2427
  upper: 2.288
  value: 2.2653
  period: 2021 Q4
  geography: South East
- code: E12000008
  lower: 2.4286
  upper: 2.4776
  value: 2.4531
  period: 2022 Q1
  geography: South East
- code: E12000008
  lower: 2.6161
  upper: 2.669
  value: 2.6426
  period: 2022 Q2
  geography: South East
- code: E12000008
  lower: 2.8029
  upper: 2.8596
  value: 2.8312
  period: 2022 Q3
  geography: South East
- code: E12000008
  lower: 2.964
  upper: 3.0239
  value: 2.9939
  period: 2022 Q4
  geography: South East
- code: E12000008
  lower: 3.2035
  upper: 3.2682
  value: 3.2359
  period: 2023 Q1
  geography: South East
- code: E12000008
  lower: 3.4167
  upper: 3.4857
  value: 3.4512
  period: 2023 Q2
  geography: South East
- code: E12000008
  lower: 3.6987
  upper: 3.7734
  value: 3.7361
  period: 2023 Q3
  geography: South East
- code: E12000008
  lower: 3.9865
  upper: 4.067
  value: 4.0267
  period: 2023 Q4
  geography: South East
- code: E12000008
  lower: 4.3289
  upper: 4.4163
  value: 4.3726
  period: 2024 Q1
  geography: South East
- code: E12000008
  lower: 4.6165
  upper: 4.7098
  value: 4.6632
  period: 2024 Q2
  geography: South East
- code: E12000008
  lower: 4.9488
  upper: 5.0488
  value: 4.9988
  period: 2024 Q3
  geography: South East
- code: E12000008
  lower: 5.2631
  upper: 5.3694
  value: 5.3162
  period: 2024 Q4
  geography: South East
- code: E12000008
  lower: 5.6554
  upper: 5.7697
  value: 5.7126
  period: 2025 Q1
  geography: South East
- code: E12000008
  lower: 5.9753
  upper: 6.0961
  value: 6.0357
  period: 2025 Q2
  geography: South East
- code: E12000008
  lower: 6.3499
  upper: 6.4781
  value: 6.414
  period: 2025 Q3
  geography: South East
- code: E12000008
  lower: 6.7155
  upper: 6.8512
  value: 6.7833
  period: 2025 Q4
  geography: South East
- code: E12000008
  lower: 7.1797
  upper: 7.3247
  value: 7.2522
  period: 2026 Q1
  geography: South East
- code: E12000008
  lower: 7.5543
  upper: 7.7069
  value: 7.6306
  period: 2026 Q2
  geography: South East
- code: E12000009
  lower: 0.3444
  upper: 0.3513
  value: 0.3478
  period: 2014 Q3
  geography: South West
- code: E12000009
  lower: 0.3558
  upper: 0.363
  value: 0.3594
  period: 2014 Q4
  geography: South West
- code: E12000009
  lower: 0.3701
  upper: 0.3776
  value: 0.3738
  period: 2015 Q1
  geography: South West
- code: E12000009
  lower: 0.3852
  upper: 0.3929
  value: 0.3891
  period: 2015 Q2
  geography: South West
- code: E12000009
  lower: 0.4025
  upper: 0.4107
  value: 0.4066
  period: 2015 Q3
  geography: South West
- code: E12000009
  lower: 0.4184
  upper: 0.4269
  value: 0.4226
  period: 2015 Q4
  geography: South West
- code: E12000009
  lower: 0.4346
  upper: 0.4434
  value: 0.439
  period: 2016 Q1
  geography: South West
- code: E12000009
  lower: 0.4558
  upper: 0.465
  value: 0.4604
  period: 2016 Q2
  geography: South West
- code: E12000009
  lower: 0.4794
  upper: 0.4891
  value: 0.4843
  period: 2016 Q3
  geography: South West
- code: E12000009
  lower: 0.4961
  upper: 0.5061
  value: 0.5011
  period: 2016 Q4
  geography: South West
- code: E12000009
  lower: 0.53
  upper: 0.5407
  value: 0.5354
  period: 2017 Q1
  geography: South West
- code: E12000009
  lower: 0.552
  upper: 0.5632
  value: 0.5576
  period: 2017 Q2
  geography: South West
- code: E12000009
  lower: 0.5885
  upper: 0.6004
  value: 0.5945
  period: 2017 Q3
  geography: South West
- code: E12000009
  lower: 0.615
  upper: 0.6274
  value: 0.6212
  period: 2017 Q4
  geography: South West
- code: E12000009
  lower: 0.6477
  upper: 0.6607
  value: 0.6542
  period: 2018 Q1
  geography: South West
- code: E12000009
  lower: 0.6748
  upper: 0.6884
  value: 0.6816
  period: 2018 Q2
  geography: South West
- code: E12000009
  lower: 0.7148
  upper: 0.7292
  value: 0.722
  period: 2018 Q3
  geography: South West
- code: E12000009
  lower: 0.7428
  upper: 0.7578
  value: 0.7503
  period: 2018 Q4
  geography: South West
- code: E12000009
  lower: 0.7782
  upper: 0.7939
  value: 0.786
  period: 2019 Q1
  geography: South West
- code: E12000009
  lower: 0.8087
  upper: 0.825
  value: 0.8168
  period: 2019 Q2
  geography: South West
- code: E12000009
  lower: 0.8461
  upper: 0.8632
  value: 0.8546
  period: 2019 Q3
  geography: South West
- code: E12000009
  lower: 0.8835
  upper: 0.9013
  value: 0.8924
  period: 2019 Q4
  geography: South West
- code: E12000009
  lower: 0.9335
  upper: 0.9523
  value: 0.9429
  period: 2020 Q1
  geography: South West
- code: E12000009
  lower: 0.9602
  upper: 0.9796
  value: 0.9699
  period: 2020 Q2
  geography: South West
- code: E12000009
  lower: 1.0544
  upper: 1.0757
  value: 1.0651
  period: 2020 Q3
  geography: South West
- code: E12000009
  lower: 1.1265
  upper: 1.1492
  value: 1.1378
  period: 2020 Q4
  geography: South West
- code: E12000009
  lower: 1.2251
  upper: 1.2499
  value: 1.2375
  period: 2021 Q1
  geography: South West
- code: E12000009
  lower: 1.3658
  upper: 1.3934
  value: 1.3796
  period: 2021 Q2
  geography: South West
- code: E12000009
  lower: 1.5073
  upper: 1.5377
  value: 1.5225
  period: 2021 Q3
  geography: South West
- code: E12000009
  lower: 1.6003
  upper: 1.6327
  value: 1.6165
  period: 2021 Q4
  geography: South West
- code: E12000009
  lower: 1.7598
  upper: 1.7953
  value: 1.7776
  period: 2022 Q1
  geography: South West
- code: E12000009
  lower: 1.9069
  upper: 1.9454
  value: 1.9262
  period: 2022 Q2
  geography: South West
- code: E12000009
  lower: 2.0613
  upper: 2.103
  value: 2.0821
  period: 2022 Q3
  geography: South West
- code: E12000009
  lower: 2.1956
  upper: 2.24
  value: 2.2178
  period: 2022 Q4
  geography: South West
- code: E12000009
  lower: 2.3768
  upper: 2.4249
  value: 2.4008
  period: 2023 Q1
  geography: South West
- code: E12000009
  lower: 2.5472
  upper: 2.5987
  value: 2.5729
  period: 2023 Q2
  geography: South West
- code: E12000009
  lower: 2.7657
  upper: 2.8215
  value: 2.7936
  period: 2023 Q3
  geography: South West
- code: E12000009
  lower: 2.9798
  upper: 3.04
  value: 3.0099
  period: 2023 Q4
  geography: South West
- code: E12000009
  lower: 3.2373
  upper: 3.3027
  value: 3.27
  period: 2024 Q1
  geography: South West
- code: E12000009
  lower: 3.4831
  upper: 3.5535
  value: 3.5183
  period: 2024 Q2
  geography: South West
- code: E12000009
  lower: 3.7783
  upper: 3.8546
  value: 3.8164
  period: 2024 Q3
  geography: South West
- code: E12000009
  lower: 4.0558
  upper: 4.1377
  value: 4.0967
  period: 2024 Q4
  geography: South West
- code: E12000009
  lower: 4.402
  upper: 4.491
  value: 4.4465
  period: 2025 Q1
  geography: South West
- code: E12000009
  lower: 4.6717
  upper: 4.7661
  value: 4.7189
  period: 2025 Q2
  geography: South West
- code: E12000009
  lower: 4.9878
  upper: 5.0886
  value: 5.0382
  period: 2025 Q3
  geography: South West
- code: E12000009
  lower: 5.3109
  upper: 5.4182
  value: 5.3646
  period: 2025 Q4
  geography: South West
- code: E12000009
  lower: 5.737
  upper: 5.8529
  value: 5.7949
  period: 2026 Q1
  geography: South West
- code: E12000009
  lower: 6.0612
  upper: 6.1836
  value: 6.1224
  period: 2026 Q2
  geography: South West
- code: E12000005
  lower: 0.3444
  upper: 0.3513
  value: 0.3479
  period: 2014 Q3
  geography: West Midlands
- code: E12000005
  lower: 0.3573
  upper: 0.3646
  value: 0.361
  period: 2014 Q4
  geography: West Midlands
- code: E12000005
  lower: 0.3734
  upper: 0.3809
  value: 0.3771
  period: 2015 Q1
  geography: West Midlands
- code: E12000005
  lower: 0.3905
  upper: 0.3984
  value: 0.3944
  period: 2015 Q2
  geography: West Midlands
- code: E12000005
  lower: 0.411
  upper: 0.4193
  value: 0.4152
  period: 2015 Q3
  geography: West Midlands
- code: E12000005
  lower: 0.4282
  upper: 0.4369
  value: 0.4326
  period: 2015 Q4
  geography: West Midlands
- code: E12000005
  lower: 0.4481
  upper: 0.4571
  value: 0.4526
  period: 2016 Q1
  geography: West Midlands
- code: E12000005
  lower: 0.4735
  upper: 0.4831
  value: 0.4783
  period: 2016 Q2
  geography: West Midlands
- code: E12000005
  lower: 0.5001
  upper: 0.5102
  value: 0.5052
  period: 2016 Q3
  geography: West Midlands
- code: E12000005
  lower: 0.5207
  upper: 0.5312
  value: 0.526
  period: 2016 Q4
  geography: West Midlands
- code: E12000005
  lower: 0.5578
  upper: 0.5691
  value: 0.5635
  period: 2017 Q1
  geography: West Midlands
- code: E12000005
  lower: 0.5868
  upper: 0.5986
  value: 0.5927
  period: 2017 Q2
  geography: West Midlands
- code: E12000005
  lower: 0.6255
  upper: 0.6382
  value: 0.6318
  period: 2017 Q3
  geography: West Midlands
- code: E12000005
  lower: 0.6578
  upper: 0.6711
  value: 0.6645
  period: 2017 Q4
  geography: West Midlands
- code: E12000005
  lower: 0.6934
  upper: 0.7074
  value: 0.7004
  period: 2018 Q1
  geography: West Midlands
- code: E12000005
  lower: 0.7227
  upper: 0.7373
  value: 0.73
  period: 2018 Q2
  geography: West Midlands
- code: E12000005
  lower: 0.771
  upper: 0.7865
  value: 0.7787
  period: 2018 Q3
  geography: West Midlands
- code: E12000005
  lower: 0.813
  upper: 0.8294
  value: 0.8212
  period: 2018 Q4
  geography: West Midlands
- code: E12000005
  lower: 0.8576
  upper: 0.8749
  value: 0.8662
  period: 2019 Q1
  geography: West Midlands
- code: E12000005
  lower: 0.8974
  upper: 0.9155
  value: 0.9064
  period: 2019 Q2
  geography: West Midlands
- code: E12000005
  lower: 0.9448
  upper: 0.9639
  value: 0.9543
  period: 2019 Q3
  geography: West Midlands
- code: E12000005
  lower: 0.9905
  upper: 1.0105
  value: 1.0005
  period: 2019 Q4
  geography: West Midlands
- code: E12000005
  lower: 1.0498
  upper: 1.071
  value: 1.0604
  period: 2020 Q1
  geography: West Midlands
- code: E12000005
  lower: 1.0809
  upper: 1.1027
  value: 1.0918
  period: 2020 Q2
  geography: West Midlands
- code: E12000005
  lower: 1.1887
  upper: 1.2127
  value: 1.2007
  period: 2020 Q3
  geography: West Midlands
- code: E12000005
  lower: 1.2748
  upper: 1.3006
  value: 1.2877
  period: 2020 Q4
  geography: West Midlands
- code: E12000005
  lower: 1.388
  upper: 1.4161
  value: 1.402
  period: 2021 Q1
  geography: West Midlands
- code: E12000005
  lower: 1.5572
  upper: 1.5887
  value: 1.573
  period: 2021 Q2
  geography: West Midlands
- code: E12000005
  lower: 1.7254
  upper: 1.7603
  value: 1.7428
  period: 2021 Q3
  geography: West Midlands
- code: E12000005
  lower: 1.8367
  upper: 1.8738
  value: 1.8553
  period: 2021 Q4
  geography: West Midlands
- code: E12000005
  lower: 2.0085
  upper: 2.049
  value: 2.0287
  period: 2022 Q1
  geography: West Midlands
- code: E12000005
  lower: 2.1993
  upper: 2.2438
  value: 2.2216
  period: 2022 Q2
  geography: West Midlands
- code: E12000005
  lower: 2.3619
  upper: 2.4096
  value: 2.3857
  period: 2022 Q3
  geography: West Midlands
- code: E12000005
  lower: 2.5124
  upper: 2.5632
  value: 2.5378
  period: 2022 Q4
  geography: West Midlands
- code: E12000005
  lower: 2.7093
  upper: 2.7641
  value: 2.7367
  period: 2023 Q1
  geography: West Midlands
- code: E12000005
  lower: 2.9102
  upper: 2.969
  value: 2.9396
  period: 2023 Q2
  geography: West Midlands
- code: E12000005
  lower: 3.1892
  upper: 3.2536
  value: 3.2214
  period: 2023 Q3
  geography: West Midlands
- code: E12000005
  lower: 3.4499
  upper: 3.5195
  value: 3.4847
  period: 2023 Q4
  geography: West Midlands
- code: E12000005
  lower: 3.7716
  upper: 3.8478
  value: 3.8097
  period: 2024 Q1
  geography: West Midlands
- code: E12000005
  lower: 4.0712
  upper: 4.1535
  value: 4.1123
  period: 2024 Q2
  geography: West Midlands
- code: E12000005
  lower: 4.4171
  upper: 4.5063
  value: 4.4617
  period: 2024 Q3
  geography: West Midlands
- code: E12000005
  lower: 4.7391
  upper: 4.8349
  value: 4.787
  period: 2024 Q4
  geography: West Midlands
- code: E12000005
  lower: 5.1539
  upper: 5.258
  value: 5.2059
  period: 2025 Q1
  geography: West Midlands
- code: E12000005
  lower: 5.4832
  upper: 5.594
  value: 5.5386
  period: 2025 Q2
  geography: West Midlands
- code: E12000005
  lower: 5.8671
  upper: 5.9856
  value: 5.9264
  period: 2025 Q3
  geography: West Midlands
- code: E12000005
  lower: 6.24
  upper: 6.366
  value: 6.303
  period: 2025 Q4
  geography: West Midlands
- code: E12000005
  lower: 6.7222
  upper: 6.858
  value: 6.7901
  period: 2026 Q1
  geography: West Midlands
- code: E12000005
  lower: 7.1009
  upper: 7.2443
  value: 7.1726
  period: 2026 Q2
  geography: West Midlands
- code: E12000003
  lower: 0.3842
  upper: 0.392
  value: 0.3881
  period: 2014 Q3
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.3995
  upper: 0.4076
  value: 0.4036
  period: 2014 Q4
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.4213
  upper: 0.4298
  value: 0.4255
  period: 2015 Q1
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.4422
  upper: 0.4511
  value: 0.4467
  period: 2015 Q2
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.4657
  upper: 0.4751
  value: 0.4704
  period: 2015 Q3
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.4847
  upper: 0.4945
  value: 0.4896
  period: 2015 Q4
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.5104
  upper: 0.5207
  value: 0.5155
  period: 2016 Q1
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.5397
  upper: 0.5506
  value: 0.5452
  period: 2016 Q2
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.571
  upper: 0.5826
  value: 0.5768
  period: 2016 Q3
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.5934
  upper: 0.6054
  value: 0.5994
  period: 2016 Q4
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.6373
  upper: 0.6502
  value: 0.6438
  period: 2017 Q1
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.6686
  upper: 0.6821
  value: 0.6754
  period: 2017 Q2
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.7115
  upper: 0.7258
  value: 0.7186
  period: 2017 Q3
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.746
  upper: 0.761
  value: 0.7535
  period: 2017 Q4
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.7857
  upper: 0.8015
  value: 0.7936
  period: 2018 Q1
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.826
  upper: 0.8427
  value: 0.8343
  period: 2018 Q2
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.8828
  upper: 0.9006
  value: 0.8917
  period: 2018 Q3
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.9287
  upper: 0.9474
  value: 0.938
  period: 2018 Q4
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 0.9797
  upper: 0.9995
  value: 0.9896
  period: 2019 Q1
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 1.0282
  upper: 1.049
  value: 1.0386
  period: 2019 Q2
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 1.0888
  upper: 1.1108
  value: 1.0998
  period: 2019 Q3
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 1.1431
  upper: 1.1662
  value: 1.1547
  period: 2019 Q4
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 1.2074
  upper: 1.2318
  value: 1.2196
  period: 2020 Q1
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 1.2382
  upper: 1.2633
  value: 1.2508
  period: 2020 Q2
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 1.3523
  upper: 1.3796
  value: 1.3659
  period: 2020 Q3
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 1.4403
  upper: 1.4694
  value: 1.4548
  period: 2020 Q4
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 1.5576
  upper: 1.5891
  value: 1.5733
  period: 2021 Q1
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 1.7235
  upper: 1.7583
  value: 1.7409
  period: 2021 Q2
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 1.9131
  upper: 1.9517
  value: 1.9324
  period: 2021 Q3
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 2.0357
  upper: 2.0769
  value: 2.0563
  period: 2021 Q4
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 2.236
  upper: 2.2812
  value: 2.2586
  period: 2022 Q1
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 2.4157
  upper: 2.4645
  value: 2.4401
  period: 2022 Q2
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 2.6018
  upper: 2.6544
  value: 2.6281
  period: 2022 Q3
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 2.7668
  upper: 2.8227
  value: 2.7947
  period: 2022 Q4
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 2.992
  upper: 3.0525
  value: 3.0223
  period: 2023 Q1
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 3.2036
  upper: 3.2683
  value: 3.2359
  period: 2023 Q2
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 3.4696
  upper: 3.5397
  value: 3.5046
  period: 2023 Q3
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 3.7334
  upper: 3.8088
  value: 3.7711
  period: 2023 Q4
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 4.0397
  upper: 4.1214
  value: 4.0806
  period: 2024 Q1
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 4.3482
  upper: 4.4361
  value: 4.3921
  period: 2024 Q2
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 4.6976
  upper: 4.7925
  value: 4.7451
  period: 2024 Q3
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 5.0366
  upper: 5.1384
  value: 5.0875
  period: 2024 Q4
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 5.4804
  upper: 5.5911
  value: 5.5357
  period: 2025 Q1
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 5.8446
  upper: 5.9627
  value: 5.9037
  period: 2025 Q2
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 6.2394
  upper: 6.3655
  value: 6.3025
  period: 2025 Q3
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 6.614
  upper: 6.7476
  value: 6.6808
  period: 2025 Q4
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 7.0911
  upper: 7.2343
  value: 7.1627
  period: 2026 Q1
  geography: Yorkshire and The Humber
- code: E12000003
  lower: 7.4699
  upper: 7.6208
  value: 7.5453
  period: 2026 Q2
  geography: Yorkshire and The Humber
numbers:
  cover:
    badge: Highest of the 9 English regions
    group: London
    label: 'Share of private cars: petrol hybrids, 2026 Q2'
    value: 11.07%
    change: Up from 1.38% in 2014 Q3
    measure_label: 'Share of private cars: petrol hybrids'
  series:
  - peak:
      low_value: 1.3751
      low_period: 2014 Q3
      peak_value: 11.0698
      peak_period: 2026 Q2
      latest_value: 11.0698
      latest_period: 2026 Q2
      latest_is_peak: true
      latest_below_peak_by: 0.0
      latest_well_below_peak: false
    unit: '% of privately kept cars'
    points:
    - ci:
      - 1.361305
      - 1.388807
      value: 1.3751
      period: 2014 Q3
    - ci:
      - 1.422743
      - 1.451485
      value: 1.4371
      period: 2014 Q4
    - ci:
      - 1.503542
      - 1.533916
      value: 1.5187
      period: 2015 Q1
    - ci:
      - 1.586839
      - 1.618897
      value: 1.6029
      period: 2015 Q2
    - ci:
      - 1.685108
      - 1.71915
      value: 1.7021
      period: 2015 Q3
    - ci:
      - 1.772944
      - 1.808762
      value: 1.7909
      period: 2015 Q4
    - ci:
      - 1.856916
      - 1.89443
      value: 1.8757
      period: 2016 Q1
    - ci:
      - 1.960132
      - 1.99973
      value: 1.9799
      period: 2016 Q2
    - ci:
      - 2.065182
      - 2.106902
      value: 2.086
      period: 2016 Q3
    - ci:
      - 2.148161
      - 2.191559
      value: 2.1699
      period: 2016 Q4
    - ci:
      - 2.256697
      - 2.302287
      value: 2.2795
      period: 2017 Q1
    - ci:
      - 2.350334
      - 2.397816
      value: 2.3741
      period: 2017 Q2
    - ci:
      - 2.457705
      - 2.507355
      value: 2.4825
      period: 2017 Q3
    - ci:
      - 2.55766
      - 2.60933
      value: 2.5835
      period: 2017 Q4
    - ci:
      - 2.675485
      - 2.729535
      value: 2.7025
      period: 2018 Q1
    - ci:
      - 2.790444
      - 2.846816
      value: 2.8186
      period: 2018 Q2
    - ci:
      - 2.938671
      - 2.998039
      value: 2.9684
      period: 2018 Q3
    - ci:
      - 3.076174
      - 3.138318
      value: 3.1072
      period: 2018 Q4
    - ci:
      - 3.225846
      - 3.291014
      value: 3.2584
      period: 2019 Q1
    - ci:
      - 3.375497
      - 3.443689
      value: 3.4096
      period: 2019 Q2
    - ci:
      - 3.534073
      - 3.605469
      value: 3.5698
      period: 2019 Q3
    - ci:
      - 3.688549
      - 3.763065
      value: 3.7258
      period: 2019 Q4
    - ci:
      - 3.810341
      - 3.887317
      value: 3.8488
      period: 2020 Q1
    - ci:
      - 3.897201
      - 3.975933
      value: 3.9366
      period: 2020 Q2
    - ci:
      - 4.089035
      - 4.171641
      value: 4.1303
      period: 2020 Q3
    - ci:
      - 4.273039
      - 4.359363
      value: 4.3162
      period: 2020 Q4
    - ci:
      - 4.503699
      - 4.594683
      value: 4.5492
      period: 2021 Q1
    - ci:
      - 4.771908
      - 4.86831
      value: 4.8201
      period: 2021 Q2
    - ci:
      - 5.09863
      - 5.201632
      value: 5.1501
      period: 2021 Q3
    - ci:
      - 5.305239
      - 5.412415
      value: 5.3588
      period: 2021 Q4
    - ci:
      - 5.563989
      - 5.676393
      value: 5.6202
      period: 2022 Q1
    - ci:
      - 5.817317
      - 5.934839
      value: 5.8761
      period: 2022 Q2
    - ci:
      - 6.081786
      - 6.20465
      value: 6.1432
      period: 2022 Q3
    - ci:
      - 6.30708
      - 6.434496
      value: 6.3708
      period: 2022 Q4
    - ci:
      - 6.595312
      - 6.72855
      value: 6.6619
      period: 2023 Q1
    - ci:
      - 6.908985
      - 7.048561
      value: 6.9788
      period: 2023 Q2
    - ci:
      - 7.318876
      - 7.466732
      value: 7.3928
      period: 2023 Q3
    - ci:
      - 7.6325
      - 7.786692
      value: 7.7096
      period: 2023 Q4
    - ci:
      - 7.95751
      - 8.118268
      value: 8.0379
      period: 2024 Q1
    - ci:
      - 8.252738
      - 8.41946
      value: 8.3361
      period: 2024 Q2
    - ci:
      - 8.572508
      - 8.74569
      value: 8.6591
      period: 2024 Q3
    - ci:
      - 8.878267
      - 9.057625
      value: 8.9679
      period: 2024 Q4
    - ci:
      - 9.228185
      - 9.414613
      value: 9.3214
      period: 2025 Q1
    - ci:
      - 9.532316
      - 9.724888
      value: 9.6286
      period: 2025 Q2
    - ci:
      - 9.876183
      - 10.075701
      value: 9.9759
      period: 2025 Q3
    - ci:
      - 10.212431
      - 10.418743
      value: 10.3156
      period: 2025 Q4
    - ci:
      - 10.601939
      - 10.816119
      value: 10.709
      period: 2026 Q1
    - ci:
      - 10.959083
      - 11.180479
      value: 11.0698
      period: 2026 Q2
    body_type: Cars
    fuel_type: Hybrid electric (petrol)
    geo_level: region
    geography: London
    notable_moves:
    - kind: rise
      value: 4.5492
      change: 0.233
      period: 2021 Q1
      previous_value: 4.3162
      previous_period: 2020 Q4
    - kind: rise
      value: 4.8201
      change: 0.2709
      period: 2021 Q2
      previous_value: 4.5492
      previous_period: 2021 Q1
    - kind: rise
      value: 5.1501
      change: 0.33
      period: 2021 Q3
      previous_value: 4.8201
      previous_period: 2021 Q2
    - kind: rise
      value: 5.6202
      change: 0.2614
      period: 2022 Q1
      previous_value: 5.3588
      previous_period: 2021 Q4
    - kind: rise
      value: 5.8761
      change: 0.2559
      period: 2022 Q2
      previous_value: 5.6202
      previous_period: 2022 Q1
    - kind: rise
      value: 6.1432
      change: 0.2671
      period: 2022 Q3
      previous_value: 5.8761
      previous_period: 2022 Q2
    - kind: rise
      value: 6.6619
      change: 0.2911
      period: 2023 Q1
      previous_value: 6.3708
      previous_period: 2022 Q4
    - kind: rise
      value: 6.9788
      change: 0.3169
      period: 2023 Q2
      previous_value: 6.6619
      previous_period: 2023 Q1
    - kind: rise
      value: 7.3928
      change: 0.414
      period: 2023 Q3
      previous_value: 6.9788
      previous_period: 2023 Q2
    - kind: rise
      value: 7.7096
      change: 0.3168
      period: 2023 Q4
      previous_value: 7.3928
      previous_period: 2023 Q3
    - kind: rise
      value: 8.0379
      change: 0.3283
      period: 2024 Q1
      previous_value: 7.7096
      previous_period: 2023 Q4
    - kind: rise
      value: 8.3361
      change: 0.2982
      period: 2024 Q2
      previous_value: 8.0379
      previous_period: 2024 Q1
    - kind: rise
      value: 8.6591
      change: 0.323
      period: 2024 Q3
      previous_value: 8.3361
      previous_period: 2024 Q2
    - kind: rise
      value: 8.9679
      change: 0.3088
      period: 2024 Q4
      previous_value: 8.6591
      previous_period: 2024 Q3
    - kind: rise
      value: 9.3214
      change: 0.3535
      period: 2025 Q1
      previous_value: 8.9679
      previous_period: 2024 Q4
    - kind: rise
      value: 9.6286
      change: 0.3072
      period: 2025 Q2
      previous_value: 9.3214
      previous_period: 2025 Q1
    - kind: rise
      value: 9.9759
      change: 0.3473
      period: 2025 Q3
      previous_value: 9.6286
      previous_period: 2025 Q2
    - kind: rise
      value: 10.3156
      change: 0.3397
      period: 2025 Q4
      previous_value: 9.9759
      previous_period: 2025 Q3
    - kind: rise
      value: 10.709
      change: 0.3934
      period: 2026 Q1
      previous_value: 10.3156
      previous_period: 2025 Q4
    - kind: rise
      value: 11.0698
      change: 0.3608
      period: 2026 Q2
      previous_value: 10.709
      previous_period: 2026 Q1
    typical_yearly_change: 0.1156
    moves_shared_by_most_geographies:
    - of: 9
      groups: 9
      period: 2014 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2015 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2015 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2015 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2015 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2016 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2016 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2016 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2016 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2017 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2017 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2017 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2017 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2018 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2018 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2018 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2018 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2019 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2019 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2019 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2019 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2020 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2020 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2020 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2020 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2021 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2021 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2021 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2021 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2022 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2022 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2022 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2022 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2023 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2023 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2023 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2023 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2024 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2024 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2024 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2024 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2025 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2025 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2025 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2025 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2026 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2026 Q2
      direction: rise
  - peak:
      low_value: 0.282
      low_period: 2014 Q3
      peak_value: 7.9884
      peak_period: 2026 Q2
      latest_value: 7.9884
      latest_period: 2026 Q2
      latest_is_peak: true
      latest_below_peak_by: 0.0
      latest_well_below_peak: false
    unit: '% of privately kept cars'
    points:
    - ci:
      - 0.279159
      - 0.284799
      value: 0.282
      period: 2014 Q3
    - ci:
      - 0.284076
      - 0.289814
      value: 0.2869
      period: 2014 Q4
    - ci:
      - 0.2955
      - 0.30147
      value: 0.2985
      period: 2015 Q1
    - ci:
      - 0.307165
      - 0.313371
      value: 0.3103
      period: 2015 Q2
    - ci:
      - 0.320948
      - 0.327432
      value: 0.3242
      period: 2015 Q3
    - ci:
      - 0.339501
      - 0.346359
      value: 0.3429
      period: 2015 Q4
    - ci:
      - 0.357884
      - 0.365114
      value: 0.3615
      period: 2016 Q1
    - ci:
      - 0.381347
      - 0.389051
      value: 0.3852
      period: 2016 Q2
    - ci:
      - 0.40346
      - 0.41161
      value: 0.4075
      period: 2016 Q3
    - ci:
      - 0.42097
      - 0.429474
      value: 0.4252
      period: 2016 Q4
    - ci:
      - 0.457846
      - 0.467096
      value: 0.4625
      period: 2017 Q1
    - ci:
      - 0.489409
      - 0.499297
      value: 0.4944
      period: 2017 Q2
    - ci:
      - 0.527083
      - 0.537731
      value: 0.5324
      period: 2017 Q3
    - ci:
      - 0.56578
      - 0.57721
      value: 0.5715
      period: 2017 Q4
    - ci:
      - 0.607586
      - 0.61986
      value: 0.6137
      period: 2018 Q1
    - ci:
      - 0.658891
      - 0.672201
      value: 0.6655
      period: 2018 Q2
    - ci:
      - 0.719881
      - 0.734425
      value: 0.7272
      period: 2018 Q3
    - ci:
      - 0.780636
      - 0.796406
      value: 0.7885
      period: 2018 Q4
    - ci:
      - 0.86379
      - 0.88124
      value: 0.8725
      period: 2019 Q1
    - ci:
      - 0.949991
      - 0.969183
      value: 0.9596
      period: 2019 Q2
    - ci:
      - 1.050763
      - 1.071991
      value: 1.0614
      period: 2019 Q3
    - ci:
      - 1.152847
      - 1.176137
      value: 1.1645
      period: 2019 Q4
    - ci:
      - 1.245317
      - 1.270475
      value: 1.2579
      period: 2020 Q1
    - ci:
      - 1.322895
      - 1.349621
      value: 1.3363
      period: 2020 Q2
    - ci:
      - 1.503497
      - 1.533871
      value: 1.5187
      period: 2020 Q3
    - ci:
      - 1.654899
      - 1.688331
      value: 1.6716
      period: 2020 Q4
    - ci:
      - 1.820796
      - 1.85758
      value: 1.8392
      period: 2021 Q1
    - ci:
      - 2.044101
      - 2.085395
      value: 2.0647
      period: 2021 Q2
    - ci:
      - 2.321392
      - 2.368288
      value: 2.3448
      period: 2021 Q3
    - ci:
      - 2.564159
      - 2.615961
      value: 2.5901
      period: 2021 Q4
    - ci:
      - 2.801437
      - 2.858031
      value: 2.8297
      period: 2022 Q1
    - ci:
      - 2.998792
      - 3.059374
      value: 3.0291
      period: 2022 Q2
    - ci:
      - 3.160865
      - 3.224721
      value: 3.1928
      period: 2022 Q3
    - ci:
      - 3.369282
      - 3.437348
      value: 3.4033
      period: 2022 Q4
    - ci:
      - 3.657948
      - 3.731846
      value: 3.6949
      period: 2023 Q1
    - ci:
      - 3.975559
      - 4.055873
      value: 4.0157
      period: 2023 Q2
    - ci:
      - 4.331066
      - 4.418562
      value: 4.3748
      period: 2023 Q3
    - ci:
      - 4.589453
      - 4.682169
      value: 4.6358
      period: 2023 Q4
    - ci:
      - 4.875581
      - 4.974077
      value: 4.9248
      period: 2024 Q1
    - ci:
      - 5.174598
      - 5.279136
      value: 5.2269
      period: 2024 Q2
    - ci:
      - 5.523675
      - 5.635265
      value: 5.5795
      period: 2024 Q3
    - ci:
      - 5.804839
      - 5.922109
      value: 5.8635
      period: 2024 Q4
    - ci:
      - 6.131904
      - 6.25578
      value: 6.1938
      period: 2025 Q1
    - ci:
      - 6.474228
      - 6.60502
      value: 6.5396
      period: 2025 Q2
    - ci:
      - 6.837144
      - 6.975268
      value: 6.9062
      period: 2025 Q3
    - ci:
      - 7.131641
      - 7.275715
      value: 7.2037
      period: 2025 Q4
    - ci:
      - 7.496702
      - 7.64815
      value: 7.5724
      period: 2026 Q1
    - ci:
      - 7.908481
      - 8.068249
      value: 7.9884
      period: 2026 Q2
    body_type: Cars
    fuel_type: Other fuel types
    geo_level: region
    geography: London
    notable_moves:
    - kind: rise
      value: 2.0647
      change: 0.2255
      period: 2021 Q2
      previous_value: 1.8392
      previous_period: 2021 Q1
    - kind: rise
      value: 2.3448
      change: 0.2801
      period: 2021 Q3
      previous_value: 2.0647
      previous_period: 2021 Q2
    - kind: rise
      value: 2.5901
      change: 0.2453
      period: 2021 Q4
      previous_value: 2.3448
      previous_period: 2021 Q3
    - kind: rise
      value: 2.8297
      change: 0.2396
      period: 2022 Q1
      previous_value: 2.5901
      previous_period: 2021 Q4
    - kind: rise
      value: 3.0291
      change: 0.1994
      period: 2022 Q2
      previous_value: 2.8297
      previous_period: 2022 Q1
    - kind: rise
      value: 3.4033
      change: 0.2105
      period: 2022 Q4
      previous_value: 3.1928
      previous_period: 2022 Q3
    - kind: rise
      value: 3.6949
      change: 0.2916
      period: 2023 Q1
      previous_value: 3.4033
      previous_period: 2022 Q4
    - kind: rise
      value: 4.0157
      change: 0.3208
      period: 2023 Q2
      previous_value: 3.6949
      previous_period: 2023 Q1
    - kind: rise
      value: 4.3748
      change: 0.3591
      period: 2023 Q3
      previous_value: 4.0157
      previous_period: 2023 Q2
    - kind: rise
      value: 4.6358
      change: 0.261
      period: 2023 Q4
      previous_value: 4.3748
      previous_period: 2023 Q3
    - kind: rise
      value: 4.9248
      change: 0.289
      period: 2024 Q1
      previous_value: 4.6358
      previous_period: 2023 Q4
    - kind: rise
      value: 5.2269
      change: 0.3021
      period: 2024 Q2
      previous_value: 4.9248
      previous_period: 2024 Q1
    - kind: rise
      value: 5.5795
      change: 0.3526
      period: 2024 Q3
      previous_value: 5.2269
      previous_period: 2024 Q2
    - kind: rise
      value: 5.8635
      change: 0.284
      period: 2024 Q4
      previous_value: 5.5795
      previous_period: 2024 Q3
    - kind: rise
      value: 6.1938
      change: 0.3303
      period: 2025 Q1
      previous_value: 5.8635
      previous_period: 2024 Q4
    - kind: rise
      value: 6.5396
      change: 0.3458
      period: 2025 Q2
      previous_value: 6.1938
      previous_period: 2025 Q1
    - kind: rise
      value: 6.9062
      change: 0.3666
      period: 2025 Q3
      previous_value: 6.5396
      previous_period: 2025 Q2
    - kind: rise
      value: 7.2037
      change: 0.2975
      period: 2025 Q4
      previous_value: 6.9062
      previous_period: 2025 Q3
    - kind: rise
      value: 7.5724
      change: 0.3687
      period: 2026 Q1
      previous_value: 7.2037
      previous_period: 2025 Q4
    - kind: rise
      value: 7.9884
      change: 0.416
      period: 2026 Q2
      previous_value: 7.5724
      previous_period: 2026 Q1
    typical_yearly_change: 0.0916
    moves_shared_by_most_geographies:
    - of: 9
      groups: 6
      period: 2015 Q1
      direction: rise
    - of: 9
      groups: 8
      period: 2015 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2015 Q3
      direction: rise
    - of: 9
      groups: 6
      period: 2015 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2016 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2016 Q2
      direction: rise
    - of: 9
      groups: 8
      period: 2016 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2017 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2017 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2017 Q3
      direction: rise
    - of: 9
      groups: 8
      period: 2017 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2018 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2018 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2018 Q3
      direction: rise
    - of: 9
      groups: 8
      period: 2018 Q4
      direction: rise
    - of: 9
      groups: 8
      period: 2019 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2019 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2019 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2019 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2020 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2020 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2020 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2020 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2021 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2021 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2021 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2021 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2022 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2022 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2022 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2022 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2023 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2023 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2023 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2023 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2024 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2024 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2024 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2024 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2025 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2025 Q2
      direction: rise
    - of: 9
      groups: 9
      period: 2025 Q3
      direction: rise
    - of: 9
      groups: 9
      period: 2025 Q4
      direction: rise
    - of: 9
      groups: 9
      period: 2026 Q1
      direction: rise
    - of: 9
      groups: 9
      period: 2026 Q2
      direction: rise
  - peak:
      low_value: 14.3302
      low_period: 2026 Q2
      peak_value: 30.5857
      peak_period: 2018 Q2
      latest_value: 14.3302
      latest_period: 2026 Q2
      latest_is_peak: false
      latest_below_peak_by: 16.2555
      latest_well_below_peak: true
    unit: '% of privately kept cars'
    points:
    - ci:
      - 25.298853
      - 25.809941
      value: 25.5544
      period: 2014 Q3
    - ci:
      - 25.774729
      - 26.295431
      value: 26.0351
      period: 2014 Q4
    - ci:
      - 26.307024
      - 26.83848
      value: 26.5728
      period: 2015 Q1
    - ci:
      - 26.801338
      - 27.34278
      value: 27.0721
      period: 2015 Q2
    - ci:
      - 27.282069
      - 27.833221
      value: 27.5576
      period: 2015 Q3
    - ci:
      - 27.715839
      - 28.275755
      value: 27.9958
      period: 2015 Q4
    - ci:
      - 28.132444
      - 28.700776
      value: 28.4166
      period: 2016 Q1
    - ci:
      - 28.611219
      - 29.189223
      value: 28.9002
      period: 2016 Q2
    - ci:
      - 29.029529
      - 29.615985
      value: 29.3228
      period: 2016 Q3
    - ci:
      - 29.350837
      - 29.943783
      value: 29.6473
      period: 2016 Q4
    - ci:
      - 29.564786
      - 30.162054
      value: 29.8634
      period: 2017 Q1
    - ci:
      - 29.808645
      - 30.410839
      value: 30.1097
      period: 2017 Q2
    - ci:
      - 30.005104
      - 30.611268
      value: 30.3082
      period: 2017 Q3
    - ci:
      - 30.158808
      - 30.768076
      value: 30.4634
      period: 2017 Q4
    - ci:
      - 30.223462
      - 30.834036
      value: 30.5287
      period: 2018 Q1
    - ci:
      - 30.279838
      - 30.891552
      value: 30.5857
      period: 2018 Q2
    - ci:
      - 30.13178
      - 30.740502
      value: 30.4361
      period: 2018 Q3
    - ci:
      - 29.923997
      - 30.528523
      value: 30.2263
      period: 2018 Q4
    - ci:
      - 29.435481
      - 30.030137
      value: 29.7328
      period: 2019 Q1
    - ci:
      - 28.995836
      - 29.58161
      value: 29.2887
      period: 2019 Q2
    - ci:
      - 28.562181
      - 29.139195
      value: 28.8507
      period: 2019 Q3
    - ci:
      - 28.171069
      - 28.740181
      value: 28.4556
      period: 2019 Q4
    - ci:
      - 27.80253
      - 28.364198
      value: 28.0834
      period: 2020 Q1
    - ci:
      - 27.471198
      - 28.026172
      value: 27.7487
      period: 2020 Q2
    - ci:
      - 26.850269
      - 27.392699
      value: 27.1215
      period: 2020 Q3
    - ci:
      - 26.338042
      - 26.870124
      value: 26.6041
      period: 2020 Q4
    - ci:
      - 25.710529
      - 26.229933
      value: 25.9702
      period: 2021 Q1
    - ci:
      - 24.884386
      - 25.3871
      value: 25.1357
      period: 2021 Q2
    - ci:
      - 23.386686
      - 23.859144
      value: 23.6229
      period: 2021 Q3
    - ci:
      - 22.534239
      - 22.989477
      value: 22.7619
      period: 2021 Q4
    - ci:
      - 21.959625
      - 22.403253
      value: 22.1814
      period: 2022 Q1
    - ci:
      - 21.478256
      - 21.91216
      value: 21.6952
      period: 2022 Q2
    - ci:
      - 21.027798
      - 21.452602
      value: 21.2402
      period: 2022 Q3
    - ci:
      - 20.430253
      - 20.842985
      value: 20.6366
      period: 2022 Q4
    - ci:
      - 19.534959
      - 19.929605
      value: 19.7323
      period: 2023 Q1
    - ci:
      - 18.532604
      - 18.907
      value: 18.7198
      period: 2023 Q2
    - ci:
      - 17.085463
      - 17.430623
      value: 17.258
      period: 2023 Q3
    - ci:
      - 16.533611
      - 16.867623
      value: 16.7006
      period: 2023 Q4
    - ci:
      - 16.139815
      - 16.465871
      value: 16.3028
      period: 2024 Q1
    - ci:
      - 15.85542
      - 16.175732
      value: 16.0156
      period: 2024 Q2
    - ci:
      - 15.564893
      - 15.879335
      value: 15.7221
      period: 2024 Q3
    - ci:
      - 15.33756
      - 15.64741
      value: 15.4925
      period: 2024 Q4
    - ci:
      - 15.107469
      - 15.412671
      value: 15.2601
      period: 2025 Q1
    - ci:
      - 14.904005
      - 15.205097
      value: 15.0546
      period: 2025 Q2
    - ci:
      - 14.680836
      - 14.977418
      value: 14.8291
      period: 2025 Q3
    - ci:
      - 14.515094
      - 14.808328
      value: 14.6617
      period: 2025 Q4
    - ci:
      - 14.335639
      - 14.625247
      value: 14.4804
      period: 2026 Q1
    - ci:
      - 14.186891
      - 14.473495
      value: 14.3302
      period: 2026 Q2
    body_type: Cars
    fuel_type: Diesel
    geo_level: region
    geography: London
    notable_moves:
    - kind: fall
      value: 23.6229
      change: -1.5128
      period: 2021 Q3
      previous_value: 25.1357
      previous_period: 2021 Q2
    - kind: fall
      value: 22.7619
      change: -0.861
      period: 2021 Q4
      previous_value: 23.6229
      previous_period: 2021 Q3
    - kind: fall
      value: 19.7323
      change: -0.9043
      period: 2023 Q1
      previous_value: 20.6366
      previous_period: 2022 Q4
    - kind: fall
      value: 18.7198
      change: -1.0125
      period: 2023 Q2
      previous_value: 19.7323
      previous_period: 2023 Q1
    - kind: fall
      value: 17.258
      change: -1.4618
      period: 2023 Q3
      previous_value: 18.7198
      previous_period: 2023 Q2
    typical_yearly_change: 0.4185
    moves_shared_by_most_geographies:
    - of: 9
      groups: 7
      period: 2026 Q2
      direction: fall
  source:
    url: https://www.gov.uk/government/statistical-data-sets/vehicle-licensing-statistics-data-tables
    name: Vehicle licensing statistics (VEH tables)
    licence: Open Government Licence v3.0
    publisher: Department for Transport
  caveats:
  - The figures count licensed cars kept by private individuals at the end of each quarter (Q2 means the
    end of June). Company cars are left out because DfT counts them at the company's registered address,
    which for leasing and rental fleets is often far from where the cars are used.
  - Cars are counted at the registered keeper's postcode, which is not necessarily where the car is driven.
  - In this table DfT groups fuel as petrol, diesel, petrol hybrid and other fuel types. Other fuel types
    covers every fuel not in the first three, including fully electric cars; DfT publishes electric vehicles
    in more detail in a separate table (VEH0142).
  - The series here starts in 2014 Q3, the first quarter the table covers the whole UK, including Northern
    Ireland.
  - The data shows which cars are licensed, not how far they are driven or why people chose them.
  - These are administrative counts, not survey estimates, so they have no margin of error; changes smaller
    than 2% are treated as no real change.
  findings:
  - ci:
    - 10.959083
    - 11.180479
    id: 37d4b438-fc17-40e5-9a43-3b1b80238b74
    unit: '% of privately kept cars'
    group: London
    value: 11.0698
    median: 7.49
    period: 2026 Q2
    related:
    - numbers:
        unit: '% of privately kept cars'
        group: London
        change: 9.6947
        end_ci:
        - 10.959083
        - 11.180479
        improved: true
        start_ci:
        - 1.361305
        - 1.388807
        direction: rise
        end_value: 11.0698
        good_news: true
        end_period: 2026 Q2
        group_code: E12000007
        pct_change: 705.04
        change_rank: 1
        change_unit: percentage points
        start_value: 1.3751
        start_period: 2014 Q3
        median_change: 7.0267
        groups_compared: 9
        higher_is_better: true
        typical_yearly_change: 0.1156
      detector: biggest_change
      title_hint: 'London: biggest rise in Cars, Hybrid electric (petrol), region'
    detector: outlier
    robust_z: 6.02
    slice_by:
    - body_type
    - fuel_type
    - geo_level
    body_type: Cars
    direction: above
    fuel_type: Hybrid electric (petrol)
    geo_level: region
    good_news: true
    group_code: E12000007
    nearest_ci:
    - 7.881515
    - 8.040737
    title_hint: London stands out (above the rest) in Cars, Hybrid electric (petrol), region
    effect_size: 6.0203
    score_parts:
      effect: 0.8576
      surprise: 1.0
      freshness: 0.9945
      relatability: 0.6
    gap_to_median: 3.5798
    nearest_group: North West
    nearest_value: 7.9611
    gap_to_nearest: 3.1087
    groups_compared: 9
    higher_is_better: true
  - ci:
    - 7.908481
    - 8.068249
    id: ae8217d3-b87f-475a-a7d5-f16e9a488eaf
    unit: '% of privately kept cars'
    group: London
    value: 7.9884
    median: 5.381
    period: 2026 Q2
    related:
    - numbers:
        unit: '% of privately kept cars'
        group: London
        change: 7.7064
        end_ci:
        - 7.908481
        - 8.068249
        improved: true
        start_ci:
        - 0.279159
        - 0.284799
        direction: rise
        end_value: 7.9884
        good_news: true
        end_period: 2026 Q2
        group_code: E12000007
        pct_change: 2732.96
        change_rank: 1
        change_unit: percentage points
        start_value: 0.282
        start_period: 2014 Q3
        median_change: 5.2091
        groups_compared: 9
        higher_is_better: true
        typical_yearly_change: 0.0916
      detector: biggest_change
      title_hint: 'London: biggest rise in Cars, Other fuel types, region'
    detector: outlier
    robust_z: 5.8
    slice_by:
    - body_type
    - fuel_type
    - geo_level
    body_type: Cars
    direction: above
    fuel_type: Other fuel types
    geo_level: region
    good_news: true
    group_code: E12000007
    nearest_ci:
    - 5.994046
    - 6.115138
    title_hint: London stands out (above the rest) in Cars, Other fuel types, region
    effect_size: 5.8047
    score_parts:
      effect: 0.853
      surprise: 1.0
      freshness: 0.9945
      relatability: 0.6
    gap_to_median: 2.6074
    nearest_group: South East
    nearest_value: 6.0546
    gap_to_nearest: 1.9338
    groups_compared: 9
    higher_is_better: true
  - ci:
    - 14.186891
    - 14.473495
    id: 5ce09c20-32eb-47af-8eb7-3c3fdab50766
    unit: '% of privately kept cars'
    group: London
    value: 14.3302
    median: 31.4603
    period: 2026 Q2
    related:
    - numbers:
        unit: '% of privately kept cars'
        group: London
        change: -11.2242
        end_ci:
        - 14.186891
        - 14.473495
        improved: true
        start_ci:
        - 25.298853
        - 25.809941
        direction: fall
        end_value: 14.3302
        good_news: true
        end_period: 2026 Q2
        group_code: E12000007
        pct_change: -43.92
        change_rank: 1
        change_unit: percentage points
        start_value: 25.5544
        start_period: 2014 Q3
        median_change: -2.1552
        groups_compared: 9
        higher_is_better: false
        typical_yearly_change: 0.4185
      detector: biggest_change
      title_hint: 'London: biggest fall in Cars, Diesel, region'
    detector: outlier
    robust_z: -4.51
    slice_by:
    - body_type
    - fuel_type
    - geo_level
    body_type: Cars
    direction: below
    fuel_type: Diesel
    geo_level: region
    good_news: true
    group_code: E12000007
    nearest_ci:
    - 25.686757
    - 26.205681
    title_hint: London stands out (below the rest) in Cars, Diesel, region
    effect_size: 4.5127
    score_parts:
      effect: 0.8186
      surprise: 0.9025
      freshness: 0.9945
      relatability: 0.6
    gap_to_median: -17.1302
    nearest_group: South East
    nearest_value: 25.9462
    gap_to_nearest: 11.616
    groups_compared: 9
    higher_is_better: false
  geo_level: region
  geography: London
  good_news: true
  chart_facts:
    end: 2026 Q2
    group: London
    start: 2014 Q3
    groups_rising: 9
    groups_falling: 0
    groups_compared: 9
    supported_checks:
    - kind: highest
      group: London
      detail: London 11.0698 vs next North West 7.9611 in 2026 Q2, clear
      period: 2026 Q2
    - end: 2026 Q2
      kind: all_rise
      start: 2014 Q3
      detail: 9 of 9 groups rose
    - end: 2026 Q2
      kind: biggest_rise
      group: London
      start: 2014 Q3
      detail: London 9.6947, next 7.5326
  data_period:
    last: 2026 Q2
    first: 2014 Q3
  exact_counts: true
  precision_pct: 2.0
more_charts:
- x: period
  y: value
  end: 2026 Q2
  type: slope
  start: 2014 Q3
  title: 'Petrol hybrid share: start and end of the series'
  series: geography
  yLabel: '% of privately kept cars'
  highlight: London
  annotation: Every region rose; London rose the most.
- x: period
  y: value
  type: map
  title: Petrol hybrid share of private cars by region
  period: 2026 Q2
  series: geography
  yLabel: '% of privately kept cars'
  highlight: London
period: 2014 Q3 to 2026 Q2
---

London is pulling ahead of the rest of England in petrol hybrid cars. According to the Department for Transport's Vehicle licensing statistics (VEH tables), 11.07% of cars kept by private individuals in London were petrol hybrids at the end of 2026 Q2. That is the highest share of England's nine regions. The data covers every quarter from 2014 Q3 to 2026 Q2.

In 2014 Q3, when the series starts, the figure was 1.38%. It has gone up in every quarter since, and the latest value is also the peak. The rise of 9.69 percentage points is the biggest of the nine regions.

The climb has quickened over time. Early on, quarterly gains were small: the share went from 1.38% in 2014 Q3 to 1.44% in 2014 Q4. From 2021 onwards the steps grew larger, for example from 4.32% in 2020 Q4 to 4.55% in 2021 Q1, and from 6.98% in 2023 Q2 to 7.39% in 2023 Q3, a rise of 0.41 percentage points in a single quarter. The latest step, from 10.71% in 2026 Q1 to 11.07% in 2026 Q2, added 0.36 percentage points. Between 2014 Q4 and 2026 Q2, the hybrid share went up in every region in every quarter, so this is a shared direction across England rather than a shift confined to the capital.

## How it compares

All nine regions saw their petrol hybrid share rise between 2014 Q3 and 2026 Q2. The North West is next behind London at 7.96%, followed by the South East at 7.63% and Yorkshire and The Humber at 7.55%. The East stands at 7.49%, the middle value of the nine regions. The South West has 6.12%, and the East Midlands 6.95%. The North East started at just 0.27% in 2014 Q3 and now stands at 7.09%, so other regions have also changed a great deal, even if London remains clearly ahead.

Other fuel types, a group that includes fully electric cars, show a similar pattern in London. Their share in London rose from 0.28% in 2014 Q3 to 7.99% in 2026 Q2, up 7.71 percentage points, and London is clearly ahead of the South East at 6.05%.

Diesel tells the opposite story. London's diesel share climbed from 25.55% in 2014 Q3 to a peak of 30.59% in 2018 Q2, then turned down. By 2026 Q2 it was 14.33%, well below that peak by 16.26 percentage points. Notable quarterly falls came in 2021 Q3, down 1.51 percentage points, and in 2023 Q3, down 1.46 percentage points. London's diesel share is now far under the typical region's 31.46%, and the nearest region, the South East, is at 25.95%. In 2026 Q2, diesel shares fell in 7 of the 9 regions.

## What the data can't tell us

These figures are administrative counts of licensed cars, not survey estimates, so they have no margin of error, and DfT treats changes smaller than 2.00% as no real change. They count cars kept by private individuals at the end of each quarter, so Q2 means the end of June. Company cars are left out, because DfT records them at the company's registered address, which for leasing and rental fleets is often far from where the cars are used. Cars are also counted at the registered keeper's postcode, which is not necessarily where they are driven.

The fuel groups are broad. In this table DfT splits cars into petrol, diesel, petrol hybrid and other fuel types, and the last group covers every other fuel, including fully electric cars. DfT publishes electric vehicles in more detail in a separate table.

The series starts in 2014 Q3 because that is the first quarter the table covers the whole UK, including Northern Ireland. Finally, the data shows which cars are licensed, not how far they are driven or why people chose them. It cannot tell us what lies behind London's lead, whether that is local policy, the kind of journeys people make, the price of cars or something else.
