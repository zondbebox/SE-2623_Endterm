"""Read-only summaries of synthetic teaching notices; no personal fields."""

CATEGORY_SQL = """SELECT c.id AS category_id, c.name AS category,
       COUNT(n.id) AS total,
       SUM(CASE WHEN n.status = 'open' THEN 1 ELSE 0 END) AS open,
       SUM(CASE WHEN n.status = 'returned' THEN 1 ELSE 0 END) AS returned
FROM categories AS c
LEFT JOIN notices AS n ON n.category_id = c.id
GROUP BY c.id, c.name
ORDER BY open DESC, total DESC, c.name COLLATE NOCASE, c.id;"""

LOCATION_SQL = """SELECT location,
       SUM(CASE WHEN type = 'lost' THEN 1 ELSE 0 END) AS lost,
       SUM(CASE WHEN type = 'found' THEN 1 ELSE 0 END) AS found,
       COUNT(*) AS total
FROM notices
GROUP BY location
ORDER BY total DESC, location COLLATE NOCASE, location;"""

WEEKLY_SQL = """WITH RECURSIVE
bounds AS (
    SELECT date(MIN(event_date), 'weekday 0', '-6 days') AS first_week,
           date(MAX(event_date), 'weekday 0', '-6 days') AS last_week
    FROM notices
),
weeks(week_start) AS (
    SELECT first_week FROM bounds WHERE first_week IS NOT NULL
    UNION ALL
    SELECT date(week_start, '+7 days') FROM weeks, bounds
    WHERE week_start < last_week
)
SELECT w.week_start,
       date(w.week_start, '+6 days') AS week_end,
       w.week_start || ' to ' || date(w.week_start, '+6 days') AS label,
       SUM(CASE WHEN n.type = 'lost' THEN 1 ELSE 0 END) AS lost,
       SUM(CASE WHEN n.type = 'found' THEN 1 ELSE 0 END) AS found,
       COUNT(n.id) AS total
FROM weeks AS w
LEFT JOIN notices AS n
  ON n.event_date BETWEEN w.week_start AND date(w.week_start, '+6 days')
GROUP BY w.week_start
ORDER BY w.week_start;"""

QUESTIONS = {
    'category': 'Which categories have the largest open-notice backlog in the synthetic dataset?',
    'location': 'How do lost and found notice counts differ across simulated locations?',
    'weekly': 'How do lost and found notice counts vary by event-date week in the synthetic dataset?',
}


def _rows(connection, sql):
    cursor = connection.execute(sql)
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def build_analytics(connection):
    """Return three reproducible series. The caller owns the SQLite connection.

    Category totals include categories without notices. Weekly ranges run from
    Monday to Sunday, including intervening empty weeks. The first and last
    weeks may contain only part of the observed event-date range. Returned is
    current notice status, not evidence of a measured recovery time or rate.
    """
    counts = _rows(connection, """SELECT COUNT(*) AS notices,
        COALESCE(SUM(status='open'), 0) AS open,
        COALESCE(SUM(status='returned'), 0) AS returned,
        COALESCE(SUM(type='lost'), 0) AS lost,
        COALESCE(SUM(type='found'), 0) AS found,
        (SELECT COUNT(*) FROM categories) AS categories FROM notices""")[0]
    return {
        'source_label': 'synthetic',
        'source_description': 'Synthetic teaching data, including demonstration edits; not observed campus activity.',
        'counts': counts,
        'category_series': _rows(connection, CATEGORY_SQL),
        'location_series': _rows(connection, LOCATION_SQL),
        'weekly_series': _rows(connection, WEEKLY_SQL),
        'questions': dict(QUESTIONS),
        'sql': {'category': CATEGORY_SQL, 'location': LOCATION_SQL, 'weekly': WEEKLY_SQL},
    }
