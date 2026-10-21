# mext

**A tool that makes an AI's reading of an argument auditable by people.** An AI transcribes the argument of a document (an op-ed, a judgment, a contract, an essay, a blog post, …) into **Matcha**, a formal language for legal reasoning, and mext computes it deterministically as **default logic**. Every interpretive judgment of the AI is recorded with its reason, and every mechanical step can be traced by a person.

It consists of a Matcha syntax checker, a solver and verifier for Reiter and prioritized Extensions with Lean proofs, analysis commands (sensitivity analysis, comparison of readings, …), and Claude Code skills ("mext analysis" and "matcha analysis" for the argument of any document, "mext-compare" for comparing readings, …).

*日本語: [README.md](README.md)*

> **Notice**
> - [Matcha](https://www.elecode.jp/matcha) is a formal language for legal reasoning by Taketsugu Hanafusa (花房孟胤). This repository implements its grammar as read from published examples (there is no official BNF).
> - The exception notation **Matcha-D (`!>`, `>> not` / `>> !`, `:: 優先` / `:: priority`, naming claims with `as`, and `"requirement"` as an ASCII spelling of 「requirement」) is an unofficial extension, unrelated to Elecode or Mr. Hanafusa.**
> - Naming with `as`, references with `$`, headings `::` and comments `//` follow examples in Mr. Hanafusa's articles (see [docs/matcha_grammar.md](docs/matcha_grammar.md) §1 and §5, in Japanese).

## Why mext

Ask an AI whether the argument of a document is sound and you get a plausible answer. What that answer depends on — which reading, which judgments — is invisible in the prose. mext splits an AI's analysis into units that people can question.

- **AI judgments in the open**: each line of the transcription cites the source (a quotation). Supplied premises, omissions, and whether each AND / OR is explicit in the source or a reading are recorded. Reviews of "fact@evaluation" steps (ok / doubtful / reject) and judgments of identity and negation all go, with reasons, into the `[ai]` section of the `.mext` file.
- **Mechanical steps people can follow**: the translation from Matcha into a default theory and the computation and verification of Extensions are deterministic: the same input gives the same result. `explain` traces which rules and evaluations a conclusion comes from, and Lean checks the computation itself. This traceability is the point of formalization.
- **Dependencies computed, not asserted**: the sensitivity analysis shows which evaluations or supplied premises a conclusion falls with. Every summary also states the scope of verification — conclusions with no opposing proposition, unreviewed or doubtful evaluations, connectives that decide a conclusion — so that results are not read too strongly.
- **Readings compared**: two transcriptions of the same document by different AIs or people are set side by side, separating weaknesses common to both (likely points of contention in the source's argument) from results that appear in one reading only (likely consequences of a transcription choice).
- **Procedure checked**: `mext audit` lists gaps in the records (sources, memo, prior predictions, reviews), and `mext lint` flags coarse transcription (tautological evaluations, quotations not found in the source, …).

mext does not judge whether an argument is *true*. It shows what follows within the transcribed theory and what that depends on, and points to where one should go back to the source. It has been tried with Claude (Opus, Sonnet, Haiku) and Codex (GPT-6.1-Sol); some of the runs are in [examples/analysis/](examples/analysis/).

## What it does

```
document ──(AI: matcha analysis)──▶ .matcha
.matcha ──(syntax check)──▶ syntax tree ──(deterministic translation)──▶ default theory (W, R, D, <)
                                                                        │
                  AI judgments ([ai]: identity, negation, reviews of evaluations) ─┤
                                                                        ▼
                Enumeration of all Extensions, selection of preferred ones, verification ──▶ Lean proof (Γ(E) = E)
```

- **Deterministic part** (this package):
  - syntax checking;
  - translation from Matcha into a default theory (requirements are read as necessary and sufficient conditions; an exception `!>` is read as a priority plus a blocked justification);
  - enumeration of all Reiter Extensions (via the correspondence with extended logic programs, Gelfond & Lifschitz 1991);
  - selection of preferred Extensions respecting priorities (after Brewka & Eiter 1999);
  - verification of claimed Extensions, and explanations of derivations and of why something does not hold;
  - Lean proofs;
  - analysis commands: sensitivity analysis, connective sensitivity, lint, version diff, summary, audit.
- **AI part** (the skills `mext-analysis`, `matcha-analysis`, `matcha-default-extensions`, `mext-compare`):
  - transcribing the argument of a document into Matcha (with a correspondence table, supplied premises, and what was left out);
  - judging identity and negation of propositions, and the type of conclusions;
  - reviewing the substance of "fact@evaluation" applications;
  - predicting Extensions, and writing the report "is the argument right?";
  - matching two readings of the same document and interpreting their differences (comparison of readings).

  Every AI judgment is written, with its reason, in the `[ai]` section of the MEXT file, where people can audit it.

## Installation

### Python package (no dependencies, Python 3.8+)

```bash
pip install git+https://github.com/JRF-2018/mext
```

This installs the commands `matcha-check` and `mext` (also `python3 -m mext.matcha_check` and `python3 -m mext`). Where pip refuses with “externally-managed-environment”, create a venv with `python3 -m venv`, or add the cloned directory to `PYTHONPATH` and run `python3 -m mext` (there are no dependencies).

### Claude Code plugin (four skills)

```bash
claude plugin marketplace add JRF-2018/mext
claude plugin install mext@jrf-mext
```

Alternatively, copy the four directories under `skills/` into `.claude/skills/` or `~/.claude/skills/` (copy them all; the skills refer to each other). The skills call `python3 -m mext`, so install the Python package as well.

### English output

The default output language is Japanese. Add `--lang en` to any command, or set `MEXT_LANG=en`, to get all output in English (diagnostics, comments in the generated part of `.mext`, report, summary, sensitivity, and so on). The locale (`LANG` etc.) is not consulted: in AI sandboxes, Colab and similar environments it often does not reflect the user's language. In `[ai]` you may use English vocabulary: `connective … explicit|reading`, `fact-kind … description|assumption|verified|author-claim`; and in Matcha-D, `:: priority $a > $b`.

The skill instructions (`SKILL.md`) are written in Japanese, but they tell the AI to answer and write files in the user's language. Ask in English and you get English files and an English report (example: [examples/analysis/car_free_op/](examples/analysis/car_free_op/)).

## Skills

| skill | how to ask | input → output |
|---|---|---|
| `mext-analysis` (mext analysis) | "Do a mext analysis of this document" | any document → `X.matcha`, `X.mext`, report `X.mext-analysis.md` |
| `matcha-analysis` (matcha analysis) | "Transcribe this document into Matcha" | any document → `X.matcha`, memo `X.matcha.md` (correspondence table, supplied premises, omissions) |
| `matcha-default-extensions` | "Check the Extensions of X.matcha" | `.matcha` → `X.mext`, report `X.report.md` |
| `mext-compare` (comparison of readings) | "Compare these two readings" | `A.mext` and `B.mext` of the same document → comparison file `A.vs.B.compare`, report `A.vs.B.compare.md` |

- A **mext analysis** transcribes the argument into Matcha, computes and verifies Extensions, and reports whether the argument (a) follows formally, (b) is substantively convincing, and (c) what it depends on. It works for op-eds, essays and proposals as well as legal documents.
- Only the mext part is deterministic; transcription and review are AI judgments. So the skills record where each line came from in the source, what the AI supplied and left out, and how it evaluated each step.
- The skills refine the transcription in response to `lint`: the previous version is kept with `snapshot`, compared with `diff`, and the revision is recorded. Revisions are allowed only to make the transcription more faithful and finer-grained, never to make a conclusion appear or disappear.
- At the end, `mext audit` lists any gaps in the procedure; the AI fixes them or explains in the report why it cannot.
- A **comparison of readings** sets two transcriptions of the same document (by different AIs or people) side by side and reports, against the source, where the readings diverge and how that changes the status and dependencies of conclusions. A premise that is decisive in both readings is likely a weakness of the source's argument; a result that appears in only one reading is likely a consequence of a transcription choice.

### Asking another AI

Without the skills installed, or with another AI, say:

> Use https://github.com/JRF-2018/mext to do a mext analysis of this document.

**To the AI**: when asked this, read [skills/mext-analysis/SKILL.md](skills/mext-analysis/SKILL.md) in this repository and follow it (for transcription only, [skills/matcha-analysis/SKILL.md](skills/matcha-analysis/SKILL.md)). Install the tools with `pip install git+https://github.com/JRF-2018/mext`. If you cannot run Python, state in the report that the deterministic part (computing Extensions) was not run, and give only your prediction in `[claimed]`. If your environment cannot reach GitHub (some sandboxes block network access), ask the user to clone the repository locally and give you the path.

## Usage

```bash
matcha-check --tree examples/tweety.matcha        # syntax check and syntax tree
mext init examples/tweety.matcha                  # template tweety.mext (Extensions not computed yet)
mext solve examples/tweety.mext                   # compute Extensions and write them
mext report examples/tweety.mext                  # Markdown tables
mext explain examples/tweety.mext E2 "¬…"         # trace a derivation (or why something does not hold)
mext verify examples/tweety.mext [--skeptical]    # verify the Extensions claimed in [claimed]
mext lean examples/tweety.mext                    # Lean proof (checkable with lean; no Mathlib needed)
mext summary X.mext                               # one-screen summary: final conclusions, decisive premises, points of contention, scope
mext sensitivity X.mext                           # sensitivity: which premises a conclusion depends on
mext connectives X.mext                           # sensitivity to AND / OR
mext lint X.mext                                  # coarseness of the transcription
mext audit X.mext                                 # gaps in the analysis procedure (✓ / ✗ / －)
mext snapshot X.mext && (edit X.matcha) && mext solve X.mext && mext diff X.v1.mext X.mext
                                                  # semantic differences before and after a revision
mext changed X.check.mext                         # whether the .matcha or the memo changed since the transcription
mext compare --init A.mext B.mext -o A.vs.B.compare && (write [match]) && mext compare A.vs.B.compare
                                                  # two readings of the same document: status, decisive premises, dependencies
```

- **sensitivity** removes contestable premises (evaluations, claims, supplied premises, facts marked as assumptions, …) one at a time or in sets, and recomputes. For each conclusion it shows what removing alone defeats it, minimal sets whose removal defeats it (independent paths), what makes its negation hold, and which doubtful evaluations it depends on. When the same evaluation is applied in several places, it distinguishes removing one application from not adopting the judgment at all ("a judgment shared by several paths").
- **Scope of verification**: `solve`, `report` and `summary` show how many evaluations were reviewed, how many final conclusions have no opposing proposition in the theory, and how many premises were supplied by the transcriber. "One Extension, every conclusion holds" may only mean that no counter-argument was written.
- **connectives** flips each AND / OR and shows changes in consequences and dependencies. Rather than demanding a justification for each connective, the AI records whether it is explicit in the source or a reading (`[ai] connective`), and the tool points at readings that decide a conclusion.
- **concern / distinct** in `[ai]` record whether several paths to the same conclusion share one weakness or are independent grounds; sensitivity and summary use them.
- **supplied** in `[ai]` records premises not in the source; summary warns when a conclusion depends on them.
- **compare** sets two readings of the same document side by side. Their atoms are worded differently (possibly in different languages), so an AI or a person writes which conclusions and premises correspond in `[match]` of the comparison file, with reasons; the tool compares each pair: status, decisive premises, shared decisive premises, dependence on supplied premises, connectives, independent paths. Identical texts are matched automatically.
- **diff** matches atoms by text, not by number, so you can see which conclusions turned, which dependencies changed, and which reviews no longer apply after a revision.

In Claude Code (installed as a plugin, the plugin name is a namespace):

```
/mext:mext-analysis tests/docs/car_free_op.md
/mext:matcha-analysis tests/docs/remote_work_op.md
/mext:matcha-default-extensions examples/self_defense.matcha
```

## A Matcha-D example

```
#Safety^Public safety <= downtown core: (
    %Cars cause most injuries <= most serious injuries downtown involve private cars@cars are the main danger
) >> removing the cars makes downtown safer as safety

#Plan <= downtown core: (
    $safety
) >> the city should adopt the plan as plan

#Objection^Access <= downtown core: (
    %Some people depend on cars <= some people with disabilities depend on cars@the plan harms them
) >> not the city should adopt the plan as objection

:: priority $plan > $objection
```

A statutory requirement (the wording of a statute, 「…」 in Japanese) can be written `"public use"` in Matcha-D, e.g. `"public use" <= the stadium is open to everyone@a public use`. Only at the start of an element is `"` the requirement notation; elsewhere it is ordinary text (`the sign said "closed"` stays a fact). In a `.mext` file, quote a text that contains `"` with `'…'` or write `\"`.

Pitfalls in English text: a line ending in "… as drivers" is read as a label (`as` names an element), and an element starting with `"` or 「 is read as a statutory requirement (if a fact begins with a quotation, use curly quotes “…”); the syntax checker warns about both. See `skills/matcha-analysis/references/writing_matcha.md` (in Japanese) for how to transcribe documents.

## Lean

- `mext lean` writes, for each Extension E, a derivation of E (a certificate) and a proof by `decide +kernel` that `checkCert T E cert = true` (since 0.6.0). Lean checks that E is consistent, that E contains W and is closed under the rules and the defaults whose justifications are consistent with E, and that using the steps of the certificate in order from W yields E.
- `lean/MextSpec.lean` (no Mathlib needed; plain Lean 4) proves the soundness theorem `Mext.checkCert_sound`: the check implies Reiter's definition of an Extension (E is consistent, contains W, and is the least set closed under the rules and the defaults whose justifications are consistent with E). It depends only on Lean's standard axioms (propext, Classical.choice, Quot.sound).
- `mext lean --import-spec MODULE` writes proofs that go on to `Mext.ReiterExtension T E` via the soundness theorem.
- The method up to 0.5, which recomputes Γ(E) inside Lean, is available as `mext lean --gamma` (soundness theorem `Mext.isExtension_sound`). On a theory with about 210 atoms, 220 rules and 70 defaults, it took 89 s and about 12 GB; the certificate method took 11 s and about 2.4 GB.
- What this shows is that each enumerated set is an Extension (soundness). That the enumeration is complete, and which Extensions are preferred, rest on mext's algorithms.

## Tests

```bash
python3 tests/run_tests.py       # syntax checker
python3 tests/run_mext_tests.py  # Extensions
python3 tests/run_tool_tests.py  # analysis commands, and English output
```

`tests/corpus/` quotes Matcha code from Elecode's "Matchaとは" and Mr. Hanafusa's blog for testing (each file names its source; copyright belongs to the original authors).

## Background

This package was made for the IPYNB report "Neuro-symbolic legal reasoning with Matcha and Wallerstein's world-systems theory: reading irregular labor in the periphery through default logic" (in Japanese): https://github.com/JRF-2018/wallerstein_theory

## Changelog

See [CHANGELOG.md](CHANGELOG.md) (in Japanese).

## Author

JRF ( http://jrf.cocolog-nifty.com/statuses , Twitter (X): @jion_rockford )

## AI

Mostly written by Claude Opus 5.5, drawing also on conversations with Grok 4.7 and Gemini 3.6 Flash.

## License

MIT License ([LICENSE](LICENSE)).
