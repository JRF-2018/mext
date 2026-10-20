# matcha analysis: car_free_op

Source: `car_free_op.md` (a fictional op-ed written as a test document). Transcription: `car_free_op.matcha`, by AI (Claude Opus 5.5). Matcha-D is an unofficial extension of Matcha.

Paragraph numbers count the body paragraphs after the title and the "(A fictional op-ed …)" note: para 1 = "Our city should close…", para 2 = safety, para 3 = business, para 4 = air quality, para 5 = disability objection, para 6 = "For these reasons…".

## 1. Summary of the argument

Main conclusion (one): **the city council should adopt a car-free downtown plan** (para 6; para 1 states it as "close its downtown core to private cars within five years").

It is supported by three numbered reasons (safety, business, air quality) and defended against two objections (shop owners' fear of losing driving customers, answered by surveys; the dependence of people with disabilities on cars, answered by permits). Scope: the whole document.

## 2. Correspondence table

| Source | `.matcha` line | Label | Notes |
|---|---|---|---|
| para 1 "Our city should close its downtown core to private cars within five years." | L35–39 | `plan` | Treated as the same thesis as para 6; transcribed once with the wording of para 6. "within five years" is dropped (§5) |
| para 2 "Most serious pedestrian injuries … happen in the downtown core" | L8 (fact) | `safety` | verbatim |
| para 2 "nearly all of them involve private cars" | L8 (fact) | `safety` | "them" spelled out as "serious pedestrian injuries downtown" (paraphrase) |
| — | L8 (evaluation, requirement) | `safety` | **supplied**: "injuries that involve private cars are caused by the private cars"; requirement wording is mine |
| para 2 "Removing the cars would remove most of the danger." | L10 | `safety` | verbatim (conclusion of the safety reason) |
| para 3 "Shop owners fear that customers who drive will stop coming." | L14–17 | `shopfear` | fact verbatim; conclusion "a car-free center would hurt local shops" is a paraphrase of the objection implied by "rather than hurt them" |
| para 3 "But surveys in other cities suggest …" | L21 (fact) | `business` | verbatim except "as drivers do" kept (no line-final "as") |
| — | L21 (requirement, evaluation) | `business` | requirement "pedestrians are at least as valuable customers as drivers are" and evaluation "the survey results from other cities hold for our city" are my articulation of the step "therefore" |
| para 3 "A car-free center could therefore help local shops rather than hurt them." | L23 | `business` | verbatim; `!> $shopfear` expresses "rather than hurt them" |
| para 4 "Traffic is the largest source of nitrogen dioxide downtown" | L29 (fact) | `air` | verbatim |
| para 4 "the levels on our main street regularly exceed the national guideline" | L30 (fact) | `air` | "the levels" spelled out as "the nitrogen dioxide levels" |
| — | L29 (evaluation), L29/L30 (requirements), L31 (conclusion) | `air` | **supplied**: the paragraph gives no conclusion. Evaluation "private cars make up most of the downtown traffic" and conclusion "a car-free center would improve air quality downtown" are supplied |
| para 6 "For these reasons, the city council should adopt a car-free downtown plan." | L35–39 | `plan` | verbatim conclusion; "For these reasons" → the three reasons joined by AND (reading) |
| para 5 "Some will object that people with disabilities depend on cars. This is a real concern" | L43–45 | `disability` | the objection's conclusion "not the city council should adopt …" is implied by "not against the plan"; `+` because the author concedes "a real concern" |
| para 5 "but it is an argument for exceptions, not against the plan: permits … can be kept." | L48–50 | `exceptions` | fact verbatim; the ":" of the source is not used in any element; conclusion verbatim except "it" → "the concern of people with disabilities" |

## 3. Transcription decisions

- **Evaluations (`@`)**: the three bridges the text leaves implicit are surfaced as evaluations: "involve" → "caused by" (safety), "other cities" → "our city" (business), "permits for disabled drivers" → "needs of people with disabilities met" (exceptions). The air paragraph's bridge ("private cars make up most of the downtown traffic") is supplied.
- **Exceptions (`!>`)**: `business !> shopfear` (the author answers the shop owners' fear with surveys); `disability !> plan` (the objection, if it stood, would defeat the plan); `exceptions !> disability` (the author's answer).
- **No priority (`:: priority`)**: the author does not weigh reasons against each other.
- The shop owners' objection is not linked to `plan`: the text treats it inside the business reason only; it is left as a claim that `business` blocks (a dead end by design).

### Connectives

| Line | Where | AND/OR | Explicit or reading |
|---|---|---|---|
| L35–39 | `plan`: `$safety`, `$business`, `$air` | AND | reading ("For these reasons" does not say whether each is needed) |
| L8 | `safety`: two facts | AND | explicit ("and") |
| L29–30 | `air`: two requirements | AND | reading (the paragraph says "and" between the facts, but the requirements are mine) |

### Fact kinds

| Fact | Kind |
|---|---|
| most serious pedestrian injuries in our city happen in the downtown core | description |
| nearly all serious pedestrian injuries downtown involve private cars | description |
| shop owners fear that customers who drive will stop coming | description |
| surveys in other cities suggest that pedestrians visit shops more often and spend about as much per month as drivers do | description (the document notes the figures are illustrative) |
| traffic is the largest source of nitrogen dioxide downtown | description |
| the nitrogen dioxide levels on our main street regularly exceed the national guideline | description |
| some will object that people with disabilities depend on cars | description |
| permits for disabled drivers, delivery vehicles and emergency services can be kept | author's claim (a feasibility claim about the plan, not a reported fact) |

## 4. Supplied premises

These are not in the text and should be the first things doubted in review.

- `injuries that involve private cars are caused by the private cars` (evaluation, L8) — needed to go from "involve" to "removing the cars would remove most of the danger".
- `private cars make up most of the downtown traffic` (evaluation, L29) — the text says "traffic", not "private cars"; the plan keeps delivery vehicles and emergency services.
- `a car-free center would improve air quality downtown` (conclusion of `air`, L31) — the paragraph states no conclusion.

## 5. What was dropped

- "within five years" (para 1): the timeline is asserted, not argued.
- The title and the "(A fictional op-ed …)" note.
- "First, / Second, / Third," as numbering only (kept as `::` headings).
- "This is a real concern" is kept only as the `+` mark on the objection's requirement.

## 6. Prediction before the first solve

(Written before running `mext init --solve`. Not to be revised.)

- One extension, preferred. It contains "the city council should adopt a car-free downtown plan" and "a car-free center could help local shops rather than hurt them". It does not contain "a car-free center would hurt local shops" (blocked by `business`) or "not the city council should adopt a car-free downtown plan" (the disability objection is blocked by `exceptions`).
- Expected weak points: the AND over the three reasons (so any one failing defeats the plan), the supplied air-quality step, and the permits evaluation (permits for disabled *drivers* do not obviously cover passengers).

Addendum after the shape check: the first check (`car_free_op.check.v1.mext`) agreed with the prediction in its Extension, but showed that the objection's conclusion was a different atom from the plan's conclusion (see §8). No disagreement with the prediction after the fix.

## 7. Syntax check and shape check

- `matcha_check`: 0 errors, 0 warnings. `--tree` shows the intended structure (three reasons joined under `plan`, two `!>` chains).
- `mext init --solve` (`car_free_op.check.mext`): 1 Extension (1 preferred); the main conclusion is in it.
- `mext lint`: 0 warnings, 3 notes.
  - "many one-step claims" (5 of 7): the source really is this simple; each reason is one or two sentences. Left as is.
  - `shopfear` and `disability` are in no Extension: intended — they are the objections the author answers, and they are blocked by `business` and `exceptions`.
- Gaps in the source found while writing: para 4 states no conclusion (supplied); the business rebuttal does not answer whether the driving customers would be lost, only that pedestrians are good customers; "within five years" is not argued.

## 8. Revision record

- v1 → v2 (`car_free_op.v1.matcha`, `car_free_op.check.v1.mext` kept): the disability objection had the object `the plan`, so its conclusion "not the city council should adopt a car-free downtown plan" was a different atom (〔the plan〕) from the main conclusion (〔the city〕) and opposed nothing. The objection is aimed at the same proposition, so the object was changed to `the city` (fidelity fix, L43). `mext diff`: no change in skeptical consequences; the stray conclusion atom 〔the plan〕 disappeared.

## 9. Next steps

- In the mext analysis, move §3 and §4 to `[ai]` (`connective`, `fact-kind`, `supplied`).
- Check the AND over the three reasons against the source with `mext connectives` (it is a reading).
- Review the three bridging evaluations and the permits evaluation severely; they are where the argument is thin.
