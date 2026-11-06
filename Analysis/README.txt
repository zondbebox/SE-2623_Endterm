ENDTERM ANALYSIS - SYNTHETIC TEACHING DATA

Frozen dataset: 122 notices, 30 October 2026 at 10:34 UTC.
Database SHA-256 and all counts are recorded in stats.json.
The three SQL files are the exact queries used by the application dashboard.
PNG figures are 300 dpi; SVG figures are editable vector graphics.
CSV files contain aggregate labels and counts; spreadsheet formula prefixes are escaped.
interpretation_en.txt contains the 150-200 word interpretation; stats.json records its word count.

Reproduce with Python 3 in this Analysis directory:
  python -m pip install -r requirements-analysis.txt
  python reproduce_analysis.py
The script opens Analysis/frozen_campus.sqlite3 read-only by default.
This frozen copy reproduces the report even after live notices change.
Do not replace the working database or delete participant notices to reproduce the charts.
The application itself does not require Matplotlib.
