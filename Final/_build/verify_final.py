"""Check the Final deliverables against the brief. Needs pymupdf and python-pptx (pip install pymupdf python-pptx).
Writes Final/Evidence/final_package_check.json."""
import json, re, sys, urllib.request
from pathlib import Path
import pymupdf
from pptx import Presentation

FINAL = Path(__file__).resolve().parents[1]
out = {}
rep = pymupdf.open(FINAL / 'Report' / 'Group_Team_ICT_FinalProject.pdf')
out['report'] = {'pages': rep.page_count, 'all_portrait_A4': all(round(p.rect.width) == 595 and round(p.rect.height) == 842 for p in rep),
                 'pages_12_to_20': 12 <= rep.page_count <= 20}
text = ''.join(p.get_text() for p in rep)
m = re.search(r'Executive summary: (\d+) words', text)
out['report']['exec_summary_words_declared'] = int(m.group(1)) if m else None
heads = ['Executive summary', 'Problem and evidence', 'Users and requirements', 'As-built architecture', 'Data', 'Security',
         'Interface', 'Testing', 'Data analysis', 'Smart extension', 'Limitations and future work', 'References', 'Individual contribution statements']
out['report']['sections_found'] = {h: h.lower() in text.lower() for h in heads}
cfg = json.loads((FINAL / '_build' / 'report_config.json').read_text(encoding='utf-8'))
wc = lambda t: len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’./@%-]*", t))
out['statements_words'] = {s['name']: wc(s['text']) for s in cfg['statements']}
out['statements_confirmed'] = cfg['statements_confirmed']

deck = pymupdf.open(FINAL / 'Presentation' / 'Group_Team_ICT_FinalPresentation.pdf')
out['presentation_pdf'] = {'pages': deck.page_count, 'all_16x9_landscape': all(abs(p.rect.width / p.rect.height - 16 / 9) < 0.01 for p in deck)}
prs = Presentation(FINAL / 'Presentation' / 'Group_Team_ICT_FinalPresentation.pptx')
notes = []
for i, s in enumerate(prs.slides, 1):
    n = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ''
    notes.append({'slide': i, 'notes_chars': len(n), 'speaker': (re.search(r'SPEAKER: ([A-Za-z ]+?)(?: \(|·|$)', n) or [None, None])[1]})
out['presentation_notes'] = notes
times = {}
for line in (FINAL / 'Presentation' / 'Speaker_Timing.md').read_text(encoding='utf-8').splitlines():
    m = re.match(r'\| (\d+) \|.*\| (\*\*)?(Zhanzhol|Daniil|Daulet)', line)
    t = re.search(r'\| (\d):(\d\d) \| \d+:\d\d \|', line)
    if m and t:
        times[m.group(3)] = times.get(m.group(3), 0) + int(t.group(1)) * 60 + int(t.group(2))
out['speaking_seconds'] = times
out['total_minutes'] = round(sum(times.values()) / 60, 2)

links = ['https://github.com/zondbebox/SE-2623_Endterm', 'https://github.com/zondbebox/SE-2623_Endterm/commit/a7e5c749095e63e1cff1280b95279ca8bae6e447',
         'https://github.com/zondbebox/SE-2623_Endterm/blob/main/Campus_Lost_Found/app.py', 'https://github.com/zondbebox/SE-2623_Endterm/blob/main/Campus_Lost_Found/stage2_features.py',
         'https://github.com/zondbebox/SE-2623_Endterm/blob/main/Campus_Lost_Found/static/locker.js', 'https://github.com/zondbebox/SE-2623_Endterm/blob/main/Campus_Lost_Found/backend/analytics.py',
         'https://www.youtube.com/oembed?url=https://youtu.be/76M3hSqR-7w&format=json', 'https://adilet.zan.kz/rus/docs/Z1300000094', 'https://adilet.zan.kz/eng/docs/Z1300000094',
         'https://adilet.zan.kz/rus/docs/Z2600000326', 'https://www.gov.kz/org/maidd', 'https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app',
         'https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc', 'https://www.sqlite.org/whentouse.html', 'https://www.w3.org/TR/WCAG22/',
         'https://www.nngroup.com/articles/ten-usability-heuristics/', 'https://flask.palletsprojects.com/en/stable/web-security/',
         'https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html',
         'https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html']
res = {}
for u in links:
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (link check)'}), timeout=25)
        res[u] = r.status
    except Exception as e:
        res[u] = repr(e)[:80]
out['links'] = res
out['screenshots'] = len(list((FINAL / 'Evidence' / 'screenshots').glob('*.png')))
(FINAL / 'Evidence' / 'final_package_check.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(out, indent=1, ensure_ascii=False))
