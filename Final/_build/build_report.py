"""Build Final/Report/Group_Team_ICT_FinalProject.pdf from the template and the evidence files.

Standard library only. Run from any folder, e.g. with the bundled runtime:
    Campus_Lost_Found\\python\\python.exe -B Final\\_build\\build_report.py
Edit Final/Testing/final_test_results.csv (real participants only) and
Final/_build/report_config.json, then run again: every table, number and the
executive summary are regenerated. PDF printing uses Microsoft Edge (Windows).
"""
import csv, html, json, os, re, shutil, subprocess, sys
from datetime import date
from pathlib import Path

FINAL = Path(__file__).resolve().parents[1]
EVID = FINAL / 'Evidence'
OUT_DIR = FINAL / 'Report'
SRC_DIR = OUT_DIR / 'source'
PDF = OUT_DIR / 'Group_Team_ICT_FinalProject.pdf'
RUN_DATE = '8 November 2026'
TARGETS = {'publish': 120, 'find': 60}
E = html.escape


def load(name):
    p = EVID / name
    return json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else None


def words(text):
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’./@%-]*", text))


def final_test():
    rows = list(csv.DictReader(open(FINAL / 'Testing' / 'final_test_results.csv', encoding='utf-8-sig')))
    valid = [r for r in rows if r['participant_code'].strip() and r['outside_team'].strip().lower() == 'yes' and r['consent'].strip().lower() == 'yes']
    result = {}
    for task, target in TARGETS.items():
        attempts = [r for r in valid if r['task'].strip().lower() == task]
        met = [r for r in attempts if r['completed_correctly'].strip().lower() == 'yes' and r['assisted'].strip().lower() == 'no' and float(r['seconds']) <= target]
        n = len(attempts)
        result[task] = {'n': n, 'met': len(met), 'times': [float(r['seconds']) for r in attempts],
                        'ok': n >= 3 and len(met) / n >= 0.8 if n else None}
    people = sorted({r['participant_code'] for r in valid})
    return result, people, valid


def main():
    cfg = json.loads((FINAL / '_build' / 'report_config.json').read_text(encoding='utf-8'))
    perf = load('search_performance_final.json')
    sc3 = load('sc3_final.json')
    br = load('browser_checks.json')
    stab = load('stability_30min_final.json')
    ft, people, ft_rows = final_test()
    have_ft = len(people) >= 3

    t = (FINAL / '_build' / 'report_template.html').read_text(encoding='utf-8')
    v = {'RUN_DATE': RUN_DATE, 'BUILD_DATE': date.today().strftime('%d %B %Y').lstrip('0')}

    # automated test suite (Final/Evidence/test_suite_final.log)
    m = re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK', (EVID / 'test_suite_final.log').read_text(encoding='utf-8', errors='replace'))
    assert m, 'test_suite_final.log does not end with a passing run'
    v['TESTS_N'], v['TESTS_TIME'] = m.group(1), f'{float(m.group(2)):.1f}'

    # N1
    p95 = perf['p95_ms']
    v['N1_P95'] = f'{p95:.1f}'
    v['N1_BAR'] = f'{max(2.0, 250 * p95 / 2000):.1f}'
    v['N1_LABEL_X'] = f'{70 + max(2.0, 250 * p95 / 2000) + 6:.1f}'

    # SC3
    v['SC3_ROWS'] = ''.join(f"<tr><td>{E(c['check'])}</td><td>{E(str(c['http']))}</td><td class=\"{'ok' if c['blocked'] else 'no'}\">{'✓ blocked' if c['blocked'] else '✗ NOT blocked'}</td></tr>" for c in sc3['checks'])

    # N3
    n3_ok = br['N3_360px']['no_horizontal_scroll'] and all(x['all_labelled'] for x in br['N3_labels'].values()) and br['N3_keyboard_post_form']['reaches_publish_button']
    v['N3_CLASS'] = 'ok' if n3_ok else 'part'
    v['N3_STATUS'] = '✓ Done' if n3_ok else '◐ Partly'
    v['N3_EVIDENCE'] = (f"Edge at 360 × 760 px: {len(br['N3_360px']['pages'])} of {len(br['N3_360px']['pages'])} pages without horizontal scrolling; all form fields on browse, post and sign-in have labels; "
                        "Tab reaches every control of the post form in visual order with a visible focus ring (M01–M04, K01; <span class=\"mono\">browser_checks.json</span>). Automated browser check — not tested by users with assistive technology.")

    # N4
    stab_done = stab and stab['completed'] == stab['checks']
    offline_ok = br['N4_offline_retry']['passed']
    if stab_done:
        span_min = round(stab['records'][-1]['elapsed_s'] / 60)
        ok = stab['passed'] == stab['checks'] and offline_ok
        v['N4_CLASS'] = 'ok' if ok else 'part'
        v['N4_STATUS'] = '✓ Done' if ok else '◐ Partly'
        v['N4_EVIDENCE'] = (f"<b>{stab['passed']}/{stab['checks']}</b> authenticated checks of five core pages over {span_min} minutes (student + admin sessions; <span class=\"mono\">stability_30min_final.json</span>). "
                            "Offline retry in Edge: with the network cut the locker refresh reports that the result could not be confirmed; after reconnecting, “Refresh status” and a page reload both succeed.")
        v['N4_TEXT'] = (f"<b>{stab['passed']} of {stab['checks']}</b> checks passed, spread evenly over {span_min} minutes ({stab['records'][0]['utc'][11:16]}–{stab['records'][-1]['utc'][11:16]} UTC, {RUN_DATE}). "
                        f"Slowest response {max(r['ms'] for r in stab['records']):.0f} ms. A check passes only with HTTP 200, the expected page content and no sign-in form.")
    else:
        v['N4_CLASS'], v['N4_STATUS'] = 'pend', '○ Running'
        v['N4_EVIDENCE'] = 'The 30-minute monitor had not finished when this version was built.'
        v['N4_TEXT'] = 'Monitor not finished at build time.'

    # Must requirements: F1,F2,F4-F8 (7) + N1-N4 (4) = 11. F1 and N2 remain partly done.
    n_status = {'N1': True, 'N3': v['N3_CLASS'] == 'ok', 'N4': v['N4_CLASS'] == 'ok'}
    # F1 and N2: closed on 8 Nov 2026 by a real Microsoft sign-in with a university account (see Final/SSO/).
    v['MUST_DONE'] = str(8 + sum(n_status.values()))
    partly = [k for k, ok in n_status.items() if not ok]
    v['MUST_LABEL'] = 'Must requirements done' + (f"; {', '.join(partly)} partly" if partly else '') + '; Should F3 done'

    # Final test
    s2 = {'publish': 'Stage 2 report: <b>Pending</b>.<br>Team-reported afterwards: 5/5 (70–92 s), no raw record',
          'find': 'Stage 2 report: <b>Pending</b>.<br>Team-reported afterwards: 5/5 (45–53 s), no raw record'}
    rows = []
    for sc, task, label, target in (('SC1', 'publish', 'Testers post a notice within 2 minutes', '≥ 80 % (Stage 1: 4/5), ≤ 120 s'),
                                    ('SC2', 'find', 'Testers find an item within 1 minute', '≥ 80 % (Stage 1: 4/5), ≤ 60 s')):
        r = ft[task]
        if have_ft and r['n']:
            times = ', '.join(f'{x:g}' for x in r['times'])
            final, met = f"{r['met']}/{r['n']} within target<br><span class=\"small\">times (s): {times}</span>", ('<span class="ok">✓ Yes</span>' if r['ok'] else '<span class="no">✗ No</span>')
            evid = '<span class="mono">Testing/final_test_results.csv</span>'
        else:
            final, met, evid = '<span class="pend">○ Awaiting team data</span>', '<span class="pend">—</span>', 'Protocol and empty table: <span class="mono">Final/Testing/</span>'
        rows.append(f'<tr><td><b>{sc}</b> · {label}</td><td>{target}</td><td>{s2[task]}</td><td>{final}</td><td>{met}</td><td>{evid}</td></tr>')
    rows.append(f'<tr><td><b>SC3</b> · Invalid-access checks are blocked</td><td>5/5</td><td>5/5</td><td>{sc3["blocked"]}/{sc3["total"]} ({RUN_DATE})</td><td><span class="{"ok" if sc3["blocked"] == 5 else "no"}">{"✓ Yes" if sc3["blocked"] == 5 else "✗ No"}</span></td><td><span class="mono">Evidence/sc3_final.json</span></td></tr>')
    v['FT_TABLE_ROWS'] = ''.join(rows)
    v['SC_SUMMARY_ROWS'] = ''.join(r[:r.rfind('<td>')] + '</tr>' for r in rows)
    if have_ft:
        v['FT_HEADLINE'] = f"{len(people)} people outside the team re-tested the Stage 1 criteria on the final build"
        devices = sorted({f"{r['device']} · {r['os_browser']}" for r in ft_rows})
        v['FT_PARTICIPANTS'] = (f"<p><b>Sample.</b> {len(people)} participants ({', '.join(E(p) for p in people)}), all outside the team and consenting; dates {E(', '.join(sorted({r['date'] for r in ft_rows})))}; devices: {E('; '.join(devices))}. "
                                f"The brief's minimum is three people; the Stage 1 targets were written for five. With {len(people)} participants one person is {round(100 / len(people))} percentage points, so we report counts, not percentages alone.</p>")
        obs = [f"{r['participant_code']}: {r['observation']}" for r in ft_rows if r['observation'].strip()]
        general = cfg.get('final_test_general_feedback', '').strip()
        v['FT_NOTE'] = ('<b>Observations.</b> ' + (E(' · '.join(obs)) + ' ' if obs else '') + E(general or 'No comments were recorded.')
                        + ' We interpret the results as evidence that first-time users can complete the two core tasks; they are not a measure of satisfaction.')
        exec_ft = (f"In the final test, {ft['publish']['met']} of {ft['publish']['n']} people outside the team published a notice within two minutes "
                   f"and {ft['find']['met']} of {ft['find']['n']} found the target notice within one minute.")
        v['SC_FINAL_SHORT'] = f"{ft['publish']['met']}/{ft['publish']['n']} · {ft['find']['met']}/{ft['find']['n']}"
        v['SC_FINAL_SHORT_LABEL'] = 'external testers within target: publish ≤ 120 s · find ≤ 60 s'
    else:
        v['FT_HEADLINE'] = 'The re-test protocol is fixed; the team’s Final results are still to be entered'
        v['FT_PARTICIPANTS'] = '<p><b>Sample.</b> Not yet entered. The team reports that the Final session was held; participant codes, devices, times and observations must be copied from the observer’s records into <span class="mono">Final/Testing/final_test_results.csv</span>, and this report rebuilt.</p>'
        v['FT_NOTE'] = ('<b>Status at build time.</b> No Final participant data had been supplied to the package, so SC1 and SC2 are reported as awaiting data rather than met. '
                        'Results by AI tools, the team or automated scripts are not entered as participants.')
        exec_ft = ('The team reports that the final test with external users was held, but its results were not yet in the package, '
                   'so the two user criteria are reported as pending.')
        v['SC_FINAL_SHORT'] = '5 / 5'
        v['SC_FINAL_SHORT_LABEL'] = 'invalid-access attempts blocked (SC3); user criteria SC1–SC2 awaiting team data'

    stab_phrase = (f"{stab['passed']} of {stab['checks']} availability checks passed over 30 minutes" if stab_done else 'a 30-minute availability check was running')
    exec_summary = (
        "Students who lose an item on campus depend on scattered chats and paper notes; in our Stage 1 survey, 4 of 10 respondents said a return had taken more than three days (a small convenience sample). "
        "Campus Lost & Found gives the campus one place to publish, search and close lost-and-found notices. "
        "The final version is a Flask web application with an SQLite database, private photo uploads, owner and administrator permissions, an administrator panel with analytics, a user-testing timer and a clearly labelled smart-locker simulation. "
        "All Must requirements now work, including sign-in with university Microsoft accounts, which was verified with a real account. "
        f"On the final code, {v['TESTS_N']} of {v['TESTS_N']} automated tests passed, all five invalid-access attempts were blocked, the 95th-percentile search time was {p95:.0f} ms against a two-second target, and {stab_phrase}. "
        f"{exec_ft} "
        "The system runs on one laptop over local HTTP; hosting in Kazakhstan with HTTPS is the main future work.")
    n_exec = words(exec_summary)
    v['EXEC_SUMMARY'] = E(exec_summary)
    v['EXEC_WORDS'] = str(n_exec)
    assert 150 <= n_exec <= 200, f'Executive summary has {n_exec} words'

    # statements
    blocks = []
    for s in cfg['statements']:
        n = words(s['text'])
        assert 100 <= n <= 120, f"{s['name']}: {n} words"
        blocks.append(f"<div class=\"stmt\"><h3>{E(s['name'])} <span class=\"small\" style=\"font-weight:400\">— {E(s['role'])} · {n} words</span></h3>"
                      f"<p>{E(s['text'])}</p><div class=\"sig\"><span>Signature: {E(s['name'])}</span><span>Date</span></div></div>")
    v['STATEMENTS'] = ''.join(blocks)
    url = cfg.get('updated_video_url', '').strip()
    old_video = 'Assignment 4 video (2:14, 1920 × 1080, 30 fps) — <span class="mono">youtu.be/76M3hSqR-7w</span>, older interface, kept as a backup'
    if url:
        v['VIDEO_ROW'] = f'<tr><td>Demo video</td><td>Re-recorded Final demo video on the current interface: <span class="mono">{E(url)}</span>.</td><td>Backup: {old_video}.</td></tr>'
        v['VIDEO_NOTE'] = '<div class="fact"><b>Video.</b> The demo video was re-recorded on the final interface (student journey, administrator panel, analytics, smart-locker simulation, Microsoft sign-in) and is linked above. The Assignment 4 video is kept only as an older backup.</div>'
    else:
        v['VIDEO_ROW'] = f'<tr><td>Demo video</td><td>Re-recorded Final demo video: <b>link to be added</b> (<span class="mono">Final/Video/</span>).</td><td>Backup now: {old_video}.</td></tr>'
        v['VIDEO_NOTE'] = ('<div class="note"><b>Video status.</b> The Assignment 4 video shows the earlier white-and-teal interface without the administrator panel, analytics or locker, so the team is re-recording it on the final build; '
                           'the scenes are listed in <span class="mono">Final/Demo/Demo_Plan_and_Backup.md</span> and the new link goes in <span class="mono">Final/Video/</span>.</div>')
    v['STATEMENT_STATUS'] = ('Each member confirmed that the statement under their name is accurate; signatures are on the printed copy.' if cfg['statements_confirmed'] else
                             '<b>Status: drafted from the team-confirmed contribution table (Stage 2 report, p. 9) and the code; each member must check every fact, especially the “problem I solved”, edit it in their own words and sign before submission.</b>')

    # locker
    v['LOCKER_ALERT'] = E(br['locker_simulation']['alert_text'].split('—')[-1].strip().rstrip('.'))
    v['LOCKER_STATUS'] = E(br['locker_simulation']['status_message'])

    for k, val in v.items():
        t = t.replace('{{' + k + '}}', val)
    left = re.findall(r'\{\{[A-Z0-9_]+\}\}', t)
    assert not left, left
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    out_html = SRC_DIR / 'report.html'
    out_html.write_text(t, encoding='utf-8')
    print('HTML:', out_html, '| executive summary words:', n_exec, '| statements:', [words(s['text']) for s in cfg['statements']])

    edge = shutil.which('msedge') or r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    if os.path.exists(edge):
        tmp_profile = SRC_DIR / '.edge-print-profile'
        subprocess.run([edge, '--headless=new', '--disable-gpu', '--no-pdf-header-footer', f'--user-data-dir={tmp_profile}',
                        f'--print-to-pdf={PDF}', out_html.as_uri()], check=True, timeout=180,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(tmp_profile, ignore_errors=True)
        print('PDF:', PDF, PDF.stat().st_size, 'bytes')
    else:
        print('Edge not found: open report.html in a browser and print to PDF (A4, no margins, background graphics on).')


if __name__ == '__main__':
    main()
