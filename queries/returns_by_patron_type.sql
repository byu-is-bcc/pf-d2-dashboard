-- How each kind of patron gives books back, as a rate rather than a count.
--
-- The rate is the point. Undergraduates are most of the loans in this extract,
-- so they are top of any raw count of late returns by definition, and a chart
-- of those counts tells you nothing except which group is biggest. Dividing by
-- the group's own loans is what turns it into a comparison.
--
-- The second worked example, and the last one you get.

SELECT
    p.patron_type,
    COUNT(*)                                                          AS loans,
    ROUND(100.0 * SUM(CASE WHEN l.return_date IS NULL
                           THEN 1 ELSE 0 END) / COUNT(*), 1)          AS pct_never_returned,
    ROUND(100.0 * SUM(CASE WHEN l.return_date IS NOT NULL
                            AND l.return_date > l.due_date
                           THEN 1 ELSE 0 END) / COUNT(*), 1)          AS pct_returned_late
FROM loans l
JOIN patrons p ON p.patron_id = l.patron_id
GROUP BY p.patron_type
ORDER BY loans DESC;
