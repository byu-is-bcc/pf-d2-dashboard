-- TODO — the one number the dashboard is about.
--
-- This query ships returning NULL, which is why the top of the page currently
-- says the headline is unwritten instead of showing you a number. Nothing else
-- on the dashboard is blocked by it. That is deliberate: the page runs, so you
-- can see the machinery working, and the empty slot is right where a visitor's
-- eye lands first so you cannot forget about it.
--
-- Write the query that produces the number your dashboard exists to report.
-- It should return exactly one row with two columns, `value` and `label`.
--
-- The test for whether you have the right number is not whether it is
-- interesting. It is whether someone would do something differently after
-- reading it. "20,000 loans" is a fact about the file. "Summer volume runs
-- under half of term-time, so the Thursday-to-Saturday staffing pattern is
-- costing about X" is a number someone acts on.
--
-- Some directions the shipped extract supports, none of which are the answer:
--   - loans that never came back, by branch or by subject
--   - what the seasonal swing actually is, and what it implies
--   - whether a branch's collection matches what its patrons borrow
--   - how the four patron types differ once you control for their loan periods
--
-- If you pointed this repo at your own database, ignore all of that. The
-- number should come out of the thing you actually care about.

SELECT
    NULL AS value,
    NULL AS label;
