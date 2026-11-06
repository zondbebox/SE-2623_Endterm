"""Administrator overview and read-only lists for the local campus database."""
from contextlib import closing
import re

from flask import abort, render_template, request

from backend.db import get_connection
from stage2_features import admin_required


PAGE_SIZE = 20
NOTICE_COLUMNS = ('SELECT n.id,n.title,n.type,n.status,n.created_at,'
                  'c.name AS category,u.email FROM notices n '
                  'JOIN categories c ON c.id=n.category_id '
                  'JOIN users u ON u.id=n.owner_id ')


def _keyword():
    value = request.args.get('q', '')
    if len(value) > 120:
        abort(400, description='Keep your search to 120 characters or fewer.')
    return value.strip()


def _pagination(total):
    raw = request.args.get('page', '1')
    if not re.fullmatch(r'[0-9]+', raw) or raw.strip('0') == '':
        abort(400, description='Choose a positive whole page number.')
    # Reject enormous input before int conversion or an SQLite OFFSET binding.
    if len(raw) > 18:
        abort(404, description='This page is not available.')
    page = int(raw)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if page > pages:
        abort(404, description='This page is not available.')
    return {'page': page, 'pages': pages, 'total': total,
            'start': (page - 1) * PAGE_SIZE + 1 if total else 0,
            'end': min(page * PAGE_SIZE, total), 'offset': (page - 1) * PAGE_SIZE}


def register_admin_panel(app):
    @app.get('/admin')
    @admin_required
    def admin_dashboard():
        with closing(get_connection(app.config['DATABASE'], read_only=True)) as conn:
            conn.execute('BEGIN')
            counts = dict(conn.execute(
                "SELECT COUNT(*) AS notices,COALESCE(SUM(status='open'),0) AS open,"
                "COALESCE(SUM(status='returned'),0) AS returned FROM notices").fetchone())
            counts['users'] = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            latest = conn.execute(NOTICE_COLUMNS +
                                  'ORDER BY n.created_at DESC,n.id DESC LIMIT 6').fetchall()
        return render_template('admin_dashboard.html', counts=counts, latest=latest)

    @app.get('/admin/notices')
    @admin_required
    def admin_notices():
        q = _keyword()
        status = request.args.get('status', '')
        if status not in ('', 'open', 'returned'):
            abort(400, description='Choose Open, Returned, or All statuses.')
        conditions, params = [], []
        if q:
            # Literal substring matching treats % and _ as text, not wildcards.
            conditions.append('instr(lower(n.title),lower(?)) > 0')
            params.append(q)
        if status:
            conditions.append('n.status=?')
            params.append(status)
        where = 'WHERE ' + ' AND '.join(conditions) + ' ' if conditions else ''
        with closing(get_connection(app.config['DATABASE'], read_only=True)) as conn:
            conn.execute('BEGIN')
            total = conn.execute('SELECT COUNT(*) FROM notices n ' + where, params).fetchone()[0]
            paging = _pagination(total)
            notices = conn.execute(NOTICE_COLUMNS + where +
                'ORDER BY n.created_at DESC,n.id DESC LIMIT ? OFFSET ?',
                (*params, PAGE_SIZE, paging['offset'])).fetchall()
        return render_template('admin_notices.html', notices=notices,
                               q=q, status=status, paging=paging)

    @app.get('/admin/users')
    @admin_required
    def admin_users():
        q = _keyword()
        where = 'WHERE instr(lower(u.email),lower(?)) > 0 ' if q else ''
        params = [q] if q else []
        with closing(get_connection(app.config['DATABASE'], read_only=True)) as conn:
            conn.execute('BEGIN')
            total = conn.execute('SELECT COUNT(*) FROM users u ' + where, params).fetchone()[0]
            paging = _pagination(total)
            users = conn.execute(
                'SELECT u.id,u.email,u.role,'
                '(SELECT COUNT(*) FROM notices n WHERE n.owner_id=u.id) AS notice_count '
                'FROM users u ' + where + 'ORDER BY u.email,u.id LIMIT ? OFFSET ?',
                (*params, PAGE_SIZE, paging['offset'])).fetchall()
        return render_template('admin_users.html', users=users, q=q, paging=paging)
