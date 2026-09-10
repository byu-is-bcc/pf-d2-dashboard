-- Loan volume per calendar month across the whole extract.
--
-- This is a worked example, not a finding. It shows you the shape: aggregate in
-- SQL, hand the dashboard a small result, let the browser draw it. Twenty
-- thousand rows is small enough that you could pull it all into pandas and
-- group it there, and you should not get in that habit, because the version of
-- this query against a real warehouse table is aggregating forty million rows
-- and the difference between "the database did it" and "my laptop did it" stops
-- being academic.
--
-- substr() on an ISO date is doing the work of DATE_TRUNC here. SQLite has no
-- date type — these columns are TEXT — and ISO-8601 sorts and slices correctly
-- as a string, which is exactly why the seed stores dates that way.

SELECT
    SUBSTR(checkout_date, 1, 7) AS month,
    COUNT(*)                    AS loans
FROM loans
GROUP BY month
ORDER BY month;
