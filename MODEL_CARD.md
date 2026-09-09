# Model Card

Template. Every section below is a `TODO` and none of the answers are in
here. Fill it in from your own training run, delete the prompts, and keep
the headings, because a reviewer looks for them by name.

A model card is the document that answers "should I use this" without
making someone read your code. It takes about twenty minutes and it is one
of the few artifacts in a student portfolio that reads as professional
rather than academic.

**Model:** TODO — name and version, matching the `version` in the artifact
**Task:** TODO — one sentence, including what the positive class means
**Owner:** TODO — your name and a link to the repository
**Date:** TODO
**Live service:** TODO — the URL of your `/docs` page

---

## Training data

TODO.

What a reader needs: where the data came from, how many rows, what one row
represents, the time period it covers, and how it was split. State the
split explicitly, including the random seed, so the numbers below are
reproducible.

Say what a row is at the moment of prediction. If a feature would not have
existed yet when the prediction is made, it does not belong in the model,
and saying so here is how a reader knows you thought about it.

If you kept the synthetic starter dataset, say that it is synthetic. A
model card that describes generated data as if it were real operational
data is worse than no card.

---

## Class balance

TODO.

The positive rate, stated as a number. Then the consequence of it.

Three things belong here:

- The base rate in your data, and in the training and test splits
  separately if they differ
- The accuracy of always predicting the majority class, which is the
  number your model has to beat before it has done anything at all
- Whether you compensated, with class weights, resampling, or a shifted
  decision threshold, and what that cost you

A model that reports 94% accuracy on a problem with a 94% base rate has
learned nothing, and this section is where a reader finds that out. Report
a metric that survives imbalance, such as ROC AUC or precision and recall
at your chosen threshold, and state the threshold.

---

## Intended use

TODO.

What decision this model is allowed to inform, and who is allowed to act on
it. Be specific enough that the sentence rules something out.

Then the out-of-scope uses, which is the half that carries the weight.
Examples of the kind of thing that belongs here: not for decisions about
individuals without human review, not valid outside the population it was
trained on, not a substitute for the process it advises.

If your model touches people, say what happens when it is wrong about one
of them.

---

## Known limitations

TODO.

The section that separates a portfolio project from a class assignment. At
minimum:

- Where performance is worst. Break your metric out by a subgroup that
  matters and report the segment your model is weakest on.
- What is not represented in the training data
- How the model degrades as the world moves away from the training period,
  and how you would know it had happened
- Anything you know is wrong with it and chose not to fix, and why
- What you would do next with another week

Include the failure you found and fixed while building this. If the
training path and the serving path disagreed at any point, that belongs
here, with what the disagreement was and what now prevents it. Finding your
own bug and writing it down is a hiring signal. Quietly fixing it is not.

---

## Latency

TODO.

Median and p95 over at least 100 requests against the deployed service, not
localhost, with the command you ran. `scripts/measure_latency.py` produces
these once you finish it.

| Metric | Value |
|---|---|
| Requests measured | TODO |
| Median (p50) | TODO ms |
| p95 | TODO ms |
| Measured against | TODO — the deployed URL |
| Cold start observed | TODO — free tiers sleep, say what the first request costs |
