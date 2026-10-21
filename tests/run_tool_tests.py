#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析コマンド（sensitivity / lint / diff / snapshot）の回帰テスト"""
import os, sys, shutil, tempfile, io, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from mext import core, analysis

EX = os.path.join(HERE, '..', 'examples')
TC = os.path.join(HERE, 'tool_cases')
fail = 0


def check(name, cond, detail=''):
    global fail
    print(('OK  ' if cond else 'NG  ') + name + ('' if cond else ': ' + detail))
    fail += 0 if cond else 1


def theory(path):
    return analysis.load(path)[1]


# --- sensitivity
th = theory(os.path.join(EX, 'sublease.mext'))
res = analysis.sensitivity(th)
l = core.lit_from_text(th, '¬甲は本件賃貸借を解除できる')
p = res['per'][l]
check('sensitivity: 独立な二つの抗弁は単独では結論を消さない', not p['singles'], str(p['singles']))
check('sensitivity: 二つの抗弁を組で外すと結論が消える', len(p['groups']) >= 1, str(p['groups']))

th = theory(os.path.join(EX, 'tweety.mext'))
res = analysis.sensitivity(th)
l = core.lit_from_text(th, '¬トゥイーティーは飛ぶ')
p = res['per'][l]
check('sensitivity: 例外の主張を外すと原則の結論（否定の否定）が出る', len(p['flips']) == 1, str(p['flips']))

th = theory(os.path.join(EX, 'chain.mext'))
res = analysis.sensitivity(th)
l = core.lit_from_text(th, 'YはXに解雇後の賃金を支払わなければならない')
l0 = core.lit_from_text(th, '本件解雇は無効である')
check('sensitivity: 連鎖の後の結論は前の主張の前提にも依存する',
      set(res['per'][l0]['singles']) < set(res['per'][l]['singles']))

th = theory(os.path.join(TC, 'three_paths.mext'))
res = analysis.sensitivity(th)
l = core.lit_from_text(th, '結論が成り立つ')
p = res['per'][l]
check('sensitivity: 三つの独立した経路は大きさ 3 の組で初めて結論を消す（auto で見つかる）',
      not p['singles'] and p['groups'] and all(len(g) == 3 for g in p['groups']) and len(p['groups']) == 8, str(p['groups']))
check('sensitivity: 独立した経路を積の形でまとめる', analysis.fmt_groups(p).startswith('独立した 3 つの経路'), analysis.fmt_groups(p))
res2 = analysis.sensitivity(th, size=2)
check('sensitivity: --size 2 では見つからない（調べた範囲の明記が必要な場合）', not res2['per'][l]['groups'])

th = theory(os.path.join(TC, 'or_paths.mext'))
res = analysis.sensitivity(th)
l = core.lit_from_text(th, '人を殺してはいけない')
p = res['per'][l]
check('sensitivity: 結論を直接導く主張があっても、経路の組を探す', len(p['groups']) == 8 and len(p['singles']) == 1, str(p))
md = analysis.sensitivity_md(th, res, 'or_paths.mext')
check('sensitivity: 経路の独立性が未判断であることを示す', 'AI が判断していない' in md)

# concern / distinct（[ai] の行を足した写しで試す）
d = tempfile.mkdtemp()
try:
    shutil.copy(os.path.join(TC, 'or_paths.matcha'), d)
    ev = ['"殺し合えば分業が止まる@協働が損なわれる理由になる"', '"殺せば危険視される@信用を失う理由になる"',
          '"他者は将来助けてくれるかもしれない@他者を生かす理由になる"']
    for name, line in (('c', 'concern 便益から義務へ ' + ' '.join(ev) + '  ; 同じ型の橋渡し'),
                       ('d', 'distinct ' + ' '.join(ev) + '  ; 別の型の理由')):
        txt = open(os.path.join(TC, 'or_paths.mext'), encoding='utf-8').read().replace('[ai]\n', '[ai]\n' + line + '\n', 1)
        f = os.path.join(d, f'or_paths_{name}.mext')
        open(f, 'w', encoding='utf-8').write(txt)
        th = theory(f)
        res = analysis.sensitivity(th)
        md = analysis.sensitivity_md(th, res, f)
        if name == 'c':
            c = res['concerns'][0]
            check('concern: 争点をまとめて崩すと結論が成り立たなくなる', c['status'][l] != 'holds', str(c))
            check('concern: 経路が争点を共有することを示す', '争点「便益から義務へ」' in md and '内容の上の弱点は一つ' in md)
        else:
            check('distinct: 経路が互いに独立であることを示す', '互いに補い合う独立した根拠' in md)
        check(f'concern / distinct: 文言がすべて候補に当たる（{name}）', not res['unresolved'], str(res['unresolved']))
finally:
    shutil.rmtree(d)

# doubtful 一覧: 単独で必要なものと組の一員を分ける
th = theory(os.path.join(EX, 'sublease.mext'))
md = analysis.sensitivity_md(th, analysis.sensitivity(th), 'sublease.mext')
check('sensitivity: 組の一員を「単独で外すと」と書かない', '組の一員' in md or '単独で外すと成り立たなくなる**' not in md)

th = theory(os.path.join(TC, 'bare_neg.mext'))
exts, pref, _ = core.solve(th)
check('neg: 結論の素の文言で書いた neg も効く（対立して Extension が二つになる）', len(exts) == 2, str(len(exts)))

th = theory(os.path.join(TC, 'shared_eval.mext'))
res = analysis.sensitivity(th)
l = core.lit_from_text(th, '義務がある')
p = res['per'][l]
cands = {c.id: c for c in res['cands']}
kinds1 = {cands[x].kind for x in p['singles']}
check('sensitivity: 同じ評価を判断ごと外すと結論が消える（評価の原子を単位とする候補）', 'eval-all' in kinds1, str(kinds1))
check('sensitivity: あてはめ一か所ずつ外しても結論は残る', 'eval-one' not in kinds1, str(kinds1))
md = analysis.sensitivity_md(th, res, 'shared_eval.mext')
check('sensitivity: 判断ごとと一か所ずつの違いを言葉で示す', '一か所ずつ外しても' in md and '複数の経路に共通する弱点' in md)

# supplied（補った前提。写しで試す）
d = tempfile.mkdtemp()
try:
    shutil.copy(os.path.join(TC, 'shared_eval.matcha'), d)
    txt = open(os.path.join(TC, 'shared_eval.mext'), encoding='utf-8').read().replace(
        '[ai]\n', '[ai]\nsupplied "便益がある@便益は義務の理由になる" "存在しない前提"  ; 試験\n', 1)
    f = os.path.join(d, 'shared_eval.mext')
    open(f, 'w', encoding='utf-8').write(txt)
    mf, th, _ = analysis.load(f)
    md = analysis.summary_md(th, mf, f)
    check('supplied: 結論の決め手が補った前提なら summary で知らせる', '原文にない前提（書き起こした者が補ったもの）に依存する' in md, md[:300])
    check('supplied: 複数の経路に共通する判断が補った前提なら、そう書く', '書き起こした者が補った前提である' in md)
    check('supplied: 当たらなかった文言を知らせる', '「存在しない前提」' in md)
    exts, pref, _ = core.solve(th)
    check('supplied: 検証の範囲に補った前提の数を出す', '補った前提 2 個' in core.scope_text(th, core.scope(th, exts, pref)))
finally:
    shutil.rmtree(d)

# review / supplied を評価の部分だけ（"@評価"）や要件の素の文言で指す（写しで試す）
d = tempfile.mkdtemp()
try:
    shutil.copy(os.path.join(TC, 'shared_eval.matcha'), d)
    txt = open(os.path.join(TC, 'shared_eval.mext'), encoding='utf-8').read().replace(
        '[ai]\n', '[ai]\nreview "@便益は義務の理由になる" doubtful  ; 試験\nsupplied "@便益は義務の理由になる"  ; 試験\nreview "Aの要件" ok  ; 試験\n', 1)
    f = os.path.join(d, 'shared_eval.mext')
    open(f, 'w', encoding='utf-8').write(txt)
    mf, th, _ = analysis.load(f)
    check('review: 評価の部分だけ（"@評価"）で指せる', set(th.eval_status.values()) == {'doubtful'}, str(th.eval_status))
    check('review / supplied: 素の文言で指しても「見当たらない」と言われない', not mf.errs, str(mf.errs))
    cands = analysis.candidates(th)
    check('supplied: 評価の部分だけで指せる', any(c.supplied for c in cands if c.kind.startswith('eval')))
    check('review: 評価の部分だけで指した審査が、感度分析の候補にも表示される',
          all(c.review == 'doubtful' for c in cands if c.kind.startswith('eval')), str([(c.kind, c.review) for c in cands]))
finally:
    shutil.rmtree(d)

# 要件の素の文言の別名が、$参照とラベルの解決を曖昧にしない（英語の例の [claimed] は "safety" などのラベルで書かれている）
cf = os.path.join(EX, 'analysis', 'car_free_op', 'car_free_op.mext')
mf, th, _ = analysis.load(cf)
check('別名: ラベルで書いた [claimed] が解決できる', all(ok for _, ok, _ in analysis.verify_claims(th, mf)), str(analysis.verify_claims(th, mf)))

# --- 検証の範囲
th = theory(os.path.join(TC, 'three_paths.mext'))
exts, pref, _ = core.solve(th)
sc = core.scope(th, exts, pref)
check('scope: 対立する命題のない最終的な結論を数える', len(sc['finals']) == 1 and len(sc['unopposed']) == 1, str(sc))
th = theory(os.path.join(EX, 'tweety.mext'))
exts, pref, _ = core.solve(th)
sc = core.scope(th, exts, pref)
check('scope: 例外のある結論は対立する命題を持つ', not sc['unopposed'], str(sc))

# --- connectives（結び方の感度）
rw = os.path.join(EX, 'analysis', 'remote_work_op', 'remote_work_op.mext')
mf, th, _ = analysis.load(rw)
rows = analysis.connective_sensitivity(th, mf)
r28 = [r for r in rows if r['where'] == 'L28'][0]
check('connectives: 三つの理由の AND を OR にすると、主な結論の依存が減る', r28['dep_change'] and r28['dep_change'][0][1:] == (7, 1), str(r28))
check('connectives: [ai] の記録がなければ未記録とする', r28['record'] is None)

# --- changed と fact-kind（写しで試す）
d = tempfile.mkdtemp()
try:
    for f in ('tweety.matcha',):
        shutil.copy(os.path.join(EX, f), d)
    with contextlib.redirect_stdout(io.StringIO()):
        core.main(['init', os.path.join(d, 'tweety.matcha')])
    mx = os.path.join(d, 'tweety.mext')
    check('changed: 作った直後は変わっていない', all(st == 'unchanged' for _, st in analysis.changed(core.MextFile(mx).load())))
    with open(os.path.join(d, 'tweety.matcha'), 'a', encoding='utf-8') as fh:
        fh.write('\n// 人が書き足した\n')
    open(os.path.join(d, 'tweety.matcha.md'), 'w', encoding='utf-8').write('# メモ\n')
    st = dict(analysis.changed(core.MextFile(mx).load()))
    check('changed: .matcha の変更と、後からできたメモを見分ける', st.get('tweety.matcha') == 'changed' and st.get('tweety.matcha.md') == 'new', str(st))
    txt = open(mx, encoding='utf-8').read().replace('[ai]\n', '[ai]\nfact-kind "トゥイーティーはペンギンである" 仮定  ; 試験\n', 1)
    open(mx, 'w', encoding='utf-8').write(txt)
    mf, th, _ = analysis.load(mx)
    cands = analysis.candidates(th)
    check('fact-kind: 仮定とした事実は感度分析の候補になる', any(c.kind == 'fact-仮定' for c in cands), str([c.kind for c in cands]))
    exts, pref, _ = core.solve(th)
    check('fact-kind: 検証の範囲に事実の種別を出す', '仮定 1' in core.scope_text(th, core.scope(th, exts, pref)))
finally:
    shutil.rmtree(d)

# --- English output（MEXT_LANG=en / --lang en）: 道具の出力に日本語が残らない
import re
from mext import i18n, matcha_check
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
i18n.set_lang('en')
try:
    ef = os.path.join(TC, 'english.mext')
    mf, th, diags = analysis.load(ef)
    exts, pref, conflicting = core.solve(th)
    res = analysis.sensitivity(th)
    texts = {
        'summary': analysis.summary_md(th, mf, ef),
        'sensitivity': analysis.sensitivity_md(th, res, ef),
        'report': core.report_md(th, exts, pref, conflicting),
        'generated': core.render_generated(th, exts, pref, conflicting, diags),
        'connectives': analysis.connectives_md(th, analysis.connective_sensitivity(th, mf), ef),
        'diff': analysis.diff_md(ef, ef, th, th, mf, mf, ('concl', 'claim')),
        'lint': ' '.join(m for _, _, _, m in analysis.lint(th, mf, exts, pref)),
        'audit': ' '.join(f'{i} {m}' for _, i, m in analysis.audit(ef)),
        'lean': core.lean_source(th, exts, 'English', 'english.mext') + core.lean_source(th, exts, 'English', 'english.mext', import_spec='MextSpec'),
        'checker': ' '.join(d.msg for d in matcha_check.check_text(open(os.path.join(HERE, 'corpus_neg', 'english_as.matcha'), encoding='utf-8').read())[1]),
    }
    for k, v in texts.items():
        bad = [m.group(0) for m in JP.finditer(v)]
        check(f'English output: {k} に日本語が残らない', not bad, ''.join(bad)[:40])
finally:
    i18n.set_lang('ja')

# --- lint
mf, th, _ = analysis.load(os.path.join(TC, 'coarse.mext'))
exts, pref, _ = core.solve(th)
items = analysis.lint(th, mf, exts, pref)
kinds = [x[2] for x in items]
for k in ('同語反復の評価', '結論の文言の書き写し', '立証の手段のない要件', '行き止まりの主張'):
    check(f'lint: {k}', k in kinds, str(kinds))
mf, th, _ = analysis.load(os.path.join(TC, 'report_views.mext'))
exts, pref, _ = core.solve(th)
check('lint: 報告型の結論（対立が一つもない）', '報告型の結論' in [x[2] for x in analysis.lint(th, mf, exts, pref)])
mf, th, _ = analysis.load(os.path.join(EX, 'analysis', 'kindness_essay', 'kindness_essay.mext'))
exts, pref, _ = core.solve(th)
check('lint: $ラベルで受けて評価する報告は数えない', '報告型の結論' not in [x[2] for x in analysis.lint(th, mf, exts, pref)])
mf, th, _ = analysis.load(os.path.join(TC, 'report_eval.mext'))
exts, pref, _ = core.solve(th)
it = [x for x in analysis.lint(th, mf, exts, pref) if x[2] == '評価に依存する報告']
check('lint: 評価に依存する報告（分けた書き方は数えない）', len(it) == 1 and '1 個' in it[0][3] and '出生 (' in it[0][3], str(it))
mf, th, _ = analysis.load(os.path.join(EX, 'theft.mext'))
exts, pref, _ = core.solve(th)
check('lint: 原典の窃盗罪の例には警告がない', not [x for x in analysis.lint(th, mf, exts, pref) if x[0] == '警告'])

# --- diff
ta, tb = theory(os.path.join(TC, 'rule_v1.mext')), theory(os.path.join(TC, 'rule_v2.mext'))
mfa, mfb = core.MextFile(os.path.join(TC, 'rule_v1.mext')).load(), core.MextFile(os.path.join(TC, 'rule_v2.mext')).load()
md = analysis.diff_md('rule_v1.mext', 'rule_v2.mext', ta, tb, mfa, mfb, ('concl', 'claim'))
check('diff: 結論の否定への転化を示す', '否定に転じた**: 「#例外^規則B [例外]」、「¬効果が生じる〔本件〕」' in md, md[:400])
check('diff: 新たに成り立つ主張を示す', '新たに成り立つ**: 「#原則^規則A [原則]」' in md)

# --- snapshot
d = tempfile.mkdtemp()
try:
    for f in ('rule_v1.matcha', 'rule_v1.mext'):
        shutil.copy(os.path.join(TC, f), d)
    with contextlib.redirect_stdout(io.StringIO()):
        analysis.cmd_snapshot(type('A', (), {'file': os.path.join(d, 'rule_v1.mext'), 'tag': None})())
    snap = os.path.join(d, 'rule_v1.v1.mext')
    ok = os.path.exists(snap) and os.path.exists(os.path.join(d, 'rule_v1.v1.matcha')) \
        and 'theory: rule_v1.v1.matcha' in open(snap, encoding='utf-8').read()
    check('snapshot: 版のファイルを作り theory: を書き換える', ok)
    shutil.copy(os.path.join(d, 'rule_v1.mext'), os.path.join(d, 'rule_v1.check.mext'))
    with contextlib.redirect_stdout(io.StringIO()):
        analysis.cmd_snapshot(type('A', (), {'file': os.path.join(d, 'rule_v1.check.mext'), 'tag': None})())
    snap2 = os.path.join(d, 'rule_v1.check.v1.mext')
    check('snapshot: 同じ .matcha を使う二つの .mext は、同じ中身の版の .matcha を共有する',
          os.path.exists(snap2) and 'theory: rule_v1.v1.matcha' in open(snap2, encoding='utf-8').read())
    with open(os.path.join(d, 'rule_v1.matcha'), 'a', encoding='utf-8') as fh:
        fh.write('\n// 書き換え\n')
    with contextlib.redirect_stdout(io.StringIO()):
        analysis.cmd_snapshot(type('A', (), {'file': os.path.join(d, 'rule_v1.mext'), 'tag': None})())
    check('snapshot: 中身の違う .matcha は次の版にする', os.path.exists(os.path.join(d, 'rule_v1.v2.matcha'))
          and 'theory: rule_v1.v2.matcha' in open(os.path.join(d, 'rule_v1.v2.mext'), encoding='utf-8').read())
finally:
    shutil.rmtree(d)

# --- "要件"（英文のための「要件」の別表記）と、.mext の文字列（'…' と \"）
mf, th, _ = analysis.load(os.path.join(TC, 'ascii_quote.mext'))
exts, pref, conflicting = core.solve(th)
check('"要件": 要件の原子の文言に "" が残る', 'taking／"public use"' in th.atoms, str(list(th.atoms)[:6]))
check("[ai]: '…' で書いた review が効く", th.reviews.get('the stadium is open to everyone@a public use', ('',))[0] == 'ok')
check('[ai]: 注の中のアポストロフィで行が壊れない', th.reviews.get('a single developer profits@mainly private', ('',))[0] == 'doubtful')
gen = core.render_generated(th, exts, pref, conflicting, [])
check("[atoms]: \" を含む文言は '…' で書く", """'taking／"public use"'""" in gen)
check('文字列: \\" のエスケープと \'…\' が同じ文言になる',
      core.lit_from_text(th, '"taking／\\"public use\\""') == core.lit_from_text(th, """'taking／"public use"'""") is not None)
check('文字列: qs と QRE が往復する', all(core.unq(core.QRE.fullmatch(core.qs(x))) == x
                                          for x in ('a"b', "a'b", 'a"b\'c', 'a\\b', 'plain')))
with contextlib.redirect_stdout(io.StringIO()) as buf:
    core.cmd_verify(type('A', (), {'file': os.path.join(TC, 'ascii_quote.mext'), 'skeptical': False})())
check('[claimed]: \'…\' で書いた予測を検証できる', 'OK' in buf.getvalue(), buf.getvalue())

# --- 一部の Extension でだけ成り立つ結論の依存（その読みの中で）
th = theory(os.path.join(TC, 'claim_views.mext'))
res = analysis.sensitivity(th)
l = core.lit_from_text(th, '神は一人一人に最良の結果をもたらそうと努める')
p = res['per'].get(l)
check('sensitivity: 一部の Extension でだけ成り立つ結論も対象にし、成り立つ Extension がなくなる前提を示す',
      p is not None and res['base'][l] == 'credulous' and any(res['cands'][int(x[1:]) - 1].kind == 'claim' for x in p['singles']), str(p))

# --- 懐疑的な結論で、単独で外すと一部の Extension には残る前提（浮動する結論）
d = tempfile.mkdtemp()
try:
    with open(os.path.join(d, 'float.matcha'), 'w', encoding='utf-8') as fh:
        fh.write("""#甲説 <= 本件: (
    %甲の根拠 <= 甲の事実@甲の評価
) >> 甲である as 甲

#乙説 <= 本件: (
    %乙の根拠 <= 乙の事実@乙の評価
) >> not 甲である as 乙

#甲からの結論 <= 本件: (
    $甲
) >> 共通の結論 as 共通甲

#乙からの結論 <= 本件: (
    %乙が成り立つ <= 乙の事実@乙の評価
    %甲が成り立たない <= 乙の事実@乙から共通へ
) >> 共通の結論 as 共通乙
""")
    with contextlib.redirect_stdout(io.StringIO()):
        core.main(['init', '--solve', os.path.join(d, 'float.matcha')])
    th = theory(os.path.join(d, 'float.mext'))
    res = analysis.sensitivity(th)
    l = core.lit_from_text(th, '共通の結論')
    p = res['per'].get(l)
    check('sensitivity: 浮動する結論の片方の橋渡しは「一部の Extension には残る」', p is not None and res['base'][l] == 'holds'
          and p['partial'] and set(p['partial']) <= set(p['singles']), str(p))
finally:
    shutil.rmtree(d)

# --- 評価のないあてはめの審査（確定規則として読まれる）
d = tempfile.mkdtemp()
try:
    for f in ('minor_contract.matcha', 'minor_contract.mext'):
        shutil.copy(os.path.join(EX, f), d)
    mp = os.path.join(d, 'minor_contract.mext')
    txt = open(mp, encoding='utf-8').read().replace('[ai]\n', '[ai]\nreview "特則／%取消しの意思表示" doubtful ; 原文の読み: 到達まで含むか不明\n', 1)
    open(mp, 'w', encoding='utf-8').write(txt)
    mf, th, _ = analysis.load(mp)
    exts, pref, _ = core.solve(th)
    st = core.scope_text(th, core.scope(th, exts, pref))
    md = analysis.summary_md(th, mf, mp)
    check('scope: 評価のないあてはめの数と審査を示す', '評価のないあてはめ' in st and 'doubtful 1' in st, st)
    check('summary: doubtful とした評価のないあてはめを示す', '## 評価のないあてはめの審査' in md and '到達まで含むか不明' in md, md[-800:])
finally:
    shutil.rmtree(d)

# --- preferred の判定（貪欲な閉包）が、適用の順序をすべて試す定義どおりの判定と一致する
import random as _random


def preferred_bruteforce(th, E, hi):
    if E == core.INCONSISTENT:
        return True
    GD = list(core.generating(th, E))
    rivals = [d for d in th.defaults.values() if d.name not in GD and all(p in E for p in d.pre)]

    def close(S):
        S = set(S)
        while True:
            new = {r.head for r in th.rules if r.head not in S and all(b in S for b in r.body)}
            if not new:
                return S
            S |= new
    for order in itertools.permutations(GD):
        S, ok = close(th.W), True
        for g in order:
            d = th.defaults[g]
            if not all(p in S for p in d.pre) or any(r.name in hi[g] and not any(-j in S for j in r.just) for r in rivals):
                ok = False
                break
            S = close(S | set(d.concl))
        if ok and S == E:
            return True
    return False


import itertools
rng = _random.Random(7)
bad, n_checked, n_false = 0, 0, 0
for _ in range(300):
    th = core.Theory()
    atoms = [th.atom('extra', str(i)) for i in range(5)]
    lits = atoms + [-a for a in atoms]
    th.W = rng.sample(atoms, rng.randrange(3))
    for j in range(6):
        c = rng.choice(lits)
        th.add_default(core.Default(str(j), rng.sample(lits, rng.randrange(3)), [c] + rng.sample(lits, rng.randrange(2)), [c], 'extra'))
    for j in range(3):
        th.add_rule(rng.sample(lits, rng.randrange(3)), rng.choice(lits))
    th.priority = {tuple(rng.sample(list(th.defaults), 2)) for _ in range(rng.randrange(1, 5))}
    exts, _ = core.extensions(th)
    hi = core.priority_closure(th.priority, list(th.defaults))
    for E in exts:
        a, b = core.preferred(th, E, hi), preferred_bruteforce(th, E, hi)
        n_checked += 1
        n_false += not b
        bad += a != b
check(f'preferred: 貪欲な判定が、順序をすべて試す判定と一致する（{n_checked} 個の Extension、うち preferred でないもの {n_false} 個）',
      bad == 0 and n_false > 0, str(bad))

# --- 補った要件（あてはめのない関門）を外す候補
d = tempfile.mkdtemp()
try:
    with open(os.path.join(d, 'hurdle.matcha'), 'w', encoding='utf-8') as fh:
        fh.write("""#類推 <= 本件: (
    %似ている <= 二つは似ている@類推の基礎になる
    %対応の具体的な根拠
) >> 類推が成り立つ as 類推
""")
    with contextlib.redirect_stdout(io.StringIO()):
        core.main(['init', os.path.join(d, 'hurdle.matcha')])
    mp = os.path.join(d, 'hurdle.mext')
    txt = open(mp, encoding='utf-8').read().replace('[ai]\n', '[ai]\nsupplied "対応の具体的な根拠" ; 類推に要ると判断した要件\n', 1)
    open(mp, 'w', encoding='utf-8').write(txt)
    mf, th, _ = analysis.load(mp)
    res = analysis.sensitivity(th)
    sr = [c for c in res['cands'] if c.kind == 'supplied-req']
    md = analysis.summary_md(th, mf, mp)
    check('sensitivity: あてはめのない補った要件を、満たすとみなす候補にする', len(sr) == 1 and sr[0].supplied
          and any(cid == sr[0].id for cid, _ in res['appear']) and not getattr(th, 'supplied_unresolved', []), str([(c.id, c.kind) for c in res['cands']]))
    check('summary: 補った要件のために成り立たない結論を示す', '書き起こした者が補った要件' in md, md[:1500])
finally:
    shutil.rmtree(d)

# --- 出典の引用が原文にあるか
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, 'src.md'), 'w', encoding='utf-8').write('第一段落。人目のない山道で、道に迷った人を助ける人もいる。\n\n第二段落。以上から結論を述べる。\n')
    open(os.path.join(d, 'q.matcha'), 'w', encoding='utf-8').write(
        '// 原文: src.md\n\n// 出典: 第1段落「人目のない山道で…助ける人もいる」\n#A <= 本件: (\n    %X <= 山道の例\n) >> 結論A as a\n\n'
        '// 出典: 第2段落「以上から反対の結論を述べる」\n#B <= 本件: (\n    %Y <= 別の例\n) >> 結論B as b\n\n'
        '// 出典: 第1段落「道に迷った人を助ける」。「例外にとどまる」は原文の評価を言い換えたもの。「」を『』に替えた\n#C <= 本件: (\n    %Z <= 例\n) >> 結論C as c\n')
    miss = analysis.quote_misses(os.path.join(d, 'q.matcha'))
    check('lint: 原文に見当たらない出典の引用（… で区切った引用は断片ごとに探す）', [m[0] for m in miss] == [8], str(miss))
finally:
    shutil.rmtree(d)

# --- Lean: 証明書（mext lean の既定）
import glob as _glob


def check_cert_py(th, E, steps):
    """Lean の checkCert を Python で写したもの"""
    ds = list(th.defaults.values())
    ok = [d for d in ds if all(-j not in E for j in d.just)]
    if any(-x in E for x in E):
        return False
    if not set(th.W) <= E or any(set(r.body) <= E and r.head not in E for r in th.rules) \
            or any(set(d.pre) <= E and not set(d.concl) <= E for d in ok):
        return False
    S = set(th.W)
    for k, n in steps:
        if k == 'rule':
            r = th.rules[n]
            if not set(r.body) <= S:
                return False
            S.add(r.head)
        else:
            d = ds[n]
            if not set(d.pre) <= S or any(-j in E for j in d.just):
                return False
            S |= set(d.concl)
    return E <= S


n_ok = n_all = 0
for f in sorted(_glob.glob(os.path.join(EX, '**', '*.mext'), recursive=True)):
    th = theory(f)
    exts, _, _ = core.solve(th)
    for E in exts:
        if E == core.INCONSISTENT:
            continue
        n_all += 1
        n_ok += check_cert_py(th, set(E), core.lean_certificate(th, set(E)))
check(f'lean: 例のすべての Extension の証明書が、checkCert の条件を満たす（{n_ok}/{n_all}）', n_ok == n_all and n_all > 0)


def check_pref_py(th, E, prio, hip, steps):
    """Lean の checkPref のうち、優先の条件の部分を Python で写したもの"""
    ds = list(th.defaults.values())
    gen = lambda d: all(p in E for p in d.pre) and all(-j not in E for j in d.just)
    rival = lambda d: all(p in E for p in d.pre) and not all(-j not in E for j in d.just)
    if not set(prio) <= set(hip) or any(p[1] == q[0] and (p[0], q[1]) not in hip for p in hip for q in hip):
        return False
    if any(gen(d) and ('dflt', k) not in steps for k, d in enumerate(ds)):
        return False
    S = set(th.W)
    for k, n in steps:
        if k == 'rule':
            S.add(th.rules[n].head)
        else:
            for a, b in hip:
                if b == n and rival(ds[a]) and not any(-j in S for j in ds[a].just):
                    return False
            S |= set(ds[n].concl)
    return True


n_ok = n_all = n_np = 0
for f in sorted(_glob.glob(os.path.join(EX, '**', '*.mext'), recursive=True)):
    th = theory(f)
    if not th.priority:
        continue
    exts, pref, _ = core.solve(th)
    pos = {d.name: k for k, d in enumerate(th.defaults.values())}
    hi = core.priority_closure(th.priority, list(th.defaults))
    prio = [(pos[a], pos[b]) for a, b in th.priority]
    hip = [(pos[a], pos[b]) for b, s_ in hi.items() for a in s_]
    for E, pf in zip(exts, pref):
        if E == core.INCONSISTENT:
            continue
        pc = core.lean_pref_certificate(th, E, hi)
        n_all += 1
        n_np += not pf
        n_ok += (pc is not None) == pf and (pc is None or (check_cert_py(th, set(E), pc) and check_pref_py(th, set(E), prio, hip, pc)))
check(f'lean: preferred の証明書が、preferred の Extension にだけあり、checkPref の条件を満たす（{n_ok}/{n_all}、preferred でないもの {n_np}）',
      n_ok == n_all and n_np > 0)


def lean_defs(text):
    """def / inductive / structure の定義の本体（コメントと空行を除く）"""
    text = re.sub(r'/-.*?-/', '', text, flags=re.S)
    text = re.sub(r'--[^\n]*', '', text)
    out, cur = {}, None
    for ln in text.splitlines():
        m = re.match(r'^(def|inductive|structure) (\w+)', ln)
        if m:
            cur = m.group(2)
            out[cur] = [ln.rstrip()]
        elif cur and ln.strip() and (ln.startswith(' ') or ln.startswith('deriving') or ln.startswith('  |')):
            out[cur].append(ln.rstrip())
        else:
            cur = None
    return {k: '\n'.join(v) for k, v in out.items()}


spec = lean_defs(open(os.path.join(HERE, '..', 'lean', 'MextSpec.lean'), encoding='utf-8').read())
prel = lean_defs(core.lean_prelude())
check('lean: 出力の検査器の定義が lean/MextSpec.lean と同じ', set(prel) <= set(spec) and all(prel[k] == spec[k] for k in prel),
      str([k for k in prel if prel.get(k) != spec.get(k)]))
check('lean: 出力の既定は証明書による検査', 'Mext.checkCert T E1 E1_cert = true' in core.lean_source(theory(os.path.join(EX, 'tweety.mext')),
      core.solve(theory(os.path.join(EX, 'tweety.mext')))[0], 'Tweety', 'tweety.mext'))

# --- 検証の範囲: 否定の側が成り立つ最終的な結論も数える
th = theory(os.path.join(EX, 'tweety.mext'))
exts, pref, _ = core.solve(th)
st = core.scope_text(th, core.scope(th, exts, pref))
check('scope: 否定が成り立つ最終的な結論を数える', '成り立つもの 1 個、否定が成り立つもの 1 個' in st, st)

# --- 不成立の主張（!#）と論点
d = tempfile.mkdtemp()
try:
    def solve_text(name, text):
        open(os.path.join(d, name + '.matcha'), 'w', encoding='utf-8').write(text)
        with contextlib.redirect_stdout(io.StringIO()):
            core.main(['init', '--solve', os.path.join(d, name + '.matcha')])
        th = theory(os.path.join(d, name + '.mext'))
        exts, pref, _ = core.solve(th)
        sk, _ = core.summarize(th, exts, pref)
        return th, sk or set()
    body = ("!#失効^憲法36条 <= 死刑規定: (\n"
            "    {o}「残虐な刑罰」: ? 残虐な刑罰の意味 ~> 刑罰は時代に応じて変遷する => {i}%人道上残虐と認められる刑罰 <= 死刑は冷厳な刑罰である@死刑は直ちに残虐とは認められない\n"
            ") >> 死刑規定は効力を失ったとはいえない as 失効論\n\n"
            "#有効 <= 死刑規定: (\n    $失効論\n) >> 死刑規定は有効である as 有効\n")
    res = []
    for o, i in (('!', ''), ('', '!')):
        th, sk = solve_text('bang' + str(len(res)), body.format(o=o, i=i))
        res.append((core.lit_from_text(th, '死刑規定は効力を失ったとはいえない') in sk, core.lit_from_text(th, '死刑規定は有効である') in sk))
    check('論点: 要件の前の ! が論点の規範に及ぶ（!「要件」: ? … と 「要件」: ? … => !%規範 が同じになる）', res[0] == res[1], str(res))
    check('$ラベル: 不成立の主張を指すと、その結論（不成立からの帰結）と結ぶ', res[0] == (True, True), str(res))
finally:
    shutil.rmtree(d)

# --- 前向き推論の閉包（fast_closure）が、導出の記録を残す closure と同じ集合になる
rng = _random.Random(23)
bad = 0
for _ in range(400):
    th = core.Theory()
    atoms = [th.atom('extra', str(i)) for i in range(6)]
    lits = atoms + [-a for a in atoms]
    th.W = rng.sample(atoms, rng.randrange(3))
    for j in range(7):
        c = rng.choice(lits)
        th.add_default(core.Default(str(j), rng.sample(lits, rng.randrange(3)), [c], [c] + rng.sample(lits, rng.randrange(2)), 'extra'))
    for j in range(5):
        th.add_rule(rng.sample(lits, rng.randrange(3)), rng.choice(lits))
    ds = list(th.defaults.values())
    sub = [d for d in ds if rng.random() < 0.6]
    bad += core.fast_closure(th, sub) != core.closure(th, sub)[0]
check('closure: 前向き推論の閉包が、もとの閉包と同じ集合になる（乱数の理論 400 個）', bad == 0, str(bad))

# --- 複数ファイルの理論: 位置の表示と、書き起こしの記録
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, 'a.md'), 'w', encoding='utf-8').write('甲は乙である。\n')
    open(os.path.join(d, 'a.matcha'), 'w', encoding='utf-8').write(
        '// 原文: a.md\n\n// 出典: 第1段落「甲は乙である」\n#前提 <= 本件: (\n    %乙である <= 甲の事実@甲は乙と評価できる\n) >> 甲は乙である as 前提\n')
    open(os.path.join(d, 'b.matcha'), 'w', encoding='utf-8').write(
        '#結論 <= 本件: (\n    $前提\n    %丙である <= 丙の事実@丙は丙と評価できる\n) >> 甲は丙でもある as 結論\n')
    with contextlib.redirect_stdout(io.StringIO()):
        core.main(['init', '--solve', os.path.join(d, 'a.matcha'), os.path.join(d, 'b.matcha'), '-o', os.path.join(d, 'ab.mext')])
        core.main(['init', '--solve', os.path.join(d, 'a.matcha'), os.path.join(d, 'b.matcha'), '-o', os.path.join(d, 'ab.check.mext')])
    mf, th, _ = analysis.load(os.path.join(d, 'ab.mext'))
    md = analysis.summary_md(th, mf, os.path.join(d, 'ab.mext'))
    check('複数ファイル: 争点の位置にファイル名を付け、出典の注を引く', 'a:L5 / 出典: 第1段落' in md and 'b:L3' in md, md[-900:])
    rows = analysis.audit(os.path.join(d, 'ab.mext'))
    check('複数ファイル: audit が X.check.mext（理論の名前）を見つける', any('書き起こしの後の変更' in r[1] for r in rows), str(rows[:3]))
finally:
    shutil.rmtree(d)

# --- compare（読みの比較）
from mext import compare
cf = compare.CompareFile(os.path.join(TC, 'views.compare')).load()
A, B = compare.Reading(cf.a), compare.Reading(cf.b)
md = compare.compare_md(A, B, cf, 'views.compare')
check('compare: ラベルで指した主張は、その結論どうしを比べる', '| 1 | 至善の神観では出生の差を自由選択の結果として説明する〔神〕 | 神は一人一人に最良の結果をもたらそうと努める〔神〕 |' in md, md[:600])
check('compare: 成否の違いを示す', '対応 2 組のうち、成否が違うもの 2 組' in md and 'B では preferred Extension が分かれる' in md)
check('compare: 対応のない最終的な結論を示す', 'A だけ（1 個）: 「二つの神観のどちらかでなければ矛盾するという著者の判断がある〔著者〕」' in md)
check('compare: [match] の関係の語を示す', '〔報告と主張〕同じ立場' in md and '[match] に書いた関係: 報告と主張 1 組' in md, md[:1500])
cfk = compare.CompareFile(os.path.join(EX, 'analysis', 'compare_kindness', 'kindness_essay.A.vs.B.compare')).load()
mdk = compare.compare_md(compare.Reading(cfk.a), compare.Reading(cfk.b), cfk)
check('compare: 一方で中間の結論のものを示す', 'A では中間の結論' in mdk)
check('compare: 解決できない [match] の行を示す', '「@x」 / 「@y」: A に見当たらない、B に見当たらない' in md)
cf2 = compare.CompareFile(os.path.join(TC, 'views.compare')).load()
cf2.matches = []
A2 = compare.Reading(os.path.join(TC, 'shared_eval.mext'))
B2 = compare.Reading(os.path.join(TC, 'shared_eval.mext'))
md = compare.compare_md(A2, B2, None)
check('compare: 同じ読みどうしは、文言で自動に対応し、違いがない', '成否が違うもの 0 組' in md and '**成否が違う**' not in md
      and 'A だけ（0 個）' in md, md[-800:])
d = tempfile.mkdtemp()
try:
    out = os.path.join(d, 'x.compare')
    with contextlib.redirect_stdout(io.StringIO()):
        compare.template(compare.Reading(os.path.join(TC, 'report_views.mext')), compare.Reading(os.path.join(TC, 'claim_views.mext')), out)
    txt = open(out, encoding='utf-8').read()
    check('compare --init: ひな形に a: b: と対応のない結論を書く', 'a: ' in txt and '[match]' in txt and '"二つの神観のどちらかでなければ矛盾するという著者の判断がある〔著者〕"' in txt)
    os.remove(out)
    compare.template(compare.Reading(os.path.join(TC, 'claim_views.mext')), compare.Reading(os.path.join(TC, 'report_views.mext')), out)
    txt2 = open(out, encoding='utf-8').read()
    check('compare --init: 結論とその否定を区別して書く', '"神は一人一人に最良の結果をもたらそうと努める〔神〕"' in txt2
          and '"¬神は一人一人に最良の結果をもたらそうと努める〔神〕"' in txt2, txt2)
    A3, B3 = compare.Reading(os.path.join(TC, 'claim_views.mext')), compare.Reading(os.path.join(TC, 'claim_views.mext'))
    md3 = compare.compare_md(A3, B3, None)
    check('compare: 結論とその否定は別々に自動で対応づける', '対応 2 組のうち' in md3 and 'A だけ（0 個）' in md3, md3[-600:])
    cf3 = compare.CompareFile(out).load()
    check('compare --init: ひな形はそのまま読める', not cf3.errs and os.path.exists(cf3.a), str(cf3.errs))
finally:
    shutil.rmtree(d)
i18n.set_lang('en')
try:
    d = tempfile.mkdtemp()
    out = os.path.join(d, 'en.compare')
    compare.template(compare.Reading(os.path.join(TC, 'english.mext')), compare.Reading(os.path.join(TC, 'english.mext')), out)
    md = compare.compare_md(compare.Reading(os.path.join(TC, 'english.mext')), compare.Reading(os.path.join(TC, 'english.mext')),
                            compare.CompareFile(out).load(), out) + open(out, encoding='utf-8').read()
    shutil.rmtree(d)
    bad = [m.group(0) for m in JP.finditer(md)]
    check('English output: compare に日本語が残らない', not bad, ''.join(bad)[:40])
finally:
    i18n.set_lang('ja')

print(f'失敗 {fail} 件')
sys.exit(1 if fail else 0)
