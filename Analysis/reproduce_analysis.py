"""Reproduce the frozen Endterm charts and aggregates without changing the app.

Run with Python 3 and matplotlib installed:
    python reproduce_analysis.py

The distributed copy resides in Endterm/Analysis beside the exact SQL queries.
The working copy resides in work/endterm. All database access is read-only.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile

SCRIPT = Path(__file__).resolve()
if SCRIPT.parent.name == 'Analysis':
    ENDTERM = SCRIPT.parent.parent
else:
    ENDTERM = SCRIPT.parents[2] / 'outputs' / 'Endterm'
    dependencies = SCRIPT.parent / 'chart_dependencies'
    if dependencies.exists():
        sys.path.insert(0, str(dependencies))

MPL_CACHE = tempfile.TemporaryDirectory(prefix='campus-analysis-mpl-')
os.environ.setdefault('MPLCONFIGDIR', MPL_CACHE.name)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np

QUERY_FILES = {
    'category': '01_category_backlog.sql',
    'location': '02_location_types.sql',
    'weekly': '03_weekly_events.sql',
}
COLORS = {'ink': '#193747', 'muted': '#536873', 'grid': '#DDE6E5',
          'open': '#9C6419', 'returned': '#23776C',
          'lost': '#325B8B', 'found': '#B46C20'}


def safe_csv(value):
    if isinstance(value, str) and (
        value.startswith(('\t', '\r', '\n'))
        or value.lstrip().startswith(('=', '+', '-', '@'))
    ):
        return "'" + value
    return value


def read_snapshot(database, query_directory, expected_count):
    queries = {name: (query_directory / filename).read_text(encoding='utf-8').strip()
               for name, filename in QUERY_FILES.items()}
    conn = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA query_only=ON')
        if conn.execute('PRAGMA journal_mode').fetchone()[0] == 'wal':
            raise RuntimeError('Use a frozen, checkpointed database in DELETE journal mode for a single-file SHA.')
        conn.execute('BEGIN')
        counts = dict(conn.execute("""SELECT COUNT(*) AS notices,
            SUM(status='open') AS open, SUM(status='returned') AS returned,
            SUM(type='lost') AS lost, SUM(type='found') AS found,
            MIN(event_date) AS earliest_event_date, MAX(event_date) AS latest_event_date
            FROM notices""").fetchone())
        if counts['notices'] != expected_count:
            raise RuntimeError(f"Expected {expected_count} frozen notices; found {counts['notices']}. No output written.")
        rows = {name: [dict(row) for row in conn.execute(sql)] for name, sql in queries.items()}
        counts['categories'] = conn.execute('SELECT COUNT(*) FROM categories').fetchone()[0]
        counts['locations'] = len(rows['location'])
        counts['weeks'] = len(rows['weekly'])
        sha = hashlib.sha256(database.read_bytes()).hexdigest()
    finally:
        conn.close()
    for series in rows.values():
        if sum(row['total'] for row in series) != counts['notices']:
            raise RuntimeError('Aggregate reconciliation failed.')
    if counts['open'] + counts['returned'] != counts['notices']:
        raise RuntimeError('Status reconciliation failed.')
    if counts['lost'] + counts['found'] != counts['notices']:
        raise RuntimeError('Type reconciliation failed.')
    return counts, rows, queries, sha


def write_csv(path, rows):
    if not rows:
        raise RuntimeError('The frozen analysis expects nonempty aggregates.')
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['source', *rows[0]])
        writer.writeheader()
        writer.writerows({'source': 'synthetic', **{key: safe_csv(value) for key, value in row.items()}}
                        for row in rows)


def setup_style():
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 11,
        'axes.labelcolor': COLORS['ink'], 'text.color': COLORS['ink'],
        'xtick.color': COLORS['muted'], 'ytick.color': COLORS['ink'],
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.spines.left': False, 'axes.spines.bottom': False,
        'axes.axisbelow': True, 'svg.fonttype': 'none',
        'savefig.facecolor': 'white', 'figure.facecolor': 'white',
    })


def layout(title, subtitle, source, note, height=7.6, left=.29):
    fig, ax = plt.subplots(figsize=(11.4, height))
    fig.subplots_adjust(left=left, right=.94, top=.78, bottom=.18)
    fig.text(.055, .95, title, fontsize=20, weight='bold', va='top')
    fig.text(.055, .897, subtitle, fontsize=11.3, va='top', color=COLORS['muted'])
    fig.text(.055, .072, source, fontsize=9, color=COLORS['muted'])
    fig.text(.055, .043, note, fontsize=9, color=COLORS['muted'])
    return fig, ax


def save_chart(fig, out, stem):
    for suffix in ('png', 'svg'):
        fig.savefig(out / (stem + '.' + suffix), dpi=300)
    plt.close(fig)


def category_chart(rows, out, source, count):
    fig, ax = layout('Open notice backlog by category',
        f'Current status of {count} synthetic teaching notices; categories ordered by open count',
        source, 'Returned is a current status. These data do not measure actual campus recovery outcomes.')
    y = np.arange(len(rows))
    opened = np.array([r['open'] for r in rows])
    returned = np.array([r['returned'] for r in rows])
    ax.barh(y, opened, .63, color=COLORS['open'], label='Open')
    ax.barh(y, returned, .63, left=opened, color=COLORS['returned'], label='Returned')
    for i, row in enumerate(rows):
        if row['open']:
            ax.text(row['open'] / 2, i, str(row['open']), color='white', ha='center', va='center', weight='bold')
        if row['returned']:
            ax.text(row['open'] + row['returned'] / 2, i, str(row['returned']), color='white', ha='center', va='center', weight='bold')
        ax.text(row['total'] + .2, i, str(row['total']) + ' all', va='center', fontsize=10)
    ax.set_yticks(y, [r['category'] for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, max(r['total'] for r in rows) + 2)
    ax.set_xlabel('Number of notices', labelpad=12)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
    ax.grid(axis='x', color=COLORS['grid'], linewidth=.7)
    ax.tick_params(axis='both', length=0, pad=8)
    ax.legend(loc='lower left', bbox_to_anchor=(0, 1.015), ncol=2, frameon=False)
    save_chart(fig, out, '01_category_backlog')


def location_chart(rows, out, source, count):
    fig, ax = layout('Lost and found notices by location',
        f'{count} synthetic notices across {len(rows)} saved location labels; open and returned statuses included',
        source, 'Locations are free-form labels. A notice is not necessarily a unique item; counts are not loss rates.',
        height=9.4, left=.29)
    y = np.arange(len(rows))
    ax.barh(y - .18, [r['lost'] for r in rows], .31, color=COLORS['lost'], label='Lost')
    ax.barh(y + .18, [r['found'] for r in rows], .31, color=COLORS['found'], label='Found')
    for i, row in enumerate(rows):
        for metric, offset in [('lost', -.18), ('found', .18)]:
            if row[metric]:
                ax.text(row[metric] + .12, i + offset, str(row[metric]), va='center', fontsize=10)
    ax.set_yticks(y, [r['location'] for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, max(max(r['lost'], r['found']) for r in rows) + 1.2)
    ax.set_xlabel('Number of notices', labelpad=12)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
    ax.grid(axis='x', color=COLORS['grid'], linewidth=.7)
    ax.tick_params(axis='both', length=0, pad=8)
    ax.legend(loc='lower left', bbox_to_anchor=(0, 1.015), ncol=2, frameon=False)
    save_chart(fig, out, '02_location_types')


def weekly_chart(rows, out, source, count):
    fig, ax = layout('Notice counts by event-date week',
        f'{count} synthetic notices; complete Monday-Sunday bins, including weeks with zero matching notices',
        source, 'Event date is not publication, processing or return time. Boundary weeks may have partial date coverage.',
        height=7.4, left=.10)
    fig.subplots_adjust(bottom=.25)
    x = np.arange(len(rows))
    for metric, marker, line in [('lost', 'o', '-'), ('found', 's', '--')]:
        values = [r[metric] for r in rows]
        ax.plot(x, values, color=COLORS[metric], marker=marker, linestyle=line,
                linewidth=2.2, markersize=7, label=metric.capitalize())
        for i, value in enumerate(values):
            other_metric = 'found' if metric == 'lost' else 'lost'
            above = value > rows[i][other_metric] or (value == rows[i][other_metric] and metric == 'lost')
            shift = 11 if above else -17
            ax.annotate(str(value), (i, value), xytext=(0, shift),
                        textcoords='offset points', ha='center', color=COLORS[metric],
                        fontsize=10, weight='bold')
    labels = [datetime.fromisoformat(r['week_start']).strftime('%d %b\n%Y') for r in rows]
    ax.set_xticks(x, labels)
    ax.set_ylim(-1.5, max(max(r['lost'], r['found']) for r in rows) + 2)
    ax.set_yticks(range(0, 15, 3))
    ax.set_xlabel('Event-date week start (Monday)', labelpad=12)
    ax.set_ylabel('Number of notices', labelpad=10)
    ax.grid(axis='y', color=COLORS['grid'], linewidth=.7)
    ax.tick_params(axis='both', length=0, pad=8)
    ax.legend(loc='lower left', bbox_to_anchor=(0, 1.015), ncol=2, frameon=False)
    save_chart(fig, out, '03_weekly_events')


def interpretation(counts, rows):
    by_category = {row['category']: row for row in rows['category']}
    library = next(row for row in rows['location'] if row['location'] == 'Library study area')
    electronics = by_category['Electronics']['returned']
    drinkware = by_category['Drinkware']['returned']
    # The prose is for this frozen dataset; fail rather than silently reuse its
    # narrative after someone edits rows but happens to preserve the row count.
    if not (sum(r['open'] == 12 for r in rows['category']) == 8
            and by_category['Electronics']['open'] == 0
            and by_category['Drinkware']['open'] == 0
            and by_category['Electronics']['total'] == electronics
            and by_category['Drinkware']['total'] == drinkware
            and rows['location'][0]['location'] == 'Library study area'
            and [r['week_start'] for r in rows['weekly'] if r['total'] == 21]
                == ['2026-09-07', '2026-09-14', '2026-09-21', '2026-09-28']
            and max(r['total'] for r in rows['weekly']) == 21):
        raise RuntimeError('The data no longer match the frozen interpretation; review its narrative first.')
    text = (
        f"The frozen dataset contains {counts['notices']} synthetic notices: {counts['open']} open and "
        f"{counts['returned']} marked returned, comprising {counts['lost']} lost and {counts['found']} found notices. "
        "Eight categories each have 12 open notices; Electronics and Drinkware have none. "
        f"The generator strongly shapes this pattern: all {electronics} Electronics notices and all {drinkware} "
        "Drinkware notices are marked returned. It cannot establish that these categories are easier to recover.\n\n"
        f"Library study area has the largest location total, with {library['total']} notices "
        f"({library['lost']} lost and {library['found']} found). Locations are free-form labels, so "
        "\"Library study area\" and \"Library, second floor\" remain separate groups. Normalising location "
        "choices would make future comparisons more consistent. Notice counts also do not identify unique "
        "physical items or account for how many people use each location.\n\n"
        "Weekly totals reach 21 in four consecutive September weeks. This reflects the seed schedule and "
        "later demonstration edits, not observed campus demand. Weeks are grouped by item event date, "
        "not publication, processing or return time; boundary weeks have partial date coverage. These "
        "aggregates verify the dashboard and suggest interface improvements, while real service evaluation "
        "requires independent observations."
    )
    words = len(text.split())
    if not 150 <= words <= 200:
        raise RuntimeError(f'Interpretation must contain 150-200 words; found {words}.')
    return text, words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ENDTERM / 'Analysis/frozen_campus.sqlite3')
    parser.add_argument('--output', type=Path, default=ENDTERM / 'Analysis')
    parser.add_argument('--freeze-utc', default='2026-10-30T10:34:00Z')
    parser.add_argument('--expected-count', type=int, default=122)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    counts, rows, queries, database_sha = read_snapshot(args.database, args.output, args.expected_count)
    body, word_count = interpretation(counts, rows)
    freeze = datetime.fromisoformat(args.freeze_utc.replace('Z', '+00:00'))
    source = (f"Source: delivered campus.sqlite3 | {counts['notices']} synthetic notices | "
              f"Frozen {freeze.strftime('%d %b %Y, %H:%M UTC')}")
    setup_style()
    category_chart(rows['category'], args.output, source, counts['notices'])
    location_chart(rows['location'], args.output, source, counts['notices'])
    weekly_chart(rows['weekly'], args.output, source, counts['notices'])
    for name, series in rows.items():
        write_csv(args.output / (name + '_aggregates.csv'), series)
    combined = []
    for name, group, metrics in [('category', 'category', ('open','returned','total')),
                                ('location', 'location', ('lost','found','total')),
                                ('weekly', 'label', ('lost','found','total'))]:
        for row in rows[name]:
            for metric in metrics:
                combined.append({'question': name, 'group': row[group], 'metric': metric, 'count': row[metric]})
    write_csv(args.output / 'all_aggregates.csv', combined)
    (args.output / 'interpretation_en.txt').write_text(body + '\n', encoding='utf-8')
    stats = {
        'source_label': 'synthetic', 'database_file': 'Campus_Lost_Found/data/campus.sqlite3',
        'database_sha256': database_sha, 'freeze_utc': args.freeze_utc,
        'generated_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'counts': counts, 'category_series': rows['category'],
        'location_series': rows['location'], 'weekly_series': rows['weekly'],
        'interpretation': body, 'interpretation_word_count': word_count,
        'interpretation_word_count_method': 'Whitespace-delimited words (Python str.split).',
        'queries': {name: {'filename': QUERY_FILES[name], 'sql': sql,
                          'sha256': hashlib.sha256((args.output / QUERY_FILES[name]).read_bytes()).hexdigest()}
                    for name, sql in queries.items()},
        'checks': {'all_three_aggregate_totals_equal_notice_count': True,
                   'status_and_type_totals_equal_notice_count': True,
                   'database_read_only': True},
        'limits': ['Synthetic data and demonstration edits are not observed campus behaviour.',
                   'Returned is current status, not measured recovery time.',
                   'The deterministic generator creates category and location bias.',
                   'Location labels are free form; equivalent places may appear separately.',
                   'Weekly bins use event_date, include zero weeks, and may have partial boundary coverage.'],
        'reproduction': {'python': sys.version.split()[0], 'matplotlib': matplotlib.__version__,
                         'numpy': np.__version__, 'command': 'python reproduce_analysis.py'},
    }
    (args.output / 'stats.json').write_text(json.dumps(stats, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (args.output / 'requirements-analysis.txt').write_text(
        f'matplotlib=={matplotlib.__version__}\nnumpy=={np.__version__}\n', encoding='utf-8')
    delivered_script = args.output / 'reproduce_analysis.py'
    if SCRIPT != delivered_script.resolve():
        shutil.copyfile(SCRIPT, delivered_script)
    (args.output / 'README.txt').write_text(
        'ENDTERM ANALYSIS - SYNTHETIC TEACHING DATA\n\n'
        'Frozen dataset: 122 notices, 30 October 2026 at 10:34 UTC.\n'
        'Database SHA-256 and all counts are recorded in stats.json.\n'
        'The three SQL files are the exact queries used by the application dashboard.\n'
        'PNG figures are 300 dpi; SVG figures are editable vector graphics.\n'
        'CSV files contain aggregate labels and counts; spreadsheet formula prefixes are escaped.\n'
        'interpretation_en.txt contains the 150-200 word interpretation; stats.json records its word count.\n\n'
        'Reproduce with Python 3 in this Analysis directory:\n'
        '  python -m pip install -r requirements-analysis.txt\n'
        '  python reproduce_analysis.py\n'
        'The script opens Analysis/frozen_campus.sqlite3 read-only by default.\n'
        'This frozen copy reproduces the report even after live notices change.\n'
        'Do not replace the working database or delete participant notices to reproduce the charts.\n'
        'The application itself does not require Matplotlib.\n', encoding='utf-8')
    print(json.dumps({'database_sha256': database_sha, 'counts': counts,
                      'interpretation_word_count': word_count, 'output': str(args.output)}, indent=2))


if __name__ == '__main__':
    main()
