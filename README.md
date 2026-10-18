# mext

Matcha の法的推論コードをデフォルト論理として読む道具一式。内容は、構文チェッカ、Reiter／優先度付き Extension の計算・検証（Lean 証明つき）、Claude Code スキル。

*Read Matcha legal-reasoning code as default logic: a syntax checker, a Reiter/prioritized extension solver with Lean certificates, and a Claude Code skill for neuro-symbolic argument review.*

> **注意**
> - [Matcha](https://www.elecode.jp/matcha) は花房孟胤氏による法的推論の形式言語である。本リポジトリはその文法を、公開されている用例から読み取って実装したものである。
> - 本リポジトリの例外記法 **Matcha-D（`as` / `!>` / `>> not`・`>> !` / `:: 優先`）は非公式の拡張で、Elecode／花房氏とは無関係である**。

## 何をするか

```
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
- **AI の部分**（スキル `matcha-default-extensions`）が受け持つもの:
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

### Claude Code のプラグイン（スキル matcha-default-extensions）

```bash
claude plugin marketplace add JRF-2018/mext
claude plugin install mext@jrf-mext
```

あるいは、`skills/matcha-default-extensions/` を、プロジェクトの `.claude/skills/` か `~/.claude/skills/` にコピーしてもよい。スキルは `python3 -m mext` を呼ぶので、上の Python パッケージも入れておく。

## 使い方

```bash
matcha-check --tree examples/tweety.matcha        # 構文チェックと構文木
mext init examples/tweety.matcha                  # ひな形 tweety.mext（Extension はまだ計算しない）
mext solve examples/tweety.mext                   # Extension を計算して書き込む
mext report examples/tweety.mext                  # Markdown の表
mext explain examples/tweety.mext E2 "¬トゥイーティーは飛ぶ"
mext verify examples/tweety.mext [--skeptical]    # [claimed] に書いた Extension を検証
mext lean examples/tweety.mext                    # Lean 証明（lean で検査できる。Mathlib 不要）
```

Claude Code では次のように使う。プラグインとして入れた場合は、プラグイン名の名前空間が付く。

```
/mext:matcha-default-extensions examples/self_defense.matcha
```

`skills/matcha-default-extensions/` を `.claude/skills/` などにコピーした場合は、`/matcha-default-extensions examples/self_defense.matcha` となる。

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
```

`tests/corpus/` には、Elecode「Matchaとは」と花房孟胤氏のブログの Matcha コードを、試験のために引用している（各ファイルの先頭に引用元を記す。著作権は原著者に帰属する）。

## 背景

本パッケージは、IPYNB のレポート「Matcha を使った neuro-symbolic な法的推論とウォーラーステイン理論 ―― デフォルト論理で読む周辺の非正規労働」のために作られた。

- https://github.com/JRF-2018/wallerstein_theory

## Author (文責)

JRF ( http://jrf.cocolog-nifty.com/statuses , Twitter (X): @jion_rockford )


## AI

Claude Opus 5.5 がほとんどを書いた。Grok 4.7 および Gemini 3.6 Flash との会話も参考にしている。

## ライセンス

MIT License（[LICENSE](LICENSE)）.
