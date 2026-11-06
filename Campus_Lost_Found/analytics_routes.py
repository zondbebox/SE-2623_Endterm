"""Administrator-only aggregate dashboard and spreadsheet-safe CSV export."""
from contextlib import closing
import csv
from functools import wraps
import io
import math

from flask import Response, abort, g, redirect, render_template, url_for

from backend.analytics import build_analytics
from backend.db import get_connection


def _csv_cell(value):
    """Prevent spreadsheet formula execution, including leading controls/spaces."""
    if not isinstance(value, str):
        return value
    if value.startswith(('\t', '\r', '\n')) or value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def _bars(rows, first, second):
    maximum = max((row['total'] for row in rows), default=0) or 1
    return [{**row, 'y': 18 + index * 38,
             'first_width': round(row[first] * 440 / maximum, 2),
             'second_width': round(row[second] * 440 / maximum, 2),
             'second_x': round(260 + row[first] * 440 / maximum, 2)}
            for index, row in enumerate(rows)]


def _weekly_chart(rows):
    maximum = max((max(row['lost'], row['found']) for row in rows), default=0) or 1
    points = []
    for index, row in enumerate(rows):
        points.append({**row,
            'x': round(65 + index * 680 / max(1, len(rows) - 1), 2),
            'lost_y': round(250 - row['lost'] * 190 / maximum, 2),
            'found_y': round(250 - row['found'] * 190 / maximum, 2)})
    stride = max(1, math.ceil(len(points) / 7))
    ticks = [row for index, row in enumerate(points)
             if index % stride == 0 or index == len(points) - 1]
    return {'rows': points, 'ticks': ticks, 'maximum': maximum,
            'lost_points': ' '.join(f"{r['x']},{r['lost_y']}" for r in points),
            'found_points': ' '.join(f"{r['x']},{r['found_y']}" for r in points)}


def register_analytics(app):
    def admin_required(view):
        @wraps(view)
        def guarded(*args, **kwargs):
            if not getattr(g, 'user', None):
                return redirect(url_for('login'))
            if g.user['role'] != 'admin':
                abort(403, description='Administrator access is required.')
            return view(*args, **kwargs)
        return guarded

    def snapshot():
        with closing(get_connection(app.config['DATABASE'], read_only=True)) as connection:
            # A read transaction keeps the counts and all three series consistent.
            connection.execute('BEGIN')
            return build_analytics(connection)

    @app.get('/admin/analytics')
    @admin_required
    def analytics():
        data = snapshot()
        return render_template('analytics.html', data=data,
            category_bars=_bars(data['category_series'], 'open', 'returned'),
            location_bars=_bars(data['location_series'], 'lost', 'found'),
            weekly=_weekly_chart(data['weekly_series']))

    @app.get('/admin/analytics.csv')
    @admin_required
    def analytics_csv():
        data = snapshot()
        stream = io.StringIO(newline='')
        writer = csv.writer(stream)
        writer.writerow(['source', 'question', 'group', 'metric', 'count'])
        for series, group_key, metrics in (
            ('category', 'category', ('open', 'returned', 'total')),
            ('location', 'location', ('lost', 'found', 'total')),
            ('weekly', 'label', ('lost', 'found', 'total')),
        ):
            for row in data[series + '_series']:
                for metric in metrics:
                    writer.writerow([_csv_cell(value) for value in
                        (data['source_label'], series, row[group_key], metric, row[metric])])
        return Response(stream.getvalue(), mimetype='text/csv', headers={
            'Content-Disposition': 'attachment; filename="campus-synthetic-analytics.csv"',
            'Cache-Control': 'no-store',
        })
