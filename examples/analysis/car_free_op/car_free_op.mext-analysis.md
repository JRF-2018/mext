# mext analysis: car_free_op

(Length: **standard**. The document is short, about 1,100 characters, with one main conclusion, so the standard length was chosen without asking, as the skill directs. Source: `car_free_op.md`, a fictional op-ed written as a test document for mext. Tool: mext 0.3.3. Analysis and transcription: Claude Opus 5.5. The mext tool prints its output in Japanese. That output is pasted below unchanged and marked "(mext output)".)

## 0. Conclusion

- **(a) Formally**: the main conclusion, "the city council should adopt a car-free downtown plan", **follows**. The theory has 2 Extensions, and only one of them is preferred (E2). The conclusion is in E2, so it is a skeptical consequence. The other Extension, E1, is one where the shop owners' fear wins. E1 is not preferred only because the op-ed's "But" (`:: 優先 $business > $fear`) ranks the business argument above the fear.
- **(b) Substantively**: the argument is **only moderately persuasive**. The three reasons are joined conjunctively ("For these reasons"), so each one is a single point of failure. Two of them rest on doubtful steps:
  - **Business**: per-customer survey results from unnamed other cities are taken to show that lost drivers will be replaced.
  - **Air quality**: the paragraph speaks of "traffic", but the plan removes only private cars. This step had to be supplied, and so did the paragraph's conclusion.
  
  The answer to the disability objection is a third doubtful step: permits for disabled *drivers* are taken to meet the needs of people with disabilities.
- **(c) Dependence** (from `sensitivity`): taken one at a time, 11 candidate premises would each make the main conclusion fail. They are:
  - all three reason claims;
  - the evaluations under the reasons, including the doubtful p5 (business) and p8 (traffic → private cars);
  - the whole chain of the disability answer: p11 (doubtful), p12, and p14, the author's own claim that "permits … can be kept".
  
  No pair of independent paths was found, because the argument has no redundancy anywhere.
- **Verification scope** (summary): 6 evaluations (ok 3, doubtful 3, reject 0; doubtful evaluations do not stop inference). There are 4 final conclusions, and 2 of them hold. Only **1** (the exceptions answer) has no opposing proposition in the theory. That conclusion holds because nothing against it was written down, not because it beat an opposing reason.

(mext output: `car_free_op.summary.md`, main table)

| 結論 | 成否 | 対立する命題 | 決め手になる争いうる前提（単独で外すと成り立たなくなる） | 注意 |
|---|---|---|---|---|
| ¬a car-free center would hurt local shops〔local shops〕 | 成り立つ（懐疑的） | あり | p5「the survey results from…」〔doubtful〕 | doubtful の評価に依存 |
| the city council should adopt a car-free downtown plan〔downtown core〕 | 成り立つ（懐疑的） | あり | p1「the involvement of priv…」、p5「the survey results from…」〔doubtful〕、p7「exceeding the national …」 ほか 3 | doubtful の評価に依存 |
| the disability concern is an argument for exceptions, not against the plan〔downtown core〕 | 成り立つ（懐疑的） | **なし** | p11「permits for disabled dr…」〔doubtful〕、p14「permits for disabled dr…」 | doubtful の評価に依存。反対の根拠が理論にない |
| the city council should adopt a car-free downtown plan〔downtown core〕 | 成り立つ（懐疑的） | あり | p1「the involvement of priv…」、p5「the survey results from…」〔doubtful〕、p7「exceeding the national …」 ほか 3 | doubtful の評価に依存 |

(The 2nd and 4th rows are the same atom. They come from the plan claim and from the disability objection, whose conclusion is the negation of the plan; see "About the tool".)

## 1. The document's argument

The op-ed's thesis is that the city should close its downtown core to private cars within five years (para 1), and that the council should adopt a car-free plan (para 6). It gives three reasons:

1. **Safety**: serious pedestrian injuries are concentrated downtown, and nearly all involve private cars.
2. **Business**: shop owners fear losing customers who drive, "but" surveys elsewhere suggest pedestrians visit shops more often and spend about as much.
3. **Air quality**: traffic is the largest source of NO2 downtown, and NO2 levels exceed the national guideline.

It answers one objection, that people with disabilities depend on cars, by proposing exceptions: permits for disabled drivers, deliveries and emergency services. Everything argumentative was transcribed. Only "within five years" was dropped, because no reason in the op-ed bears on the timing (see §2).

## 2. Transcription (matcha analysis)

The full transcription is in `car_free_op.matcha` (53 lines, 7 claims). The memo is `car_free_op.matcha.md`, which holds the correspondence table, the judgments, the supplied premises and the prior prediction. The key lines:

```
#Business argument <= local shops: (
    %local shops would not lose sales without customers who drive <= surveys in other cities suggest that pedestrians visit shops more often and spend about the same per month compared with drivers@the survey results from other cities hold in our city and lost driving customers would be made up by pedestrian customers
) >> a car-free center could help local shops rather than hurt them as business
:: 優先 $business > $fear
...
    // Supplied premise: the paragraph speaks of traffic, not of private cars; ...
    %removing private cars would cut nitrogen dioxide downtown substantially <= traffic is the largest source of nitrogen dioxide downtown@private cars make up most of that traffic
// Supplied premise: para 4 states no conclusion; ...
) >> a car-free center would improve air quality downtown as air
...
#Car-free downtown plan <= downtown core: (
    $safety
    $business
    $air
) >> the city council should adopt a car-free downtown plan as plan
```

- **Evaluations made visible (6)**:
  - injuries "involve" cars → the cars cause the danger;
  - the fear is well founded (the objection's own step);
  - the survey transfers to our city, and lost drivers are replaced;
  - exceeding the guideline calls for action;
  - traffic → private cars;
  - permits meet the needs of people with disabilities.
- **Supplied premises**: the step from traffic to private cars (L32) and the air-quality conclusion (L34), since para 4 states no conclusion. These are the parts the analysis should doubt most.
- **Dropped**: the title and the note that the figures are illustrative; "within five years", which the op-ed asserts without any support (a gap in the argument); and the phrase "a real concern", which is reflected only as the absence of a `!` mark.
- **Wording changes**: "about as much per month as drivers do" became "about the same per month compared with drivers", to keep the keyword `as` out of the text. The colon in para 5 was removed, because `:` is an operator.
- **Lint**: 0 warnings and 2 info items. "Many one-step claims" is the op-ed's own shape: the steps it skips are already exposed as evaluations. "Disability objection in no Extension" is intended. No revisions were made.
- **Connectives**: there are 3 conjunctions. All of them are readings, none explicit, and all three change dependencies when flipped.

(mext output: `car_free_op.connectives.md`)

| 位置 | 属するもの | 今の結び方 | 入れ替えると成り立たなくなる | 入れ替えると新たに成り立つ | 入れ替えると依存が変わる最終的な結論（単独で効く前提の数: 今 → 入れ替え後） | AI の記録 |
|---|---|---|---|---|---|---|
| L9 | 要件「private cars are the main source of danger to pedestrians downtown」 | AND（2 項） | — | — | 「the city council should adopt a car-free downtown plan〔downtown core〕」 11 → 11 | 読み |
| L27 | 主張「air」 | AND（2 項） | — | — | 「the city council should adopt a car-free downtown plan〔downtown core〕」 11 → 9 | 読み |
| L49 | 主張「plan」 | AND（3 項） | — | — | 「the city council should adopt a car-free downtown plan〔downtown core〕」 11 → 4 | 読み |

  **Re-checked against the source.** The tool flags these connectives because each is a reading with no explicit cue in the text.
  - **L49**: "For these reasons" gathers the reasons but does not say whether each is needed. It is not "each of which alone would suffice". AND is kept. AND is the *more fragile* reading (11 single dependencies against 4 under OR), so it was not chosen to make the conclusion come out. Under OR, the conclusion would survive the loss of any one reason, but still not the loss of the disability answer.
  - **L27**: the air argument needs both a problem (exceedance) and a remedy (cars cause it). AND is kept.
  - **L9**: flipping it changes nothing.
- **Fact kinds**: 7 descriptions and 1 author's claim. The author's claim is "permits for disabled drivers, delivery vehicles and emergency services can be kept", which is a proposal, not a reported fact. Note also that the source itself says its figures are illustrative.

## 3. Syntax check

(mext output: `python3 -m mext.matcha_check --tree car_free_op.matcha`)

```
== car_free_op.matcha: エラー 0 件, 警告 0 件
```

## 4. AI judgments (`[ai]` in `car_free_op.mext`)

| Kind | Target | Judgment | Reason (short) |
|---|---|---|---|
| neg | "would hurt local shops" / "could help local shops rather than hurt them" | negation | "rather than hurt them", offered as the answer ("But") to the fear |
| review | injuries involve cars → cars cause the danger | ok | ordinary reading of "involve" |
| review | shop owners' fear is well founded | ok | plausible; the op-ed does not dispute it |
| review | other-city surveys hold here, and lost drivers are replaced | **doubtful** | transfer from unnamed other cities; "suggest" is made into a premise; per-customer figures say nothing about customer *numbers* |
| review | exceeding the guideline calls for action | ok | |
| review | traffic → private cars make up most of it | **doubtful** | supplied premise; buses, deliveries and emergency vehicles are traffic too, and the plan keeps deliveries |
| review | permits for disabled drivers meet the needs of people with disabilities | **doubtful** | does not cover people who are driven or who use taxis; "can be kept" is a proposal |
| connective | plan, L9, air | 読み (reading) | see §2 |
| fact-kind | 10 facts | 記述 ×9 (incl. the two claim objects, which the tool does not count), 著者の主張 ×1 | see the memo §3 |

**Judgments withheld**: I did not identify "removing the cars would remove most of the danger" with "a car-free center would be safer". There was no need, since the plan refers to the claims through `$`. No `[extra]` knowledge was added. In particular, no rule that the plan's benefits outweigh the needs of people with disabilities was added, because the op-ed does not state one (see §8).

## 5. Default theory and Extensions

There are 42 atoms, 37 rules and 13 defaults; the full tables are in `car_free_op.report-tables.md`. Two defaults can conflict: fear/business and disability/plan.

(mext output: `[extensions]` of `car_free_op.mext`)

```
E1:
  generating: e1, safety, e2, fear, e3, e4, e5, air, e6, exceptions
E2 preferred:
  generating: e1, safety, e2, e3, business, e4, e5, air, e6, exceptions, plan
```

In E1, the fear claim fires first and blocks the business claim. With the business claim gone, the plan's AND fails, and the plan is *not proved* (not refuted). E1 is not preferred because `business > fear`.

(mext output: `explain car_free_op.mext E1 "plan"`, excerpt)

```
k7 「#Car-free downtown plan [plan]」 はこの Extension に含まれない
  デフォルト plan（L49 主張）は前提 x3 を欠く
      ...
            k3 「#Business argument [business]」 はこの Extension に含まれない
              デフォルト business（L18 主張）は正当化 -c2 が E と矛盾するため働かない
```

In E2, the main conclusion is derived from all three reasons. The disability objection is blocked by `ab(disability)`, which comes from the exceptions claim:

(mext output: `explain car_free_op.mext E2 "disability"`, excerpt)

```
k5 「#Disability objection [disability]」 はこの Extension に含まれない
  デフォルト disability（L38 主張）は正当化 -c4, -ab1 が E と矛盾するため働かない
    ...
    ab1 「ab(disability)」 ← デフォルト exceptions（L43 主張。正当化 k6, c5 は E と無矛盾）
      f1 「downtown core」 …（上に既出）
      r7 「exceptions／%the concern can be met by exceptions to the plan」 ← 規則 r24（L44 %the concern can be met by exceptions to the plan）
        v6 「permits for disabled drivers, delivery vehicles and emergency services can be kept@permits for disabled drivers would meet the needs of people with disabilities」 ← デフォルト e6（L44 評価 @permits for disabled drivers would meet the needs of people with disabilities（AI: 疑わしい）。正当化 v6, r7 は E と無矛盾）
          f10 「permits for disabled drivers, delivery vehicles and emergency services can be kept」 ← 確定事実 W 
```

The full derivations of the plan are in the `explain` output. Every leaf of the derivation is a W fact reached through one evaluation per requirement. Lean: `car_free_op.lean` was generated and checked with `lean` without errors. This proves that each listed set is an Extension (soundness only).

## 6. Substantive validity of the applications, and sensitivity

**The three doubtful evaluations:**

- **Business (p5)**: this is the weakest link in substance.
  - The shop owners' worry is about *how many* customers come.
  - The survey answers *how often and how much* a pedestrian customer visits and spends.
  - "Visit more often and spend about as much per month" would offset the loss only if the drivers who stop coming are replaced by new pedestrian customers. The op-ed does not show that.
  - The surveys are also unnamed, come from "other cities", and only "suggest".
- **Air (p8, supplied)**: the plan removes private cars and keeps deliveries and emergency vehicles. So "traffic is the largest NO2 source" supports the plan only to the extent that private cars make up that traffic.
- **Disability answer (p11)**: "permits for disabled drivers" covers one group. People with disabilities who are passengers, use taxis or ride-hailing, or cannot walk from the edge of the zone are not addressed. "Can be kept" is also the author's proposal (p14), not a result.

**Claim steps that are not evaluations** (and are therefore not reviewed by the tool):

- The safety claim's step "cars cause the danger → removing the cars removes most of the danger" ignores displacement. Traffic may move to the streets around the zone, and the danger may shift to the vehicles that remain.
- The business conclusion is weakened in the op-ed itself ("could … help"). After the `neg`, mext represents it as "not hurt", so the positive "help" carries no further weight in the theory.

(mext output: `car_free_op.sensitivity.md`, dependence table)

| 結論 | 基準 | 単独で外すと成り立たなくなる | 組で外すと成り立たなくなる（極小の組） | 外すと否定が成り立つ | 極小の支持の組（一例） | 調べた範囲 |
|---|---|---|---|---|---|---|
| removing the cars would remove most of the danger〔downtown core〕 | 成り立つ | p1, p2 | — | — | p1, p2 | 全候補で大きさ 2 まで |
| ¬a car-free center would hurt local shops〔local shops〕 | 成り立つ | p5, p6 | — | p5, p6 | p5, p6 | 全候補で大きさ 2 まで |
| a car-free center would improve air quality downtown〔downtown core〕 | 成り立つ | p7, p8, p9 | — | — | p7, p8, p9 | 全候補で大きさ 2 まで |
| the city council should adopt a car-free downtown plan〔downtown core〕 | 成り立つ | p1, p2, p5, p6, p7, p8, p9, p11, p12, p13, p14 | — | — | p1, p2, p5, p6, p7, p8, p9, p13 | 全候補で大きさ 2 まで |
| the disability concern is an argument for exceptions, not against the plan〔downtown core〕 | 成り立つ | p11, p12, p14 | — | — | p11, p12, p14 | 全候補で大きさ 2 まで |

p5 = business evaluation (doubtful), p8 = traffic → private cars (doubtful, supplied), p11 = permits evaluation (doubtful), p14 = "permits … can be kept" (author's claim).

The main conclusion depends **singly** on all three doubtful evaluations and on the author's claim p14. No "independent paths" were found, so no `concern`/`distinct` judgment was needed. The 11 premises are each necessary on their own, not merely members of a group.

Non-monotonicity: removing p5 or p6 makes "a car-free center would hurt local shops" hold. The business argument is the only thing holding the shop owners' fear back.

**As-written theory**: identical to the reviewed one, since there is no `reject`, so `X.asis.mext` was not made.

**Trials:**

| Trial | Change | Result (mext) |
|---|---|---|
| `car_free_op.alt-permits-reject.mext` | reject p11 (the permits answer fails) | 3 Extensions, 2 preferred. The plan and ¬plan are each credulous, and neither is skeptical. "最終的な結論 4 個のうち、成り立つもの 0 個" |
| `car_free_op.alt-nopriority.mext` (+ `.alt-nopriority.matcha`) | drop `:: 優先 $business > $fear` | 2 Extensions, both preferred. The plan is credulous only. "skeptical: k1, c1, k4, c3, k6, c5" (no plan) |

## 7. Skeptical and credulous consequences

(mext output: `[summary]` of `car_free_op.mext`)

```
extensions: 2 (preferred: 1)
skeptical: k1, c1, -c2, k3, k4, c3, c4, k6, c5, k7
credulous: k1, c1, -c2, k3, k4, c3, c4, k6, c5, k7
```

Since there is a single preferred Extension, the skeptical and credulous consequences coincide. They include the plan (c4, k7), the denial of the shop owners' fear (−c2), all three reasons, and the exceptions answer.

## 8. Rebuttal candidates (burden of proof)

1. **Contest the business evaluation (p5).** Show that lost driving customers are not replaced, or that the surveys do not transfer to this city. The fear then holds and the plan falls (sensitivity: "外すと新たに成り立つ" fear). This is the cheapest rebuttal, because the op-ed offers no evidence about customer *numbers*.
2. **Contest the permits answer (p11/p14).** Show that permits for disabled drivers leave out disabled passengers, or that permits cannot practically be kept. In the trial `alt-permits-reject`, the result is a Nixon diamond between the plan and the disability objection: the plan is no longer skeptical. The op-ed's *only* answer to the objection is exceptions. It never argues that the plan should win even if some needs remain unmet. To restore the conclusion, it would need that argument (a priority `plan > disability`).
3. **Contest traffic → private cars (p8).** Show that buses, deliveries or through-traffic on the ring roads are the main NO2 sources. The air reason then falls, and with AND the plan falls too. Under the OR reading (§2), this rebuttal would not be enough on its own.
4. **Contest the "But" itself.** If the business argument does not outrank the fear, for instance because the two are seen as equally weighty, the plan is only credulous (`alt-nopriority`).

On the burden of proof: the facts themselves (injury concentration, NO2 exceedance, surveys) are only illustrative in this fictional text. A real reply would first ask for their sources.

## 9. Verifying the predicted Extension

The prior prediction, from the memo §6 and copied into `[claimed]`:

```
E1*: "the city council should adopt a car-free downtown plan〔downtown core〕", "safety", "business", "air", -"a car-free center would hurt local shops〔local shops〕", !"disability"
```

(mext output)

```
E1: OK（主張されたリテラルを満たすpreferred Extension: E2）
E1: OK（すべてのpreferred Extensionで成り立つ: E2）
```

The prediction was right, both credulously and skeptically. One thing it did not anticipate is the non-preferred Extension E1, where the fear blocks the business claim. That Extension shows how much of the conclusion rests on a single word, "But": a priority the op-ed asserts without argument. This is a feature of the source text, not an error in the transcription.

## 10. Overall assessment

**Strengths:**

- The op-ed has a clear structure: three distinct reasons and an explicit answer to an objection.
- The safety reason is the most solid of the three, with a direct and ok-reviewed evaluation.
- The op-ed concedes the disability concern instead of dismissing it.

**Weaknesses:**

- Every reason and the objection answer are single points of failure (11 single dependencies).
- Three of the six evaluations are doubtful, and one of them had to be supplied.
- The business reason answers a different question from the one the fear raises: spending per customer instead of the number of customers.
- The disability answer covers only disabled drivers.
- The timeframe ("within five years") and the air-quality conclusion are not argued at all.

**What formalization made visible:**

- The op-ed rebuts the fear and the disability objection in different ways. The fear is not refuted, only *outranked* by a "But". The disability objection is *undercut* by exceptions, and the plan is never weighed against it directly. If the exceptions fail, the op-ed has no fallback.
- The air-quality paragraph is a pair of facts with no stated inference.

**Limits:** the same AI transcribed and reviewed this argument, so it may be lenient toward its own transcription. In particular, the choice of AND at L49 and the wording of the evaluations are its own. A second reader (a person or another AI) should check `car_free_op.matcha` and its memo.

## About the tool

- The `summary` table shows the conclusion "the city council should adopt a car-free downtown plan" twice. One row is for the plan claim. The other is for the disability objection, whose conclusion is the negation of the same atom (`>> not …`). The second row reports the *winning* side ("成り立つ") rather than "the objection's conclusion ¬plan does not hold". The count "成り立つもの 2 個" in the scope line is correct. Only the row labelling is confusing. Workaround: read the rows together with `sensitivity`.
- After the `neg`, the business conclusion's own wording ("could help … rather than hurt them") is shown only as "¬a car-free center would hurt local shops". This is by design, since `neg` merges atoms. Note, though, that the positive "help" claim drops out of the theory.

## Appendix: files

All files are in `tests/analysis_runs5/car_free_op/`.

| File | Contents |
|---|---|
| `car_free_op.md` | source (unchanged) |
| `car_free_op.matcha` | transcription |
| `car_free_op.matcha.md` | transcription memo (correspondence, judgments, supplied premises, prior prediction) |
| `car_free_op.check.mext` | shape check (no `[ai]`), with source hashes recorded |
| `car_free_op.mext` | default theory and Extensions with `[ai]` and `[claimed]` |
| `car_free_op.report-tables.md` | `mext report` output |
| `car_free_op.summary.md` | `mext summary` output |
| `car_free_op.connectives.md` | `mext connectives` output |
| `car_free_op.sensitivity.md` | `mext sensitivity` output |
| `car_free_op.lean` | Lean proof (checked) |
| `car_free_op.alt-permits-reject.mext` | trial: permits answer rejected |
| `car_free_op.alt-nopriority.matcha`, `car_free_op.alt-nopriority.mext` | trial: no `business > fear` priority |
| `car_free_op.mext-analysis.md` | this report |
