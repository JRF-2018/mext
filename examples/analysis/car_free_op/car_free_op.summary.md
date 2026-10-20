# Summary: car_free_op.mext

(output of mext summary; for details see mext report, mext sensitivity, mext explain)

- 1 Extension(s) (1 preferred).
- Scope of verification: 4 evaluations (unreviewed 0, ok 1, doubtful 3, reject 0; doubtful and unreviewed evaluations do not stop inference). 8 facts in W (description 7, author-claim 1; the kinds are AI judgments; assumptions and author claims are candidates in the sensitivity analysis). 3 premises supplied by the transcriber ([ai] supplied; not in the source). Of 4 final conclusions, 2 hold and 2 have no opposing proposition (negation) in the theory (these did not defeat any counter-argument; no counter-argument was written).
- Scope of the sensitivity analysis: 12 candidates; searched all candidates up to size 2; for conclusions with no dependency found, sets meeting every support set were tried up to size 4. “—” means none was found within that scope.
- Connectives: of 3 places, flipping 3 changes a final conclusion or its dependencies (explicit 1, reading 2, unrecorded 0; records are AI judgments; see mext connectives).

## Final conclusions

| conclusion | status | opposing proposition | decisive contestable premises (removing alone defeats it) | notes |
|---|---|---|---|---|
| a car-free center would hurt local shops〔the car-free center〕 | does not hold | **none** | — | mext explain shows why it does not hold (missing requirements, defeat by an exception, an opposing claim, etc.) |
| the city council should adopt a car-free downtown plan〔the city〕 | holds (skeptically) | yes | p1 “injuries that involve p…” [supplied], p4 “the survey results from…” [doubtful], p6 “private cars make up mo…” [doubtful] [supplied] and 2 more | **depends on premises not in the source (supplied by the transcriber)**: p1, p6, p7. depends on doubtful evaluations |
| the concern of people with disabilities is an argument for exceptions, not against the plan〔the plan〕 | holds (skeptically) | **none** | p10 “permits for disabled dr…” [doubtful], p12 “permits for disabled dr…” | depends on doubtful evaluations. no counter-argument in the theory |

## Points of contention (doubtful or unreviewed evaluations on which final conclusions depend)

- p10 “permits for disabled drivers meet the needs of pe…” [doubtful]: removing it alone defeats “the city council should adopt a car-free downtown plan〔the city〕” and 1 more (L49 / Source: para 5 "but it is an argument for exceptions, not against the plan: permits for disabled drivers, delivery vehicles and emergency services can be kept." / [ai] line 35)
- p4 “the survey results from other cities hold for our…” [doubtful]: removing it alone defeats “the city council should adopt a car-free downtown plan〔the city〕” (L21 / Source: para 3 "But surveys in other cities suggest that pedestrians visit shops more often and spend about as much per month as drivers do." / [ai] line 33)
- p6 “private cars make up most of the downtown traffic” [doubtful] [supplied]: removing it alone defeats “the city council should adopt a car-free downtown plan〔the city〕” (L29 / Source: para 4 "Traffic is the largest source of nitrogen dioxide downtown, and the levels on our main street regularly exceed the national guideline." / [ai] line 30)

## Tracing derivations

```
python3 -m mext explain car_free_op.mext E1 "the city council should adopt a car-free downtown plan〔the city〕"
python3 -m mext explain car_free_op.mext E1 "the concern of people with disabilities is an argument for exceptions, not against the plan〔the plan〕"
```
