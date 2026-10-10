# Test fixtures: ALL DATA HERE IS FAKE

These files are small, hand-made and invented. They copy the *shape* of real publisher files
(column names, suppression markers, title/footnote rows) but none of the numbers are real.
Never use them for a story.

| File | Mimics |
|---|---|
| `fake_ons_wellbeing.csv` | ONS API CSV for `wellbeing-local-authority` (long format, `v4_3` value column, `[c]`/`[x]` markers) |
| `fake_messy.csv` | A badly formatted spreadsheet export: title row, `£`/`%`/comma numbers, markers, a repeated header row, wide year columns, mixed date formats, a footnote |

XLSX fixtures are built at test time in `conftest.py` (so no binary files are committed).
