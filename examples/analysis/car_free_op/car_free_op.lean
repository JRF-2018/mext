/-
  MEXT の Extension 検証（mext.py が自動生成）
  リテラルは整数で表す: 原子 i は i、その否定は -i。
  Γ(E) を有限回の反復で計算し、Γ(E) = E を decide +kernel（カーネルでの評価）で確かめる。
-/
namespace Mext

structure Dflt where
  pre : List Int
  just : List Int
  concl : List Int
deriving Repr

structure Theory where
  W : List Int
  rules : List (List Int × Int)
  defaults : List Dflt

def subsetL (a b : List Int) : Bool := a.all (fun x => b.contains x)

def sameSet (a b : List Int) : Bool := subsetL a b && subsetL b a

def consistentL (S : List Int) : Bool := S.all (fun x => !S.contains (-x))

/-- E に照らして正当化が無矛盾なデフォルト -/
def okDefaults (T : Theory) (E : List Int) : List Dflt :=
  T.defaults.filter (fun d => d.just.all (fun j => !E.contains (-j)))

/-- 1 ステップ: 規則と（前提が満たされた）デフォルトの結論を加える -/
def step (T : Theory) (ds : List Dflt) (S : List Int) : List Int :=
  let fromRules := (T.rules.filter (fun r => subsetL r.1 S)).map (fun r => r.2)
  let fromDefs := ((ds.filter (fun d => subsetL d.pre S)).map (fun d => d.concl)).flatten
  (S ++ fromRules ++ fromDefs).eraseDups

def iter (T : Theory) (ds : List Dflt) : Nat → List Int → List Int
  | 0, S => S
  | n + 1, S => iter T ds n (step T ds S)

/-- Γ(E)（反復回数は規則とデフォルトの数 + 1 で十分） -/
def gamma (T : Theory) (E : List Int) : List Int :=
  iter T (okDefaults T E) (T.rules.length + T.defaults.length + 1) T.W

/-- E は Extension か（無矛盾で、Γ(E) = E） -/
def isExtension (T : Theory) (E : List Int) : Bool :=
  consistentL E && sameSet (gamma T E) E

end Mext

namespace Mext.Car_free_op

/-! car_free_op.mext の原子命題
  1 = k1: #Safety argument [safety]
  2 = f1: downtown core
  3 = r1: safety／%private cars are the main source of danger to pedestrians downtown
  4 = f2: most serious pedestrian injuries in our city happen in the downtown core
  5 = f3: nearly all of them involve private cars
  6 = x1: （L9 の AND・2項・1）
  7 = v1: （most serious pedestrian injuries in our city happen in the downtown core & nearly all of them involve private cars）@the involvement of private cars in nearly all of the injuries shows that the cars cause the danger
  8 = c1: removing the cars would remove most of the danger〔downtown core〕
  9 = k2: #Shop owners' objection [fear]
  10 = f4: local shops
  11 = r2: fear／%customers who drive will stop coming
  12 = f5: shop owners fear that customers who drive will stop coming
  13 = v2: shop owners fear that customers who drive will stop coming@the shop owners' fear is well founded
  14 = c2: a car-free center would hurt local shops〔local shops〕
  15 = k3: #Business argument [business]
  16 = r3: business／%local shops would not lose sales without customers who drive
  17 = f6: surveys in other cities suggest that pedestrians visit shops more often and spend about the same per month compared with drivers
  18 = v3: surveys in other cities suggest that pedestrians visit shops more often and spend about the same per month compared with drivers@the survey results from other cities hold in our city and lost driving customers would be made up by pedestrian customers
  19 = k4: #Air quality argument [air]
  20 = r4: air／%air quality downtown needs to be improved
  21 = f7: the nitrogen dioxide levels on our main street regularly exceed the national guideline
  22 = v4: the nitrogen dioxide levels on our main street regularly exceed the national guideline@exceeding the national guideline shows a problem that calls for action
  23 = r5: air／%removing private cars would cut nitrogen dioxide downtown substantially
  24 = f8: traffic is the largest source of nitrogen dioxide downtown
  25 = v5: traffic is the largest source of nitrogen dioxide downtown@private cars make up most of that traffic
  26 = x2: （L27 の AND・2項・1）
  27 = c3: a car-free center would improve air quality downtown〔downtown core〕
  28 = k5: #Disability objection [disability]
  29 = r6: disability／%people with disabilities depend on cars
  30 = f9: people with disabilities depend on cars
  31 = c4: the city council should adopt a car-free downtown plan〔downtown core〕
  32 = k6: #Answer by exceptions [exceptions]
  33 = r7: exceptions／%the concern can be met by exceptions to the plan
  34 = f10: permits for disabled drivers, delivery vehicles and emergency services can be kept
  35 = v6: permits for disabled drivers, delivery vehicles and emergency services can be kept@permits for disabled drivers would meet the needs of people with disabilities
  36 = c5: the disability concern is an argument for exceptions, not against the plan〔downtown core〕
  37 = k7: #Car-free downtown plan [plan]
  38 = r8: plan／$safety
  39 = r9: plan／$business
  40 = r10: plan／$air
  41 = x3: （L49 の AND・3項・1）
  42 = ab1: ab(disability)
-/

def T : Mext.Theory where
  W := [2, 4, 5, 10, 12, 17, 21, 24, 30, 34]
  rules := [([4, 5], 6), ([-4], -6), ([-5], -6), ([7], 3), ([-7], -3), ([-3], -1), ([13], 11), ([-13], -11), ([-11], -9), ([18], 16), ([-18], -16), ([-16], -15), ([22], 20), ([-22], -20), ([25], 23), ([-25], -23), ([20, 23], 26), ([-20], -26), ([-23], -26), ([-26], -19), ([30], 29), ([-30], -29), ([-29], -28), ([35], 33), ([-35], -33), ([-33], -32), ([38, 39, 40], 41), ([-38], -41), ([-39], -41), ([-40], -41), ([-41], -37), ([1], 38), ([-1], -38), ([15], 39), ([-15], -39), ([19], 40), ([-19], -40)]
  defaults := [
    ⟨[6], [7, 3], [7]⟩,  -- e1
    ⟨[2, 3], [1, 8], [1, 8]⟩,  -- safety
    ⟨[12], [13, 11], [13]⟩,  -- e2
    ⟨[10, 11], [9, 14], [9, 14]⟩,  -- fear
    ⟨[17], [18, 16], [18]⟩,  -- e3
    ⟨[10, 16], [15, -14], [15, -14]⟩,  -- business
    ⟨[21], [22, 20], [22]⟩,  -- e4
    ⟨[24], [25, 23], [25]⟩,  -- e5
    ⟨[2, 26], [19, 27], [19, 27]⟩,  -- air
    ⟨[2, 29], [28, -31, -42], [28, -31]⟩,  -- disability
    ⟨[34], [35, 33], [35]⟩,  -- e6
    ⟨[2, 33], [32, 36], [32, 36, 42]⟩,  -- exceptions
    ⟨[2, 41], [37, 31], [37, 31]⟩  -- plan
  ]

def E1 : List Int := [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 29, 30, 32, 33, 34, 35, 36, 38, 40, 42]
theorem E1_isExtension : Mext.isExtension T E1 = true := by decide +kernel

def E2 : List Int := [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, -14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42]
theorem E2_isExtension : Mext.isExtension T E2 = true := by decide +kernel

end Mext.Car_free_op
