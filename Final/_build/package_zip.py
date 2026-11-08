"""Zip the Final package (Final/ + root README.md) without build caches, secrets or databases."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'SE-2623_Final_Package.zip'
SKIP_DIRS = {'node_modules', '.edge-print-profile', '__pycache__'}
SKIP_SUFFIX = {'.sqlite3', '.key', '.env', '.jsonl'}
n = 0
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(ROOT / 'README.md', 'SE-2623_Final/README.md')
    # application files changed or added for the Final (Microsoft sign-in), so the package shows the exact code
    for rel in ('microsoft_auth.py', 'test_microsoft_auth.py', 'app.py', 'templates/login.html', 'templates/base.html', 'TESTS.bat', 'TESTS.sh'):
        z.write(ROOT / 'Campus_Lost_Found' / rel, 'SE-2623_Final/Campus_Lost_Found_Final_changes/' + rel)
        n += 1
    for p in sorted((ROOT / 'Final').rglob('*')):
        if p.is_dir() or SKIP_DIRS & set(p.parts) or p.suffix.lower() in SKIP_SUFFIX:
            continue
        z.write(p, 'SE-2623_Final/Final/' + p.relative_to(ROOT / 'Final').as_posix())
        n += 1
print(OUT, n + 1, 'files', round(OUT.stat().st_size / 1e6, 1), 'MB')
