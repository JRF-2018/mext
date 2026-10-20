---
name: matcha-default-extensions
description: Matcha / Matcha-D（法的推論の形式言語 Matcha に例外記法を足したもの）のファイルをデフォルト論理として読み、構文チェック、原子命題化の判断、Extension の計算と検証、あてはめ（@評価）の実質的妥当性の審査を行い、「論証は正しいか」のレポート（X.report.md）と MEXT ファイル（X.mext）を作る。.matcha ファイルの Extension、デフォルト論理、論証のチェックを求められたときに使う。
---

# matcha-default-extensions

`.matcha` ファイルを、**決定論的なプログラム**（構文チェック、変換、Extension、Lean）と**あなた（AI）の判断**（同一視・否定・あてはめの審査など）に分けて検査する。あなたの判断は、すべて `.mext` の `[ai]` `[extra]` `[claimed]` に理由とともに書く。生成部分は手で直さない。

## 準備

- `python3 -m mext --help` が動くかを確かめる。動かなければ `pip install git+https://github.com/JRF-2018/mext`（プラグインなら、このスキルの 2 つ上のディレクトリを `PYTHONPATH` に加えてもよい）。
- 参照する文書（`references/`）:
  - `matcha_grammar.md`: 文法
  - `mext.md`: MEXT の書式と**変換規則**（判断の前に §2 を一度読む）、各コマンドの説明
  - `ai_judgments.md`: `[ai]` `[extra]` `[claimed]` の書き方
  - `reading_results.md`: **出力の読み方**（レポートを書く前に必ず読む）
  - `report_templates.md`: レポートの章立て
- 引数: `X.matcha`、一つの理論を成す複数の `.matcha`（`mext init A.matcha B.matcha -o X.mext`。構文チェックは `--shared-labels`）、または既存の `X.mext`（`[ai]` などを引き継ぐ）。`.matcha` は書き換えない。出力は `X.mext` と同じディレクトリに置く。
- 会話への返答もファイルも、**利用者の言語で**書く。
- 利用者の言語が英語なら、mext のコマンドに `--lang en` を付けるか `MEXT_LANG=en` にする（道具の出力も英語になる）。

## 手順

1. **構文チェック**: `python3 -m mext.matcha_check --tree X.matcha`。エラーがあれば、直し方の提案だけを `X.report.md` に書いて終える。
2. **ひな形**: `python3 -m mext init X.matcha`（Extension はまだ計算しない）。生成部分の `[atoms]` などで変換結果をつかむ。
3. **判断を書く**: `ai_judgments.md` に従い、`[ai]`（同一・否定・結論の型・審査など）と、必要なら `[extra]` を書く。迷う判断は書かずに保留する。
4. **予測**: **解く前に**、ありうる Extension を `[claimed]` に書く。
5. **求解と検証**:

   ```bash
   python3 -m mext solve X.mext
   python3 -m mext summary X.mext -o X.summary.md
   python3 -m mext sensitivity X.mext -o X.sensitivity.md
   python3 -m mext connectives X.mext -o X.connectives.md
   python3 -m mext verify X.mext && python3 -m mext verify --skeptical X.mext
   python3 -m mext explain X.mext E1 "主要な結論"    # 否定は ¬ を前に付ける
   python3 -m mext lean X.mext                      # lean があれば lean X.lean で確かめる
   ```

   `reject` があれば、審査を反映しない版 `X.asis.mext`（`cp` してから `solve --no-review`）と比べる。誤記の訂正や抗弁の立証などは試算 `X.alt-*.mext` で。
6. **点検**: `python3 -m mext audit X.mext`。✗ をなくすか、なくせない理由をレポートに書く。
7. **レポート**: `reading_results.md` を読んでから、`report_templates.md` の章立てで `X.report.md` を書く。

## 守ること

- 数字と導出は mext の出力に従う。自分の推論で上書きしない。
- 原典（`.matcha`）の誤記らしきものは直さずに指摘する（訂正は試算で）。
- 道具の不具合と思われる挙動は、回避したうえで、レポートの末尾に「道具について」として書く。
