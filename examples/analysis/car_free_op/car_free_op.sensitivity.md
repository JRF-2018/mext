# 感度分析: car_free_op.mext

（mext sensitivity の出力。争いうる前提を外して Extension を計算し直した結果。外すのは下の候補だけで、W の事実と規則はそのまま。「成り立つ」は、すべての preferred Extension に含まれること）

基準の理論: Extension 2 個（preferred 1 個）。候補 14 個。全候補で組の大きさ 2 まで調べた（依存が見つからない結論は、支持の組を集めて、そのすべてと交わる組を大きさ 4 まで調べた）。「—」は、調べた範囲で見つからなかったことを表し、より大きな組で効く可能性は残る。

## 候補の前提

| ID | 種類 | 名前 | 内容 | 行 | AI の審査 |
|---|---|---|---|---|---|
| p1 | 評価 | e1 | （most serious pedestrian injuries in our city happen in the downtown core & nearly all of them involve private cars）@the involvement of private cars in nearly all of the injuries shows that the cars cause the danger | 9 | ok |
| p2 | 主張 | safety | #Safety argument [safety] | 7 |  |
| p3 | 評価 | e2 | shop owners fear that customers who drive will stop coming@the shop owners' fear is well founded | 14 | ok |
| p4 | 主張 | fear | #Shop owners' objection [fear] | 13 |  |
| p5 | 評価 | e3 | surveys in other cities suggest that pedestrians visit shops more often and spend about the same per month compared with drivers@the survey results from other cities hold in our city and lost driving customers would be made up by pedestrian customers | 20 | doubtful |
| p6 | 主張 | business | #Business argument [business] | 18 |  |
| p7 | 評価 | e4 | the nitrogen dioxide levels on our main street regularly exceed the national guideline@exceeding the national guideline shows a problem that calls for action | 29 | ok |
| p8 | 評価 | e5 | traffic is the largest source of nitrogen dioxide downtown@private cars make up most of that traffic | 32 | doubtful |
| p9 | 主張 | air | #Air quality argument [air] | 27 |  |
| p10 | 主張 | disability | #Disability objection [disability] | 38 |  |
| p11 | 評価 | e6 | permits for disabled drivers, delivery vehicles and emergency services can be kept@permits for disabled drivers would meet the needs of people with disabilities | 44 | doubtful |
| p12 | 主張 | exceptions | #Answer by exceptions [exceptions] | 43 |  |
| p13 | 主張 | plan | #Car-free downtown plan [plan] | 49 |  |
| p14 | 事実（著者の主張） | f10 | permits for disabled drivers, delivery vehicles and emergency services can be kept | L44 | 著者の主張 |

## 結論ごとの依存

| 結論 | 基準 | 単独で外すと成り立たなくなる | 組で外すと成り立たなくなる（極小の組） | 外すと否定が成り立つ | 極小の支持の組（一例） | 調べた範囲 |
|---|---|---|---|---|---|---|
| removing the cars would remove most of the danger〔downtown core〕 | 成り立つ | p1, p2 | — | — | p1, p2 | 全候補で大きさ 2 まで |
| ¬a car-free center would hurt local shops〔local shops〕 | 成り立つ | p5, p6 | — | p5, p6 | p5, p6 | 全候補で大きさ 2 まで |
| a car-free center would improve air quality downtown〔downtown core〕 | 成り立つ | p7, p8, p9 | — | — | p7, p8, p9 | 全候補で大きさ 2 まで |
| the city council should adopt a car-free downtown plan〔downtown core〕 | 成り立つ | p1, p2, p5, p6, p7, p8, p9, p11, p12, p13, p14 | — | — | p1, p2, p5, p6, p7, p8, p9, p13 | 全候補で大きさ 2 まで |
| the disability concern is an argument for exceptions, not against the plan〔downtown core〕 | 成り立つ | p11, p12, p14 | — | — | p11, p12, p14 | 全候補で大きさ 2 まで |

## AI が doubtful とした評価

- p5「surveys in other cities suggest that pedestrians visit shops more often and spend about the same per month compared with drivers@the survey results from other cities hold in our city and lost driving customers would be made up by pedestrian customers」: **単独で外すと成り立たなくなる**: 「¬a car-free center would hurt local shops〔local shops〕」、「the city council should adopt a car-free downtown plan〔downtown core〕」
- p8「traffic is the largest source of nitrogen dioxide downtown@private cars make up most of that traffic」: **単独で外すと成り立たなくなる**: 「a car-free center would improve air quality downtown〔downtown core〕」、「the city council should adopt a car-free downtown plan〔downtown core〕」
- p11「permits for disabled drivers, delivery vehicles and emergency services can be kept@permits for disabled drivers would meet the needs of people with disabilities」: **単独で外すと成り立たなくなる**: 「the city council should adopt a car-free downtown plan〔downtown core〕」、「the disability concern is an argument for exceptions, not against the plan〔downtown core〕」

## 外すと新たに成り立つ結論（非単調性）

- p5 を外すと「a car-free center would hurt local shops〔local shops〕」が成り立つ（surveys in other cities suggest that pedestrians visit shops more often and spend about the same per month compared with drivers@the survey results from other cities hold in our city and lost driving customers would be made up by pedestrian customers が、それを打ち消していた）
- p6 を外すと「a car-free center would hurt local shops〔local shops〕」が成り立つ（#Business argument [business] が、それを打ち消していた）

注: 「組で外すと」は、単独では結論が残るが、組で外すと成り立たなくなる極小の組である（同じ結論への独立した経路が複数ある場合に現れる）。「極小の支持の組」は、候補をこの順に外せるだけ外して、なお結論が残る組の一例で、ほかの組もありうる。^根拠（条文・原理の名前）は表示であって、独立に立証される前提ではないので、候補には入らない。
