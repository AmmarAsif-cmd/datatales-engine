# Boundaries for map charts

Ultra-generalised (BUC) boundaries from the ONS Open Geography Portal, fetched once by
`scripts/fetch-boundaries.mjs` and committed. The build never downloads anything.

| File                     | Areas                                                 | ONS layer                                                        |
| ------------------------ | ----------------------------------------------------- | ---------------------------------------------------------------- |
| `nations.json`           | 4 UK nations                                          | Countries (December 2023) UK BUC                                 |
| `regions.json`           | 9 English regions + Wales, Scotland, Northern Ireland | Regions (December 2023) EN BUC, Countries (December 2023) UK BUC |
| `local-authorities.json` | 374 local authority districts                         | Local Authority Districts (December 2022) UK BUC V2              |

LAD December 2022 is used because it matches every local authority code in the ONS wellbeing
data (later vintages lack the pre-2023 Cumbria, North Yorkshire and Somerset districts).

Coordinates: British National Grid (EPSG:27700) in units of 100 m, rings as flat
`[x0, y0, x1, y1, ...]` arrays.

Source: Office for National Statistics licensed under the Open Government Licence v.3.0.
Contains OS data © Crown copyright and database right 2024.
