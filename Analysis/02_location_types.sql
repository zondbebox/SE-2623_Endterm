SELECT location,
       SUM(CASE WHEN type = 'lost' THEN 1 ELSE 0 END) AS lost,
       SUM(CASE WHEN type = 'found' THEN 1 ELSE 0 END) AS found,
       COUNT(*) AS total
FROM notices
GROUP BY location
ORDER BY total DESC, location COLLATE NOCASE, location;
