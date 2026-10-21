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
import shlex
import shutil

try:
    from . import core
    from .i18n import t as _t, join, q, en as _en
except ImportError:            # パッケージとしてではなく直接実行された場合
    import core                # noqa: E402
    from i18n import t as _t, join, q, en as _en  # noqa: E402
INCONSISTENT = core.INCONSISTENT


# ---------------------------------------------------------------------------
# 共通
# ---------------------------------------------------------------------------
def load(path):
    mf = core.MextFile(path).load()
    th, diags = core.build(mf)
    return mf, th, diags


def variant(th, drop_defaults=(), drop_facts=(), add_facts=()):
    """前提を外した理論（規則と原子はそのまま）。add_facts は満たすとみなす要件（補った要件を外す試算）"""
    t = copy.copy(th)
    t.defaults = {k: v for k, v in th.defaults.items() if k not in drop_defaults}
    t.priority = {(a, b) for a, b in th.priority if a in t.defaults and b in t.defaults}
    t.W = [l for l in th.W if l not in drop_facts] + [l for l in add_facts if l not in th.W]
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


def kept(st, mode):
    """感度分析で結論が「残っている」か。mode が 'holds' なら懐疑的に、'credulous' なら少なくとも一つの preferred Extension で"""
    return st == 'holds' or (mode == 'credulous' and st == 'credulous')


class _PM:
    """単独で外すと懐疑的には成り立たなくなるが、一部の Extension には残る前提の印"""
    def __getitem__(self, i):
        return ' (still in some Extensions)' if _en() else '〔一部の Extension には残る〕'


PARTIAL_MARK = _PM()


class _L(dict):
    """値が (日本語, 英語) の辞書。出力の言語に合わせて返す"""
    def __getitem__(self, k):
        v = dict.__getitem__(self, k)
        return v[1] if _en() else v[0]

    def get(self, k, d=None):
        return self[k] if k in self else d


STATUS_JA = _L({'holds': ('成り立つ（懐疑的）', 'holds (skeptically)'), 'neg': ('否定が成り立つ', 'its negation holds'),
                'credulous': ('一部の Extension でだけ成り立つ', 'holds only in some Extensions'), 'none': ('成り立たない', 'does not hold')})


def esc(s):
    return s.replace('|', '\\|')


# ---------------------------------------------------------------------------
# 感度分析
# ---------------------------------------------------------------------------
class Cand:
    def __init__(self, cid, kind, key, label, text, line, review):
        self.id, self.kind, self.key, self.label, self.text, self.line, self.review = \
            cid, kind, key, label, text, line, review


KIND_JA = _L({'eval': ('評価', 'evaluation'), 'eval-all': ('評価（判断ごと。すべてのあてはめ）', 'evaluation (the whole judgment, all applications)'),
              'eval-one': ('評価（あてはめ一か所）', 'evaluation (one application)'), 'issue': ('論点', 'issue'), 'reason': ('理由', 'reason'),
              'extra': ('追加のデフォルト', 'added default'), 'claim': ('主張', 'claim'), 'fact': ('事実', 'fact'),
              'extra-fact': ('追加の事実', 'added fact'), 'fact-仮定': ('事実（仮定）', 'fact (assumption)'),
              'fact-著者の主張': ('事実（著者の主張）', "fact (author's claim)"),
              'supplied-req': ('補った要件（外すと、満たすとみなす）', 'supplied requirement (removing it treats it as met)')})


def candidates(th, facts=False):
    out = []
    # 同じ評価（事実@評価）が複数の箇所であてはめられていると、評価の原子一つを複数のデフォルトが支える。
    # そのときは「あてはめ一か所を外す」（デフォルト一つ）と「この判断を採らない」（原子を支えるデフォルトすべて。
    # review reject と同じ）を別の候補にする
    multi = {}
    for d in th.defaults.values():
        if d.kind == 'eval':
            multi.setdefault(d.concl[0], []).append(d)
    for d in th.defaults.values():
        if d.kind in ('eval', 'issue', 'reason', 'extra', 'claim'):
            if d.kind == 'eval':
                text = th.lit_text(d.concl[0])
                # 実際に効いた審査（"@評価" などの別名で書かれた review も含む）
                review = getattr(th, 'eval_status', {}).get(text) or ''
                ds = multi[d.concl[0]]
                if len(ds) > 1:
                    if d is ds[0]:
                        out.append(Cand(None, 'eval-all', ('a', d.concl[0]), '+'.join(x.name for x in ds), text, d.line, review))
                    out.append(Cand(None, 'eval-one', ('d', d.name), _t('{n}（L{l} のあてはめ）', '{n} (application at L{l})', n=d.name, l=d.line), text, d.line, review))
                    continue
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
        if a.kind == 'extra' or facts or kind_ai in ('仮定', '著者の主張') or a.text in getattr(th, 'supplied', {}):
            kind = 'extra-fact' if a.kind == 'extra' else ('fact-' + kind_ai if kind_ai else 'fact')
            out.append(Cand(None, kind, ('f', l), th.lit_str(l), th.lit_text(l), a.lines[0] if a.lines else '', kind_ai or ''))
    # 補った要件のうち、あてはめの評価を持たないもの（書き起こした者が足した関門）は、「満たすとみなす」ことを候補にする。
    # 外すと新たに成り立つ結論（感度分析の「外すと新たに成り立つ結論」）として効く
    seen = set()
    for t in getattr(th, 'supplied', {}):
        l = core.lit_from_text(th, t)
        if l is None or l < 0 or th.by_id[l].kind != 'req' or l in seen:
            continue
        if any(d.kind == 'eval' and len(d.just) > 1 and abs(d.just[1]) == l for d in th.defaults.values()):
            continue       # あてはめの評価があれば、その評価に印が付く
        seen.add(l)
        out.append(Cand(None, 'supplied-req', ('r', l), th.lit_str(l), th.lit_text(l), th.by_id[l].lines[0] if th.by_id[l].lines else '', ''))
    for i, c in enumerate(out, 1):
        c.id = f'p{i}'
    mark_supplied(th, out)
    return out


def req_names(th, l):
    """要件の原子の文言と、その素の名前（「主張／%要件」の %要件・要件）"""
    t = th.by_id[abs(l)].text
    tail = t.split('／', 1)[-1]
    return {t, tail, tail.lstrip('%'), tail.strip('「」')}


def mark_supplied(th, cands):
    """[ai] の supplied（書き起こした者が補った前提）を候補に印として付ける。評価・主張・事実の文言、ラベル、
    または要件の文言（その要件へのあてはめの評価に印を付ける）で書ける。当たらなかった文言は th.supplied_unresolved に"""
    sup = getattr(th, 'supplied', {})
    hit = set()
    for c in cands:
        c.supplied = False
        names = {c.text, str(c.label), c.id}
        if c.kind.startswith('eval') and '@' in c.text:
            names.add('@' + c.text.rsplit('@', 1)[1])      # 評価の部分だけ（"@評価"）でも指せる
        if c.kind.startswith('eval'):
            d = th.defaults[c.key[1]] if c.key[0] == 'd' else next(x for x in th.defaults.values()
                                                                    if x.kind == 'eval' and x.concl[0] == c.key[1])
            if len(d.just) > 1:
                names |= req_names(th, d.just[1])
        if c.kind == 'claim':
            d = th.defaults[c.key[1]]
            names |= {d.name}
        if c.kind == 'supplied-req':
            names |= req_names(th, c.key[1])
        for t in sup:
            if t in names:
                c.supplied = True
                hit.add(t)
    th.supplied_unresolved = [t for t in sup if t not in hit]


def drop(th, cands):
    names = [c.key[1] for c in cands if c.key[0] == 'd']
    atoms = {c.key[1] for c in cands if c.key[0] == 'a'}
    if atoms:
        names += [d.name for d in th.defaults.values() if d.kind == 'eval' and d.concl[0] in atoms]
    return variant(th, names, [c.key[1] for c in cands if c.key[0] == 'f'], [c.key[1] for c in cands if c.key[0] == 'r'])


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
        # 一部の Extension でだけ成り立つ結論も対象にする（その結論が成り立つ読みの中での依存を見るため）
        targets += [l for l in sorted(cr0, key=abs) if l not in sk0 and th.by_id[abs(l)].kind == 'concl' and l not in targets]
    cands = candidates(th, facts)
    auto = size == 'auto'
    pool = cands
    if auto:
        # 候補が多ければ、大きさ 2 の組は争いうる前提（主張そのものを除く）だけで調べる
        if len(cands) > AUTO_MAX_CANDS:
            pool = [c for c in cands if c.kind != 'claim']
        gsize = AUTO_GLOBAL if len(pool) <= AUTO_MAX_CANDS * 1.5 else 1
    else:
        gsize = int(size)
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
        for S in itertools.combinations(cands if k == 1 else pool, k):
            run(S)
            grid.add(frozenset(c.id for c in S))
    grid_desc = (_t('全候補で大きさ {k} まで', 'all candidates up to size {k}', k=gsize) if pool is cands or gsize == 1 else
                 _t('全候補で大きさ 1、主張を除く {n} 個で大きさ {k} まで', 'all candidates at size 1, {n} non-claim candidates up to size {k}',
                   n=len(pool), k=gsize))
    out = {'base': base, 'cands': cands, 'targets': targets, 'size': gsize, 'auto': auto, 'grid_desc': grid_desc,
           'n_ext': n0, 'n_pref': p0, 'per': {}}
    by_id = {c.id: c for c in cands}
    for l in targets:
        if base[l] not in ('holds', 'credulous'):
            out['per'][l] = None
            continue
        # 一部の Extension でだけ成り立つ結論は、成り立つ Extension が一つもなくなる組を探す（その読みの中での依存）
        mode = base[l]
        # 結論を直接導く唯一の主張（own）は、外せば結論が消えるのが当然なので、経路の探索では固定して残す
        own = {c.id for c in cands if c.kind == 'claim' and l in th.defaults[c.key[1]].concl}
        own = {x for x in own if not kept(status(l, *results[frozenset([x])]), mode)}   # それ一つで結論が消える、自明な場合だけ
        free = [c for c in cands if c.id not in own]
        fsupport = minimal_support(th, l, free, mode)
        support = idsort(fsupport + sorted(own))
        explored = grid_desc
        supports = [frozenset(fsupport)]
        killers = [ids for ids in grid if not kept(status(l, *results[ids]), mode)]
        if auto and fsupport and not [K for K in killers if not (K & own)]:
            deep, supports, k = deep_search(th, l, free, fsupport, gsize, run, mode)
            killers += deep
            explored += _t('、支持の組 {n} 通りのすべてと交わる組を大きさ {k} まで', '; sets meeting all {n} support sets up to size {k}', n=len(supports), k=k)
        minimal = [S for S in killers if not any(T < S for T in killers)]
        singles = sorted([next(iter(S)) for S in minimal if len(S) == 1], key=lambda x: int(x[1:]))
        groups = sorted([sorted(S, key=lambda x: int(x[1:])) for S in minimal if len(S) > 1])
        flips = sorted([next(iter(ids)) for ids in grid
                        if len(ids) == 1 and status(l, *results[ids]) == 'neg'], key=lambda x: int(x[1:]))
        # 懐疑的に成り立つ結論について、単独で外したとき一部の Extension には残るもの（すべての読みでは成り立たなくなるが、
        # どの読みからも導けなくなるわけではない）
        partial = [x for x in singles if mode == 'holds' and status(l, *results[frozenset([x])]) == 'credulous']
        out['per'][l] = {'singles': singles, 'groups': groups, 'flips': flips, 'support': support,
                         'explored': explored, 'supports': supports, 'partial': partial}
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
    for c in sorted(cands, key=lambda c: c.kind != 'eval-all'):
        if text in (c.id, c.text, str(c.label)):
            return c
    l = core.lit_from_text(th, text)
    if l is None:
        return None
    for c in cands:
        if c.key == ('a', l):
            return c
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
            return _t('ただし、AI の判断で、{n} つの経路は争点「{c}」（{i}）を共有している。'
                      'この争点一つを崩すと、すべての経路が同時に崩れる（計算の上では経路は複数でも、内容の上の弱点は一つ）',
                      'However, by the AI\'s judgment, the {n} paths share the point of contention “{c}” ({i}). '
                      'Defeating it defeats all paths at once (several paths in the computation, one weakness in content)',
                      n=len(sups), c=c["name"], i=", ".join(c["ids"]))
    for d in res.get('distincts', []):
        if all(set(d['ids']) & S for S in sups):
            return _t('AI の判断で、{n} つの経路の要（{i}）は内容の上でも互いに独立である（distinct）。経路は互いに補い合う独立した根拠である',
                      'By the AI\'s judgment, the key premises of the {n} paths ({i}) are independent in content (distinct): '
                      'the paths are independent grounds supporting each other', n=len(sups), i=", ".join(d["ids"]))
    return _t('経路が内容の上でも独立か（同じ争点を共有していないか）は、AI が判断していない（[ai] の concern / distinct）',
              'The AI has not judged whether the paths are independent in content (no shared point of contention; [ai] concern / distinct)')


def deep_search(th, l, cands, first_support, gsize, run, mode='holds'):
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
                if not kept(status(l, sk, cr), mode):
                    killers.append(h)
                    continue
                S = support_avoiding(th, l, cands, h, run, mode)
                if S is not None and frozenset(S) not in supports:
                    supports.append(frozenset(S))
                    grew = True
                    break
            if not grew:
                break
        if killers:
            break
    return killers, supports, k


def support_avoiding(th, l, cands, excluded, run, mode='holds'):
    """excluded を外したうえで、なお l が残る候補の極小の組（なければ None）"""
    pool = [c for c in cands if c.id not in excluded]
    out = set(excluded)
    sk, cr = run([c for c in cands if c.id in out])
    if not kept(status(l, sk, cr), mode):
        return None
    keep = list(pool)
    for c in list(pool):
        trial = [x for x in keep if x is not c]
        sk, cr = run([x for x in cands if x not in trial])
        if kept(status(l, sk, cr), mode):
            keep = trial
    return [c.id for c in keep]


def minimal_support(th, l, cands, mode='holds'):
    """l が懐疑的帰結に残る、候補の極小の組を一つ（候補の順に外せるものを外していく）"""
    keep = list(cands)
    for c in list(cands):
        trial = [x for x in keep if x is not c]
        sk, cr, _, _ = consequences(drop(th, [x for x in cands if x not in trial]))
        if kept(status(l, sk, cr), mode):
            keep = trial
    return [c.id for c in keep]


def idsort(xs):
    return sorted(xs, key=lambda x: int(x[1:]))


def is_product(p):
    """組が、独立した経路（互いに素な支持の組）から一つずつ外す形になっているか"""
    groups = p['groups']
    sups = [S for S in p.get('supports', []) if S]
    if not groups or len(sups) < 2 or any(a & b for a, b in itertools.combinations(sups, 2)):
        return False
    prod = 1
    for S in sups:
        prod *= len(S)
    gs = {frozenset(g) for g in groups}
    return len(gs) == prod and all(len(g) == len(sups) and all(len(g & S) == 1 for S in sups) for g in gs)


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
            return _t('独立した {n} つの経路から一つずつ外すと成り立たなくなる: {s}（{p} 通り）',
                      'fails when one premise is removed from each of {n} independent paths: {s} ({p} combinations)',
                      n=len(sups), s=' × '.join('{' + ', '.join(idsort(S)) + '}' for S in sups), p=prod)
    if limit is None:
        limit = len(groups)
    shown = '; '.join('{' + ', '.join(g) + '}' for g in groups[:limit])
    return shown + (_t('; ほか {n} 組（--full ですべて）', '; {n} more sets (all with --full)', n=len(groups) - limit) if len(groups) > limit else '')


def shared_judgments(res):
    """判断ごと外すと結論が消えるが、あてはめを一か所ずつ外しても消えない評価: [(判断の候補, あてはめの候補, 結論)]"""
    dep1 = {}
    for l, p in res['per'].items():
        for x in (p or {}).get('singles', []):
            dep1.setdefault(x, []).append(l)
    out = []
    for c in res['cands']:
        if c.kind != 'eval-all' or c.id not in dep1:
            continue
        sib = [x for x in res['cands'] if x.kind == 'eval-one' and x.text == c.text]
        keep = [l for l in dep1[c.id] if not any(l in dep1.get(x.id, []) for x in sib)]
        if keep:
            out.append((c, sib, keep))
    return out


def sensitivity_md(th, res, path, full=False):
    cands = {c.id: c for c in res['cands']}
    Q = q
    J = join
    out = [_t('# 感度分析: {f}', '# Sensitivity analysis: {f}', f=os.path.basename(path)), '',
           _t('（mext sensitivity の出力。争いうる前提を外して Extension を計算し直した結果。'
              '外すのは下の候補だけで、規則と、候補でない W の事実はそのまま（W の事実が候補になるのは、[ai] fact-kind で仮定・著者の主張としたもの、'
              '補った事実、--facts のとき）。「成り立つ」は、すべての preferred Extension に含まれること）',
              '(output of mext sensitivity: Extensions recomputed after removing contestable premises. Only the candidates below are '
              'removed; rules and the facts in W that are not candidates stay (facts in W become candidates when [ai] fact-kind marks them '
              'as assumptions or author claims, when supplied, or with --facts). “Holds” means being in every preferred Extension)'), '',
           _t('基準の理論: Extension {e} 個（preferred {p} 個）。候補 {n} 個。{g}調べた', 'Base theory: {e} Extension(s) ({p} preferred). '
              '{n} candidates. Searched {g}', e=res["n_ext"], p=res["n_pref"], n=len(cands), g=res["grid_desc"])
           + (_t('（依存が見つからない結論は、支持の組を集めて、そのすべてと交わる組を大きさ 4 まで調べた）',
                 ' (for conclusions with no dependency found, sets meeting every collected support set were tried up to size 4)')
              if res.get('auto') else '')
           + _t('。「—」は、調べた範囲で見つからなかったことを表し、より大きな組で効く可能性は残る。',
                '. “—” means none was found within that scope; larger sets may still matter.'), '',
           _t('## 候補の前提', '## Candidate premises'), '',
           _t('| ID | 種類 | 名前 | 内容 | 行 | AI の審査 | 補った前提 |', '| ID | kind | name | content | line | AI review | supplied |'),
           '|---|---|---|---|---|---|---|']
    for c in res['cands']:
        rvw = core.FACT_KIND_JA2EN.get(c.review, c.review) if _en() else c.review
        out.append(f'| {c.id} | {KIND_JA.get(c.kind, c.kind)} | {esc(str(c.label))} | {esc(c.text)} | {c.line} | {rvw} | '
                   + (_t('**補った**', '**supplied**') if getattr(c, 'supplied', False) else '') + ' |')
    out += ['', _t('## 結論ごとの依存', '## Dependencies of each conclusion'), '', _t('「成り立たなくなる」は、懐疑的に成り立つ結論では、すべての preferred Extension には入らなくなること（一部の Extension に残る場合は'
                 '〔一部の Extension には残る〕と印を付ける）。一部の Extension でだけ成り立つ結論では、どの preferred Extension にも入らなくなること。',
                 '“Defeats” means, for a conclusion that holds skeptically, that it is no longer in every preferred Extension (marked '
                 '“(still in some Extensions)” when it remains in some); for a conclusion that holds only in some Extensions, that it is in no preferred Extension.'), '',
            _t('| 結論 | 基準 | 単独で外すと成り立たなくなる | 組で外すと成り立たなくなる（極小の組） | 外すと否定が成り立つ | 極小の支持の組（一例） | 調べた範囲 |',
               '| conclusion | base | removing alone defeats it | removing a set defeats it (minimal sets) | removing makes its negation hold | a minimal support set (example) | scope searched |'),
            '|---|---|---|---|---|---|---|']

    def ids(xs, partial=()):
        return ', '.join(x + (PARTIAL_MARK[0] if x in partial else '') for x in xs) if xs else '—'
    for l in res['targets']:
        p = res['per'][l]
        if p is None:
            out.append(f'| {esc(th.lit_text(l))} | {STATUS_JA[res["base"][l]]} | | | | | |')
            continue
        groups = fmt_groups(p, limit=None if full else 8)
        pn = path_note(p, res)
        if pn and is_product(p):
            groups += _t('。', '. ') + pn
        out.append(f'| {esc(th.lit_text(l))} | {STATUS_JA[res["base"][l]]} | {ids(p["singles"], p.get("partial", ()))} | {groups} | {ids(p["flips"])} | {ids(p["support"])} | {p["explored"]} |')
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
    doubt = [c for c in res['cands'] if c.review in ('doubtful',)
             and not (c.kind == 'eval-one' and c.id not in dep1 and c.id not in depg)]
    out += ['', _t('## AI が doubtful とした評価', '## Evaluations the AI marked doubtful'), '']
    if not doubt:
        out.append(_t('（なし）', '(none)'))
    for c in doubt:
        parts = []
        if c.id in dep1:
            parts.append(_t('**単独で外すと成り立たなくなる**: ', '**removing it alone defeats**: ') + J(Q(th.lit_text(l)) for l in dep1[c.id]))
            if c.kind == 'eval-all':
                sib = [x for x in res['cands'] if x.kind == 'eval-one' and x.text == c.text]
                keep = [l for l in dep1[c.id] if not any(l in dep1.get(x.id, []) for x in sib)]
                if keep:
                    parts.append(_t('ただし、あてはめ {n} か所を一か所ずつ外しても {c} は残る（この判断が複数の経路に共通する弱点である）',
                                    'but removing its {n} applications one at a time leaves {c} standing (the judgment is a weakness shared by several paths)',
                                    n=len(sib), c=J(Q(th.lit_text(l)) for l in keep)))
        if c.id in depg:
            parts.append(_t('組の一員（これ一つを外しても残るが、これを含む組を外すと成り立たなくなる）: ',
                            'member of a set (removing it alone leaves the conclusion, removing a set containing it defeats it): ')
                         + J(Q(th.lit_text(l)) for l in depg[c.id]))
        if not parts:
            parts.append(_t('調べた範囲（表の「調べた範囲」の列）では、これを外しても対象の結論はどれも成り立ったまま。より大きな組で効く可能性は残る',
                            'within the scope searched (see the “scope searched” column), every target conclusion survives its removal; larger sets may still matter'))
        out.append(f'- {c.id}' + (' ' if _en() else '') + f'{Q(c.text)}: ' + _t('。', '. ').join(parts))
    if res.get('concerns'):
        out += ['', _t('## 争点のまとまり（[ai] の concern）', '## Shared points of contention ([ai] concern)'), '',
                _t('| 争点 | 前提 | まとめて外すと成り立たなくなる結論 | 理由（AI） |', '| point | premises | conclusions defeated when all are removed | reason (AI) |'),
                '|---|---|---|---|']
        for c in res['concerns']:
            lost = [l for l, st in c['status'].items() if kept(res['base'][l], 'credulous') and not kept(st, res['base'][l])]
            out.append(f'| {esc(c["name"])} | {", ".join(c["ids"])} | '
                       + esc(J(Q(th.lit_text(l)) for l in lost) or _t('（なし）', '(none)')) + f' | {esc(c["note"])} |')
    if res.get('distincts'):
        out += ['', _t('## 互いに独立とされた前提（[ai] の distinct）', '## Premises judged independent ([ai] distinct)'), '']
        out += [f'- {", ".join(d["ids"])}: {d["note"]}' for d in res['distincts']]
    if res.get('unresolved'):
        out += ['', _t('**[ai] の concern / distinct で、候補に当たらなかった文言**: ', '**Texts in [ai] concern / distinct that match no candidate**: ')
                + J(Q(m) for m in res['unresolved'])]
    shared_unres = getattr(th, 'supplied_unresolved', None) or []
    if shared_unres:
        out += ['', _t('**[ai] の supplied で、候補に当たらなかった文言**（評価・主張・事実・要件の文言で書く）: ',
                       '**Texts in [ai] supplied that match no candidate** (use the text of an evaluation, claim, fact or requirement): ')
                + J(Q(m) for m in shared_unres)]
    out += ['', _t('## 外すと新たに成り立つ結論（非単調性）', '## Conclusions that appear when a premise is removed (non-monotonicity)'), '']
    if not res['appear']:
        out.append(_t('（なし）', '(none)'))
    for cid, l in res['appear']:
        if cands[cid].kind == 'supplied-req':
            out.append(_t('- {i} を外す（補った要件 {x} を満たすとみなす）と{c}が成り立つ（成り立たないのは、書き起こした者が足した要件による）',
                          '- removing {i} (treating the supplied requirement {x} as met) makes {c} hold (it fails only because of a requirement the transcriber added)',
                          i=cid, c=Q(th.lit_text(l)), x=Q(cands[cid].text)))
            continue
        out.append(_t('- {i} を外すと{c}が成り立つ（{x} が、それを打ち消していた）', '- removing {i} makes {c} hold ({x} was blocking it)',
                      i=cid, c=Q(th.lit_text(l)), x=cands[cid].text))
    shared = [f'- {c.id}' + (' ' if _en() else '') + f'{Q(c.text)}'
              + _t('（あてはめ {n} か所: {s}）: あてはめを一か所ずつ外しても {k} は残るが、判断ごと外すと成り立たなくなる。この判断が複数の経路に共通する弱点である',
                   ' ({n} applications: {s}): removing the applications one at a time leaves {k} standing, but removing the whole judgment defeats it. '
                   'The judgment is a weakness shared by several paths',
                   n=len(sib), s=", ".join(x.id for x in sib), k=J(Q(th.lit_text(l)) for l in keep))
              + (_t('。**これは書き起こした者が補った前提である**（原文にない。別の読みでは、この共通の弱点は現れない可能性がある）',
                    '. **This premise was supplied by the transcriber** (not in the source; another reading may not show this shared weakness)')
                 if any(getattr(x, 'supplied', False) for x in [c] + sib) else '')
              for c, sib, keep in shared_judgments(res)]
    if shared:
        out += ['', _t('## 複数の経路に共通する判断', '## Judgments shared by several paths'), ''] + shared
    if any(c.kind == 'eval-all' for c in res['cands']):
        out += ['', _t('注: 同じ評価が複数の箇所にあてはめられているときは、「評価（判断ごと）」と「評価（あてはめ一か所）」を別の候補にした。'
                       '前者はその判断を採らないこと（review reject と同じ）、後者はあてはめの経路を一つだけ外すことである。'
                       '経路を一つ外しても結論が残るのに、判断ごと外すと結論が消えるなら、その判断が複数の経路に共通する弱点である。',
                       'Note: when the same evaluation is applied at several places, “evaluation (the whole judgment)” and “evaluation (one application)” '
                       'are separate candidates. The former means not adopting the judgment (as review reject); the latter removes one path of application. '
                       'If removing one path leaves the conclusion but removing the whole judgment defeats it, the judgment is a weakness shared by several paths.')]
    out += ['', _t('注: 「組で外すと」は、単独では結論が残るが、組で外すと成り立たなくなる極小の組である（同じ結論への独立した経路が複数ある場合に現れる）。'
                   '「極小の支持の組」は、候補をこの順に外せるだけ外して、なお結論が残る組の一例で、ほかの組もありうる。'
                   '^根拠（条文・原理の名前）は表示であって、独立に立証される前提ではないので、候補には入らない。',
                   'Note: “removing a set” lists minimal sets whose removal defeats a conclusion that survives any single removal (they appear when '
                   'independent paths lead to the same conclusion). “A minimal support set” is one example obtained by removing candidates in order as '
                   'long as the conclusion survives; others may exist. ^basis (names of statutes or principles) is a label, not an independently '
                   'proved premise, so it is not a candidate.')]
    return '\n'.join(out)


def cmd_sensitivity(args):
    mf, th, _ = load(args.file)
    targets = None
    if args.target:
        errs = []
        targets = [core.lit_from_text(th, t, errs) for t in args.target]
        if errs:
            raise SystemExit(_t('対象を解決できません: ', 'cannot resolve the targets: ') + '; '.join(errs))
    res = sensitivity(th, targets, args.size, args.facts)
    md = sensitivity_md(th, res, args.file, full=getattr(args, 'full', False))
    if args.output:
        open(args.output, 'w', encoding='utf-8').write(md + '\n')
        print(_t('{o} を書き出しました', 'wrote {o}', o=args.output))
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
        owner = (_t('要件{h}', 'requirement {h}', h=q(req.head)) if req is not None and req.head else '') or \
                (_t('主張{h}', 'claim {h}', h=q(claim.label or claim.head)) if claim is not None else _t('（最上位）', '(top level)'))
        rows.append({'where': where, 'owner': owner, 'op': old, 'lost': lost, 'gained': gained, 'record': rec,
                     'final_hit': [t for t in lost + gained if t in finals] + [t for t, _, _ in dep_change],
                     'dep_change': dep_change, 'n': len(g.items)})
    return rows


def connectives_md(th, rows, path):
    out = [_t('# 結び方の感度: {f}', '# Sensitivity to connectives: {f}', f=os.path.basename(path)), '',
           _t('（mext connectives の出力。二つ以上を並べた箇所の AND / OR を一つずつ入れ替えて計算し直し、'
              '懐疑的帰結（結論・主張）が変わる箇所を示す。結び方が原文に明示されているかの記録は、[ai] の connective による AI の判断）',
              '(output of mext connectives: each AND / OR joining two or more items is flipped in turn and the theory recomputed, '
              'showing where skeptical consequences (conclusions, claims) change. Whether a connective is explicit in the source is '
              'an AI judgment recorded by [ai] connective)'), '']
    dec = [r for r in rows if r['lost'] or r['gained'] or r['dep_change']]
    rec = {k: sum(1 for r in dec if r['record'] == k) for k in ('明示', '読み', None)}
    out.append(_t('並べた箇所 {n} か所のうち、入れ替えると帰結か、最終的な結論の依存（単独で外すと結論が消える前提）が変わるもの {d} か所'
                  '（原文に明示 {a}・読み {b}・未記録 {c}）。明示のない結び方が結論を左右しているなら、結論から逆算した結び方でないかを、原文に照らして確かめる。',
                  'Of {n} places, flipping {d} changes a consequence or the dependencies of a final conclusion (premises whose removal '
                  'alone defeats it) (explicit in the source {a}, reading {b}, unrecorded {c}). If a connective that is not explicit decides '
                  'a conclusion, check against the source that it was not chosen backwards from the conclusion.',
                  n=len(rows), d=len(dec), a=rec['明示'], b=rec['読み'], c=rec[None]))
    out += ['', _t('| 位置 | 属するもの | 今の結び方 | 入れ替えると成り立たなくなる | 入れ替えると新たに成り立つ | 入れ替えると依存が変わる最終的な結論（単独で効く前提の数: 今 → 入れ替え後） | AI の記録 |',
                   '| place | belongs to | connective | flipping defeats | flipping makes hold | final conclusions whose dependencies change (number of single decisive premises: now → flipped) | AI record |'),
            '|---|---|---|---|---|---|---|']
    recname = {'明示': _t('明示', 'explicit'), '読み': _t('読み', 'reading')}
    for r in dec:
        out.append(f'| {r["where"]} | {esc(r["owner"])} | {r["op"]}' + _t('（{n} 項）', ' ({n} items)', n=r["n"]) + ' | '
                   + esc(join(q(x) for x in r['lost']) or '—') + ' | '
                   + esc(join(q(x) for x in r['gained']) or '—') + ' | '
                   + esc(join(f'{q(x)} {a} → {b}' for x, a, b in r['dep_change']) or '—') + ' | '
                   + (recname.get(r["record"]) or _t('**未記録**', '**unrecorded**')) + ' |')
    out += ['', _t('依存の数が減る入れ替え（AND → OR）は結論を壊れにくくし、増える入れ替え（OR → AND）は壊れやすくする。'
                   '今の結び方が、結論を最も壊れにくくする向きに選ばれていて、しかも原文に明示がないなら、とくに確かめる。',
                   'A flip that reduces dependencies (AND → OR) makes a conclusion more robust; one that increases them (OR → AND) makes it '
                   'more fragile. Check especially when the current connective is the one that makes the conclusion most robust and is '
                   'not explicit in the source.')]
    quiet = [r for r in rows if r not in dec]
    if quiet:
        out += ['', _t('入れ替えても帰結が変わらない箇所: ', 'Places where flipping changes nothing: ') + join(f'{r["where"]} ({r["op"]})' for r in quiet)]
    return '\n'.join(out)


def cmd_connectives(args):
    mf, th, _ = load(args.file)
    md = connectives_md(th, connective_sensitivity(th, mf), args.file)
    if args.output:
        open(args.output, 'w', encoding='utf-8').write(md + '\n')
        print(_t('{o} を書き出しました', 'wrote {o}', o=args.output))
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
        print(_t('{f} には source: 行がない（mext 0.3.3 より前に作られた）。変更は判定できない',
                 '{f} has no source: lines (made before mext 0.3.3); changes cannot be determined', f=args.file))
        return 2
    ja = _L({'unchanged': ('変わっていない', 'unchanged'), 'changed': ('**変わった**', '**changed**'),
             'missing': ('見つからない', 'missing'), 'new': ('**記録の後にできた**', '**created after the record**')})
    rows = changed(mf)
    print(_t('# 記録の後の変更: {f}\n', '# Changes since the record: {f}\n', f=os.path.basename(args.file)))
    print(_t('（mext changed の出力。この .mext を最後に init / solve した時点のハッシュ値と、今のファイルを比べた）\n',
             '(output of mext changed: hashes recorded when this .mext was last init/solved, compared with the current files)\n'))
    for rel, st in rows:
        print(f'- {rel}: {ja[st]}')
    return 1 if any(st != 'unchanged' for _, st in rows) else 0


# ---------------------------------------------------------------------------
# 原文の出典と試算へのたどり
# ---------------------------------------------------------------------------
def cand_file(th, c):
    """候補の行がある .matcha（複数ファイルの理論で位置を示すため）。わからなければ None"""
    if c.key[0] == 'd' and c.key[1] in th.defaults:
        return getattr(th.defaults[c.key[1]], 'file', None)
    if c.key[0] == 'a':
        d = next((x for x in th.defaults.values() if x.kind == 'eval' and x.concl[0] == c.key[1]), None)
        return getattr(d, 'file', None) if d else None
    return None


def where(th, line, file=None):
    """行の位置の表示: 単一ファイルなら L12、複数ファイルなら post_2:L12"""
    if len(th.files) > 1 and file:
        return f'{os.path.splitext(os.path.basename(file))[0]}:L{line}'
    return f'L{line}'


def source_note(th, line, file=None):
    """.matcha の line 行の直前にある // 出典: コメント（複数ファイルの理論では file を指定する）"""
    if file is None:
        if len(th.files) != 1:
            return ''
        file = th.files[0]
    if not isinstance(line, int) or line <= 0:
        return ''
    try:
        lines = open(file, encoding='utf-8').read().splitlines()
    except OSError:
        return ''
    for i in range(line - 2, max(-1, line - 8), -1):
        t = lines[i].strip()
        if t.startswith('//') and ('出典' in t or 'source' in t.lower()):
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
        if any(core.mentions(ln, text) and core.split_note(ln)[0].strip() not in own for _, ln in mf.ai_lines + mf.extra_lines):
            out.append(os.path.basename(f))
    return out


# ---------------------------------------------------------------------------
# 一画面の要約（summary）
# ---------------------------------------------------------------------------
def short(c, n=36):
    """候補の短い表示: 評価は「@評価」の部分だけ"""
    t = c.text.rsplit('@', 1)[1] if c.kind.startswith('eval') and '@' in c.text else c.text
    t = t if len(t) <= n else t[:n - 1] + '…'
    t = q(t)
    mark = _t('〔doubtful〕', ' [doubtful]') if c.review == 'doubtful' else (_t('〔未審査〕', ' [unreviewed]') if c.kind.startswith('eval') and not c.review else '')
    if getattr(c, 'supplied', False):
        mark += _t('〔補った前提〕', ' [supplied]')
    return f'{c.id} {t}{mark}' if _en() else f'{c.id}{t}{mark}'


def review_note(th, c):
    """候補（評価）に効いた [ai] review の理由（別名で書いたものも）"""
    if not c.kind.startswith('eval'):
        return ''
    ev = c.text.rsplit('@', 1)[-1]
    for key, (st, note) in getattr(th, 'reviews', {}).items():
        if key == c.text or key == '@' + ev or core.lit_from_text(th, key) == core.lit_from_text(th, c.text):
            return note
    return ''


def summary_md(th, mf, path):
    exts, pref, _ = core.solve(th)
    sc = core.scope(th, exts, pref)
    sk, cr = core.summarize(th, exts, pref)
    sk, cr = sk or set(), cr or set()
    # 最終的な結論ごとに、成り立つ側（結論か、その否定）を調べる
    shown = list(dict.fromkeys((-l if -l in sk else l) for l in sc['finals']))   # 結論とその否定が両方とも最終的な結論のときは一行にする
    targets = [l for l in shown if l in sk or l in cr] or None
    res = sensitivity(th, targets)
    cands = {c.id: c for c in res['cands']}
    out = [_t('# 要約: {f}', '# Summary: {f}', f=os.path.basename(path)), '',
           _t('（mext summary の出力。詳しくは mext report・mext sensitivity・mext explain）',
              '(output of mext summary; for details see mext report, mext sensitivity, mext explain)'), '',
           _t('- Extension {n} 個（preferred {p} 個）。', '- {n} Extension(s) ({p} preferred).', n=len(exts), p=sum(1 for p in pref if p)),
           _t('- 検証の範囲: ', '- Scope of verification: ') + core.scope_text(th, sc), '']
    finals = sc['finals']
    out.insert(-1, _t('- 感度分析の範囲: 候補 {n} 個。{g}調べ、依存が見つからない結論は支持の組と交わる組を大きさ 4 まで広げた。'
                     '「—」は調べた範囲で見つからなかったことを表す。',
                     '- Scope of the sensitivity analysis: {n} candidates; searched {g}; for conclusions with no dependency found, '
                     'sets meeting every support set were tried up to size 4. “—” means none was found within that scope.',
                     n=len(res['cands']), g=res['grid_desc']))
    crow = connective_sensitivity(th, mf)
    dec = [r for r in crow if r['final_hit']]
    if crow:
        rec = {k: sum(1 for r in dec if r['record'] == k) for k in ('明示', '読み', None)}
        out.insert(-1, _t('- 結び方: 並べた箇所 {n} か所のうち、入れ替えると最終的な結論か、その依存が変わるもの {d} か所'
                          '（原文に明示 {a}・読み {b}・未記録 {c}。記録は AI の判断。詳しくは mext connectives）。',
                          '- Connectives: of {n} places, flipping {d} changes a final conclusion or its dependencies '
                          '(explicit {a}, reading {b}, unrecorded {c}; records are AI judgments; see mext connectives).',
                          n=len(crow), d=len(dec), a=rec['明示'], b=rec['読み'], c=rec[None]))
    out += [_t('## 最終的な結論', '## Final conclusions'), '', _t('「成り立たなくなる」は、懐疑的に成り立つ結論では、すべての preferred Extension には入らなくなること（一部の Extension に残る場合は'
                 '〔一部の Extension には残る〕と印を付ける）。一部の Extension でだけ成り立つ結論では、どの preferred Extension にも入らなくなること。',
                 '“Defeats” means, for a conclusion that holds skeptically, that it is no longer in every preferred Extension (marked '
                 '“(still in some Extensions)” when it remains in some); for a conclusion that holds only in some Extensions, that it is in no preferred Extension.'), '',
            _t('| 結論 | 成否 | 対立する命題 | 決め手になる争いうる前提（単独で外すと成り立たなくなる） | 注意 |',
               '| conclusion | status | opposing proposition | decisive contestable premises (removing alone defeats it) | notes |'),
            '|---|---|---|---|---|']
    contested = {}
    for l in shown[:12]:
        st0 = status(l, sk, cr)
        st = STATUS_JA[st0]
        opp = _t('あり', 'yes') if core.opposed(th, l) else _t('**なし**', '**none**')
        p = res['per'].get(l)
        notes = []
        keys = '—'
        if p:
            singles = [cands[x] for x in p['singles']]
            ev = [c for c in singles if c.kind != 'claim']
            keys = join(short(c, 24) + (PARTIAL_MARK[0] if c.id in p.get('partial', ()) else '') for c in ev[:3]) \
                + (_t(' ほか {n}（主張を除く）', ' and {n} more (claims excluded)', n=len(ev) - 3) if len(ev) > 3 else '') if ev else '—'
            if p['groups']:
                g = fmt_groups(p, limit=3)
                if is_product(p):
                    notes.append(g)
                    pn = path_note(p, res)
                    if pn:
                        notes.append(pn)
                else:
                    notes.append(_t('組で外すと成り立たなくなる: ', 'removing a set defeats it: ') + g)
            if not p['singles'] and not p['groups']:
                notes.append(_t('調べた範囲では、外すと成り立たなくなる前提はない（W の事実と、反論が立証されていないことから出ている）',
                                'no removable premise defeats it within the scope searched (it follows from facts in W and from unproved counter-arguments)')
                             if not p['support'] else _t('調べた範囲（{e}）では見つからない', 'none found within the scope searched ({e})', e=p["explored"]))
            if any(c.review == 'doubtful' for c in singles):
                notes.append(_t('doubtful の評価に依存', 'depends on doubtful evaluations'))
            if any(getattr(c, 'supplied', False) for c in singles):
                notes.insert(0, _t('**原文にない前提（書き起こした者が補ったもの）に依存する**: ',
                                   '**depends on premises not in the source (supplied by the transcriber)**: ')
                             + ', '.join(c.id for c in singles if getattr(c, 'supplied', False)))
            for x in p['singles']:
                if cands[x].kind.startswith('eval') and cands[x].review in ('doubtful', ''):
                    contested.setdefault(x, {'1': [], 'g': []})['1'].append(l)
            for x in dict.fromkeys(y for g2 in p['groups'] for y in g2):
                if x not in p['singles'] and cands[x].kind.startswith('eval') and cands[x].review in ('doubtful', ''):
                    contested.setdefault(x, {'1': [], 'g': []})['g'].append(l)
        if st0 == 'holds' and not core.opposed(th, l):
            notes.append(_t('反対の根拠が理論にない', 'no counter-argument in the theory'))
        elif st0 == 'credulous':
            ins = [f'E{i}' for i, (E, pp) in enumerate(zip(exts, pref), 1) if pp and E != INCONSISTENT and l in E]
            outs = [f'E{i}' for i, (E, pp) in enumerate(zip(exts, pref), 1) if pp and E != INCONSISTENT and l not in E]
            notes.append(_t('preferred Extension が分かれている（{a} では成り立ち、{b} では成り立たない）。対立する主張のあいだで優先が決まらない。'
                            '原文がどちらかを優先しているかを確かめる（優先していれば :: 優先 で書く。決着をつけていなければ、それが原文の論証の状態である）。'
                            '決め手の列は、外すと成り立つ preferred Extension が一つもなくなる前提（その読みの中での依存）',
                            'the preferred Extensions split (it holds in {a} but not in {b}): no priority settles the conflicting claims. '
                            'Check whether the source prefers one side (if so, write :: priority; if it leaves the question open, that is the state of its argument). '
                            'The decisive column lists premises whose removal leaves no preferred Extension containing it (dependencies within that reading)',
                            a=', '.join(ins), b=', '.join(outs)))
        elif st0 != 'holds' and [cid for cid, x in res.get('appear', []) if x == l and cands[cid].kind == 'supplied-req']:
            sr = [cid for cid, x in res['appear'] if x == l and cands[cid].kind == 'supplied-req']
            notes.append(_t('**書き起こした者が補った要件（{i}）のために成り立たない**。それを満たすとみなすと成り立つ',
                            '**fails only because of a requirement supplied by the transcriber ({i})**; treating it as met makes it hold', i=', '.join(sr)))
        elif st0 != 'holds':
            notes.append(_t('成り立たない理由（要件の不足、例外による阻却、対立する主張など）は mext explain でたどれる',
                            'mext explain shows why it does not hold (missing requirements, defeat by an exception, an opposing claim, etc.)'))
        out.append(f'| {esc(th.lit_text(l))} | {st} | {opp} | {esc(keys)} | {esc(_t("。", ". ").join(notes))} |')
    if len(finals) > 12:
        out.append(_t('\n（ほか {n} 個。mext sensitivity で全部を見る）', '\n({n} more; see mext sensitivity for all)', n=len(finals) - 12))
    out += ['', _t('## 争点（最終的な結論が依存している、doubtful または未審査の評価）',
                   '## Points of contention (doubtful or unreviewed evaluations on which final conclusions depend)'), '']
    if not contested:
        out.append(_t('（なし）', '(none)'))
    ranked = sorted(contested.items(), key=lambda kv: (-len(kv[1]['1']), -len(kv[1]['g']), int(kv[0][1:])))

    def names(ls):
        ls = list(dict.fromkeys(ls))
        return q(th.lit_text(ls[0])) + (_t(' ほか {n} 個', ' and {n} more', n=len(ls) - 1) if len(ls) > 1 else '')
    for x, d in ranked[:8]:
        parts = []
        if d['1']:
            part = all(x in (res['per'].get(l) or {}).get('partial', ()) for l in d['1'])
            parts.append(_t('単独で外すと {x} が成り立たなくなる', 'removing it alone defeats {x}', x=names(d["1"]))
                         + (PARTIAL_MARK[0] if part else ''))
        if d['g']:
            parts.append(_t('組の一員として {x} を支える（これ一つを外しても残る）', 'supports {x} as a member of a set (removing it alone leaves it)', x=names(d["g"])))
        c = cands[x]
        cf = cand_file(th, c)
        nav = [where(th, c.line, cf)] if c.line else []
        sn = source_note(th, c.line, cf)
        if sn:
            nav.append(sn)
        ai_ln = [i for i, ln in mf.ai_lines if core.mentions(ln, c.text)]
        if ai_ln:
            nav.append(_t('[ai] {n} 行目', '[ai] line {n}', n=ai_ln[0]))
        tf = trial_files(path, c.text)
        if tf:
            nav.append(_t('試算: ', 'trials: ') + join(tf))
        why = review_note(th, c)
        if why:
            parts.append(_t('AI の理由: {w}', 'AI’s reason: {w}', w=why if len(why) <= 80 else why[:79] + '…'))
        out.append(f'- {short(c, 50)}: ' + _t('。', '. ').join(parts) + ((_t('（{n}）', ' ({n})', n=" / ".join(nav))) if nav else ''))
    if len(ranked) > 8:
        out.append(_t('- ほか {n} 個（mext sensitivity の「AI が doubtful とした評価」を見る）',
                      '- {n} more (see “Evaluations the AI marked doubtful” in mext sensitivity)', n=len(ranked) - 8))
    apps = [x for x in getattr(th, 'app_status', []) if x[2] in ('doubtful', 'reject')]
    if apps:
        out += ['', _t('## 評価のないあてはめの審査（確定規則として読まれ、感度分析の候補にならない）',
                       '## Reviews of applications without an evaluation (read as strict rules; not candidates in the sensitivity analysis)'), '']
        for key, line, st, note, af in apps:
            sn = source_note(th, line, af)
            out.append(f'- {q(key)} 〔{st}〕' + (_t(': AI の理由: {w}', ': AI’s reason: {w}', w=note) if note else '')
                       + _t('（{l}{s}）', ' ({l}{s})', l=where(th, line, af), s=(' / ' + sn) if sn else ''))
        out.append(_t('（doubtful でも推論は止まらない。争うなら、あてはめを `事実@評価` の形に書き直すと、感度分析で外せる）',
                      '(doubtful does not stop inference. To contest it, rewrite the application as `fact@evaluation` so that the sensitivity analysis can remove it)'))
    sj = shared_judgments(res)
    if sj:
        out += ['', _t('## 複数の経路に共通する判断', '## Judgments shared by several paths'), '']
        for c, sib, keep in sj:
            sup = any(getattr(x, 'supplied', False) for x in [c] + sib)
            out.append(f'- {short(c, 50)}' + _t('（あてはめ {n} か所）: 一か所ずつ外しても {k} は残るが、判断ごと外すと成り立たなくなる',
                                               ' ({n} applications): removing them one at a time leaves {k}, but removing the whole judgment defeats it',
                                               n=len(sib), k=names(keep))
                       + (_t('。**書き起こした者が補った前提である**（別の読みでは、この共通の弱点は現れない可能性がある）',
                             '. **It was supplied by the transcriber** (another reading may not show this shared weakness)') if sup else ''))
    # 導出のたどり方（最終的な結論ごとに、それを含む preferred Extension で explain する）
    cmds = []
    for l in shown[:6]:
        idx = [i for i, (E, p) in enumerate(zip(exts, pref), 1) if p and E != INCONSISTENT and l in E]
        if idx:
            t = th.lit_text(l)
            t = shlex.quote(t) if re.search(r'["$`\\!]', t) else f'"{t}"'
            cmds.append(f'python3 -m mext explain {os.path.basename(path)} E{idx[0]} {t}')
    if cmds:
        out += ['', _t('## 導出をたどる', '## Tracing derivations'), '', '```'] + cmds + ['```']
    if res.get('concerns'):
        out += ['', _t('## 争点のまとまり（[ai] の concern）', '## Shared points of contention ([ai] concern)'), '']
        for c in res['concerns']:
            lost = [l for l in finals if kept(res['base'].get(l), 'credulous') and not kept(c['status'].get(l), res['base'].get(l))]
            out.append(f'- {q(c["name"])} ({", ".join(c["ids"])}): '
                       + (_t('まとめて崩すと、最終的な結論 {x} が成り立たなくなる', 'defeating them all defeats the final conclusion {x}', x=names(lost)) if lost
                          else _t('まとめて崩しても、最終的な結論はどれも成り立ったまま', 'defeating them all leaves every final conclusion standing')))
    if res.get('unresolved'):
        out.append(_t('\n**[ai] の concern / distinct で、候補に当たらなかった文言**: ', '\n**Texts in [ai] concern / distinct that match no candidate**: ')
                   + join(q(m) for m in res['unresolved']))
    if getattr(th, 'supplied_unresolved', None):
        out.append(_t('\n**[ai] の supplied で、候補に当たらなかった文言**: ', '\n**Texts in [ai] supplied that match no candidate**: ')
                   + join(q(m) for m in th.supplied_unresolved))
    return '\n'.join(out)


def cmd_summary(args):
    mf, th, _ = load(args.file)
    md = summary_md(th, mf, args.file)
    if args.output:
        open(args.output, 'w', encoding='utf-8').write(md + '\n')
        print(_t('{o} を書き出しました', 'wrote {o}', o=args.output))
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


REPORT_RE = re.compile(
    r'(と|として|を|で)(説明|判断|解釈|主張|考え|述べ|論じ|指摘|評価)(する|できる|している|した|される|がある|もできる|も可能)'
    r'|という(判断|見方|考え|解釈|立場|見解|主張)(がある|もある|もできる|をとる|を示す)|(著者|筆者)(は|の判断|の見方)|(解釈|考え|説明)も(でき|可能)|(応答|説明|解釈|回答|答え)(が|も)(なされる|与えられる|示される)'
    r'|\b(the author|the writer|the essay|the article)\b|\b(argues|claims|contends|suggests|explains) that\b'
    r'|\bcan be (read|interpreted|explained) as\b', re.I)
LEVEL = _L({'警告': ('警告', 'warning'), '情報': ('情報', 'note')})
LINT_NAMES = _L({'同語反復の評価': ('同語反復の評価', 'tautological evaluation'), '結論の文言の書き写し': ('結論の文言の書き写し', 'copied conclusion text'),
                 '立証の手段のない要件': ('立証の手段のない要件', 'requirement with no means of proof'), '事実の中の評価語': ('事実の中の評価語', 'evaluative words in a fact'),
                 '一段の主張が多い': ('一段の主張が多い', 'many one-step claims'), '行き止まりの主張': ('行き止まりの主張', 'dead-end claims'),
                 'どの Extension にも出ない主張': ('どの Extension にも出ない主張', 'claim in no Extension'),
                 '報告型の結論': ('報告型の結論', 'reported views as conclusions'),
                 '評価に依存する報告': ('評価に依存する報告', 'reports that depend on evaluations'),
                 '原文に見当たらない引用': ('原文に見当たらない引用', 'quotations not found in the source'), '効いていない判断': ('効いていない判断', 'ineffective judgment'),
                 '構文': ('構文', 'syntax')})


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
                                    _t('評価「@{e}」が要件「{h}」とほぼ同じ文言である。事実から要件への判断が一段にまとめられ、'
                                       'mext からは中身が見えない。判断の段階（中間の要件や、評価の理由）を書き分けられないか',
                                       'the evaluation “@{e}” nearly repeats the requirement “{h}”. The judgment from the fact to the '
                                       'requirement is folded into one step that mext cannot inspect. Can the steps (intermediate '
                                       'requirements, reasons for the evaluation) be written out?', e=e.eval, h=n.head)))
            if n.kind == 'req' and n.facts is None and n.body is None and n.mark != '!':
                hit = concl_texts.get(norm(n.head))
                if hit:
                    lab = f'$' + hit[0] if hit[0] else _t('（as でラベルを付けて）$ラベル', '$label (after adding a label with as)')
                    out.append((W, at(f, n.line), '結論の文言の書き写し',
                                _t('要件「{h}」は {w} の主張の結論と同じ文言である。前の主張の結論を要件にするなら {l} と書く'
                                   '（文言を写すと別の命題になり、同一視の判断が要る）',
                                   'the requirement “{h}” repeats the conclusion of the claim at {w}. To use an earlier conclusion as a '
                                   'requirement, write {l} (copying the text makes a different proposition that needs a same judgment)',
                                   h=n.head, w=hit[1], l=lab)))
                else:
                    out.append((W, at(f, n.line), '立証の手段のない要件',
                                _t('要件「{h}」には、あてはめる事実（<=）も下位の要件（:）もない。'
                                   'この要件は成り立ちようがないので、これを含む主張は働かない。意図したもの（原文の論証の穴）なら、メモにそう書く',
                                   'the requirement “{h}” has neither an applied fact (<=) nor sub-requirements (:). It cannot hold, so '
                                   'the claim containing it cannot apply. If intended (a gap in the source), say so in the memo', h=n.head)))
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
                                _t('事実「{h}」に評価の語（{w}）がある。評価が事実として W に入っていないか（評価なら「事実@評価」に分ける）',
                                   'the fact “{h}” contains evaluative words ({w}). Is an evaluation stored as a fact in W? '
                                   '(If so, split it into fact@evaluation)', h=n.head, w="・".join(words))))
    if n_claims >= 3 and len(one_step) >= 0.7 * n_claims:
        out.append((I, _t('全体', 'whole'), '一段の主張が多い',
                    _t('主張 {n} 個のうち {k} 個が、要件一つ・評価一つ以下である（{x}）。原文の論証がそれだけ単純か、論証の中身が評価にまとめられていないかを確かめる',
                       '{k} of {n} claims have at most one requirement and one evaluation ({x}). Check whether the source is that simple, '
                       'or whether the substance of the argument is folded into evaluations',
                       n=n_claims, k=len(one_step), x=join(map(str, one_step[:8])) + ('…' if len(one_step) > 8 else ''))))
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
        names = join(f'{x.label or x.head} ({at(f, x.line)})' for f, x in lonely)
        out.append((I, _t('全体', 'whole'), '行き止まりの主張',
                    _t('結論がどこにも使われていない主張が {n} 個ある: {x}。最終的な結論以外は、原文がそれを結論の支えや限定として置いていないか確かめる'
                       '（つながっていなければ、ほかの結論には効かない）',
                       '{n} claims have conclusions used nowhere: {x}. Apart from final conclusions, check whether the source uses them to '
                       'support or qualify a conclusion (unconnected, they affect no other conclusion)', n=len(lonely), x=names)))
    # 報告型の結論: 「…と説明する」「著者は…と考える」のように、立場を述べたことを結論にした書き起こし。
    # 報告は互いに両立するので、原文が両立しないとする立場どうしも対立しない（Extension が分かれない）。
    # 報告を $ラベルで受けて著者が評価している場合（「甲野氏は…と主張している」を前提に使う）は、報告の形が正しいので数えない
    reported = [(f, n) for f, n in claims if n.conclusion and REPORT_RE.search(n.conclusion['text']) and not (n.label and n.label in refs)]
    concls = [d.concl[1] for d in th.defaults.values() if d.kind == 'claim' and len(d.concl) > 1]
    no_opp = bool(concls) and not any(core.opposed(th, c) for c in concls)
    if len(reported) >= 2 and (no_opp or len(reported) >= 0.3 * len(claims)):
        names = join(f'{x.label or x.head} ({at(f, x.line)})' for f, x in reported[:6]) + ('…' if len(reported) > 6 else '')
        out.append((I, _t('全体', 'whole'), '報告型の結論',
                    _t('主張 {n} 個のうち {k} 個の結論が、立場を述べたことの報告の形である（{x}）。{o}'
                       '原文がその立場を主張しているなら立場そのものを結論にし、原文が両立しないとする立場どうしは、互いに否定し合う結論（>> not）として書く。'
                       '報告の形のままだと、報告どうしは両立するので対立が理論に現れない',
                       '{k} of {n} claims conclude with a report of a view ({x}).{o} If the source asserts the view, make the view itself the '
                       'conclusion; write views the source holds to be incompatible as conclusions that negate each other (>> not). '
                       'Reports are compatible with each other, so conflicts do not appear in the theory',
                       n=len(claims), k=len(reported), x=names,
                       o=_t('理論の中に、主張の結論と対立する命題が一つもない。', ' No conclusion of a claim has an opposing proposition in the theory.') if no_opp else '')))
    # 評価に依存する報告: 報告型の結論（原文にそう書かれている）が、その説明を受け入れる評価を要件にしている。
    # 評価を外す（review reject・感度分析）と、原文に書かれていることまで消える
    # $ラベルで前の主張を受けている主張は、報告を受けて評価する形（分けた書き方）なので数えない
    mixed = [(f, n) for f, n in claims if n.conclusion and REPORT_RE.search(n.conclusion['text'])
             and (evals_in(n.body) if n.body is not None else []) + (evals_in(n.facts) if n.facts is not None else [])
             and not (n.body is not None and any(x.kind == 'ref' for x in walk(n.body)))]
    if mixed:
        names = join(f'{x.label or x.head} ({at(f, x.line)})' for f, x in mixed[:6]) + ('…' if len(mixed) > 6 else '')
        out.append((I, _t('全体', 'whole'), '評価に依存する報告',
                    _t('報告の形の結論が評価を要件にしている主張が {k} 個ある（{x}）。評価を外すと、原文に書かれていること（報告）まで消える。'
                       '「原文にそう書かれている」と「その説明を受け入れる」を分けるなら、事実だけの報告の主張と、それを $ラベル で受けて評価する主張の二つにする',
                       '{k} claims conclude with a report but require an evaluation ({x}). Removing the evaluation also removes what the source says '
                       '(the report). To separate “the source says so” from “the explanation is accepted”, write a report claim with facts only, '
                       'and a second claim that takes it with $label and evaluates it', k=len(mixed), x=names)))
    # どの Extension にも出ない主張（著者が ! で不成立とした主張は除く）
    failed = {k for k, m, _, _ in th.marks if m == '!'}
    if exts is not None:
        live = [E for E, p in zip(exts, pref) if E != INCONSISTENT]
        union = set().union(*live) if live else set()
        for name, d in th.defaults.items():
            if d.kind == 'claim' and d.concl[0] not in union and d.concl[0] not in failed:
                out.append((I, f'L{d.line}', 'どの Extension にも出ない主張',
                            _t('主張 {n}（{c}）は、どの Extension にも含まれない。要件を満たす事実がないか、例外に打ち負かされている（mext explain で理由をたどれる）',
                               'claim {n} ({c}) is in no Extension: no fact satisfies its requirements, or an exception defeats it (see mext explain)',
                               n=name, c=th.lit_text(d.concl[0]))))
    # 出典の引用が原文にあるか（// 原文: のファイルがあるときだけ。段落番号までは確かめない）
    for f in th.files:
        miss = quote_misses(f)
        if miss:
            out.append((I, _t('全体', 'whole') if loc else os.path.basename(f), '原文に見当たらない引用',
                        _t('出典の注の引用 {n} か所が、原文のファイルに見当たらない（{x}）。引用を写し間違えたか、言い換えたか、別の箇所を指している。'
                           '原文に照らして直す（言い換えなら引用の形にしない）',
                           '{n} quotations in source notes are not found in the source file ({x}). They may be miscopied, paraphrased, or '
                           'point elsewhere. Check against the source (do not put a paraphrase in quotation marks)',
                           n=len(miss), x=join(f'L{ln}' + (f' {q(t[:24] + ("…" if len(t) > 24 else ""))}') for ln, t in miss[:6])
                           + ('…' if len(miss) > 6 else ''))))
    for e in mf.errs:
        out.append((W, '[ai]', '効いていない判断', e))
    return out


SRC_DECL = re.compile(r'^\s*//\s*(?:原文|Source document|Source text|Source)\s*[:：]\s*(\S+?\.(?:md|txt|html?))\b', re.I)
QUOTE_RE = re.compile(r'「((?:[^「」]|「[^「」]*」)*)」|“([^”]*)”|"([^"]*)"')
QUOTE_NORM = re.compile(r'[\s　「」『』“”"\'‘’（）()、，,。．.・]')


def quote_misses(path):
    """// 出典: / // Source: の注にある引用のうち、// 原文: のファイルに見当たらないもの: [(行, 引用)]"""
    import unicodedata
    try:
        lines = open(path, encoding='utf-8').read().splitlines()
    except OSError:
        return []
    src = None
    for ln in lines[:15]:
        m = SRC_DECL.match(ln)
        if m:
            cand = os.path.join(os.path.dirname(os.path.abspath(path)), m.group(1))
            if os.path.exists(cand):
                src = cand
                break
    if not src:
        return []
    def norm(t):
        return QUOTE_NORM.sub('', unicodedata.normalize('NFKC', t)).lower()
    body = norm(open(src, encoding='utf-8', errors='replace').read())
    out = []
    for i, ln in enumerate(lines, 1):
        t = ln.strip()
        if not t.startswith('//') or not re.search(r'出典|source', t, re.I) or SRC_DECL.match(ln):
            continue
        # 引用として調べるのは、注の最初の文（最初の引用の後の「。」まで）だけ。後ろの説明文の「…」は、語の言及や言い換えのことがある
        first = QUOTE_RE.search(t)
        if first:
            end = t.find('。', first.end())
            t = t if end < 0 else t[:end]
        for m in QUOTE_RE.finditer(t):
            qt = next(g for g in m.groups() if g is not None)
            frags = [norm(x) for x in re.split(r'…|\.\.\.|⋯|（略）|\(略\)', qt)]
            frags = [x for x in frags if len(x) >= 4]
            if frags and not all(x in body for x in frags):
                out.append((i, qt))
    return out


def cmd_lint(args):
    mf, th, diags = load(args.file)
    exts, pref, _ = core.solve(th)
    items = [('警告' if d.level == 'warning' else '情報', (f'{d.file}:' if d.file else '') + f'L{d.line}', '構文', d.msg)
             for d in diags if d.level in ('warning', 'info')]
    items += lint(th, mf, exts, pref)
    print(_t('# 書き起こしの検査: {f}\n', '# Transcription check: {f}\n', f=os.path.basename(args.file)))
    print(_t('（mext lint の出力。決定論的な目安で、警告があっても誤りとは限らない。直すかどうかは原文に照らして判断する）\n',
             '(output of mext lint: deterministic hints; a warning is not necessarily an error. Decide against the source whether to fix it)\n'))
    if not items:
        print(_t('指摘はない。', 'No findings.'))
        return 0
    print(_t('| 種類 | 位置 | 項目 | 内容 |\n|---|---|---|---|', '| level | place | item | detail |\n|---|---|---|---|'))
    for lv, where, what, msg in items:
        print(f'| {LEVEL[lv]} | {where} | {LINT_NAMES.get(what, what)} | {esc(msg)} |')
    nw = sum(1 for x in items if x[0] == '警告')
    print(_t('\n警告 {w} 件、情報 {i} 件', '\n{w} warnings, {i} notes', w=nw, i=len(items) - nw))
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
                out[th.lit_text(l)].add(f'{KIND_JA.get(c.kind, c.kind)}{q(c.text)}' if not _en() else f'{KIND_JA.get(c.kind, c.kind)} {q(c.text)}')
    return out


def diff_md(pa, pb, ta, tb, mfa, mfb, kinds, sens=True):
    ska, cra, na, pa_n = consequences(ta)
    skb, crb, nb, pb_n = consequences(tb)

    def keep(th, S):
        return {th.lit_text(l) for l in S if th.by_id[abs(l)].kind in kinds}
    A, B = keep(ta, ska), keep(tb, skb)
    Ac, Bc = keep(ta, cra), keep(tb, crb)
    kname = _L({'concl': ('結論', 'conclusions'), 'claim': ('主張', 'claims'), 'req': ('要件', 'requirements'), 'eval': ('評価', 'evaluations')})
    out = [_t('# 版の差分: {a} → {b}', '# Differences between versions: {a} → {b}', a=os.path.basename(pa), b=os.path.basename(pb)), '',
           _t('（mext diff の出力。原子は番号ではなく文言で対応づけている。「成り立つ」は、すべての preferred Extension に含まれること）',
              '(output of mext diff: atoms are matched by text, not by number. “Holds” means being in every preferred Extension)'), '',
           '## Extension', '',
           f'- {os.path.basename(pa)}: ' + _t('Extension {n} 個（preferred {p} 個）', '{n} Extension(s) ({p} preferred)', n=na, p=pa_n),
           f'- {os.path.basename(pb)}: ' + _t('Extension {n} 個（preferred {p} 個）', '{n} Extension(s) ({p} preferred)', n=nb, p=pb_n), '',
           _t('## 懐疑的帰結の変化（{k}）', '## Changes in skeptical consequences ({k})', k=_t('・', ', ').join(kname[k] for k in kinds)), '']
    flips = sorted(x for x in A if flip(x) in B)
    lost = sorted(x for x in A - B if flip(x) not in B)
    gained = sorted(x for x in B - A if flip(x) not in A)
    for title, xs in ((_t('否定に転じた', 'turned into their negation'), flips), (_t('成り立たなくなった', 'no longer hold'), lost),
                      (_t('新たに成り立つ', 'newly hold'), gained)):
        out.append(f'- **{title}**: ' + (join(q(x) for x in xs) if xs else _t('なし', 'none')))
    weak = sorted(x for x in lost if x in Bc)
    if weak:
        out.append(_t('  - うち、新しい版でも一部の Extension では成り立つもの: ', '  - of these, still holding in some Extensions of the new version: ')
                   + join(q(x) for x in weak))
    out += ['', _t('## 原子の増減', '## Atoms added and removed'), '']

    def rv(th, x):
        st = th.eval_status.get(x)
        return _t('（審査: {s}）', ' (review: {s})', s=st or _t('なし', 'none'))
    for k in ('concl', 'claim', 'eval', 'req'):
        a = {x for x, y in ta.atoms.items() if y.kind == k}
        b = {x for x, y in tb.atoms.items() if y.kind == k}
        add, rem = sorted(b - a), sorted(a - b)
        if add or rem:
            out.append(_t('- {k}: 追加 {a}、削除 {r}', '- {k}: {a} added, {r} removed', k=kname[k], a=len(add), r=len(rem)))
            out += [f'  - ＋ {x}' + (rv(tb, x) if k == 'eval' else '') for x in add[:30]]
            out += [f'  - － {x}' + (rv(ta, x) if k == 'eval' else '') for x in rem[:30]]
    if out[-1] == '':
        out.append(_t('（増減なし）', '(none)'))
    ch_rv = [(x, ta.eval_status.get(x), tb.eval_status.get(x)) for x in sorted(set(ta.eval_status) & set(tb.eval_status))
             if ta.eval_status.get(x) != tb.eval_status.get(x)]
    if ch_rv:
        none = _t('なし', 'none')
        out += ['', _t('実際に効いた審査が変わった評価:', 'Evaluations whose effective review changed:'), '']
        out += [f'- {q(x)}: {a or none} → {b or none}' for x, a, b in ch_rv]
    # 依存の変化（単独で外すと成り立たなくなる前提。前提は文言で対応づける）
    if sens:
        da, db = dependency(ta), dependency(tb)
        rows = []
        for x in sorted(set(da) & set(db)):
            if da[x] != db[x]:
                rows.append((x, sorted(da[x] - db[x]), sorted(db[x] - da[x])))
        out += ['', _t('## 依存の変化（単独で外すと結論が成り立たなくなる前提）', '## Changes in dependencies (premises whose removal alone defeats a conclusion)'), '']
        if not rows:
            out.append(_t('（両方の版で成り立つ結論について、変化はない）', '(no change for conclusions holding in both versions)'))
        for x, gone, new_ in rows:
            out.append(f'- {q(x)}')
            out += [_t('  - 依存しなくなった: ', '  - no longer depends on: ') + y for y in gone]
            out += [_t('  - 新たに依存する: ', '  - newly depends on: ') + y for y in new_]
    if ta.priority != tb.priority:
        out += ['', _t('## 優先順位', '## Priorities'), ''] + [f'- ＋ {a} > {b}' for a, b in sorted(tb.priority - ta.priority)] \
            + [f'- － {a} > {b}' for a, b in sorted(ta.priority - tb.priority)]
    ra, rb = ta.reviews, tb.reviews
    ch = [(x, ra.get(x, ('—',))[0], rb.get(x, ('—',))[0]) for x in sorted(set(ra) | set(rb))
          if ra.get(x, ('—',))[0] != rb.get(x, ('—',))[0]]
    out += ['', _t('## [ai] に書かれた行の増減', '## Lines added and removed in [ai]'), '']
    out += [f'- review{q(x)}: {a} → {b}' for x, a, b in ch] or [_t('- review の行の変化はない', '- no change in review lines')]
    la = {core.split_note(ln)[0].strip() for _, ln in mfa.ai_lines if core.split_note(ln)[0].strip()}
    lb = {core.split_note(ln)[0].strip() for _, ln in mfb.ai_lines if core.split_note(ln)[0].strip()}
    for x in sorted(lb - la):
        if not x.startswith('review'):
            out.append(f'- ＋ {x}')
    for x in sorted(la - lb):
        if not x.startswith('review'):
            out.append(f'- － {x}')
    if mfb.errs:
        out += ['', _t('**新しい版で効いていない [ai] の判断**（書き起こしを直したために、文言がどこにも当たらなくなったもの）:',
                       '**[ai] judgments with no effect in the new version** (their texts match nothing after the transcription was revised):'), '']
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
    files = mf.theory_files()

    def same_file(a, b):
        return open(a, 'rb').read() == open(b, 'rb').read()

    def usable(tag):
        # X.check.mext と X.mext が同じ X.matcha を使うとき、先に保存した同じ中身の X.vN.matcha はそのまま使う
        if os.path.exists(f'{base}.{tag}.mext'):
            return False
        return all(not os.path.exists(f'{os.path.splitext(f)[0]}.{tag}{os.path.splitext(f)[1]}')
                   or same_file(f, f'{os.path.splitext(f)[0]}.{tag}{os.path.splitext(f)[1]}') for f in files)
    if args.tag:
        tag = args.tag
        if not usable(tag):
            raise SystemExit(_t('版 {t} のファイルがすでにあり、中身が違います（別の --tag を使う）',
                                'files for version {t} already exist with different contents (use another --tag)', t=tag))
    else:
        k = 1
        while not usable(f'v{k}'):
            k += 1
        tag = f'v{k}'
    mapping = {}
    for f in files:
        b, ext = os.path.splitext(f)
        dst = f'{b}.{tag}{ext}'
        if not os.path.exists(dst):
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
    print(_t('{m} と {f} に保存しました（書き起こしを直したら mext diff {a} {b} で比べる）',
             'saved {m} and {f} (after revising the transcription, compare with mext diff {a} {b})',
             m=dst_mext, f=join(mapping.values()), a=os.path.basename(dst_mext), b=os.path.basename(args.file)))
    return 0


# ---------------------------------------------------------------------------
# 手順の点検（audit）
# ---------------------------------------------------------------------------
def verify_claims(th, mf, skeptical=False):
    """[claimed] の各行を検証する: [(名前, 成否 True/False, 説明)]"""
    exts, pref, _ = core.solve(th)
    out = []
    for name, claim_pref, items in mf.ext_claims:
        errs, need, absent = [], [], []
        for x in items:
            x = x.strip()
            (absent if x.startswith('!') else need).append(core.lit_from_text(th, x[1:] if x.startswith('!') else x, errs))
        if errs:
            out.append((name, False, '; '.join(errs)))
            continue
        pool = [i for i, E in enumerate(exts) if E != INCONSISTENT and (pref[i] or not claim_pref)]
        match = [i for i in pool if all(l in exts[i] for l in need) and all(l not in exts[i] for l in absent)]
        ok = (bool(pool) and set(match) == set(pool)) if skeptical else bool(match)
        out.append((name, ok, ''))
    return out


def audit(path):
    """分析の手順の抜けを点検する: [(結果 'ok'|'ng'|'na', 項目, 説明)]"""
    mf, th, diags = load(path)
    base = os.path.splitext(path)[0]
    rows = []

    def add(ok, item, msg=''):
        rows.append(('ok' if ok is True else ('na' if ok is None else 'ng'), item, msg))
    # 書き起こしの記録と、その後の変更
    files = th.files
    # 書き起こしの記録は X.check.mext。単一ファイルなら X.matcha から、複数ファイルの理論なら、この .mext の名前から探す
    cands_check = ([os.path.splitext(files[0])[0] + '.check.mext'] if len(files) == 1 else []) + \
        ([base + '.check.mext'] if not base.endswith('.check') else [path])
    check = next((c for c in cands_check if os.path.exists(c)), None)
    if check:
        cmf = core.MextFile(check).load()
        if not cmf.sources:
            add(False, _t('書き起こしの記録', 'transcription record'),
                _t('{f} に source: の記録がない', '{f} has no source: lines', f=os.path.basename(check)))
        else:
            ch = [(r, st) for r, st in changed(cmf) if st != 'unchanged']
            add(True if not ch else False, _t('書き起こしの後の変更', 'changes after transcription'),
                _t('なし', 'none') if not ch else join(f'{r}: {st}' for r, st in ch)
                + _t('（人の改訂なら、原文を読み直してその版を正とする手順をとったか）',
                    ' (if a human revised them, re-read the source and treat that version as authoritative)'))
    else:
        add(None, _t('書き起こしの記録', 'transcription record'),
            _t('X.check.mext がない（matcha分析を経ていない理論なら、問題ない）', 'no X.check.mext (fine if the theory did not come from a matcha analysis)'))
    memo = [core.memo_path(f) for f in files if os.path.exists(core.memo_path(f))]
    add(True if memo else None, _t('書き起こしのメモ', 'transcription memo'),
        join(os.path.basename(m) for m in memo) if memo else _t('なし', 'none'))
    # 構文と書き起こしの検査
    warn = [d for d in diags if d.level == 'warning']
    exts, pref, _ = core.solve(th)
    lint_w = [x for x in lint(th, mf, exts, pref) if x[0] == '警告']
    add(not warn and not lint_w, _t('構文の警告と lint の警告', 'syntax and lint warnings'),
        _t('なし', 'none') if not (warn or lint_w) else _t('構文 {a} 件、lint {b} 件', 'syntax {a}, lint {b}', a=len(warn), b=len(lint_w)))
    add(not mf.errs, _t('効いていない [ai] の判断', 'ineffective [ai] judgments'),
        _t('なし', 'none') if not mf.errs else _t('{n} 件（solve の注意を見る）', '{n} (see the notices of solve)', n=len(mf.errs)))
    # AI の判断の記録
    sc = core.scope(th, exts, pref)
    add(sc['unreviewed'] == 0, _t('評価の審査（review）', 'reviews of evaluations'),
        _t('未審査 {n} 個 / 評価 {m} 個', 'unreviewed {n} of {m}', n=sc['unreviewed'], m=sc['evals']))
    if sc.get('facts_total'):
        add(sc['facts']['未分類'] == 0, _t('事実の種別（fact-kind）', 'kinds of facts (fact-kind)'),
            _t('未分類 {n} 個 / 事実 {m} 個', 'unclassified {n} of {m}', n=sc['facts']['未分類'], m=sc['facts_total']))
    rows_c = connective_sensitivity(th, mf)
    dec = [r for r in rows_c if r['final_hit']]
    unrec = [r for r in dec if r['record'] is None]
    add(not unrec, _t('結論を左右する結び方の記録（connective）', 'records of decisive connectives (connective)'),
        _t('結論を左右する {a} か所のうち未記録 {b} か所', '{b} of {a} decisive places unrecorded', a=len(dec), b=len(unrec))
        + (' (' + join(r['where'] for r in unrec) + ')' if unrec else ''))
    if getattr(th, 'supplied_unresolved', None) is None:
        mark_supplied(th, candidates(th))
    add(not th.supplied_unresolved, _t('補った前提の記録（supplied）', 'records of supplied premises (supplied)'),
        _t('{n} 個（当たらない文言 {u} 個）', '{n} (unresolved {u})', n=len(getattr(th, 'supplied', {})), u=len(th.supplied_unresolved)))
    # 予測の検証
    if not mf.ext_claims:
        add(False, _t('予測（[claimed]）', 'prediction ([claimed])'), _t('ない', 'missing'))
    else:
        v1 = verify_claims(th, mf)
        v2 = verify_claims(th, mf, skeptical=True)
        add(True, _t('予測（[claimed]）の検証', 'verification of the prediction ([claimed])'),
            _t('信憑的 {a}/{n}、懐疑的 {b}/{n}（外れた予測も記録として残す。外れた理由をレポートに書く）',
              'credulous {a}/{n}, skeptical {b}/{n} (keep failed predictions; explain them in the report)',
              a=sum(ok for _, ok, _ in v1), b=sum(ok for _, ok, _ in v2), n=len(v1)))
    # 出力のファイル
    for suf, item in (('.summary.md', 'summary'), ('.sensitivity.md', 'sensitivity'), ('.connectives.md', 'connectives'),
                      (('.mext-analysis.md', '.report.md'), _t('レポート', 'report'))):
        # レポートは、mext-analysis なら X.mext-analysis.md、matcha-default-extensions なら X.report.md
        f = next((base + x for x in (suf if isinstance(suf, tuple) else (suf,)) if os.path.exists(base + x)),
                 base + (suf[0] if isinstance(suf, tuple) else suf))
        add(True if os.path.exists(f) else None, _t('出力: {i}', 'output: {i}', i=item),
            os.path.basename(f) if os.path.exists(f) else _t('なし', 'none'))
    return rows


def cmd_audit(args):
    rows = audit(args.file)
    mark = {'ok': '✓', 'ng': '✗', 'na': '－'}
    print(_t('# 手順の点検: {f}\n', '# Procedure audit: {f}\n', f=os.path.basename(args.file)))
    print(_t('（mext audit の出力。✗ は手順の抜け。なくすか、なくせない理由をレポートに書く。－ は当てはまらないか、任意のもの）\n',
            '(output of mext audit. ✗ marks a gap in the procedure: fix it, or state in the report why it cannot be fixed. － means not applicable or optional)\n'))
    print(_t('**✓ は手順が記録されていることを示すだけで、書き起こしや審査の妥当性を保証しない。**'
             '書き起こしが原文を適切に写しているか、評価が妥当かは、人や別の AI が原文と照らして確かめる。\n',
             '**A ✓ only shows that a step was recorded; it does not guarantee that the transcription or the reviews are sound.** '
             'Whether the transcription renders the source faithfully, and whether the evaluations are right, must be checked against the source by a person or another AI.\n'))
    print(_t('| 結果 | 項目 | 内容 |\n|---|---|---|', '| result | item | detail |\n|---|---|---|'))
    for r, item, msg in rows:
        print(f'| {mark[r]} | {item} | {esc(msg)} |')
    return 1 if any(r == 'ng' for r, _, _ in rows) else 0


def add_parsers(sub):
    p = sub.add_parser('sensitivity', help='感度分析: 前提を外すと、どの結論が成り立たなくなるか / sensitivity: which conclusions fail when premises are removed')
    p.add_argument('file')
    p.add_argument('--target', action='append', help='対象の結論（何度でも指定できる。既定は懐疑的帰結と、一部の Extension でだけ成り立つ結論） / target conclusion (repeatable)')
    p.add_argument('--size', default='auto', help="同時に外す前提の数の上限（整数か auto） / max number of premises removed together (integer or auto)")
    p.add_argument('--facts', action='store_true', help='Matcha の事実（W）も候補にする / also use the facts in W as candidates')
    p.add_argument('--full', action='store_true', help='組を省略せずにすべて示す / list every set without abbreviation')
    p.add_argument('-o', '--output')
    p = sub.add_parser('summary', help='一画面の要約 / one-screen summary of final conclusions, decisive premises and the scope of verification')
    p.add_argument('file')
    p.add_argument('-o', '--output')
    p = sub.add_parser('connectives', help='結び方の感度 / sensitivity to AND / OR connectives')
    p.add_argument('file')
    p.add_argument('-o', '--output')
    p = sub.add_parser('changed', help='記録の後の変更 / whether the .matcha or the memo changed since this .mext was made')
    p.add_argument('file')
    p = sub.add_parser('audit', help='手順の点検 / audit the analysis procedure (records, reviews, prediction, outputs)')
    p.add_argument('file')
    p = sub.add_parser('lint', help='書き起こしの粗さの検査 / check the transcription for coarseness')
    p.add_argument('file')
    p = sub.add_parser('diff', help='二つの版の差 / differences between two versions (consequences, Extensions, evaluations, [ai])')
    p.add_argument('old')
    p.add_argument('new')
    p.add_argument('--all', action='store_true', help='要件・評価の帰結の変化も示す / also show requirements and evaluations')
    p.add_argument('--no-sensitivity', action='store_true', help='依存の変化を省く / omit changes in dependencies')
    p = sub.add_parser('snapshot', help='版の保存 / save X.matcha and X.mext as X.vN.*')
    p.add_argument('file')
    p.add_argument('--tag', help='版の名前 / version tag (default v1, v2, …)')
    return {'sensitivity': cmd_sensitivity, 'summary': cmd_summary, 'connectives': cmd_connectives,
            'changed': cmd_changed, 'audit': cmd_audit, 'lint': cmd_lint, 'diff': cmd_diff, 'snapshot': cmd_snapshot}
