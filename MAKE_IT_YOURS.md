# Make it yours

**Commit this file with the rest of the project. It is part of the deliverable.**

This is a decision record, not a set of instructions. Five questions, answered in
writing before you call D2 finished.

The reason it exists is sharper here than anywhere else in the catalog. A
dashboard is the one thing you build in this program that a recruiter *looks
at* rather than reads. They form an opinion in about four seconds and most of
that opinion is visual. Several hundred students start from this template. The
ones who never make a decision ship the same gray library dashboard, and the
fourth one somebody sees in a day gets four seconds and a back button.

Writing the answer down is what turns a default into a decision. You can make
the same choice the template makes — you just have to say that you chose it, and
why.

None of these need to be long. Two or three sentences each. They need to be
*true*.

`python scripts/check_decisions.py` checks the mechanical half: whether the
values are set. It cannot check whether your reasoning is any good. That is what
this file is for, and it is what a reviewer reads.

---

## 1. The question, and who is asking it

`QUESTION` and `READER` in `app.py` are both `None`. The page currently says its
subject is unwritten, which is accurate.

A dashboard without a question is a pile of charts. The test is whether a
stranger, having read the top of your page, can say what the page is *for*
without scrolling.

The reader matters more than it sounds. "A branch manager deciding summer hours"
and "a recruiter with forty seconds and no context" want opposite pages. The
first wants density and the ability to filter. The second wants one number, big,
and three sentences of context. You cannot serve both and choosing is the work.

> **The question this dashboard answers:**
> `TODO`
>
> **Who I built it for:**
> `TODO`
>
> **What that reader does differently after reading it:**
> `TODO`

---

## 2. The data

The seed is a library circulation extract: 20,000 loans, five branches, four
patron types, two years. It is the same seed D1 ships, so if you did D1 your
queries already run here.

Three legitimate paths, and they are not equally good:

- **Your D1 database.** The intended one. Set `DASHBOARD_DB` and go.
- **A source you went and found.** The strongest, and the one that makes the
  scheduled refresh mean something, because a source that changes is the only
  kind worth refreshing. See the notes in `fetch()` in `scripts/refresh.py`.
- **The shipped library seed.** Fine. It is real, it has genuine structure in
  it, and a good question asked of it beats a bad question asked of something
  more impressive. But you are then sharing a dataset with everyone else who
  entered cold, so sections 1, 3 and 4 are carrying the whole load.

If you stay on the seed, say so plainly here and say what you are doing to make
the page yours anyway. That is a defensible answer. Not mentioning it is not.

> **What this dashboard is built on:**
> `TODO`
>
> **Why that source, and where it comes from:**
> `TODO`
>
> **If it is the shipped seed: what makes my version of it distinguishable:**
> `TODO`

---

## 3. What leads, and what got cut

`SECTIONS` in `app.py` ships as `["headline", "kpis", "seasonality", "returns"]`.
That is not a design. It is the order the functions were written in.

The top-left of a dashboard is the most expensive real estate you will ever own
and everything above the fold competes for it. Decide what wins.

Then decide what loses. **Name one thing you built and removed.** A chart that
was interesting to make and did not earn its place is the most common thing
standing between a student dashboard and a good one, and cutting it is a
judgement a reviewer can see.

> **What leads, and why:**
> `TODO`
>
> **The order I settled on:**
> `TODO`
>
> **What I built and cut, and why it did not earn its place:**
> `TODO`

---

## 4. The accent

`ACCENT` in `app.py` is `None`. Every chart renders in placeholder gray until
you set it. This is deliberate and it is the same mechanism Project 000 uses
with `--accent`: there is no default for you to passively inherit, so choosing
one is unavoidable.

Pick one. One. A palette where every series is a different saturated color is
not a design decision, it is the absence of one, and it makes the reader work
out which series matters. One accent against gray does that work for them —
which is why `returns_by_patron_type` is drawn accent-against-gray rather than
in two full-strength colors.

Then name the exact places it is allowed to appear. Being specific here is the
whole exercise. "Used for highlights" is not an answer. "The headline number,
the leading series on every chart, and nothing else" is.

Check it before you commit. Anything at body text size needs 4.5:1 contrast
against your background.
[webaim.org/resources/contrastchecker](https://webaim.org/resources/contrastchecker/)

> **My accent:**
> `TODO` (hex)
>
> **It appears in exactly these places:**
> `TODO`
>
> **Contrast ratio against the page background:**
> `TODO`

---

## 5. The gate nobody gave you

`check_your_own_gate()` in `scripts/checks.py` is a stub. It fails until you
write it.

Eight gates ship finished. They cover the failures that are generic — row
counts, nulls, orphans, dates that run backwards, a category appearing that
nobody told you about. Those are the ones a stranger could have written without
seeing your data.

Write one they could not have. It should encode something *your* dashboard
depends on being true, which someone who had not read your SQL would not think
to check, and it should fail loudly when that thing stops being true.

And set `max_data_age_days` in `checks.toml` while you are in there. There is no
correct value. It depends entirely on what you connected, which is why the
template refuses to guess.

> **The gate I wrote, in one sentence:**
> `TODO`
>
> **What breaks on my dashboard if this stops being true:**
> `TODO`
>
> **My `max_data_age_days`, and why that number:**
> `TODO`

---

## The gate

D2 is **not yet** — not finished, not passing review — if all four of these are
still true at once:

- the dashboard is built on the shipped library seed, unchanged, *and*
- the question it answers is the one the template implies rather than one you
  chose, *and*
- `SECTIONS` is still in the order it shipped in, *and*
- the only quality gates are the eight that came with the template

That is a reviewable line, not encouragement. An alumni reviewer opening your
dashboard next to the template will be able to tell in about four seconds, and
the same gate is on their checklist.

Note what it does **not** say. Any one of those four being template-default is
fine. Building on the seed because you decided the library question was the one
you wanted to answer is a decision, and it is defensible. Leaving all four
because you never opened this file is not.
