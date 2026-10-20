### 検証の範囲
評価 6 個（未審査 0・ok 3・doubtful 3・reject 0。doubtful と未審査の評価も推論を止めない）。W の事実 8 個（記述 7・著者の主張 1。種別は AI の判断。仮定と著者の主張は感度分析で外す候補にする）。最終的な結論 4 個のうち、成り立つもの 2 個、理論の中に対立する命題（否定）がないもの 1 個（これらは、反対の根拠に勝ったのではなく、反対の根拠が書かれていないだけである）。結論ごとの依存は mext summary・mext sensitivity で調べる。

### 原子命題
| 名前 | 種類 | 文言 | 行 |
|---|---|---|---|
| k1 | claim | #Safety argument [safety] | L7 |
| f1 | fact | downtown core | L7,L27,L38,L43,L49 |
| r1 | req | safety／%private cars are the main source of danger to pedestrians downtown | L9 |
| f2 | fact | most serious pedestrian injuries in our city happen in the downtown core | L9 |
| f3 | fact | nearly all of them involve private cars | L9 |
| x1 | aux | （L9 の AND・2項・1） | L9 |
| v1 | eval | （most serious pedestrian injuries in our city happen in the downtown core & nearly all of them involve private cars）@the involvement of private cars in nearly all of the injuries shows that the cars cause the danger | L9 |
| c1 | concl | removing the cars would remove most of the danger〔downtown core〕 | L10 |
| k2 | claim | #Shop owners' objection [fear] | L13 |
| f4 | fact | local shops | L13,L18 |
| r2 | req | fear／%customers who drive will stop coming | L14 |
| f5 | fact | shop owners fear that customers who drive will stop coming | L14 |
| v2 | eval | shop owners fear that customers who drive will stop coming@the shop owners' fear is well founded | L14 |
| c2 | concl | a car-free center would hurt local shops〔local shops〕 | L15,L21 |
| k3 | claim | #Business argument [business] | L18 |
| r3 | req | business／%local shops would not lose sales without customers who drive | L20 |
| f6 | fact | surveys in other cities suggest that pedestrians visit shops more often and spend about the same per month compared with drivers | L20 |
| v3 | eval | surveys in other cities suggest that pedestrians visit shops more often and spend about the same per month compared with drivers@the survey results from other cities hold in our city and lost driving customers would be made up by pedestrian customers | L20 |
| k4 | claim | #Air quality argument [air] | L27 |
| r4 | req | air／%air quality downtown needs to be improved | L29 |
| f7 | fact | the nitrogen dioxide levels on our main street regularly exceed the national guideline | L29 |
| v4 | eval | the nitrogen dioxide levels on our main street regularly exceed the national guideline@exceeding the national guideline shows a problem that calls for action | L29 |
| r5 | req | air／%removing private cars would cut nitrogen dioxide downtown substantially | L32 |
| f8 | fact | traffic is the largest source of nitrogen dioxide downtown | L32 |
| v5 | eval | traffic is the largest source of nitrogen dioxide downtown@private cars make up most of that traffic | L32 |
| x2 | aux | （L27 の AND・2項・1） | L27 |
| c3 | concl | a car-free center would improve air quality downtown〔downtown core〕 | L34 |
| k5 | claim | #Disability objection [disability] | L38 |
| r6 | req | disability／%people with disabilities depend on cars | L39 |
| f9 | fact | people with disabilities depend on cars | L39 |
| c4 | concl | the city council should adopt a car-free downtown plan〔downtown core〕 | L40,L53 |
| k6 | claim | #Answer by exceptions [exceptions] | L43 |
| r7 | req | exceptions／%the concern can be met by exceptions to the plan | L44 |
| f10 | fact | permits for disabled drivers, delivery vehicles and emergency services can be kept | L44 |
| v6 | eval | permits for disabled drivers, delivery vehicles and emergency services can be kept@permits for disabled drivers would meet the needs of people with disabilities | L44 |
| c5 | concl | the disability concern is an argument for exceptions, not against the plan〔downtown core〕 | L45 |
| k7 | claim | #Car-free downtown plan [plan] | L49 |
| r8 | req | plan／$safety | L50 |
| r9 | req | plan／$business | L51 |
| r10 | req | plan／$air | L52 |
| x3 | aux | （L49 の AND・3項・1） | L49 |
| ab1 | ab | ab(disability) |  |

### デフォルト
| 名前 | 前提 | 正当化 | 結論 | 種類 | 注 |
|---|---|---|---|---|---|
| e1 | x1 | v1, r1 | v1 | eval | L9 評価 @the involvement of private cars in nearly all of the injuries shows that the cars cause the danger |
| safety | f1, r1 | k1, c1 | k1, c1 | claim | L7 主張 |
| e2 | f5 | v2, r2 | v2 | eval | L14 評価 @the shop owners' fear is well founded |
| fear | f4, r2 | k2, c2 | k2, c2 | claim | L13 主張 |
| e3 | f6 | v3, r3 | v3 | eval | L20 評価 @the survey results from other cities hold in our city and lost driving customers would be made up by pedestrian customers（AI: 疑わしい） |
| business | f4, r3 | k3, -c2 | k3, -c2 | claim | L18 主張 |
| e4 | f7 | v4, r4 | v4 | eval | L29 評価 @exceeding the national guideline shows a problem that calls for action |
| e5 | f8 | v5, r5 | v5 | eval | L32 評価 @private cars make up most of that traffic（AI: 疑わしい） |
| air | f1, x2 | k4, c3 | k4, c3 | claim | L27 主張 |
| disability | f1, r6 | k5, -c4, -ab1 | k5, -c4 | claim | L38 主張 |
| e6 | f10 | v6, r7 | v6 | eval | L44 評価 @permits for disabled drivers would meet the needs of people with disabilities（AI: 疑わしい） |
| exceptions | f1, r7 | k6, c5 | k6, c5, ab1 | claim | L43 主張 |
| plan | f1, x3 | k7, c4 | k7, c4 | claim | L49 主張 |

優先順位（自動で付けたものを含む）: business > fear, exceptions > disability

### AI によるあてはめの審査（[ai] の review）
| 対象 | 判定 | 理由 |
|---|---|---|
| （most serious pedestrian injuries in our city happen in the downtown core & nearly all of them involve private cars）@the involvement of private cars in nearly all of the injuries shows that the cars cause the danger | ok | a pedestrian injured in a collision with a car is injured by the car; "involve" → "cause" is an ordinary reading. (Whether removing the cars removes the danger — displacement to other streets, to delivery vehicles or bicycles — is the claim's own step, see report §6) |
| shop owners fear that customers who drive will stop coming@the shop owners' fear is well founded | ok | the objection's own inference; it is plausible that customers who can no longer drive downtown come less, and the op-ed does not dispute it |
| surveys in other cities suggest that pedestrians visit shops more often and spend about the same per month compared with drivers@the survey results from other cities hold in our city and lost driving customers would be made up by pedestrian customers | 疑わしい | three leaps: (1) unnamed surveys in other cities are transferred to our city; (2) "suggest" is turned into a premise; (3) the surveys compare spending per customer, but the fear is about the number of customers — that drivers who stop coming are replaced by pedestrians is not shown |
| the nitrogen dioxide levels on our main street regularly exceed the national guideline@exceeding the national guideline shows a problem that calls for action | ok | regularly exceeding a national guideline is an accepted reason for action |
| traffic is the largest source of nitrogen dioxide downtown@private cars make up most of that traffic | 疑わしい | supplied premise (car_free_op.matcha.md §4): "traffic" includes buses, delivery vehicles and emergency services, and the op-ed itself keeps deliveries and emergency vehicles (para 5); diesel delivery and bus traffic can be a large share of NO2 |
| permits for disabled drivers, delivery vehicles and emergency services can be kept@permits for disabled drivers would meet the needs of people with disabilities | 疑わしい | permits for disabled *drivers* do not cover people with disabilities who are driven by others or rely on taxis; and "can be kept" is a proposal (fact-kind 著者の主張), not a shown result |

### Extension
- **E1**（preferred ではない）: 生成デフォルト = e1, safety, e2, fear, e3, e4, e5, air, e6, exceptions
  - #Safety argument [safety]
  - removing the cars would remove most of the danger〔downtown core〕
  - #Shop owners' objection [fear]
  - a car-free center would hurt local shops〔local shops〕
  - #Air quality argument [air]
  - a car-free center would improve air quality downtown〔downtown core〕
  - #Answer by exceptions [exceptions]
  - the disability concern is an argument for exceptions, not against the plan〔downtown core〕
- **E2**（preferred）: 生成デフォルト = e1, safety, e2, e3, business, e4, e5, air, e6, exceptions, plan
  - #Safety argument [safety]
  - removing the cars would remove most of the danger〔downtown core〕
  - ¬a car-free center would hurt local shops〔local shops〕
  - #Business argument [business]
  - #Air quality argument [air]
  - a car-free center would improve air quality downtown〔downtown core〕
  - the city council should adopt a car-free downtown plan〔downtown core〕
  - #Answer by exceptions [exceptions]
  - the disability concern is an argument for exceptions, not against the plan〔downtown core〕
  - #Car-free downtown plan [plan]

### 懐疑的帰結と信憑的帰結（preferred Extension について）
- 懐疑的（すべての preferred Extension で成り立つ）: #Safety argument [safety]、removing the cars would remove most of the danger〔downtown core〕、¬a car-free center would hurt local shops〔local shops〕、#Business argument [business]、#Air quality argument [air]、a car-free center would improve air quality downtown〔downtown core〕、the city council should adopt a car-free downtown plan〔downtown core〕、#Answer by exceptions [exceptions]、the disability concern is an argument for exceptions, not against the plan〔downtown core〕、#Car-free downtown plan [plan]
- 信憑的（いずれかの preferred Extension で成り立つ）: #Safety argument [safety]、removing the cars would remove most of the danger〔downtown core〕、¬a car-free center would hurt local shops〔local shops〕、#Business argument [business]、#Air quality argument [air]、a car-free center would improve air quality downtown〔downtown core〕、the city council should adopt a car-free downtown plan〔downtown core〕、#Answer by exceptions [exceptions]、the disability concern is an argument for exceptions, not against the plan〔downtown core〕、#Car-free downtown plan [plan]
