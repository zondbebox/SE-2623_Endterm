WITH RECURSIVE
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
ORDER BY w.week_start;
