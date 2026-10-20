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
           'fact': '事実', 'extra-fact': '追加の事実', 'fact-仮定': '事実（仮定）', 'fact-著者の主張': '事実（著者の主張）'}


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
    fk = getattr(th, 'fact_kinds', {})
    for l in th.W:
        a = th.by_id[abs(l)]
        kind_ai = fk.get(a.text, (None,))[0]
        if a.kind == 'extra' or facts or kind_ai in ('仮定', '著者の主張'):
            kind = 'extra-fact' if a.kind == 'extra' else ('fact-' + kind_ai if kind_ai else 'fact')
            out.append(Cand(None, kind, ('f', l), th.lit_str(l), th.lit_text(l), a.lines[0] if a.lines else '', kind_ai or ''))
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


AUTO_GLOBAL = 2        # size='auto' のとき、全候補で調べる組の大きさ
AUTO_LOCAL = 4         # 依存が見つからない結論について、支持の組の中で調べる組の大きさの上限
AUTO_MAX_CANDS = 80    # 全候補がこれより多ければ、全候補で調べるのは大きさ 1 まで


def sensitivity(th, targets=None, size='auto', facts=False):
    """size が整数なら、その大きさまでの組を全候補で調べる。'auto' なら、全候補では大きさ 2（候補が多ければ 1）まで調べ、
    依存が見つからない結論について、支持の組を集めながら、そのすべてと交わる組を大きさ 4 まで調べる（deep_search）"""
    sk0, cr0, n0, p0 = consequences(th)
    if targets is None:
        targets = default_targets(th, sk0)
    cands = candidates(th, facts)
    auto = size == 'auto'
    gsize = (AUTO_GLOBAL if len(cands) <= AUTO_MAX_CANDS else 1) if auto else int(size)
    base = {l: status(l, sk0, cr0) for l in targets}
    concl_atoms = [a.id for a in th.atoms.values() if a.kind == 'concl']
    results = {}          # frozenset(候補 id) -> (sk, cr)。探索の途中で外した大きな組も入る（計算の再利用のため）
    grid = set()          # 全候補で調べた組（大きさ gsize まで）

    def run(S):
        ids = frozenset(c.id for c in S)
        if ids not in results:
            sk, cr, _, _ = consequences(drop(th, S))
            results[ids] = (sk, cr)
        return results[ids]
    for k in range(1, gsize + 1):
        for S in itertools.combinations(cands, k):
            run(S)
            grid.add(frozenset(c.id for c in S))
    out = {'base': base, 'cands': cands, 'targets': targets, 'size': gsize, 'auto': auto,
           'n_ext': n0, 'n_pref': p0, 'per': {}}
    by_id = {c.id: c for c in cands}
    for l in targets:
        if base[l] != 'holds':
            out['per'][l] = None
            continue
        # 結論を直接導く唯一の主張（own）は、外せば結論が消えるのが当然なので、経路の探索では固定して残す
        own = {c.id for c in cands if c.kind == 'claim' and l in th.defaults[c.key[1]].concl}
        own = {x for x in own if status(l, *results[frozenset([x])]) != 'holds'}   # それ一つで結論が消える、自明な場合だけ
        free = [c for c in cands if c.id not in own]
        fsupport = minimal_support(th, l, free)
        support = idsort(fsupport + sorted(own))
        explored = f'全候補で大きさ {gsize} まで'
        supports = [frozenset(fsupport)]
        killers = [ids for ids in grid if status(l, *results[ids]) != 'holds']
        if auto and fsupport and not [K for K in killers if not (K & own)]:
            deep, supports, k = deep_search(th, l, free, fsupport, gsize, run)
            killers += deep
            explored += f'、支持の組 {len(supports)} 通りのすべてと交わる組を大きさ {k} まで'
        minimal = [S for S in killers if not any(T < S for T in killers)]
        singles = sorted([next(iter(S)) for S in minimal if len(S) == 1], key=lambda x: int(x[1:]))
        groups = sorted([sorted(S, key=lambda x: int(x[1:])) for S in minimal if len(S) > 1])
        flips = sorted([next(iter(ids)) for ids in grid
                        if len(ids) == 1 and status(l, *results[ids]) == 'neg'], key=lambda x: int(x[1:]))
        out['per'][l] = {'singles': singles, 'groups': groups, 'flips': flips, 'support': support,
                         'explored': explored, 'supports': supports}
    # [ai] の concern（一つの争点を共有する前提の組）を一つの単位として外す
    out['concerns'], out['distincts'], out['unresolved'] = [], [], []
    for name, (members, note) in getattr(th, 'concerns', {}).items():
        cs = [resolve(th, cands, m) for m in members]
        out['unresolved'] += [m for m, c in zip(members, cs) if c is None]
        ids = idsort({c.id for c in cs if c})
        if not ids:
            continue
        sk, cr = run([by_id[x] for x in ids])
        out['concerns'].append({'name': name, 'ids': ids, 'note': note,
                                'status': {l: status(l, sk, cr) for l in targets}})
    for members, note in getattr(th, 'distincts', []):
        cs = [resolve(th, cands, m) for m in members]
        out['unresolved'] += [m for m, c in zip(members, cs) if c is None]
        ids = idsort({c.id for c in cs if c})
        if ids:
            out['distincts'].append({'ids': ids, 'note': note})
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


def resolve(th, cands, text):
    """[ai] の concern / distinct に書いた文言（評価・主張の文言、ラベル、デフォルト名、候補 ID）から候補を得る"""
    for c in cands:
        if text in (c.id, c.text, str(c.label)):
            return c
    l = core.lit_from_text(th, text)
    if l is None:
        return None
    for c in cands:
        if c.key[0] == 'd' and th.defaults[c.key[1]].concl and th.defaults[c.key[1]].concl[0] == l:
            return c
        if c.key == ('f', l):
            return c
    return None


def path_note(p, res):
    """独立した経路について、[ai] の concern / distinct の判断を添える"""
    sups = [S for S in p.get('supports', []) if S]
    if len(sups) < 2 or not p['groups']:
        return ''
    for c in res.get('concerns', []):
        if all(set(c['ids']) & S for S in sups):
            return (f'ただし、AI の判断で、{len(sups)} つの経路は争点「{c["name"]}」（{", ".join(c["ids"])}）を共有している。'
                    'この争点一つを崩すと、すべての経路が同時に崩れる（計算の上では経路は複数でも、内容の上の弱点は一つ）')
    for d in res.get('distincts', []):
        if all(set(d['ids']) & S for S in sups):
            return (f'AI の判断で、{len(sups)} つの経路の要（{", ".join(d["ids"])}）は内容の上でも互いに独立である（distinct）。'
                    '経路は互いに補い合う独立した根拠である')
    return '経路が内容の上でも独立か（同じ争点を共有していないか）は、AI が判断していない（[ai] の concern / distinct）'


def deep_search(th, l, cands, first_support, gsize, run):
    """依存が見つからない結論について、支持の組を集めながら、そのすべてと交わる組（hitting set）を試す。
    結論を消す組は、すべての支持の組と交わる必要がある（単調な部分について）。見つかった反例（外しても結論が残る組）
    からは、それを避ける新しい支持の組を作って加える。戻り値: (結論を消す組, 支持の組の一覧, 調べた大きさ)"""
    by_id = {c.id: c for c in cands}
    supports = [frozenset(first_support)]
    killers, tested = [], set()
    k = gsize
    for k in range(gsize + 1, AUTO_LOCAL + 1):
        while True:
            U = sorted(set().union(*supports), key=lambda x: int(x[1:]))
            hs = [frozenset(h) for n in range(1, k + 1) for h in itertools.combinations(U, n)
                  if all(set(h) & S for S in supports)]
            hs = [h for h in hs if h not in tested and not any(K <= h for K in killers)]
            hs = [h for h in hs if not any(g < h for g in hs)]
            if not hs:
                break
            grew = False
            for h in hs:
                tested.add(h)
                sk, cr = run([by_id[x] for x in h])
                if status(l, sk, cr) != 'holds':
                    killers.append(h)
                    continue
                S = support_avoiding(th, l, cands, h, run)
                if S is not None and frozenset(S) not in supports:
                    supports.append(frozenset(S))
                    grew = True
                    break
            if not grew:
                break
        if killers:
            break
    return killers, supports, k


def support_avoiding(th, l, cands, excluded, run):
    """excluded を外したうえで、なお l が残る候補の極小の組（なければ None）"""
    pool = [c for c in cands if c.id not in excluded]
    out = set(excluded)
    sk, cr = run([c for c in cands if c.id in out])
    if status(l, sk, cr) != 'holds':
        return None
    keep = list(pool)
    for c in list(pool):
        trial = [x for x in keep if x is not c]
        sk, cr = run([x for x in cands if x not in trial])
        if status(l, sk, cr) == 'holds':
            keep = trial
    return [c.id for c in keep]


def minimal_support(th, l, cands):
    """l が懐疑的帰結に残る、候補の極小の組を一つ（候補の順に外せるものを外していく）"""
    keep = list(cands)
    for c in list(cands):
        trial = [x for x in keep if x is not c]
        sk, cr, _, _ = consequences(drop(th, [x for x in cands if x not in trial]))
        if status(l, sk, cr) == 'holds':
            keep = trial
    return [c.id for c in keep]


def idsort(xs):
    return sorted(xs, key=lambda x: int(x[1:]))


def fmt_groups(p, limit=8):
    """組の一覧。独立した経路（互いに素な支持の組）から一つずつ外す形なら、積の形でまとめる"""
    groups = p['groups']
    if not groups:
        return '—'
    sups = sorted([S for S in p.get('supports', []) if S], key=lambda S: min(int(x[1:]) for x in S))
    if len(sups) > 1 and all(not (a & b) for a, b in itertools.combinations(sups, 2)):
        prod = 1
        for S in sups:
            prod *= len(S)
        gs = {frozenset(g) for g in groups}
        if len(gs) == prod and all(len(g) == len(sups) and all(len(g & S) == 1 for S in sups) for g in gs):
            return (f'独立した {len(sups)} つの経路から一つずつ外すと成り立たなくなる: '
                    + ' × '.join('{' + ', '.join(idsort(S)) + '}' for S in sups) + f'（{prod} 通り）')
    shown = '; '.join('{' + ', '.join(g) + '}' for g in groups[:limit])
    return shown + (f'; ほか {len(groups) - limit} 組' if len(groups) > limit else '')


def sensitivity_md(th, res, path):
    cands = {c.id: c for c in res['cands']}
    out = [f'# 感度分析: {os.path.basename(path)}', '',
           '（mext sensitivity の出力。争いうる前提を外して Extension を計算し直した結果。'
           '外すのは下の候補だけで、W の事実と規則はそのまま。「成り立つ」は、すべての preferred Extension に含まれること）', '',
           f'基準の理論: Extension {res["n_ext"]} 個（preferred {res["n_pref"]} 個）。候補 {len(cands)} 個。全候補で組の大きさ {res["size"]} まで調べた'
           + ('（依存が見つからない結論は、支持の組を集めて、そのすべてと交わる組を大きさ 4 まで調べた）' if res.get('auto') else '') + '。「—」は、調べた範囲で見つからなかったことを表し、より大きな組で効く可能性は残る。', '',
           '## 候補の前提', '', '| ID | 種類 | 名前 | 内容 | 行 | AI の審査 |', '|---|---|---|---|---|---|']
    for c in res['cands']:
        out.append(f'| {c.id} | {KIND_JA.get(c.kind, c.kind)} | {esc(str(c.label))} | {esc(c.text)} | {c.line} | {c.review} |')
    out += ['', '## 結論ごとの依存', '',
            '| 結論 | 基準 | 単独で外すと成り立たなくなる | 組で外すと成り立たなくなる（極小の組） | 外すと否定が成り立つ | 極小の支持の組（一例） | 調べた範囲 |',
            '|---|---|---|---|---|---|---|']

    def ids(xs):
        return ', '.join(xs) if xs else '—'
    for l in res['targets']:
        p = res['per'][l]
        if p is None:
            out.append(f'| {esc(th.lit_text(l))} | {STATUS_JA[res["base"][l]]} | | | | | |')
            continue
        groups = fmt_groups(p)
        pn = path_note(p, res)
        if pn and groups.startswith('独立した'):
            groups += '。' + pn
        out.append(f'| {esc(th.lit_text(l))} | 成り立つ | {ids(p["singles"])} | {groups} | {ids(p["flips"])} | {ids(p["support"])} | {p["explored"]} |')
    # 疑わしい評価への依存: 単独で必要なものと、組の一員にすぎないものを分ける
    dep1, depg = {}, {}
    for l in res['targets']:
        p = res['per'][l]
        if not p:
            continue
        for x in p['singles']:
            dep1.setdefault(x, []).append(l)
        for x in dict.fromkeys(y for g in p['groups'] for y in g):
            if x not in p['singles']:
                depg.setdefault(x, []).append(l)
    doubt = [c for c in res['cands'] if c.review in ('doubtful',)]
    out += ['', '## AI が doubtful とした評価', '']
    if not doubt:
        out.append('（なし）')
    for c in doubt:
        parts = []
        if c.id in dep1:
            parts.append('**単独で外すと成り立たなくなる**: ' + '、'.join(f'「{th.lit_text(l)}」' for l in dep1[c.id]))
        if c.id in depg:
            parts.append('組の一員（これ一つを外しても残るが、これを含む組を外すと成り立たなくなる）: '
                         + '、'.join(f'「{th.lit_text(l)}」' for l in depg[c.id]))
        if not parts:
            parts.append(f'調べた範囲（表の「調べた範囲」の列）では、これを外しても対象の結論はどれも成り立ったまま。'
                         'より大きな組で効く可能性は残る')
        out.append(f'- {c.id}「{c.text}」: ' + '。'.join(parts))
    if res.get('concerns'):
        out += ['', '## 争点のまとまり（[ai] の concern）', '',
                '| 争点 | 前提 | まとめて外すと成り立たなくなる結論 | 理由（AI） |', '|---|---|---|---|']
        for c in res['concerns']:
            lost = [l for l, st in c['status'].items() if res['base'][l] == 'holds' and st != 'holds']
            out.append(f'| {esc(c["name"])} | {", ".join(c["ids"])} | '
                       + esc('、'.join(f'「{th.lit_text(l)}」' for l in lost) or '（なし）') + f' | {esc(c["note"])} |')
    if res.get('distincts'):
        out += ['', '## 互いに独立とされた前提（[ai] の distinct）', '']
        out += [f'- {", ".join(d["ids"])}: {d["note"]}' for d in res['distincts']]
    if res.get('unresolved'):
        out += ['', '**[ai] の concern / distinct で、候補に当たらなかった文言**: ' + '、'.join(f'「{m}」' for m in res['unresolved'])]
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
# 結び方の感度（connectives）
# ---------------------------------------------------------------------------
def connective_groups(th):
    """二つ以上を並べた箇所（AND / OR の組）: (ファイル, 組のノード, 属する主張, 属する要件)"""
    out = []

    def rec(f, n, claim, req):
        if n.kind == 'claim':
            claim = n
        if n.kind in ('req', 'issue'):
            req = n
        if n.kind == 'group' and len(n.items) >= 2 and n.op in ('AND', 'OR'):
            out.append((f, n, claim, req))
        for k in ('facts', 'body', 'reason', 'norm', 'application'):
            x = getattr(n, k, None)
            if x is not None:
                rec(f, x, claim, req)
        for x in getattr(n, 'items', []) or []:
            rec(f, x, claim, req)
    for f, doc in zip(th.files, th.docs):
        rec(f, doc, None, None)
    return out


def connective_record(th, f, g, claim, req):
    """[ai] の connective の記録（明示 / 読み / None）"""
    names = [f'L{g.line}']
    if len(th.files) > 1:
        names.append(f'{os.path.splitext(os.path.basename(f))[0]}:L{g.line}')
    if req is not None and req.head:
        names += [req.head, f'%{req.head}', f'「{req.head}」']
    if claim is not None:
        names += [x for x in (claim.label, claim.head, f'#{claim.head}' if claim.head else None) if x]
    for nm in names:
        if nm in getattr(th, 'connectives', {}):
            return th.connectives[nm][0], nm
    return None, None


def concl_status(th):
    sk, cr, _, _ = consequences(th)
    return {th.lit_text(l): 'holds' for l in sk if th.by_id[abs(l)].kind in ('concl', 'claim')}, sk, cr


def connective_sensitivity(th, mf):
    """各組の AND / OR を入れ替えて理論を作り直し、懐疑的帰結（結論・主張）の変化を調べる"""
    base, sk0, cr0 = concl_status(th)
    finals = {th.lit_text(l) for l in core.final_conclusions(th)} | {th.lit_text(-l) for l in core.final_conclusions(th)}
    dep0 = {t: v for t, v in dependency(th).items() if t in finals}
    mf2 = copy.copy(mf)
    rows = []
    for f, g, claim, req in connective_groups(th):
        old = g.op
        g.op = 'OR' if old == 'AND' else 'AND'
        try:
            mf2.errs = []
            th2 = core.build_from_docs(mf2, th.ai, th.files, th.docs)
            new, _, _ = concl_status(th2)
            dep2 = {t: v for t, v in dependency(th2).items() if t in finals}
        finally:
            g.op = old
        dep_change = [(t, len(dep0[t]), len(dep2[t])) for t in sorted(set(dep0) & set(dep2)) if dep0[t] != dep2[t]]
        lost = sorted(t for t in base if t not in new)
        gained = sorted(t for t in new if t not in base)
        rec, nm = connective_record(th, f, g, claim, req)
        where = (f'{os.path.basename(f)}:' if len(th.files) > 1 else '') + f'L{g.line}'
        owner = (f'要件「{req.head}」' if req is not None and req.head else '') or \
                (f'主張「{claim.label or claim.head}」' if claim is not None else '（最上位）')
        rows.append({'where': where, 'owner': owner, 'op': old, 'lost': lost, 'gained': gained, 'record': rec,
                     'final_hit': [t for t in lost + gained if t in finals] + [t for t, _, _ in dep_change],
                     'dep_change': dep_change, 'n': len(g.items)})
    return rows


def connectives_md(th, rows, path):
    out = [f'# 結び方の感度: {os.path.basename(path)}', '',
           '（mext connectives の出力。二つ以上を並べた箇所の AND / OR を一つずつ入れ替えて計算し直し、'
           '懐疑的帰結（結論・主張）が変わる箇所を示す。結び方が原文に明示されているかの記録は、[ai] の connective による AI の判断）', '']
    dec = [r for r in rows if r['lost'] or r['gained'] or r['dep_change']]
    rec = {k: sum(1 for r in dec if r['record'] == k) for k in ('明示', '読み', None)}
    out.append(f'並べた箇所 {len(rows)} か所のうち、入れ替えると帰結か、最終的な結論の依存（単独で外すと結論が消える前提）が変わるもの {len(dec)} か所'
               f'（原文に明示 {rec["明示"]}・読み {rec["読み"]}・未記録 {rec[None]}）。'
               '明示のない結び方が結論を左右しているなら、結論から逆算した結び方でないかを、原文に照らして確かめる。')
    out += ['', '| 位置 | 属するもの | 今の結び方 | 入れ替えると成り立たなくなる | 入れ替えると新たに成り立つ | 入れ替えると依存が変わる最終的な結論（単独で効く前提の数: 今 → 入れ替え後） | AI の記録 |',
            '|---|---|---|---|---|---|---|']
    for r in dec:
        out.append(f'| {r["where"]} | {esc(r["owner"])} | {r["op"]}（{r["n"]} 項） | '
                   + esc('、'.join(f'「{t}」' for t in r['lost']) or '—') + ' | '
                   + esc('、'.join(f'「{t}」' for t in r['gained']) or '—') + ' | '
                   + esc('、'.join(f'「{t}」 {a} → {b}' for t, a, b in r['dep_change']) or '—') + f' | {r["record"] or "**未記録**"} |')
    out += ['', '依存の数が減る入れ替え（AND → OR）は結論を壊れにくくし、増える入れ替え（OR → AND）は壊れやすくする。'
            '今の結び方が、結論を最も壊れにくくする向きに選ばれていて、しかも原文に明示がないなら、とくに確かめる。']
    quiet = [r for r in rows if r not in dec]
    if quiet:
        out += ['', '入れ替えても帰結が変わらない箇所: ' + '、'.join(f'{r["where"]}（{r["op"]}）' for r in quiet)]
    return '\n'.join(out)


def cmd_connectives(args):
    mf, th, _ = load(args.file)
    md = connectives_md(th, connective_sensitivity(th, mf), args.file)
    if args.output:
        open(args.output, 'w', encoding='utf-8').write(md + '\n')
        print(f'{args.output} を書き出しました')
    else:
        print(md)
    return 0


# ---------------------------------------------------------------------------
# 書き起こしの後の変更（changed）
# ---------------------------------------------------------------------------
def changed(mf):
    """source: 行に記録したハッシュ値と、今のファイルを比べる。[(ファイル, 状態)]"""
    base = os.path.dirname(os.path.abspath(mf.path))
    out = []
    for rel, h in mf.sources.items():
        p = os.path.join(base, rel)
        if not os.path.exists(p):
            out.append((rel, 'missing'))
        else:
            out.append((rel, 'unchanged' if core.file_hash(p) == h else 'changed'))
    for f in mf.theory_files():
        m = core.memo_path(f)
        rel = os.path.relpath(m, base)
        if os.path.exists(m) and rel not in mf.sources:
            out.append((rel, 'new'))
    return out


def cmd_changed(args):
    mf = core.MextFile(args.file).load()
    if not mf.sources:
        print(f'{args.file} には source: 行がない（mext 0.3.3 より前に作られた）。変更は判定できない')
        return 2
    ja = {'unchanged': '変わっていない', 'changed': '**変わった**', 'missing': '見つからない', 'new': '**記録の後にできた**'}
    rows = changed(mf)
    print(f'# 記録の後の変更: {os.path.basename(args.file)}\n')
    print('（mext changed の出力。この .mext を最後に init / solve した時点のハッシュ値と、今のファイルを比べた）\n')
    for rel, st in rows:
        print(f'- {rel}: {ja[st]}')
    return 1 if any(st != 'unchanged' for _, st in rows) else 0


# ---------------------------------------------------------------------------
# 原文の出典と試算へのたどり
# ---------------------------------------------------------------------------
def source_note(th, line):
    """.matcha の line 行の直前にある // 出典: コメント（単一ファイルの場合）"""
    if len(th.files) != 1 or not isinstance(line, int) or line <= 0:
        return ''
    try:
        lines = open(th.files[0], encoding='utf-8').read().splitlines()
    except OSError:
        return ''
    for i in range(line - 2, max(-1, line - 8), -1):
        t = lines[i].strip()
        if t.startswith('//') and '出典' in t:
            return t.lstrip('/').strip()
        if t and not t.startswith('//'):
            if i < line - 2:
                break
    return ''


def trial_files(path, text):
    """同じディレクトリの X.alt-*.mext のうち、本体と違う [ai] / [extra] の行で text を扱っているもの（その前提を変えた試算）"""
    import glob
    base = os.path.splitext(path)[0]
    try:
        mf0 = core.MextFile(path).load()
        own = {core.split_note(ln)[0].strip() for _, ln in mf0.ai_lines + mf0.extra_lines}
    except Exception:          # noqa: BLE001
        own = set()
    out = []
    for f in sorted(glob.glob(base + '.alt-*.mext')):
        try:
            mf = core.MextFile(f).load()
        except Exception:      # noqa: BLE001
            continue
        if any(text in ln and core.split_note(ln)[0].strip() not in own for _, ln in mf.ai_lines + mf.extra_lines):
            out.append(os.path.basename(f))
    return out


# ---------------------------------------------------------------------------
# 一画面の要約（summary）
# ---------------------------------------------------------------------------
def short(c, n=36):
    """候補の短い表示: 評価は「@評価」の部分だけ"""
    t = c.text.rsplit('@', 1)[1] if c.kind == 'eval' and '@' in c.text else c.text
    t = t if len(t) <= n else t[:n - 1] + '…'
    mark = '〔doubtful〕' if c.review == 'doubtful' else ('〔未審査〕' if c.kind == 'eval' and not c.review else '')
    return f'{c.id}「{t}」{mark}'


def summary_md(th, mf, path):
    exts, pref, _ = core.solve(th)
    sc = core.scope(th, exts, pref)
    sk, cr = core.summarize(th, exts, pref)
    sk, cr = sk or set(), cr or set()
    # 最終的な結論ごとに、成り立つ側（結論か、その否定）を調べる
    shown = list(dict.fromkeys((-l if -l in sk else l) for l in sc['finals']))   # 結論とその否定が両方とも最終的な結論のときは一行にする
    targets = [l for l in shown if l in sk] or None
    res = sensitivity(th, targets)
    cands = {c.id: c for c in res['cands']}
    out = [f'# 要約: {os.path.basename(path)}', '',
           '（mext summary の出力。詳しくは mext report・mext sensitivity・mext explain）', '',
           f'- Extension {len(exts)} 個（preferred {sum(1 for p in pref if p)} 個）。',
           f'- 検証の範囲: {core.scope_text(th, sc)}', '']
    finals = sc['finals']
    crow = connective_sensitivity(th, mf)
    dec = [r for r in crow if r['final_hit']]
    if crow:
        rec = {k: sum(1 for r in dec if r['record'] == k) for k in ('明示', '読み', None)}
        out.insert(-1, f'- 結び方: 並べた箇所 {len(crow)} か所のうち、入れ替えると最終的な結論か、その依存が変わるもの {len(dec)} か所'
                       f'（原文に明示 {rec["明示"]}・読み {rec["読み"]}・未記録 {rec[None]}。記録は AI の判断。詳しくは mext connectives）。')
    out += ['## 最終的な結論', '',
            '| 結論 | 成否 | 対立する命題 | 決め手になる争いうる前提（単独で外すと成り立たなくなる） | 注意 |',
            '|---|---|---|---|---|']
    contested = {}
    for l in shown[:12]:
        st0 = status(l, sk, cr)
        st = STATUS_JA[st0]
        opp = 'あり' if core.opposed(th, l) else '**なし**'
        p = res['per'].get(l)
        notes = []
        keys = '—'
        if p:
            singles = [cands[x] for x in p['singles']]
            ev = [c for c in singles if c.kind != 'claim']
            keys = '、'.join(short(c, 24) for c in ev[:3]) + (f' ほか {len(ev) - 3}' if len(ev) > 3 else '') if ev else '—'
            if p['groups']:
                g = fmt_groups(p, limit=3)
                if g.startswith('独立した'):
                    notes.append(g)
                    pn = path_note(p, res)
                    if pn:
                        notes.append(pn)
                else:
                    notes.append('組で外すと成り立たなくなる: ' + g)
            if not p['singles'] and not p['groups']:
                notes.append('調べた範囲では、外すと成り立たなくなる前提はない（W の事実と、反論が立証されていないことから出ている）'
                             if not p['support'] else f'調べた範囲（{p["explored"]}）では見つからない')
            if any(c.review == 'doubtful' for c in singles):
                notes.append('doubtful の評価に依存')
            for x in p['singles']:
                if cands[x].kind == 'eval' and cands[x].review in ('doubtful', ''):
                    contested.setdefault(x, {'1': [], 'g': []})['1'].append(l)
            for x in dict.fromkeys(y for g2 in p['groups'] for y in g2):
                if x not in p['singles'] and cands[x].kind == 'eval' and cands[x].review in ('doubtful', ''):
                    contested.setdefault(x, {'1': [], 'g': []})['g'].append(l)
        if st0 == 'holds' and not core.opposed(th, l):
            notes.append('反対の根拠が理論にない')
        elif st0 != 'holds':
            notes.append('成り立たない理由（要件の不足、例外による阻却、対立する主張など）は mext explain でたどれる')
        out.append(f'| {esc(th.lit_text(l))} | {st} | {opp} | {esc(keys)} | {esc("。".join(notes))} |')
    if len(finals) > 12:
        out.append(f'\n（ほか {len(finals) - 12} 個。mext sensitivity で全部を見る）')
    out += ['', '## 争点（最終的な結論が依存している、doubtful または未審査の評価）', '']
    if not contested:
        out.append('（なし）')
    ranked = sorted(contested.items(), key=lambda kv: (-len(kv[1]['1']), -len(kv[1]['g']), int(kv[0][1:])))

    def names(ls):
        ls = list(dict.fromkeys(ls))
        return f'「{th.lit_text(ls[0])}」' + (f' ほか {len(ls) - 1} 個' if len(ls) > 1 else '')
    for x, d in ranked[:8]:
        parts = []
        if d['1']:
            parts.append(f'単独で外すと {names(d["1"])} が成り立たなくなる')
        if d['g']:
            parts.append(f'組の一員として {names(d["g"])} を支える（これ一つを外しても残る）')
        c = cands[x]
        nav = [f'L{c.line}'] if c.line else []
        sn = source_note(th, c.line)
        if sn:
            nav.append(sn)
        tf = trial_files(path, c.text)
        if tf:
            nav.append('試算: ' + '、'.join(tf))
        out.append(f'- {short(c, 50)}: ' + '。'.join(parts) + (f'（{" / ".join(nav)}）' if nav else ''))
    if len(ranked) > 8:
        out.append(f'- ほか {len(ranked) - 8} 個（mext sensitivity の「AI が doubtful とした評価」を見る）')
    if res.get('concerns'):
        out += ['', '## 争点のまとまり（[ai] の concern）', '']
        for c in res['concerns']:
            lost = [l for l in finals if res['base'].get(l) == 'holds' and c['status'].get(l) != 'holds']
            out.append(f'- 「{c["name"]}」（{", ".join(c["ids"])}）: まとめて崩すと、最終的な結論 '
                       + (names(lost) + ' が成り立たなくなる' if lost else 'はどれも成り立ったまま'))
    if res.get('unresolved'):
        out.append('\n**[ai] の concern / distinct で、候補に当たらなかった文言**: ' + '、'.join(f'「{m}」' for m in res['unresolved']))
    return '\n'.join(out)


def cmd_summary(args):
    mf, th, _ = load(args.file)
    md = summary_md(th, mf, args.file)
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
    """懐疑的帰結に入る結論の文言 -> 単独で外すと成り立たなくなる前提の文言の集合（候補を一つずつ外して計算する）"""
    sk0, cr0, _, _ = consequences(th)
    targets = default_targets(th, sk0)
    out = {th.lit_text(l): set() for l in targets}
    for c in candidates(th):
        sk, cr, _, _ = consequences(drop(th, [c]))
        for l in targets:
            if status(l, sk, cr) != 'holds':
                out[th.lit_text(l)].add(f'{KIND_JA.get(c.kind, c.kind)}「{c.text}」')
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
    txt = re.sub(r'(?m)^source:\s*(\S+)', lambda m: 'source: ' + mapping.get(os.path.basename(m.group(1)), m.group(1)), txt)
    open(dst_mext, 'w', encoding='utf-8').write(txt)
    print(f'{dst_mext} と ' + '、'.join(mapping.values()) + ' に保存しました（書き起こしを直したら mext diff '
          f'{os.path.basename(dst_mext)} {os.path.basename(args.file)} で比べる）')
    return 0


def add_parsers(sub):
    p = sub.add_parser('sensitivity', help='感度分析: 前提を外すと、どの結論が成り立たなくなるか')
    p.add_argument('file')
    p.add_argument('--target', action='append', help='対象の結論（文言。何度でも指定できる。既定は懐疑的帰結の結論すべて）')
    p.add_argument('--size', default='auto', help="同時に外す前提の数の上限（整数）。既定の auto は、全候補で 2 まで調べ、"
                   "依存が見つからない結論は、支持の組のすべてと交わる組を 4 まで調べる")
    p.add_argument('--facts', action='store_true', help='Matcha の事実（W）も候補にする（既定は [extra] で足した事実だけ）')
    p.add_argument('-o', '--output')
    p = sub.add_parser('summary', help='一画面の要約: 最終的な結論ごとの成否・対立する命題・決め手になる前提と、検証の範囲')
    p.add_argument('file')
    p.add_argument('-o', '--output')
    p = sub.add_parser('connectives', help='結び方の感度: AND / OR を一つずつ入れ替えると、どの帰結が変わるか')
    p.add_argument('file')
    p.add_argument('-o', '--output')
    p = sub.add_parser('changed', help='この .mext を作った後に、.matcha や書き起こしのメモが変わったか')
    p.add_argument('file')
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
    return {'sensitivity': cmd_sensitivity, 'summary': cmd_summary, 'connectives': cmd_connectives,
            'changed': cmd_changed, 'lint': cmd_lint, 'diff': cmd_diff, 'snapshot': cmd_snapshot}
