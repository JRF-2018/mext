# mext分析・matcha分析の例

`tests/docs/` の文書（mext のテスト用に作った架空の事案・論説・小論）に、スキルを Claude Code CLI（`claude -p`、Claude Opus 5.5）で実行した結果である。非対話の実行なので、レポートの長さは聞かずに「標準」になっている。`reply.txt` は、そのとき AI が会話に返した文章である。

| ディレクトリ | スキル | 文書 | 最終的な出力 |
|---|---|---|---|
| `yatoidome_memo/` | mext-analysis | 契約社員の雇止めについての検討メモ（労働契約法 19 条） | `yatoidome_memo.mext-analysis.md` |
| `remote_work_op/` | mext-analysis | 論説「リモートワークを『原則』にせよ」 | `remote_work_op.mext-analysis.md` |
| `kindness_essay/` | mext-analysis（0.3.3） | 小論「なぜ見知らぬ人に親切にするのか」（架空の論者の見解の引用と賛同、弱い主張を含む） | `kindness_essay.mext-analysis.md`、`kindness_essay.summary.md`、`kindness_essay.connectives.md` |
| `kindness_human/` | mext-analysis（0.3.3）、人の改訂の後 | 上の書き起こしを、人（試験のための仮の人）が直した後に、もう一度 mext分析を頼んだもの。第5段落の留保を、賛同を覆す例外（`!> $賛同`）から、別の命題に改めた | `kindness_essay.mext-analysis.md`、`kindness_essay.matcha.proposed.md` |
| `car_free_op/` | mext-analysis（0.3.3）、英語 | 英語の架空の論説「Our city center should be car-free」を、英語で「https://github.com/JRF-2018/mext を使って mext analysis を」と頼んだもの（スキルを名指ししていない）。書き起こし・メモ・レポート・返答は英語、mext の出力は日本語のまま | `car_free_op.mext-analysis.md` |
| `deterministic_code_essay/` | matcha-analysis | 小論「AI に判断させるより、AI に書かせたコードに判断させよ」 | `deterministic_code_essay.matcha`、`deterministic_code_essay.matcha.md` |

各ディレクトリのファイル:

- `X.md`: 原文（入力）
- `X.matcha`: 書き起こし。各行の直前の `// 出典:` が原文の箇所を示す
- `X.matcha.md`: 書き起こしのメモ（対応表・書き起こしの判断・補った前提・落としたもの）
- `X.mext`: デフォルト理論と Extension。AI の判断は `[ai]` に理由つきで書かれている
- `X.alt-*.mext`: 試算（評価を退けた場合、反論が立証された場合など）
- `X.lean`: 各 Extension が Reiter の Extension であることの Lean 証明
- `X.mext-analysis.md`: 最終レポート
- `X.sensitivity.md`、`X.summary.md`、`X.connectives.md`: 感度分析・要約・結び方の感度。`kindness_*` ではスキルが作ってレポートに使った。`yatoidome_memo` と `remote_work_op` の `X.sensitivity.md` は、実行のあとに 0.3.0 の道具で作って足したもので、レポートには反映されていない

`remote_work_op` のレポート末尾の「道具について」で報告された不具合（`(A & B)@評価` の原子の文言に行番号が入る）は、この実行のあと mext 0.2.0 で直した。

`kindness_human` は、人が書き起こしを直した場合の手順の例である。mext分析は `mext changed` で書き起こしの変更を見つけ、人の書いた `.matcha` とメモには手を付けずに、今の書き起こしを正として分析し直した。新しいメモは `kindness_essay.matcha.proposed.md` として別に作り（非対話の実行なので、利用者に確かめられないため）、AI のもとの読みは試算 `alt-undercut` として並べた。

`kindness_essay` と `kindness_human` のレポート末尾の「道具について」で挙がった点のうち、次のものは 0.3.3 の公開前に直した: summary で、成り立たない結論に「反対の根拠が理論にない」と出ること、否定が成り立つ結論の決め手の列が空になること、`neg` を結論の素の文言（〔対象〕なし）で書くと効かないこと、主張の対象が事実の種別の「未分類」に数えられること。`changed` が差分を示さないのは設計どおりである（書き起こしの時点の記録としてハッシュ値だけを持つ）。

`car_free_op` のレポート末尾で挙がった二点のうち、summary で同じ結論が二行に出る件は 0.3.3 の公開前に直した。もう一つ（`neg` で否定とした二つの結論が一つの原子にまとまり、肯定の文言が「¬…」としてしか表に出ない）は、`neg` の仕様どおりの振る舞いである（`neg "A" "B"` は B を ¬A そのものとして扱う）。
