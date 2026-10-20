# -*- coding: utf-8 -*-
"""読みの比較（mext compare）: 同じ文書を別々に書き起こした二つの MEXT を突き合わせる（決定論的）。

原子の文言は読みごとに違うので、どの結論・前提が対応するかは AI（または人）が比較のファイル（X.compare）の
[match] に書く。文言が同じ（〔対象〕を除いて同じ）最終的な結論と、文言が同じ前提は、道具が自動で対応づける。
対応ごとに、成否、決め手（単独で外すと成り立たなくなる前提）、補った前提への依存、独立した経路、結び方の読みを比べる。

    @mext-compare 1
    a: tmp7/killing.mext
    b: tmp8/article.mext

    [match]
    match "A の結論の文言" "B の結論の文言"   ; 対応の理由
    match "A の評価の文言" "B の評価の文言"   ; 前提どうしも対応づけられる

どちらの読みが正しいかは示さない。違いは、書き起こしの選択か、原文の読みの違いである。
"""
import difflib
import os
import re

try:
    from . import core, analysis
    from .i18n import t as _t, join, q, en as _en
except ImportError:            # パッケージとしてではなく直接実行された場合
    import core                # noqa: E402
    import analysis            # noqa: E402
    from i18n import t as _t, join, q, en as _en  # noqa: E402
INCONSISTENT = core.INCONSISTENT
CJK = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')     # 表示を縮める長さを、日本語と英語で変える


def base_text(t):
    """結論の文言から〔対象〕を除いたもの（自動の対応づけに使う）"""
    return re.sub(r'〔[^〔〕]*〕$', '', t.lstrip('¬')).strip()


class CompareFile:
    def __init__(self, path):
        self.path = path
        self.a = self.b = None
        self.matches = []     # (A の文言, B の文言, 注, 行番号)
        self.errs = []

    def load(self):
        sec = None
        base = os.path.dirname(os.path.abspath(self.path))
        for i, ln in enumerate(open(self.path, encoding='utf-8').read().splitlines(), 1):
            body, note = core.split_note(ln)
            s = body.strip()
            if not s:
                continue
            m = re.match(r'^\[(\w+)\]$', s)
            if m:
                sec = m.group(1)
                continue
            m = re.match(r'^(a|b):\s*(.+)$', s)
            if sec is None and m:
                setattr(self, m.group(1), os.path.normpath(os.path.join(base, m.group(2).strip())))
                continue
            if sec is None and s.startswith('@mext-compare'):
                continue
            words, quoted = core.split_words(s)
            if sec == 'match' and len(words) == 3 and words[0] == 'match' and quoted[1] and quoted[2]:
                self.matches.append((words[1], words[2], note, i))
            else:
                self.errs.append(_t('{i} 行目を解釈できません: {l}', 'cannot parse line {i}: {l}', i=i, l=ln.strip()))
        if not (self.a and self.b):
            raise SystemExit(_t('{p}: a: と b: の行が要ります', '{p}: needs the lines a: and b:', p=self.path))
        return self


class Reading:
    """一つの読み（MEXT）について、比較に使う数をまとめて計算する"""
    def __init__(self, path):
        self.path = path
        self.mf, self.th, self.diags = analysis.load(path)
        th = self.th
        self.exts, self.pref, _ = core.solve(th)
        self.sc = core.scope(th, self.exts, self.pref)
        sk, cr = core.summarize(th, self.exts, self.pref)
        self.sk, self.cr = sk or set(), cr or set()
        self.finals = list(dict.fromkeys((-l if -l in self.sk else l) for l in self.sc['finals']))
        self.cands = analysis.candidates(th)
        self.res = None

    def lit(self, text):
        """結論・主張の文言（または別名）からリテラルを得る。前提（候補）なら None"""
        l = core.lit_from_text(self.th, text)
        if l is None or self.th.by_id[abs(l)].kind not in ('concl', 'claim'):
            return None
        if self.th.by_id[abs(l)].kind == 'claim':       # ラベルや #主張名で指したら、その主張の結論と比べる
            for d in self.th.defaults.values():
                if d.kind == 'claim' and len(d.concl) > 1 and d.concl[0] == abs(l):
                    return d.concl[1] if l > 0 else -d.concl[1]
        return l

    def cand(self, text):
        return analysis.resolve(self.th, self.cands, text)

    def status(self, l):
        return analysis.status(l, self.sk, self.cr)

    def analyze(self, extra_targets):
        targets = list(dict.fromkeys([l for l in self.finals if l in self.sk] +
                                     [l if l in self.sk else -l for l in extra_targets if l in self.sk or -l in self.sk]))
        self.res = analysis.sensitivity(self.th, targets or None)
        self.by_id = {c.id: c for c in self.res['cands']}
        self.crow = analysis.connective_sensitivity(self.th, self.mf)
        self.lint = analysis.lint(self.th, self.mf, self.exts, self.pref)

    def per(self, l):
        """結論 l（成り立つ側）の依存"""
        side = l if l in self.sk else (-l if -l in self.sk else l)
        p = self.res['per'].get(side) if self.res else None
        conn = [r for r in self.crow if self.th.lit_text(side) in r['final_hit'] or self.th.lit_text(side) in r['lost'] + r['gained']]
        return side, p, conn

    def overview(self):
        th, sc = self.th, self.sc
        n_claims = sum(1 for d in th.defaults.values() if d.kind == 'claim')
        return {
            'atoms': len(th.atoms), 'rules': len(th.rules), 'defaults': len(th.defaults), 'claims': n_claims,
            'exts': len(self.exts), 'pref': sum(1 for p in self.pref if p),
            'evals': sc['evals'], 'ok': sc['ok'], 'doubtful': sc['doubtful'], 'unreviewed': sc['unreviewed'], 'reject': sc['reject'],
            'supplied': sc['supplied'], 'finals': len(sc['finals']), 'finals_hold': len(sc['finals_hold']),
            'unopposed': len(sc['unopposed']),
            'lint_w': sum(1 for x in self.lint if x[0] == '警告'), 'lint_i': sum(1 for x in self.lint if x[0] != '警告'),
        }


def pair_matches(cf, A, B):
    """[match] の行と、文言が同じものの自動の対応づけ。(結論の対応, 前提の対応, 解決できなかった行)"""
    concl, prem, bad = [], [], []
    seen_a, seen_b = set(), set()
    for ta, tb, note, i in cf.matches if cf else []:
        la, lb = A.lit(ta), B.lit(tb)
        if la is not None and lb is not None:
            concl.append((la, lb, note or _t('（理由なし）', '(no reason given)'), 'match'))
            seen_a.add(abs(la))
            seen_b.add(abs(lb))
            continue
        ca, cb = (A.cand(ta) if la is None else None), (B.cand(tb) if lb is None else None)
        if ca is not None and cb is not None:
            prem.append((ca, cb, note or _t('（理由なし）', '(no reason given)'), 'match'))
            continue
        why = []
        if la is None and ca is None:
            why.append(_t('A に見当たらない', 'not found in A'))
        if lb is None and cb is None:
            why.append(_t('B に見当たらない', 'not found in B'))
        if not why:
            why.append(_t('一方は結論、他方は前提', 'one is a conclusion and the other a premise'))
        bad.append((i, ta, tb, join(why)))
    # 自動: 〔対象〕を除いた文言が同じ最終的な結論
    bmap = {}
    for l in B.finals:
        bmap.setdefault(base_text(B.th.lit_text(abs(l))), abs(l))
    for l in A.finals:
        if abs(l) in seen_a:
            continue
        k = base_text(A.th.lit_text(abs(l)))
        lb = bmap.get(k)
        if lb is not None and lb not in seen_b:
            concl.append((abs(l), lb, _t('文言が同じ（自動）', 'same text (automatic)'), 'auto'))
            seen_a.add(abs(l))
            seen_b.add(lb)
    # 自動: 文言が同じ前提
    have = {(ca.text, cb.text) for ca, cb, _, _ in prem}
    btext = {}
    for c in B.cands:
        btext.setdefault(c.text, c)
    for c in A.cands:
        cb = btext.get(c.text)
        if cb is not None and cb.kind == c.kind and (c.text, cb.text) not in have:
            prem.append((c, cb, _t('文言が同じ（自動）', 'same text (automatic)'), 'auto'))
            have.add((c.text, cb.text))
    return concl, prem, bad


def deps(R, p):
    """依存の表示用の値: (決め手の候補, 組の数, 独立した経路の数)"""
    if not p:
        return [], 0, 0
    singles = [R.by_id[x] for x in p['singles']]
    paths = len([S for S in p.get('supports', []) if S]) if analysis.is_product(p) else 0
    return singles, len(p['groups']), paths


def fmt_singles(singles, n=3):
    ev = [c for c in singles if c.kind != 'claim']
    if not ev:
        return '—'
    return join(analysis.short(c, 20 if CJK.search(c.text) else 40) for c in ev[:n]) + (_t(' ほか {n}', ' and {n} more', n=len(ev) - n) if len(ev) > n else '')


def compare_md(A, B, cf=None, cpath=None):
    concl, prem, bad = pair_matches(cf, A, B)
    A.analyze([la for la, _, _, _ in concl])
    B.analyze([lb for _, lb, _, _ in concl])
    pa = {ca.id: cb.id for ca, cb, _, _ in prem}           # A の候補 -> B の候補
    na, nb = os.path.basename(A.path), os.path.basename(B.path)
    out = [_t('# 読みの比較: A = {a}、B = {b}', '# Comparison of readings: A = {a}, B = {b}', a=na, b=nb), '',
           _t('（mext compare の出力。対応は、比較のファイルの [match]（AI か人の判断）と、文言が同じもの（自動）。'
              '比べているのは書き起こした二つの理論で、どちらの読みが正しいかは示さない。違いは、書き起こしの選択か、原文の読みの違いである）',
              '(output of mext compare. Correspondences come from [match] in the comparison file (judgments by an AI or a person) and from '
              'identical texts (automatic). It compares two transcribed theories and does not say which reading is right: a difference is '
              'either a choice of transcription or a different reading of the source)'), '']
    if cpath:
        out += [_t('- 比較のファイル: {p}', '- Comparison file: {p}', p=os.path.basename(cpath))]
    out += [f'- A: {A.path}', f'- B: {B.path}', '']
    # 1. 全体
    oa, ob = A.overview(), B.overview()
    rows = [('atoms', _t('原子', 'atoms')), ('rules', _t('規則', 'rules')), ('defaults', _t('デフォルト', 'defaults')),
            ('claims', _t('主張', 'claims')), ('exts', 'Extension'), ('pref', 'preferred'),
            ('evals', _t('評価', 'evaluations')), ('ok', 'ok'), ('doubtful', 'doubtful'), ('unreviewed', _t('未審査', 'unreviewed')),
            ('reject', 'reject'), ('supplied', _t('補った前提', 'supplied premises')),
            ('finals', _t('最終的な結論', 'final conclusions')), ('finals_hold', _t('うち成り立つもの', 'of which hold')),
            ('unopposed', _t('うち対立する命題がないもの', 'of which have no opposing proposition')),
            ('lint_w', _t('lint の警告', 'lint warnings')), ('lint_i', _t('lint の情報', 'lint notes'))]
    out += [_t('## 1. 全体', '## 1. Overview'), '', '| | A | B |', '|---|---|---|']
    out += [f'| {lab} | {oa[k]} | {ob[k]} |' for k, lab in rows]
    out.append('')
    # 2. 対応する結論
    out += [_t('## 2. 対応する結論', '## 2. Corresponding conclusions'), '',
            _t('決め手は、単独で外すと成り立たなくなる争いうる前提（主張そのものを除く）。共通の決め手は、[match] で対応づけた前提のうち、両方で決め手のもの。',
               'Decisive premises are contestable premises whose removal alone defeats the conclusion (claims themselves excluded). '
               'Shared ones are premises matched in [match] that are decisive in both readings.'), '',
            _t('| # | A の結論 | B の結論 | 成否 A / B | 決め手 A | 決め手 B | 共通の決め手 | 違い | 対応の根拠 |',
               '| # | conclusion in A | conclusion in B | status A / B | decisive in A | decisive in B | shared decisive | differences | basis of the match |'),
            '|---|---|---|---|---|---|---|---|---|']
    n_diff_status = 0
    for k, (la, lb, note, how) in enumerate(concl, 1):
        sa, pa_, conn_a = A.per(la)
        sb, pb_, conn_b = B.per(lb)
        sta, stb = A.status(la), B.status(lb)
        da, ga, patha = deps(A, pa_)
        db, gb, pathb = deps(B, pb_)
        shared = [(x.id, pa[x.id]) for x in da if x.kind != 'claim' and pa.get(x.id) in {y.id for y in db}]
        diff = []
        if sta != stb:
            n_diff_status += 1
            diff.append(_t('**成否が違う**', '**status differs**'))
            for side, st_ in (('A', sta), ('B', stb)):
                if st_ == 'credulous':
                    diff.append(_t('{s} では preferred Extension が分かれる（優先の決まらない対立がある）',
                                   'the preferred Extensions of {s} split (a conflict no priority settles)', s=side))
        sup_a = [c.id for c in da if getattr(c, 'supplied', False)]
        sup_b = [c.id for c in db if getattr(c, 'supplied', False)]
        if bool(sup_a) != bool(sup_b):
            diff.append(_t('補った前提に依存するのは {s} だけ', 'only {s} depends on supplied premises', s='A' if sup_a else 'B'))
        ea = [c for c in da if c.kind != 'claim']
        eb = [c for c in db if c.kind != 'claim']
        if bool(ea) != bool(eb):
            diff.append(_t('決め手があるのは {s} だけ', 'only {s} has decisive premises', s='A' if ea else 'B'))
        if patha != pathb and (patha or pathb):
            diff.append(_t('独立した経路 A {a}・B {b}', 'independent paths A {a}, B {b}', a=patha or '—', b=pathb or '—'))
        ra = [r for r in conn_a if r['record'] != '明示']
        rb = [r for r in conn_b if r['record'] != '明示']
        if bool(ra) != bool(rb):
            diff.append(_t('明示のない結び方に左右されるのは {s} だけ', 'only {s} turns on connectives not explicit in the source',
                           s='A' if ra else 'B'))
        doubt_a = [c.id for c in da if c.review == 'doubtful']
        doubt_b = [c.id for c in db if c.review == 'doubtful']
        if bool(doubt_a) != bool(doubt_b):
            diff.append(_t('doubtful の評価に依存するのは {s} だけ', 'only {s} depends on doubtful evaluations', s='A' if doubt_a else 'B'))
        st = f'{analysis.STATUS_JA[sta]} / {analysis.STATUS_JA[stb]}'
        sh = join(f'{x}={y}' for x, y in shared) if shared else '—'
        out.append(f'| {k} | {analysis.esc(A.th.lit_text(la))} | {analysis.esc(B.th.lit_text(lb))} | {st} | '
                   f'{analysis.esc(fmt_singles(da))} | {analysis.esc(fmt_singles(db))} | {sh} | '
                   f'{analysis.esc(_t("。", "; ").join(diff)) or "—"} | {analysis.esc(note)} |')
    if not concl:
        out.append(_t('| | （対応する結論がない。[match] に書く） | | | | | | | |', '| | (no corresponding conclusions; write them in [match]) | | | | | | | |'))
    out.append('')
    out.append(_t('対応 {n} 組のうち、成否が違うもの {d} 組。', '{d} of {n} corresponding pairs differ in status.', n=len(concl), d=n_diff_status))
    out.append('')
    # 3. 対応のない最終的な結論
    ma = {abs(la) for la, _, _, _ in concl}
    mb = {abs(lb) for _, lb, _, _ in concl}
    ua = [l for l in A.finals if abs(l) not in ma]
    ub = [l for l in B.finals if abs(l) not in mb]
    out += [_t('## 3. 対応のない最終的な結論', '## 3. Final conclusions with no counterpart'), '',
            _t('一方の読みにしかない結論は、もう一方が書き起こさなかったか、別の形（中間の結論、前提、別の命題）で書いたものである。'
               '対応するものがあれば [match] に書く。',
               'A conclusion found in only one reading was either not transcribed by the other or written in another form (an intermediate '
               'conclusion, a premise, a different proposition). If there is a counterpart, write it in [match].'), '']
    for side, R, us in (('A', A, ua), ('B', B, ub)):
        out.append(_t('- {s} だけ（{n} 個）: ', '- only in {s} ({n}): ', s=side, n=len(us))
                   + (join(f'{q(R.th.lit_text(l))}（{analysis.STATUS_JA[R.status(l)]}）' if not _en()
                           else f'{q(R.th.lit_text(l))} ({analysis.STATUS_JA[R.status(l)]})' for l in us[:12])
                      + (_t(' ほか {n} 個', ' and {n} more', n=len(us) - 12) if len(us) > 12 else '') if us else '—'))
    out.append('')
    # 4. 対応する前提
    out += [_t('## 4. 対応する前提', '## 4. Corresponding premises'), '',
            _t('同じ判断を、二つの読みがどう審査し、どの結論の決め手にしているか。',
               'How the two readings review the same judgment, and which conclusions it decides.'), '']
    if prem:
        out += [_t('| A の前提 | B の前提 | 種類 | 審査 A / B | 決め手にしている結論の数 A / B | 対応の根拠 |',
                   '| premise in A | premise in B | kind | review A / B | conclusions it decides A / B | basis of the match |'),
                '|---|---|---|---|---|---|']
        dec_a = decisive_count(A)
        dec_b = decisive_count(B)
        for ca, cb, note, how in prem[:40]:
            ra = ca.review or (_t('未審査', 'unreviewed') if ca.kind.startswith('eval') else '—')
            rb = cb.review or (_t('未審査', 'unreviewed') if cb.kind.startswith('eval') else '—')
            out.append(f'| {analysis.esc(analysis.short(ca, 40))} | {analysis.esc(analysis.short(cb, 40))} | '
                       f'{analysis.KIND_JA.get(ca.kind, ca.kind)} | {ra} / {rb} | {dec_a.get(ca.id, 0)} / {dec_b.get(cb.id, 0)} | {analysis.esc(note)} |')
        if len(prem) > 40:
            out.append(_t('\n（ほか {n} 組）', '\n({n} more)', n=len(prem) - 40))
    else:
        out.append(_t('（なし。同じ判断を指す前提は [match] で対応づけられる）', '(none; premises for the same judgment can be matched in [match])'))
    out.append('')
    # 5. 解決できなかった行
    errs = (cf.errs if cf else []) + [_t('{i} 行目 {a} / {b}: {w}', 'line {i} {a} / {b}: {w}', i=i, a=q(ta), b=q(tb), w=w) for i, ta, tb, w in bad]
    if errs:
        out += [_t('## 5. 解決できなかった [match] の行', '## 5. [match] lines that could not be resolved'), '']
        out += [f'- {e}' for e in errs]
        out.append('')
    return '\n'.join(out)


def decisive_count(R):
    cnt = {}
    for l, p in R.res['per'].items():
        for x in (p or {}).get('singles', []):
            cnt[x] = cnt.get(x, 0) + 1
    return cnt


def template(A, B, out_path):
    """比較のファイルのひな形: 自動の対応と、対応のない最終的な結論を注として並べる"""
    base = os.path.dirname(os.path.abspath(out_path))
    concl, prem, _ = pair_matches(None, A, B)
    ma = {abs(la) for la, _, _, _ in concl}
    mb = {abs(lb) for _, lb, _, _ in concl}
    lines = ['@mext-compare 1',
             f'a: {os.path.relpath(os.path.abspath(A.path), base)}',
             f'b: {os.path.relpath(os.path.abspath(B.path), base)}',
             _t('; 読みの比較（mext compare）。[match] の行は AI（または人）の判断。; の後に理由を書く。',
                '; comparison of readings (mext compare). Lines in [match] are judgments by an AI (or a person); write the reason after ;.'),
             _t(';   match "A の文言" "B の文言"   … 同じ結論（または同じ前提）を指す。ラベルや #主張名 でもよい',
                ';   match "text in A" "text in B"   … the same conclusion (or premise); labels and #claim names also work'),
             _t('; 文言が同じ（〔対象〕を除いて同じ）最終的な結論と、文言が同じ前提は、自動で対応づける（ここに書かなくてよい）。',
                '; Final conclusions with the same text (ignoring 〔target〕) and premises with the same text are matched automatically.'),
             '', '[match]']
    ua = [abs(l) for l in A.finals if abs(l) not in ma]
    ub = [abs(l) for l in B.finals if abs(l) not in mb]
    sugg = []
    for la in ua:
        ta = base_text(A.th.lit_text(la))
        best = max(((difflib.SequenceMatcher(None, ta, base_text(B.th.lit_text(lb))).ratio(), lb) for lb in ub), default=None)
        if best and best[0] >= 0.6:
            sugg.append((best[0], la, best[1]))
    if sugg:
        lines.append(_t('; 文言の近い組（文字の一致の割合による機械的な候補。対応するかは原文と両方の読みに照らして判断する）:',
                        '; pairs with similar texts (mechanical candidates by character overlap; judge against the source and both readings):'))
        lines += [f';   match {core.qs(A.th.lit_text(la))} {core.qs(B.th.lit_text(lb))}   ; {r:.2f}' for r, la, lb in sorted(sugg, reverse=True)]
    lines.append(_t('; 対応のない最終的な結論（A）:', '; final conclusions with no counterpart (A):'))
    lines += [f';   {core.qs(A.th.lit_text(l))}' for l in ua]
    lines.append(_t('; 対応のない最終的な結論（B）:', '; final conclusions with no counterpart (B):'))
    lines += [f';   {core.qs(B.th.lit_text(l))}' for l in ub]
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def cmd_compare(args):
    files = args.files
    if args.init:
        if len(files) != 2:
            raise SystemExit(_t('--init には A.mext と B.mext を指定する', '--init takes A.mext and B.mext'))
        out = args.output or '{}.vs.{}.compare'.format(*(os.path.splitext(os.path.basename(f))[0] for f in files))
        if os.path.exists(out):
            raise SystemExit(_t('{o} はすでにあります（上書きしない）', '{o} already exists (not overwritten)', o=out))
        template(Reading(files[0]), Reading(files[1]), out)
        print(_t('{o} を書き出しました（[match] に対応を書いてから mext compare {o}）', 'wrote {o} (write correspondences in [match], then run mext compare {o})', o=out))
        return 0
    cf, cpath = None, None
    if len(files) == 1 and files[0].endswith('.compare'):
        cpath = files[0]
        cf = CompareFile(cpath).load()
        a, b = cf.a, cf.b
    elif len(files) == 2:
        a, b = files
        if args.match:
            cpath = args.match
            cf = CompareFile(cpath).load()
    else:
        raise SystemExit(_t('X.compare か、A.mext B.mext を指定する', 'give X.compare, or A.mext B.mext'))
    md = compare_md(Reading(a), Reading(b), cf, cpath)
    if args.output:
        open(args.output, 'w', encoding='utf-8').write(md + '\n')
        print(_t('{o} を書き出しました', 'wrote {o}', o=args.output))
    else:
        print(md)
    return 0


def add_parsers(sub):
    p = sub.add_parser('compare', help='読みの比較 / compare two transcriptions (readings) of the same document')
    p.add_argument('files', nargs='+', help='X.compare、または A.mext B.mext / X.compare, or A.mext B.mext')
    p.add_argument('-m', '--match', help='対応を書いた比較のファイル（A.mext B.mext と使う） / comparison file with [match] (with A.mext B.mext)')
    p.add_argument('--init', action='store_true', help='比較のファイルのひな形を書き出す / write a template comparison file')
    p.add_argument('-o', '--output')
    return {'compare': cmd_compare}
