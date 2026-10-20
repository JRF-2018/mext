# mext分析・matcha分析の例

`tests/docs/` の文書（mext のテスト用に作った架空の事案・論説・小論）に、スキルを Claude Code CLI（`claude -p`、Claude Opus 5.5）で実行した結果である。非対話の実行なので、レポートの長さは聞かずに「標準」になっている。`reply.txt` は、そのとき AI が会話に返した文章である。

| ディレクトリ | スキル | 文書 | 最終的な出力 |
|---|---|---|---|
| `yatoidome_memo/` | mext-analysis | 契約社員の雇止めについての検討メモ（労働契約法 19 条） | `yatoidome_memo.mext-analysis.md` |
| `remote_work_op/` | mext-analysis | 論説「リモートワークを『原則』にせよ」 | `remote_work_op.mext-analysis.md` |
| `kindness_essay/` | mext-analysis（0.3.0） | 小論「なぜ見知らぬ人に親切にするのか」（架空の論者の見解の引用と賛同、弱い主張を含む） | `kindness_essay.mext-analysis.md`、`kindness_essay.sensitivity.md` |
| `deterministic_code_essay/` | matcha-analysis | 小論「AI に判断させるより、AI に書かせたコードに判断させよ」 | `deterministic_code_essay.matcha`、`deterministic_code_essay.matcha.md` |

各ディレクトリのファイル:

- `X.md`: 原文（入力）
- `X.matcha`: 書き起こし。各行の直前の `// 出典:` が原文の箇所を示す
- `X.matcha.md`: 書き起こしのメモ（対応表・書き起こしの判断・補った前提・落としたもの）
- `X.mext`: デフォルト理論と Extension。AI の判断は `[ai]` に理由つきで書かれている
- `X.alt-*.mext`: 試算（評価を退けた場合、反論が立証された場合など）
- `X.lean`: 各 Extension が Reiter の Extension であることの Lean 証明
- `X.mext-analysis.md`: 最終レポート
- `X.sensitivity.md`: 感度分析（`mext sensitivity` の出力）。`kindness_essay` ではスキルが作ってレポートに使った。ほかの二つは、実行のあとに 0.3.0 の道具で作って足したもので、レポートには反映されていない

`remote_work_op` のレポート末尾の「道具について」で報告された不具合（`(A & B)@評価` の原子の文言に行番号が入る）は、この実行のあと mext 0.2.0 で直した。

`kindness_essay` のレポート末尾の「道具について」で挙がった二点（`report` に `-o` がないこと、行き止まりの主張を知らせる lint の項目がないこと）は、この実行のあと、0.3.0 の公開前に直した。
