# mext

**AI が文書の論証を読んだ結果を、人が監査できる形にする道具。** AI は、文書（論説・判決・契約・評論・ブログなど）の論証を、法的推論の形式言語 Matcha に書き起こす。mext はそれをデフォルト論理として決定論的に計算する。AI の解釈はすべて理由つきでファイルに残り、機械「的」に変換された部分は人がたどれる。

内容は、Matcha の構文チェッカ、Reiter／優先度付き Extension の計算・検証（Lean 証明つき）、感度分析・読みの比較などの分析コマンド、そして Claude Code スキル（任意の文書の論証を分析する「mext分析」「matcha分析」、読みを比べる「mext-compare」など）。

*mext makes an AI's reading of an argument auditable: the AI transcribes the argument of any document into the legal-reasoning language Matcha, and mext computes it deterministically as default logic, so that every interpretive judgment is recorded with its reason and every mechanical step can be traced.* **English: [README.en.md](README.en.md)**

> **注意**
> - [Matcha](https://www.elecode.jp/matcha) は花房孟胤氏による法的推論の形式言語である。本リポジトリはその文法を、公開されている用例から読み取って実装したものである。
> - 本リポジトリの例外記法 **Matcha-D（`!>` / `>> not`・`>> !` / `:: 優先`、主張への `as` 名前付け、英文のための `"要件"`）は非公式の拡張で、Elecode／花房氏とは無関係である**。
> - 名前付けの `as`・参照の `$`・見出しの `::`・コメントの `//` は、花房氏の連載の用例にあるものを使っている（詳しくは [docs/matcha_grammar.md](docs/matcha_grammar.md) §1・§5）。

## なぜ mext か

AI に「この文書の論証は正しいか」と聞けば、もっともらしい答えが返ってくる。けれども、その答えがどの読みと、どの判断に依存しているかは、文章からは見えない。mext は AI の分析を、人が疑える単位に分ける。

- **AI の判断を表に出す**: 書き起こしの各行に、原文の出典（引用）を付ける。補った前提、落としたもの、結び方（AND / OR）が原文に明示されているか読みかを記録する。「事実@評価」の評価の審査（ok / doubtful / reject）、命題の同一・否定などの判断は、すべて `.mext` の `[ai]` に理由つきで書く。
- **機械「的」な部分を人が追える**: Matcha からデフォルト理論への変換、Extension の計算と検証は決定論的で、同じ入力からは同じ結果が出る。どの結論がどの規則と評価から導かれたかを `explain` でたどれ、計算そのものは Lean で検査できる。形式化の意義は、この部分を人が追いやすいことにある。
- **何に依存しているかを計算で示す**: 感度分析は、どの評価や補った前提を外すと結論が崩れるかを示す。あわせて、対立する命題のない結論の数、未審査や doubtful の評価の数、結論を左右する結び方など、「結果を強く読みすぎない」ための検証の範囲を必ず出す。
- **読みどうしを比べる**: 同じ文書を別々の AI や人が書き起こした読みを突き合わせ、両方に共通する弱点（原文の論証の争点の候補）と、一方の読みでしか現れない結果（書き起こしの選択の結果）を分ける。
- **手順を点検する**: `mext audit` が、出典・メモ・事前の予測・審査などの記録の抜けを一覧にし、`mext lint` が書き起こしの粗さ（同語反復の評価、原文に見当たらない引用など）を知らせる。

mext は論証の「正しさ」を判定しない。示すのは、書き起こした理論の中で何が導け、それが何に依存しているかであり、そのうえで原文に戻るべき箇所を指す。Claude（Opus・Sonnet・Haiku）と Codex（GPT-6.1-Sol）で試してきた。試験の記録の一部は [examples/analysis/](examples/analysis/) にある。

## 何をするか

```
文書 ──(AI: matcha分析)──▶ .matcha
.matcha ──(構文チェック)──▶ 構文木 ──(決定論的な変換)──▶ デフォルト理論 (W, R, D, <)
                                                        │
              AI の判断（[ai]: 同一・否定・評価の審査）─┤
                                                        ▼
                          Extension の全列挙・preferred の選択・検証 ──▶ Lean 証明（Γ(E) = E）
```

- **決定論的な部分**（このパッケージ）が受け持つもの:
  - 構文チェック
  - Matcha からデフォルト理論への変換。要件は必要十分条件として読み、例外 `!>` は優先順位と正当化の阻却として読む。
  - Reiter の Extension の全列挙（Gelfond & Lifschitz 1991 の拡張論理プログラムとの対応による）
  - 優先順位を尊重する preferred Extension の選択（Brewka & Eiter 1999 の考え方による）
  - 主張された Extension の検証と、導出の根拠・不成立の理由の説明
  - Lean 証明の出力
- **AI の部分**（スキル `mext-analysis`、`matcha-analysis`、`matcha-default-extensions`、`mext-compare`）が受け持つもの:
  - 文書の論証を Matcha に書き起こすこと（原文との対応表、補った前提、落としたものを記録する）
  - 命題の同一・否定の判断
  - 結論の型（成立の効果か、不成立からの帰結か）の判断
  - 「事実@評価」のあてはめの実質審査
  - Extension の予測と、「論証は正しいか」のレポート
  - 同じ文書の二つの読みの対応づけと、違いの解釈（読みの比較）

  AI の判断は、すべて MEXT ファイルの `[ai]` 節に理由とともに書かれ、人が監査できる。

## インストール

### Python パッケージ（依存なし、Python 3.8 以降）

```bash
pip install git+https://github.com/JRF-2018/mext
```

`matcha-check` と `mext` のコマンドが入る（`python3 -m mext.matcha_check`、`python3 -m mext` でも呼べる）。pip が「externally-managed-environment」で入らない環境では、`python3 -m venv` で venv を作って入れるか、clone したディレクトリを `PYTHONPATH` に加えて `python3 -m mext` で動かす（依存ライブラリはない）。

### Claude Code のプラグイン（スキル 4 つ）

```bash
claude plugin marketplace add JRF-2018/mext
claude plugin install mext@jrf-mext
```

あるいは、`skills/` の中の四つのディレクトリを、プロジェクトの `.claude/skills/` か `~/.claude/skills/` にコピーしてもよい（スキルどうしが手順を参照するので、すべてコピーする）。スキルは `python3 -m mext` を呼ぶので、上の Python パッケージも入れておく。

## スキル

| スキル | 頼み方の例 | 入力 → 出力 |
|---|---|---|
| `mext-analysis`（mext分析） | 「この文書を mext分析して」 | 任意の文書 → `X.matcha`、`X.mext`、レポート `X.mext-analysis.md` |
| `matcha-analysis`（matcha分析） | 「この文書を matcha分析して」 | 任意の文書 → `X.matcha`、メモ `X.matcha.md`（原文との対応表・補った前提・落としたもの） |
| `matcha-default-extensions` | 「X.matcha の Extension を調べて」 | `.matcha` → `X.mext`、レポート `X.report.md` |
| `mext-compare`（読みの比較） | 「この二つの読みを比べて」 | 同じ文書の `A.mext` と `B.mext` → 比較のファイル `A.vs.B.compare`、レポート `A.vs.B.compare.md` |

- **mext分析**は、文書の論証を Matcha に書き起こし（matcha分析）、デフォルト論理として Extension を計算・検証し、「この文書の論証は形式的に妥当か、実質的に説得的か、何に依存しているか」を述べるレポートを返す。法律の文書に限らず、論説、評論、企画書などにも使える。文書が大きいときは、レポートの長さ（要点／標準／詳細）を先に聞く。
- 決定論的なのは mext の部分（構文チェック、変換、Extension、Lean）だけで、書き起こしと審査は AI の判断である。そのため、書き起こしのどの行が原文のどこから来たか、AI が何を補い、何を落とし、どう評価したかを、すべてファイルに残す。
- 書き起こしは AI の解釈なので、スキルは `lint` の警告を受けて書き起こしを磨き上げる手順を踏む。書き直す前の版は `snapshot` で残し、`diff` で前後を比べ、何を受けて何を直したかを記録する。書き直してよいのは原文への忠実さと粒度を上げるためだけで、結論を出す（消す）ための書き直しは禁じている。
- **読みの比較**は、同じ文書を別々に（別の AI や人が）書き起こした二つの読みを突き合わせ、どこで読みが分かれ、それが結論の成否や依存をどう変えるかを、原文に照らして述べる。両方の読みで同じ前提が決め手なら、それは原文の論証の弱点である見込みが高く、一方の読みでしか現れない結果は、書き起こしの選択による見込みが高い。
- 試した例は [examples/analysis/](examples/analysis/) にある。

### 英語での利用

英語の文書を英語で頼めば、書き起こし・メモ・レポート・会話への返答は英語になる（例: [examples/analysis/car_free_op/](examples/analysis/car_free_op/)）。mext の出力（構文チェッカの診断、report、summary、sensitivity など）も、`--lang en` を付けるか環境変数 `MEXT_LANG=en` にすれば英語になる（0.4.0 以降。既定は日本語）。ロケール（`LANG` など）は見ない。AI のサンドボックスや Colab などでは、ロケールが利用者の言語を表さないことが多いためである。`[ai]` の語彙（`explicit`/`reading`、`description`/`assumption`/`verified`/`author-claim`）と優先順位の記法（`:: priority $a > $b`）も英語で書ける。英語の説明は [README.en.md](README.en.md)。

### AI に頼むとき

スキルを入れていない環境や、ほかの AI に頼むときは、次のように言えばよい。

> https://github.com/JRF-2018/mext を使って、この文書を mext分析してください。

**AI の方へ**: そう頼まれたら、このリポジトリの [skills/mext-analysis/SKILL.md](skills/mext-analysis/SKILL.md) を読み、その手順に従ってください（書き起こしだけを頼まれたら [skills/matcha-analysis/SKILL.md](skills/matcha-analysis/SKILL.md)）。道具は `pip install git+https://github.com/JRF-2018/mext` で入ります。Python を実行できない環境では、決定論的な部分（Extension の計算）を実行できなかったことをレポートに明記し、予測だけを `[claimed]` として示してください。

## 使い方

```bash
matcha-check --tree examples/tweety.matcha        # 構文チェックと構文木
mext init examples/tweety.matcha                  # ひな形 tweety.mext（Extension はまだ計算しない）
mext solve examples/tweety.mext                   # Extension を計算して書き込む
mext report examples/tweety.mext                  # Markdown の表
mext explain examples/tweety.mext E2 "¬トゥイーティーは飛ぶ"
mext verify examples/tweety.mext [--skeptical]    # [claimed] に書いた Extension を検証
mext lean examples/tweety.mext                    # Lean 証明（lean で検査できる。Mathlib 不要）
mext summary examples/sublease.mext               # 一画面の要約: 最終的な結論・対立する命題・決め手・争点・検証の範囲
mext sensitivity examples/sublease.mext           # 感度分析: 結論ごとに、どの前提を外すと成り立たなくなるか
mext lint examples/sublease.mext                  # 書き起こしの粗さの検査
mext connectives examples/sublease.mext           # 結び方の感度: AND / OR を入れ替えると何が変わるか
mext audit X.mext                                 # 分析の手順の抜けの点検（✓ / ✗ / －）
mext changed X.check.mext                         # 書き起こしの後に .matcha やメモが変わったか
mext snapshot X.mext && （X.matcha を直す） && mext solve X.mext && mext diff X.v1.mext X.mext
                                                  # 書き起こしを直す前後の、帰結・依存・審査の差
mext compare --init A.mext B.mext -o A.vs.B.compare && （[match] を書く） && mext compare A.vs.B.compare
                                                  # 同じ文書の二つの読みの、結論ごとの成否・決め手・依存の違い
```

- **感度分析**（`sensitivity`）は、争いうる前提（評価、主張、`[extra]` で足した前提など）を一つずつ、または組で外して Extension を計算し直す。そして結論ごとに、外すと成り立たなくなる前提、外すと否定が成り立つ前提、AI が doubtful とした評価のうち結論が依存しているものを示す。「Extension が一つで結論が出た」ことが、何に支えられているかを見るためのものである。
- **検証の範囲**: `solve`・`report`・`summary` は、評価の審査の内訳と、理論の中に対立する命題（否定）を持たない最終的な結論の数を表示する。「Extension が一つで、すべての結論が成り立つ」という見栄えは、反対の根拠が書かれていないだけのことがあるからである。
- **connectives**: AND / OR を一つずつ入れ替えて、帰結と依存の変化を示す。日本語の文章では結び方が明示されないことが多いので、根拠を書かせる代わりに、「明示か読みか」を `[ai]` に記録させ、結論を左右する読みの結び方を指す。
- **concern / distinct**: 同じ結論を支える経路が複数あっても、それが独立した根拠か、同じ弱点の言い換えかは計算では分からない。この判断を AI が `[ai]` に書くと、感度分析と summary がそれを使って「経路は三本でも弱点は一つ」などと示す。
- **audit** は、分析の手順の抜け（書き起こしの記録、未審査の評価、未記録の結び方、予測の検証、出力のファイルなど）を一覧にする。スキルは最後にこれを回し、✗ をなくすか、なくせない理由をレポートに書く。手順を守ったかの点検を、スキルの指示の文章ではなく道具に任せるためのものである。
- **summary** は、最終的な結論ごとの成否・対立する命題の有無・決め手になる前提と、争点（結論が依存している doubtful の評価）を一画面にまとめる。全表と全導出への入口である。
- **lint** は、同語反復の評価（`%A <= 事実@A`）、結論の文言の書き写し、立証の手段のない要件など、書き起こしの粗さを知らせる。
- **compare** は、同じ文書の二つの読みを比べる。原子の文言は読みごとに違う（言語が違うこともある）ので、どの結論・前提が対応するかは AI か人が比較のファイルの `[match]` に理由つきで書き、道具は対応ごとに成否・決め手・共通の決め手・補った前提への依存・結び方・独立した経路を比べる。文言が同じものは自動で対応づける。
- **diff** は、原子を番号ではなく文言で対応づけて比べる。書き起こしを直すと原子の番号や行番号がずれるので、普通の diff では、論証の何が変わったか（どの結論が否定に転じたか、何に依存するようになったか、どの審査が外れたか）が読めないためである。

Claude Code では次のように使う。プラグインとして入れた場合は、プラグイン名の名前空間が付く。

```
/mext:mext-analysis tests/docs/yatoidome_memo.md
/mext:matcha-analysis tests/docs/remote_work_op.md
/mext:matcha-default-extensions examples/self_defense.matcha
```

スキルを `.claude/skills/` などにコピーした場合は、`/mext-analysis …` のように名前空間なしになる。「この文書を mext分析して」と普通に頼んでもよい。

複数の `.matcha` を一つの理論にまとめる場合は `mext init A.matcha B.matcha -o X.mext` とする。構文チェックは `matcha-check --shared-labels A.matcha B.matcha` で行う。

## Matcha-D の例

```
#飛行^鳥の通念 <= トゥイーティー: (
    %鳥である <= トゥイーティーは鳥である
) >> トゥイーティーは飛ぶ as 鳥は飛ぶ

#非飛行^ペンギンの通念 <= トゥイーティー: (
    %ペンギンである <= トゥイーティーはペンギンである
) >> !トゥイーティーは飛ぶ as ペンギン例外 !> $鳥は飛ぶ
```

`mext solve` の結果は、Reiter の Extension が 2 個、preferred Extension が 1 個（ペンギン例外が勝つ）になる。

英文では、法文上の文言の要件「…」を `"public use"` のように ASCII の二重引用符でも書ける（Matcha-D、0.5.0 以降）。要素の先頭に置いたときだけ要件の記法になる。`.mext` の中では、`"` を含む文言を `'…'` で囲むか `\"` と書く。

## 文書

- [docs/matcha_grammar.md](docs/matcha_grammar.md): Matcha / Matcha-D の文法（EBNF とレイアウトの規則）
- [docs/mext.md](docs/mext.md): MEXT（Matcha EXTension notation）の書式、変換規則、Extension と preferred の定義

## Lean

- `mext lean` は、各 Extension E について、Γ(E) を計算する関数で `isExtension T E = true` を `decide +kernel` で示すファイルを出力する。
- `lean/MextSpec.lean`（Mathlib を使う）には、その Bool の判定が Reiter の Extension の定義（E は無矛盾で、W を含み、規則と正当化が E と無矛盾なデフォルトとで閉じた最小の集合）を導く、という健全性定理 `Mext.isExtension_sound` がある。
- `mext lean --import-spec MODULE` とすると、その健全性定理を使って `Mext.ReiterExtension T E` まで示すファイルを出力する。

## テスト

```bash
python3 tests/run_tests.py       # 構文チェッカの回帰テスト
python3 tests/run_mext_tests.py  # Extension の回帰テスト
python3 tests/run_tool_tests.py  # 分析コマンド（sensitivity / lint / diff / audit など）と英語の出力の回帰テスト
```

`tests/docs/` には、スキル mext-analysis / matcha-analysis を試すための文書（自作の架空の事案・論説・小論）がある。その実行結果は `examples/analysis/` にある。

`tests/corpus/` には、Elecode「Matchaとは」と花房孟胤氏のブログの Matcha コードを、試験のために引用している（各ファイルの先頭に引用元を記す。著作権は原著者に帰属する）。

## 背景

本パッケージは、IPYNB のレポート「Matcha を使った neuro-symbolic な法的推論とウォーラーステイン理論 ―― デフォルト論理で読む周辺の非正規労働」のために作られた。

- https://github.com/JRF-2018/wallerstein_theory

## 変更履歴

[CHANGELOG.md](CHANGELOG.md) を参照。

## Author (文責)

JRF ( http://jrf.cocolog-nifty.com/statuses , Twitter (X): @jion_rockford )


## AI

Claude Opus 5.5 がほとんどを書いた。Grok 4.7 および Gemini 3.6 Flash との会話も参考にしている。

## ライセンス

MIT License（[LICENSE](LICENSE)）.
