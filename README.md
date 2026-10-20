# mext

Matcha の法的推論コードをデフォルト論理として読む道具一式。内容は、構文チェッカ、Reiter／優先度付き Extension の計算・検証（Lean 証明つき）、Claude Code スキル（任意の文書の論証を分析する「mext分析」「matcha分析」を含む）。

*Read Matcha legal-reasoning code as default logic: a syntax checker, a Reiter/prioritized extension solver with Lean certificates, and Claude Code skills for neuro-symbolic argument review of any document.*

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
mext snapshot X.mext && （X.matcha を直す） && mext solve X.mext && mext diff X.v1.mext X.mext
                                                  # 書き起こしを直す前後の、帰結・依存・審査の差
```

- **感度分析**（`sensitivity`）は、争いうる前提（評価、主張、`[extra]` で足した前提など）を一つずつ、または組で外して Extension を計算し直す。そして結論ごとに、外すと成り立たなくなる前提、外すと否定が成り立つ前提、AI が doubtful とした評価のうち結論が依存しているものを示す。「Extension が一つで結論が出た」ことが、何に支えられているかを見るためのものである。
- **検証の範囲**: `solve`・`report`・`summary` は、評価の審査の内訳と、理論の中に対立する命題（否定）を持たない最終的な結論の数を表示する。「Extension が一つで、すべての結論が成り立つ」という見栄えは、反対の根拠が書かれていないだけのことがあるからである。
- **concern / distinct**: 同じ結論を支える経路が複数あっても、それが独立した根拠か、同じ弱点の言い換えかは計算では分からない。この判断を AI が `[ai]` に書くと、感度分析と summary がそれを使って「経路は三本でも弱点は一つ」などと示す。
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
python3 tests/run_tool_tests.py  # sensitivity / lint / diff / snapshot の回帰テスト
```

`tests/docs/` には、スキル mext-analysis / matcha-analysis を試すための文書（自作の架空の事案・論説・小論）がある。その実行結果は `examples/analysis/` にある。

`tests/corpus/` には、Elecode「Matchaとは」と花房孟胤氏のブログの Matcha コードを、試験のために引用している（各ファイルの先頭に引用元を記す。著作権は原著者に帰属する）。

## 背景

本パッケージは、IPYNB のレポート「Matcha を使った neuro-symbolic な法的推論とウォーラーステイン理論 ―― デフォルト論理で読む周辺の非正規労働」のために作られた。

- https://github.com/JRF-2018/wallerstein_theory

## 変更履歴

- **0.3.2**（2026-10-20）
  - 感度分析と summary で、「単独で外すと成り立たなくなる」前提と「組の一員（これ一つを外しても残る）」前提を分けて示すようにした（以前は doubtful の一覧で両者を混同していた）。
  - `[ai]` に `concern`（内容の上で一つの争点を共有する前提）と `distinct`（互いに独立な前提）を加えた。感度分析は concern をまとめて外した場合も計算し、独立した経路について「弱点は一つ」「補い合う独立した根拠」「未判断」を添える。
  - 結論を直接導く唯一の主張があると、自動の拡張が経路の組を探さない不具合を直した。
  - 手引きに、複数の理由で同じ結論を支える書き方（冗長性・累積・相互補強）を足した。
- **0.3.1**（2026-10-20）
  - 「検証の範囲」（評価の審査の内訳、対立する命題のない最終的な結論の数）を、`solve`・`[summary]`・`report` に出すようにした。
  - コマンド `summary`（一画面の要約）を追加した。
  - `sensitivity` の既定を `--size auto` にした。大きさ 2 までで依存が見つからない結論は、支持の組を集めてそのすべてと交わる組を大きさ 4 まで調べる。独立した経路から一つずつ外す形は積の形でまとめる。結論ごとに「調べた範囲」を示す。
  - スキル mext-analysis のレポートの §0 を、summary と検証の範囲にもとづいて書くようにした。
- **0.3.0**（2026-10-20）
  - コマンド `sensitivity`（感度分析）、`lint`（書き起こしの粗さの検査）、`diff`（版の意味の差分）、`snapshot`（版の保存）を追加した。
  - スキル mext-analysis / matcha-analysis に、lint を受けて書き起こしを磨き上げる手順（版の保存・差分・改訂の記録。結論のための書き直しは禁止）と、感度分析にもとづいて「何に依存しているか」を書く手順を入れた。
  - 手引き（writing_matcha.md）に、引用と賛同の分け方、`^根拠` が表示であって立証される前提ではないこと、同語反復の評価や弱い主張の強め書きを避けることを足した。
  - `[ai]` の審査が書き起こしの変更で外れたとき、同じ「@評価」を持つ原子を付け替えの候補として示すようにした。
  - 0.2.0 で入れた `$ラベル` の連結を、参照先が主張のときだけに限った（規範を使い回す原典の書き方では結ばない）。
- **0.2.0**（2026-10-20）
  - スキル `mext-analysis`（mext分析）と `matcha-analysis`（matcha分析）を追加した。任意の文書の論証を Matcha に書き起こして分析する。
  - 要件の位置に書いた `$ラベル` が主張を指すとき、その主張と必要十分に結ぶようにした（主張の連鎖。例 `examples/chain.matcha`）。規範を指す `$名前`（原典の用例。規範を別の事実に使い回す）は従来どおり結ばない。
  - 文法の文書で、`as`・`$`・`::`・`//` が原典（花房氏の連載）の用例にあることを明記し、Matcha-D が足したもの（`!>`、`>> not`・`>> !`、`:: 優先`、主張への `as`）と区別した。
  - `(A & B)@評価` の評価の原子の文言を、行番号ではなく事実の中身から作るようにした（以前の「（L7 の事実群）@評価」の文言も別名として引ける）。
  - `[ai]` の `same` / `neg` に原子の文言を書いたのに「別名です」と注意が出ることがある不具合を直した。
- **0.1.0**（2026-10-19）: 最初の公開。

## Author (文責)

JRF ( http://jrf.cocolog-nifty.com/statuses , Twitter (X): @jion_rockford )


## AI

Claude Opus 5.5 がほとんどを書いた。Grok 4.7 および Gemini 3.6 Flash との会話も参考にしている。

## ライセンス

MIT License（[LICENSE](LICENSE)）.
