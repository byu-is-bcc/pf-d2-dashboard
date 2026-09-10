-- The numbers in the strip across the top of the dashboard.
--
-- One query, one round trip, four numbers. Running four separate COUNT queries
-- against four separate connections is the version of this that everyone writes
-- first and it is slower for no benefit.

SELECT
    COUNT(*)                                                              AS total_loans,
    COUNT(DISTINCT patron_id)                                             AS distinct_patrons,
    SUM(CASE WHEN return_date IS NULL THEN 1 ELSE 0 END)                  AS never_returned,
    SUM(CASE WHEN return_date IS NOT NULL AND return_date > due_date
             THEN 1 ELSE 0 END)                                           AS returned_late
FROM loans;
