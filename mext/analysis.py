# -*- coding: utf-8 -*-
"""MEXT の分析コマンド（決定論的）: 感度分析（sensitivity）、書き起こしの検査（lint）、版の差分（diff）、版の保存（snapshot）。

- sensitivity: 争いうる前提（評価・論点・理由・[extra] のデフォルト、主張、必要なら事実）を外して Extension を
  計算し直し、結論ごとに「これを外すと成り立たなくなる」前提を一覧にする。デフォルト論理は非単調なので、
  前提を外すと新たに成り立つ結論もある。それも示す。
- lint: 書き起こしの粗さ（同語反復の評価、一段の評価だけの主張、立証の手段のない要件など）を警告する。
- diff: 二つの版の MEXT を、原子の番号ではなく文言で対応づけて、帰結・Extension・評価・[ai] の差を示す。
- snapshot: X.matcha と X.mext を X.vN.matcha と X.vN.mext として保存する（書き起こしを直す前に使う）。
"""
import copy
import itertools
import os
import re
import shutil

try:
    from . import core
except ImportError:            # パッケージとしてではなく直接実行された場合
    import core                # noqa: E402
INCONSISTENT = core.INCONSISTENT


# ---------------------------------------------------------------------------
# 共通
# ---------------------------------------------------------------------------
def load(path):
    mf = core.MextFile(path).load()
    th, diags = core.build(mf)
    return mf, th, diags


def variant(th, drop_defaults=(), drop_facts=()):
    """前提を外した理論（規則と原子はそのまま）"""
    t = copy.copy(th)
    t.defaults = {k: v for k, v in th.defaults.items() if k not in drop_defaults}
    t.priority = {(a, b) for a, b in th.priority if a in t.defaults and b in t.defaults}
    t.W = [l for l in th.W if l not in drop_facts]
    t.notes = []
    return t


def consequences(th):
    """(懐疑的帰結, 信憑的帰結, Extension の数, preferred の数)。preferred Extension がなければ空集合"""
    exts, pref, _ = core.solve(th)
    sk, cr = core.summarize(th, exts, pref)
    return (sk or set()), (cr or set()), len(exts), sum(1 for p in pref if p)


def status(l, sk, cr):
    if l in sk:
        return 'holds'
    if -l in sk:
        return 'neg'
    if l in cr:
        return 'credulous'
    return 'none'


STATUS_JA = {'holds': '成り立つ（懐疑的）', 'neg': '否定が成り立つ', 'credulous': '一部の Extension でだけ成り立つ',
             'none': '成り立たない'}


def esc(s):
    return s.replace('|', '\\|')


# ---------------------------------------------------------------------------
# 感度分析
# ---------------------------------------------------------------------------
class Cand:
    def __init__(self, cid, kind, key, label, text, line, review):
        self.id, self.kind, self.key, self.label, self.text, self.line, self.review = \
            cid, kind, key, label, text, line, review


KIND_JA = {'eval': '評価', 'issue': '論点', 'reason': '理由', 'extra': '追加のデフォルト', 'claim': '主張',
           'fact': '事実', 'extra-fact': '追加の事実'}


def candidates(th, facts=False):
    out = []
    for d in th.defaults.values():
        if d.kind in ('eval', 'issue', 'reason', 'extra', 'claim'):
            if d.kind == 'eval':
                text = th.lit_text(d.concl[0])
                rv = th.reviews.get(text)
                review = rv[0] if rv else ''
            elif d.kind == 'claim':
                text = th.lit_text(d.concl[0])
                review = ''
            else:
                text = ', '.join(th.lit_text(c) for c in d.concl)
                review = ''
            out.append(Cand(None, d.kind, ('d', d.name), d.name, text, d.line, review))
    for l in th.W:
        a = th.by_id[abs(l)]
        if a.kind == 'extra' or facts:
            out.append(Cand(None, 'extra-fact' if a.kind == 'extra' else 'fact', ('f', l), th.lit_str(l),
                            th.lit_text(l), a.lines[0] if a.lines else '', ''))
    for i, c in enumerate(out, 1):
        c.id = f'p{i}'
    return out


def drop(th, cands):
    return variant(th, [c.key[1] for c in cands if c.key[0] == 'd'], [c.key[1] for c in cands if c.key[0] == 'f'])


def default_targets(th, sk):
    """既定の対象: 懐疑的帰結に入る結論の原子（否定も含む）。なければ主張"""
    t = [l for l in sorted(sk, key=abs) if th.by_id[abs(l)].kind == 'concl']
    if not t:
        t = [l for l in sorted(sk, key=abs) if th.by_id[abs(l)].kind == 'claim']
    return t


def sensitivity(th, targets=None, size=2, facts=False):
    sk0, cr0, n0, p0 = consequences(th)
    if targets is None:
        targets = default_targets(th, sk0)
    cands = candidates(th, facts)
    base = {l: status(l, sk0, cr0) for l in targets}
    concl_atoms = [a.id for a in th.atoms.values() if a.kind == 'concl']
    results = {}          # frozenset(候補 id) -> (sk, cr)
    for k in range(1, size + 1):
        for S in itertools.combinations(cands, k):
            ids = frozenset(c.id for c in S)
            if k > 1:
                # 単独で（またはより小さい組で）すべての対象を消す組の上位集合は調べても新しい情報がない
                pass
            sk, cr, _, _ = consequences(drop(th, S))
            results[ids] = (sk, cr)
    out = {'base': base, 'cands': cands, 'targets': targets, 'size': size, 'n_ext': n0, 'n_pref': p0, 'per': {}}
    for l in targets:
        if base[l] != 'holds':
            out['per'][l] = None
            continue
        killers = [ids for ids, (sk, cr) in results.items() if status(l, sk, cr) != 'holds']
        minimal = [S for S in killers if not any(T < S for T in killers)]
        singles = sorted([next(iter(S)) for S in minimal if len(S) == 1], key=lambda x: int(x[1:]))
        groups = sorted([sorted(S, key=lambda x: int(x[1:])) for S in minimal if len(S) > 1])
        flips = sorted([next(iter(ids)) for ids, (sk, cr) in results.items()
                        if len(ids) == 1 and status(l, sk, cr) == 'neg'], key=lambda x: int(x[1:]))
        out['per'][l] = {'singles': singles, 'groups': groups, 'flips': flips,
                         'support': minimal_support(th, l, cands)}
    # 外すと新たに成り立つ結論（非単調性）
    appear = []
    for c in cands:
        sk, cr = results[frozenset([c.id])]
        for a in concl_atoms:
            for l in (a, -a):
                if l in sk and l not in sk0:
                    appear.append((c.id, l))
    out['appear'] = appear
    return out


def minimal_support(th, l, cands):
    """l が懐疑的帰結に残る、候補の極小の組を一つ（候補の順に外せるものを外していく）"""
    keep = list(cands)
    for c in list(cands):
        trial = [x for x in keep if x is not c]
        sk, cr, _, _ = consequences(drop(th, [x for x in cands if x not in trial]))
        if status(l, sk, cr) == 'holds':
            keep = trial
    return [c.id for c in keep]


def sensitivity_md(th, res, path):
    cands = {c.id: c for c in res['cands']}
    out = [f'# 感度分析: {os.path.basename(path)}', '',
           '（mext sensitivity の出力。争いうる前提を外して Extension を計算し直した結果。'
           '外すのは下の候補だけで、W の事実と規則はそのまま。「成り立つ」は、すべての preferred Extension に含まれること）', '',
           f'基準の理論: Extension {res["n_ext"]} 個（preferred {res["n_pref"]} 個）。候補 {len(cands)} 個、組の大きさ {res["size"]} まで。', '',
           '## 候補の前提', '', '| ID | 種類 | 名前 | 内容 | 行 | AI の審査 |', '|---|---|---|---|---|---|']
    for c in res['cands']:
        out.append(f'| {c.id} | {KIND_JA.get(c.kind, c.kind)} | {esc(str(c.label))} | {esc(c.text)} | {c.line} | {c.review} |')
    out += ['', '## 結論ごとの依存', '',
            '| 結論 | 基準 | 単独で外すと成り立たなくなる | 組で外すと成り立たなくなる（極小の組） | 外すと否定が成り立つ | 極小の支持の組（一例） |',
            '|---|---|---|---|---|---|']

    def ids(xs):
        return ', '.join(xs) if xs else '—'
    for l in res['targets']:
        p = res['per'][l]
        if p is None:
            out.append(f'| {esc(th.lit_text(l))} | {STATUS_JA[res["base"][l]]} | | | | |')
            continue
        groups = '; '.join('{' + ', '.join(g) + '}' for g in p['groups']) or '—'
        out.append(f'| {esc(th.lit_text(l))} | 成り立つ | {ids(p["singles"])} | {groups} | {ids(p["flips"])} | {ids(p["support"])} |')
    # 疑わしい評価への依存
    dep = {}
    for l in res['targets']:
        p = res['per'][l]
        if not p:
            continue
        for x in p['singles'] + [y for g in p['groups'] for y in g]:
            dep.setdefault(x, []).append(l)
    doubt = [c for c in res['cands'] if c.review in ('doubtful',)]
    out += ['', '## AI が doubtful とした評価', '']
    if not doubt:
        out.append('（なし）')
    for c in doubt:
        ls = dep.get(c.id, [])
        out.append(f'- {c.id}「{c.text}」: ' + ('次の結論がこれに依存する（外すと成り立たなくなる）: '
                                              + '、'.join(f'「{th.lit_text(l)}」' for l in ls) if ls
                                              else 'これを外しても、対象の結論はどれも成り立ったまま（単独でも、ほかの候補との組でも）'))
    out += ['', '## 外すと新たに成り立つ結論（非単調性）', '']
    if not res['appear']:
        out.append('（なし）')
    for cid, l in res['appear']:
        out.append(f'- {cid} を外すと「{th.lit_text(l)}」が成り立つ（{cands[cid].text} が、それを打ち消していた）')
    out += ['', '注: 「組で外すと」は、単独では結論が残るが、組で外すと成り立たなくなる極小の組である（同じ結論への独立した経路が複数ある場合に現れる）。'
            '「極小の支持の組」は、候補をこの順に外せるだけ外して、なお結論が残る組の一例で、ほかの組もありうる。'
            '^根拠（条文・原理の名前）は表示であって、独立に立証される前提ではないので、候補には入らない。']
    return '\n'.join(out)


def cmd_sensitivity(args):
    mf, th, _ = load(args.file)
    targets = None
    if args.target:
        errs = []
        targets = [core.lit_from_text(th, t, errs) for t in args.target]
        if errs:
            raise SystemExit('対象を解決できません: ' + '; '.join(errs))
    res = sensitivity(th, targets, args.size, args.facts)
    md = sensitivity_md(th, res, args.file)
    if args.output:
        open(args.output, 'w', encoding='utf-8').write(md + '\n')
        print(f'{args.output} を書き出しました')
    else:
        print(md)
    return 0


# ---------------------------------------------------------------------------
# 書き起こしの検査（lint）
# ---------------------------------------------------------------------------
PUNCT = re.compile(r'[\s　、。，．・「」『』（）()%％!！?？]')
EVAL_WORDS = ('べき', '必要', '当然', '妥当', '不当', '相当', '示唆', 'すぎない', 'にすぎず', '望ましい', '正しい')


def norm(s):
    return PUNCT.sub('', s or '')


def similar(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    return short in long_ and len(short) >= 0.8 * len(long_)


def walk(n):
    yield n
    for k in ('facts', 'body', 'reason', 'norm', 'application'):
        x = getattr(n, k, None)
        if x is not None:
            yield from walk(x)
    for x in getattr(n, 'items', []) or []:
        yield from walk(x)


def evals_in(n):
    """n の下にある「事実@評価」（事実または事実の組）"""
    return [x for x in walk(n) if x.kind in ('fact', 'group') and x.eval]


def lint(th, mf, exts=None, pref=None):
    W, I = '警告', '情報'
    out = []
    loc = th.files[0] if len(th.files) == 1 else None

    def at(f, line):
        return f'L{line}' if loc else f'{os.path.basename(f)}:L{line}'
    concl_texts = {}
    n_claims, one_step = 0, []
    for f, doc in zip(th.files, th.docs):
        for n in walk(doc):
            if n.kind == 'claim' and n.conclusion:
                concl_texts.setdefault(norm(n.conclusion['text']), (n.label, at(f, n.line)))
    for f, doc in zip(th.files, th.docs):
        for n in walk(doc):
            if n.kind == 'req' and n.facts is not None:
                for e in evals_in(n.facts):
                    if similar(e.eval, n.head):
                        out.append((W, at(f, e.line), '同語反復の評価',
                                    f'評価「@{e.eval}」が要件「{n.head}」とほぼ同じ文言である。事実から要件への判断が一段にまとめられ、'
                                    'mext からは中身が見えない。判断の段階（中間の要件や、評価の理由）を書き分けられないか'))
            if n.kind == 'req' and n.facts is None and n.body is None and n.mark != '!':
                hit = concl_texts.get(norm(n.head))
                if hit:
                    lab = f'$' + hit[0] if hit[0] else '（as でラベルを付けて）$ラベル'
                    out.append((W, at(f, n.line), '結論の文言の書き写し',
                                f'要件「{n.head}」は {hit[1]} の主張の結論と同じ文言である。前の主張の結論を要件にするなら {lab} と書く'
                                '（文言を写すと別の命題になり、同一視の判断が要る）'))
                else:
                    out.append((W, at(f, n.line), '立証の手段のない要件',
                                f'要件「{n.head}」には、あてはめる事実（<=）も下位の要件（:）もない。'
                                'この要件は成り立ちようがないので、これを含む主張は働かない。意図したもの（原文の論証の穴）なら、メモにそう書く'))
            if n.kind == 'claim' and n.body is not None:
                reqs = [x for x in walk(n.body) if x.kind in ('req', 'ref', 'issue', 'plain')]
                evs = evals_in(n.body) + (evals_in(n.facts) if n.facts is not None else [])
                n_claims += 1
                if len(reqs) <= 1 and len(evs) <= 1:
                    one_step.append(n.label or n.head or at(f, n.line))
            if n.kind == 'fact' and n.head:
                words = [w for w in EVAL_WORDS if w in n.head]
                if words:
                    out.append((I, at(f, n.line), '事実の中の評価語',
                                f'事実「{n.head}」に評価の語（{"・".join(words)}）がある。評価が事実として W に入っていないか'
                                '（評価なら「事実@評価」に分ける）'))
    if n_claims >= 3 and len(one_step) >= 0.7 * n_claims:
        out.append((I, '全体', '一段の主張が多い',
                    f'主張 {n_claims} 個のうち {len(one_step)} 個が、要件一つ・評価一つ以下である（{"、".join(map(str, one_step[:8]))}'
                    + ('…' if len(one_step) > 8 else '') + '）。原文の論証がそれだけ単純か、論証の中身が評価にまとめられていないかを確かめる'))
    # 行き止まりの主張: ラベルがどこからも参照されず（$・!>・:: 優先）、例外として他を打ち負かすこともなく、
    # 結論がほかの主張と共有されていない主張。最終的な結論は行き止まりなので、二つ以上あるときだけ知らせる
    refs, claims = set(), []
    for f, doc in zip(th.files, th.docs):
        for n in walk(doc):
            if n.kind == 'ref':
                refs.add(n.head)
            if n.kind == 'priority':
                refs.update(n.head)
            for e in getattr(n, 'excepts', []) or []:
                refs.add(e)
            if n.kind == 'claim':
                claims.append((f, n))
    concl_count = {}
    for f, n in claims:
        if n.conclusion:
            k = norm(n.conclusion['text'])
            concl_count[k] = concl_count.get(k, 0) + 1
    lonely = []
    for f, n in claims:
        shared = n.conclusion and concl_count.get(norm(n.conclusion['text']), 0) > 1
        if not (n.label and n.label in refs) and not n.excepts and not shared:
            lonely.append((f, n))
    if len(lonely) >= 2:
        names = '、'.join(f'{x.label or x.head}（{at(f, x.line)}）' for f, x in lonely)
        out.append((I, '全体', '行き止まりの主張',
                    f'結論がどこにも使われていない主張が {len(lonely)} 個ある: {names}。最終的な結論以外は、'
                    '原文がそれを結論の支えや限定として置いていないか確かめる（つながっていなければ、ほかの結論には効かない）'))
    # どの Extension にも出ない主張（著者が ! で不成立とした主張は除く）
    failed = {k for k, m, _, _ in th.marks if m == '!'}
    if exts is not None:
        live = [E for E, p in zip(exts, pref) if E != INCONSISTENT]
        union = set().union(*live) if live else set()
        for name, d in th.defaults.items():
            if d.kind == 'claim' and d.concl[0] not in union and d.concl[0] not in failed:
                out.append((I, f'L{d.line}', 'どの Extension にも出ない主張',
                            f'主張 {name}（{th.lit_text(d.concl[0])}）は、どの Extension にも含まれない。'
                            '要件を満たす事実がないか、例外に打ち負かされている（mext explain で理由をたどれる）'))
    for e in mf.errs:
        out.append((W, '[ai]', '効いていない判断', e))
    return out


def cmd_lint(args):
    mf, th, diags = load(args.file)
    exts, pref, _ = core.solve(th)
    items = [('警告' if d.level == 'warning' else '情報', (f'{d.file}:' if d.file else '') + f'L{d.line}', '構文', d.msg)
             for d in diags if d.level in ('warning', 'info')]
    items += lint(th, mf, exts, pref)
    print(f'# 書き起こしの検査: {os.path.basename(args.file)}\n')
    print('（mext lint の出力。決定論的な目安で、警告があっても誤りとは限らない。直すかどうかは原文に照らして判断する）\n')
    if not items:
        print('指摘はない。')
        return 0
    print('| 種類 | 位置 | 項目 | 内容 |\n|---|---|---|---|')
    for lv, where, what, msg in items:
        print(f'| {lv} | {where} | {what} | {esc(msg)} |')
    nw = sum(1 for x in items if x[0] == '警告')
    print(f'\n警告 {nw} 件、情報 {len(items) - nw} 件')
    return 0


# ---------------------------------------------------------------------------
# 版の差分（diff）
# ---------------------------------------------------------------------------
def texts(th, S):
    return {th.lit_text(l) for l in S}


def flip(t):
    return t[1:] if t.startswith('¬') else '¬' + t


def dependency(th):
    """懐疑的帰結に入る結論の文言 -> 単独で外すと成り立たなくなる前提の文言の集合"""
    res = sensitivity(th, size=1)
    cands = {c.id: c for c in res['cands']}
    out = {}
    for l, p in res['per'].items():
        if p is not None:
            out[th.lit_text(l)] = {f'{KIND_JA.get(cands[x].kind, cands[x].kind)}「{cands[x].text}」' for x in p['singles']}
    return out


def diff_md(pa, pb, ta, tb, mfa, mfb, kinds, sens=True):
    ska, cra, na, pa_n = consequences(ta)
    skb, crb, nb, pb_n = consequences(tb)

    def keep(th, S):
        return {th.lit_text(l) for l in S if th.by_id[abs(l)].kind in kinds}
    A, B = keep(ta, ska), keep(tb, skb)
    Ac, Bc = keep(ta, cra), keep(tb, crb)
    out = [f'# 版の差分: {os.path.basename(pa)} → {os.path.basename(pb)}', '',
           '（mext diff の出力。原子は番号ではなく文言で対応づけている。「成り立つ」は、すべての preferred Extension に含まれること）', '',
           '## Extension', '', f'- {os.path.basename(pa)}: Extension {na} 個（preferred {pa_n} 個）',
           f'- {os.path.basename(pb)}: Extension {nb} 個（preferred {pb_n} 個）', '',
           '## 懐疑的帰結の変化（' + '・'.join({'concl': '結論', 'claim': '主張', 'req': '要件', 'eval': '評価'}[k] for k in kinds) + '）', '']
    flips = sorted(t for t in A if flip(t) in B)
    lost = sorted(t for t in A - B if flip(t) not in B)
    gained = sorted(t for t in B - A if flip(t) not in A)
    for title, xs in (('否定に転じた', flips), ('成り立たなくなった', lost), ('新たに成り立つ', gained)):
        out.append(f'- **{title}**: ' + ('、'.join(f'「{x}」' for x in xs) if xs else 'なし'))
    weak = sorted(t for t in lost if t in Bc)
    if weak:
        out.append('  - うち、新しい版でも一部の Extension では成り立つもの: ' + '、'.join(f'「{x}」' for x in weak))
    out += ['', '## 原子の増減', '']
    def rv(th, t):
        st = th.eval_status.get(t)
        return f'（審査: {st or "なし"}）'
    for k, ja in (('concl', '結論'), ('claim', '主張'), ('eval', '評価'), ('req', '要件')):
        a = {t for t, x in ta.atoms.items() if x.kind == k}
        b = {t for t, x in tb.atoms.items() if x.kind == k}
        add, rem = sorted(b - a), sorted(a - b)
        if add or rem:
            out.append(f'- {ja}: 追加 {len(add)}、削除 {len(rem)}')
            out += [f'  - ＋ {x}' + (rv(tb, x) if k == 'eval' else '') for x in add[:30]]
            out += [f'  - － {x}' + (rv(ta, x) if k == 'eval' else '') for x in rem[:30]]
    if out[-1] == '':
        out.append('（増減なし）')
    ch_rv = [(t, ta.eval_status.get(t), tb.eval_status.get(t)) for t in sorted(set(ta.eval_status) & set(tb.eval_status))
             if ta.eval_status.get(t) != tb.eval_status.get(t)]
    if ch_rv:
        out += ['', '実際に効いた審査が変わった評価:', ''] + [f'- 「{t}」: {a or "なし"} → {b or "なし"}' for t, a, b in ch_rv]
    # 依存の変化（単独で外すと成り立たなくなる前提。前提は文言で対応づける）
    if sens:
        da, db = dependency(ta), dependency(tb)
        rows = []
        for t in sorted(set(da) & set(db)):
            if da[t] != db[t]:
                rows.append((t, sorted(da[t] - db[t]), sorted(db[t] - da[t])))
        out += ['', '## 依存の変化（単独で外すと結論が成り立たなくなる前提）', '']
        if not rows:
            out.append('（両方の版で成り立つ結論について、変化はない）')
        for t, gone, new_ in rows:
            out.append(f'- 「{t}」')
            out += [f'  - 依存しなくなった: {x}' for x in gone] + [f'  - 新たに依存する: {x}' for x in new_]
    if ta.priority != tb.priority:
        out += ['', '## 優先順位', ''] + [f'- ＋ {a} > {b}' for a, b in sorted(tb.priority - ta.priority)] \
            + [f'- － {a} > {b}' for a, b in sorted(ta.priority - tb.priority)]
    ra, rb = ta.reviews, tb.reviews
    ch = [(t, ra.get(t, ('—',))[0], rb.get(t, ('—',))[0]) for t in sorted(set(ra) | set(rb))
          if ra.get(t, ('—',))[0] != rb.get(t, ('—',))[0]]
    out += ['', '## [ai] に書かれた行の増減', '']
    out += [f'- review「{t}」: {a} → {b}' for t, a, b in ch] or ['- review の行の変化はない']
    la = {core.split_note(ln)[0].strip() for _, ln in mfa.ai_lines if core.split_note(ln)[0].strip()}
    lb = {core.split_note(ln)[0].strip() for _, ln in mfb.ai_lines if core.split_note(ln)[0].strip()}
    for x in sorted(lb - la):
        if not x.startswith('review'):
            out.append(f'- ＋ {x}')
    for x in sorted(la - lb):
        if not x.startswith('review'):
            out.append(f'- － {x}')
    if mfb.errs:
        out += ['', '**新しい版で効いていない [ai] の判断**（書き起こしを直したために、文言がどこにも当たらなくなったもの）:', '']
        out += [f'- {e}' for e in mfb.errs]
    return '\n'.join(out)


def cmd_diff(args):
    mfa, ta, _ = load(args.old)
    mfb, tb, _ = load(args.new)
    kinds = ('concl', 'claim', 'req', 'eval') if args.all else ('concl', 'claim')
    print(diff_md(args.old, args.new, ta, tb, mfa, mfb, kinds, not args.no_sensitivity))
    return 0


# ---------------------------------------------------------------------------
# 版の保存（snapshot）
# ---------------------------------------------------------------------------
def cmd_snapshot(args):
    mf = core.MextFile(args.file).load()
    base = os.path.splitext(args.file)[0]
    k = 1
    while os.path.exists(f'{base}.v{k}.mext'):
        k += 1
    tag = args.tag or f'v{k}'
    files = mf.theory_files()
    mapping = {}
    for f in files:
        b, ext = os.path.splitext(f)
        dst = f'{b}.{tag}{ext}'
        if os.path.exists(dst):
            raise SystemExit(f'{dst} はすでにあります')
        shutil.copyfile(f, dst)
        mapping[os.path.basename(f)] = os.path.basename(dst)
    dst_mext = f'{base}.{tag}.mext'
    txt = open(args.file, encoding='utf-8').read()

    def fix(m):
        p = m.group(1)
        return 'theory: ' + os.path.join(os.path.dirname(p), mapping.get(os.path.basename(p), os.path.basename(p))) \
            if os.path.dirname(p) else 'theory: ' + mapping.get(p, p)
    txt = re.sub(r'(?m)^theory:\s*(\S+)', fix, txt)
    open(dst_mext, 'w', encoding='utf-8').write(txt)
    print(f'{dst_mext} と ' + '、'.join(mapping.values()) + ' に保存しました（書き起こしを直したら mext diff '
          f'{os.path.basename(dst_mext)} {os.path.basename(args.file)} で比べる）')
    return 0


def add_parsers(sub):
    p = sub.add_parser('sensitivity', help='感度分析: 前提を外すと、どの結論が成り立たなくなるか')
    p.add_argument('file')
    p.add_argument('--target', action='append', help='対象の結論（文言。何度でも指定できる。既定は懐疑的帰結の結論すべて）')
    p.add_argument('--size', type=int, default=2, help='同時に外す前提の数の上限（既定 2）')
    p.add_argument('--facts', action='store_true', help='Matcha の事実（W）も候補にする（既定は [extra] で足した事実だけ）')
    p.add_argument('-o', '--output')
    p = sub.add_parser('lint', help='書き起こしの粗さの検査')
    p.add_argument('file')
    p = sub.add_parser('diff', help='二つの版の MEXT の、帰結・Extension・評価・[ai] の差')
    p.add_argument('old')
    p.add_argument('new')
    p.add_argument('--all', action='store_true', help='要件・評価の帰結の変化も示す')
    p.add_argument('--no-sensitivity', action='store_true', help='依存の変化（感度分析）を省く')
    p = sub.add_parser('snapshot', help='X.matcha と X.mext を X.vN.* として保存する')
    p.add_argument('file')
    p.add_argument('--tag', help='版の名前（既定 v1, v2, …）')
    return {'sensitivity': cmd_sensitivity, 'lint': cmd_lint, 'diff': cmd_diff, 'snapshot': cmd_snapshot}
