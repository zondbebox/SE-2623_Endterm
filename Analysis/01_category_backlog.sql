SELECT c.id AS category_id, c.name AS category,
       COUNT(n.id) AS total,
       SUM(CASE WHEN n.status = 'open' THEN 1 ELSE 0 END) AS open,
       SUM(CASE WHEN n.status = 'returned' THEN 1 ELSE 0 END) AS returned
FROM categories AS c
LEFT JOIN notices AS n ON n.category_id = c.id
GROUP BY c.id, c.name
ORDER BY open DESC, total DESC, c.name COLLATE NOCASE, c.id;
