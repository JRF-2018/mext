# mext

Matcha の法的推論コードをデフォルト論理として読む道具一式。内容は、構文チェッカ、Reiter／優先度付き Extension の計算・検証（Lean 証明つき）、Claude Code スキル（任意の文書の論証を分析する「mext分析」「matcha分析」を含む）。

*Read Matcha legal-reasoning code as default logic: a syntax checker, a Reiter/prioritized extension solver with Lean certificates, and Claude Code skills for neuro-symbolic argument review of any document.* **English: [README.en.md](README.en.md)**

> **注意**
> - [Matcha](https://www.elecode.jp/matcha) は花房孟胤氏による法的推論の形式言語である。本リポジトリはその文法を、公開されている用例から読み取って実装したものである。
> - 本リポジトリの例外記法 **Matcha-D（`!>` / `>> not`・`>> !` / `:: 優先`、および主張への `as` 名前付け）は非公式の拡張で、Elecode／花房氏とは無関係である**。
> - 名前付けの `as`・参照の `$`・見出しの `::`・コメントの `//` は、花房氏の連載の用例にあるものを使っている（詳しくは [docs/matcha_grammar.md](docs/matcha_grammar.md) §1・§5）。

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
- **AI の部分**（スキル `mext-analysis`、`matcha-analysis`、`matcha-default-extensions`）が受け持つもの:
  - 文書の論証を Matcha に書き起こすこと（原文との対応表、補った前提、落としたものを記録する）
  - 命題の同一・否定の判断
  - 結論の型（成立の効果か、不成立からの帰結か）の判断
  - 「事実@評価」のあてはめの実質審査
  - Extension の予測と、「論証は正しいか」のレポート

  AI の判断は、すべて MEXT ファイルの `[ai]` 節に理由とともに書かれ、人が監査できる。

## インストール

### Python パッケージ（依存なし、Python 3.8 以降）

```bash
pip install git+https://github.com/JRF-2018/mext
```

`matcha-check` と `mext` のコマンドが入る（`python3 -m mext.matcha_check`、`python3 -m mext` でも呼べる）。

### Claude Code のプラグイン（スキル 3 つ）

```bash
claude plugin marketplace add JRF-2018/mext
claude plugin install mext@jrf-mext
```

あるいは、`skills/` の中の三つのディレクトリを、プロジェクトの `.claude/skills/` か `~/.claude/skills/` にコピーしてもよい（`mext-analysis` はほかの二つの手順を参照するので、三つともコピーする）。スキルは `python3 -m mext` を呼ぶので、上の Python パッケージも入れておく。

## スキル

| スキル | 頼み方の例 | 入力 → 出力 |
|---|---|---|
| `mext-analysis`（mext分析） | 「この文書を mext分析して」 | 任意の文書 → `X.matcha`、`X.mext`、レポート `X.mext-analysis.md` |
| `matcha-analysis`（matcha分析） | 「この文書を matcha分析して」 | 任意の文書 → `X.matcha`、メモ `X.matcha.md`（原文との対応表・補った前提・落としたもの） |
| `matcha-default-extensions` | 「X.matcha の Extension を調べて」 | `.matcha` → `X.mext`、レポート `X.report.md` |

- **mext分析**は、文書の論証を Matcha に書き起こし（matcha分析）、デフォルト論理として Extension を計算・検証し、「この文書の論証は形式的に妥当か、実質的に説得的か、何に依存しているか」を述べるレポートを返す。法律の文書に限らず、論説、評論、企画書などにも使える。文書が大きいときは、レポートの長さ（要点／標準／詳細）を先に聞く。
- 決定論的なのは mext の部分（構文チェック、変換、Extension、Lean）だけで、書き起こしと審査は AI の判断である。そのため、書き起こしのどの行が原文のどこから来たか、AI が何を補い、何を落とし、どう評価したかを、すべてファイルに残す。
- 書き起こしは AI の解釈なので、スキルは `lint` の警告を受けて書き起こしを磨き上げる手順を踏む。書き直す前の版は `snapshot` で残し、`diff` で前後を比べ、何を受けて何を直したかを記録する。書き直してよいのは原文への忠実さと粒度を上げるためだけで、結論を出す（消す）ための書き直しは禁じている。
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
```

- **感度分析**（`sensitivity`）は、争いうる前提（評価、主張、`[extra]` で足した前提など）を一つずつ、または組で外して Extension を計算し直す。そして結論ごとに、外すと成り立たなくなる前提、外すと否定が成り立つ前提、AI が doubtful とした評価のうち結論が依存しているものを示す。「Extension が一つで結論が出た」ことが、何に支えられているかを見るためのものである。
- **検証の範囲**: `solve`・`report`・`summary` は、評価の審査の内訳と、理論の中に対立する命題（否定）を持たない最終的な結論の数を表示する。「Extension が一つで、すべての結論が成り立つ」という見栄えは、反対の根拠が書かれていないだけのことがあるからである。
- **connectives**: AND / OR を一つずつ入れ替えて、帰結と依存の変化を示す。日本語の文章では結び方が明示されないことが多いので、根拠を書かせる代わりに、「明示か読みか」を `[ai]` に記録させ、結論を左右する読みの結び方を指す。
- **concern / distinct**: 同じ結論を支える経路が複数あっても、それが独立した根拠か、同じ弱点の言い換えかは計算では分からない。この判断を AI が `[ai]` に書くと、感度分析と summary がそれを使って「経路は三本でも弱点は一つ」などと示す。
- **audit** は、分析の手順の抜け（書き起こしの記録、未審査の評価、未記録の結び方、予測の検証、出力のファイルなど）を一覧にする。スキルは最後にこれを回し、✗ をなくすか、なくせない理由をレポートに書く。手順を守ったかの点検を、スキルの指示の文章ではなく道具に任せるためのものである。
- **summary** は、最終的な結論ごとの成否・対立する命題の有無・決め手になる前提と、争点（結論が依存している doubtful の評価）を一画面にまとめる。全表と全導出への入口である。
- **lint** は、同語反復の評価（`%A <= 事実@A`）、結論の文言の書き写し、立証の手段のない要件など、書き起こしの粗さを知らせる。
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
