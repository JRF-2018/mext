# Sensitivity analysis: car_free_op.mext

(output of mext sensitivity: Extensions recomputed after removing contestable premises. Only the candidates below are removed; facts in W and rules stay. “Holds” means being in every preferred Extension)

Base theory: 1 Extension(s) (1 preferred). 12 candidates. Searched all candidates up to size 2 (for conclusions with no dependency found, sets meeting every collected support set were tried up to size 4). “—” means none was found within that scope; larger sets may still matter.

## Candidate premises

| ID | kind | name | content | line | AI review | supplied |
|---|---|---|---|---|---|---|
| p1 | evaluation | e1 | （most serious pedestrian injuries in our city happen in the downtown core & nearly all serious pedestrian injuries downtown involve private cars）@injuries that involve private cars are caused by the private cars | 8 | ok | **supplied** |
| p2 | claim | safety | #safety [safety] | 7 |  |  |
| p3 | claim | shopfear | #shop owners' objection [shopfear] | 14 |  |  |
| p4 | evaluation | e2 | surveys in other cities suggest that pedestrians visit shops more often and spend about as much per month as drivers do@the survey results from other cities hold for our city | 21 | doubtful |  |
| p5 | claim | business | #business^surveys in other cities [business] | 20 |  |  |
| p6 | evaluation | e3 | traffic is the largest source of nitrogen dioxide downtown@private cars make up most of the downtown traffic | 29 | doubtful | **supplied** |
| p7 | claim | air | #air quality [air] | 28 |  | **supplied** |
| p8 | claim | plan | #car-free downtown [plan] | 35 |  |  |
| p9 | claim | disability | #disability objection [disability] | 43 |  |  |
| p10 | evaluation | e4 | permits for disabled drivers, delivery vehicles and emergency services can be kept@permits for disabled drivers meet the needs of people with disabilities | 49 | doubtful |  |
| p11 | claim | exceptions | #exceptions [exceptions] | 48 |  |  |
| p12 | fact (author's claim) | f12 | permits for disabled drivers, delivery vehicles and emergency services can be kept | L49 | author-claim |  |

## Dependencies of each conclusion

| conclusion | base | removing alone defeats it | removing a set defeats it (minimal sets) | removing makes its negation hold | a minimal support set (example) | scope searched |
|---|---|---|---|---|---|---|
| removing the cars would remove most of the danger〔the downtown core〕 | holds (skeptically) | p1, p2 | — | — | p1, p2 | all candidates up to size 2 |
| a car-free center could help local shops rather than hurt them〔the car-free center〕 | holds (skeptically) | p4, p5 | — | — | p4, p5 | all candidates up to size 2 |
| a car-free center would improve air quality downtown〔the downtown core〕 | holds (skeptically) | p6, p7 | — | — | p6, p7 | all candidates up to size 2 |
| the city council should adopt a car-free downtown plan〔the city〕 | holds (skeptically) | p1, p2, p4, p5, p6, p7, p8, p10, p11, p12 | — | p10, p11, p12 | p1, p2, p4, p5, p6, p7, p8 | all candidates up to size 2 |
| the concern of people with disabilities is an argument for exceptions, not against the plan〔the plan〕 | holds (skeptically) | p10, p11, p12 | — | — | p10, p11, p12 | all candidates up to size 2 |

## Evaluations the AI marked doubtful

- p4 “surveys in other cities suggest that pedestrians visit shops more often and spend about as much per month as drivers do@the survey results from other cities hold for our city”: **removing it alone defeats**: “a car-free center could help local shops rather than hurt them〔the car-free center〕”, “the city council should adopt a car-free downtown plan〔the city〕”
- p6 “traffic is the largest source of nitrogen dioxide downtown@private cars make up most of the downtown traffic”: **removing it alone defeats**: “a car-free center would improve air quality downtown〔the downtown core〕”, “the city council should adopt a car-free downtown plan〔the city〕”
- p10 “permits for disabled drivers, delivery vehicles and emergency services can be kept@permits for disabled drivers meet the needs of people with disabilities”: **removing it alone defeats**: “the city council should adopt a car-free downtown plan〔the city〕”, “the concern of people with disabilities is an argument for exceptions, not against the plan〔the plan〕”

## Conclusions that appear when a premise is removed (non-monotonicity)

- removing p4 makes “a car-free center would hurt local shops〔the car-free center〕” hold (surveys in other cities suggest that pedestrians visit shops more often and spend about as much per month as drivers do@the survey results from other cities hold for our city was blocking it)
- removing p5 makes “a car-free center would hurt local shops〔the car-free center〕” hold (#business^surveys in other cities [business] was blocking it)
- removing p10 makes “¬the city council should adopt a car-free downtown plan〔the city〕” hold (permits for disabled drivers, delivery vehicles and emergency services can be kept@permits for disabled drivers meet the needs of people with disabilities was blocking it)
- removing p11 makes “¬the city council should adopt a car-free downtown plan〔the city〕” hold (#exceptions [exceptions] was blocking it)
- removing p12 makes “¬the city council should adopt a car-free downtown plan〔the city〕” hold (permits for disabled drivers, delivery vehicles and emergency services can be kept was blocking it)

Note: “removing a set” lists minimal sets whose removal defeats a conclusion that survives any single removal (they appear when independent paths lead to the same conclusion). “A minimal support set” is one example obtained by removing candidates in order as long as the conclusion survives; others may exist. ^basis (names of statutes or principles) is a label, not an independently proved premise, so it is not a candidate.
