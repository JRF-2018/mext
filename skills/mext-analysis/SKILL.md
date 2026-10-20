---
name: mext-analysis
description: 「mext分析」。任意の文書（法律の文書に限らない）の論証を、Matcha / Matcha-D に書き起こし（matcha分析）、デフォルト論理として読んで Extension を計算・検証し（MEXT）、「この文書の論証は正しいか」を述べる Markdown のレポート（X.mext-analysis.md）を返す。「mext分析して」「https://github.com/JRF-2018/mext を使って分析して」「この文書の論証をデフォルト論理で検査して」と頼まれたときに使う。すでに .matcha がある場合は matcha-default-extensions を使う。
---

# mext-analysis（mext分析）

文書の論証を、(1) Matcha に書き起こし、(2) デフォルト論理として計算・検証し、(3) 「形式的に導けるか、実質的に説得的か、何に依存しているか」を述べるレポートにする。

決定論的なのは mext の部分だけで、書き起こしと審査はあなた（AI）の判断である。だから、**あなたの判断はすべてファイルに残す**（書き起こしの判断はメモに、審査の判断は `.mext` の `[ai]` に）。手順を守ったかの点検は、最後に `mext audit` が行う。

## 準備

- `python3 -m mext --help` が動くかを確かめる。動かなければ `pip install git+https://github.com/JRF-2018/mext`（プラグインなら、このスキルの 2 つ上のディレクトリを `PYTHONPATH` に加えてもよい）。
- 参照する文書（必要なときに読む）:
  - `../matcha-analysis/SKILL.md`: 書き起こしの手順
  - `../matcha-default-extensions/references/ai_judgments.md`: `[ai]` の判断の書き方
  - `../matcha-default-extensions/references/reading_results.md`: **出力の読み方**（レポートを書く前に必ず読む）
  - `../matcha-default-extensions/references/report_templates.md`: レポートの章立て
  - `references/existing_transcriptions.md`: すでに書き起こしがある場合
- 手元にこれらがない場合（ほかの AI など）は、https://github.com/JRF-2018/mext の `skills/` を読む。
- 引数は文書のファイル `X.md`（貼られた文章なら `X.source.md` として保存する）。出力は同じディレクトリに置き、原文は書き換えない。
- 会話への返答もファイルも、**利用者の言語で**書く（最初の一文から）。
- 利用者の言語が英語なら、mext のコマンドに `--lang en` を付けるか `MEXT_LANG=en` にする（道具の出力も英語になる）。

## 手順

1. **長さを決める**: 文書が 5,000 字未満で主な結論が 3 つ以下なら「標準」。それより大きければ、聞けるなら「要点・標準・詳細」を聞く（聞けなければ「標準」にし、そう書く）。
2. **既存の書き起こしを確かめる**: `X.matcha` がすでにあれば、`references/existing_transcriptions.md` に従う（人が直していたら、その版を正として原文から組み立て直す。上書きしない）。
3. **matcha分析**: `../matcha-analysis/SKILL.md` に従い、`X.matcha` とメモ `X.matcha.md` を作る（事前の予測、lint による磨き上げを含む）。
4. **MEXT**:

   ```bash
   python3 -m mext init X.matcha
   # [ai] に書く: メモの判断を移す（結び方 → connective、事実の種別 → fact-kind、補った前提 → supplied）
   #              そのうえで same / neg / failure / effect / review を理由つきで（ai_judgments.md）
   # [claimed] に、メモの「事前の予測」を写す（新しく予測しない）
   python3 -m mext solve X.mext
   python3 -m mext summary X.mext -o X.summary.md
   python3 -m mext sensitivity X.mext -o X.sensitivity.md
   python3 -m mext connectives X.mext -o X.connectives.md
   python3 -m mext verify X.mext && python3 -m mext verify --skeptical X.mext
   python3 -m mext lean X.mext        # 任意
   ```

5. **原文に戻る**: summary の争点、結論を左右する結び方（読み・未記録）、補った前提に依存する結論、「独立した経路」（`concern` / `distinct` を判断する）について、原文を読み直す。判断が変われば `[ai]` を書き換え（注は `; 審査で改めた: …`）、解き直す。書き起こしの誤りに気づいたら、`snapshot` → 修正 → `solve` → `diff` で直し、メモの改訂の記録に書く（**結論のための書き直しはしない**）。試算は `X.alt-*.mext` に作る。
6. **点検**: `python3 -m mext audit X.mext`。✗ をなくすか、なくせない理由をレポートに書く。
7. **レポート**: `reading_results.md` を読んでから、`report_templates.md` の章立てで `X.mext-analysis.md` を書く。§0 は summary を土台にする。会話には §0 とファイルの一覧を返す。

## 守ること

- 数字と導出は mext の出力に従う。自分の推論で上書きしない。
- 原文にない主張を作らない。原文の論証を強くも弱くもしない。
- 書き起こしと審査を同じ AI がする限界を、レポートの総評で一言述べ、必要なら別の AI か人に `X.matcha` を見てもらうことを勧める。
- 道具の不具合と思われる挙動は、回避したうえで、レポートの末尾に「道具について」として書く。
