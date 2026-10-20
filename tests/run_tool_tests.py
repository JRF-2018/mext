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
finally:
    shutil.rmtree(d)

print(f'失敗 {fail} 件')
sys.exit(1 if fail else 0)
