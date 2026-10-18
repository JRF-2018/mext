#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mext.py の回帰テスト: 例題の Extension の数・preferred の数・主要な帰結を確かめる"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from mext import core as mext

EX = os.path.join(HERE, '..', 'examples')
# (ファイル, Extension 数, preferred 数 or None, 懐疑的帰結に含まれるべき文言, 含まれてはならない文言)
CASES = [
    ('tweety.mext', 2, 1, ['¬トゥイーティーは飛ぶ'], ['トゥイーティーは飛ぶ']),
    ('nixon.mext', 2, None, [], ['ニクソンは平和主義者である', '¬ニクソンは平和主義者である']),
    ('sublease.mext', 2, 1, ['¬甲は本件賃貸借を解除できる'], []),
    ('minor_contract.mext', 2, 1, ['¬本件売買は有効である'], ['本件売買は有効である']),
    ('theft.mext', 1, None, ['甲に窃盗罪が成立する'], []),
    ('theft_fail.mext', 1, None, ['甲に窃盗罪は成立しない'], ['甲に窃盗罪が成立する']),
    ('self_defense.mext', 2, 1, ['¬甲に傷害罪が成立する'], ['甲に傷害罪が成立する']),
]
fail = 0
for fn, n_ext, n_pref, must, mustnot in CASES:
    mf = mext.MextFile(os.path.join(EX, fn)).load()
    th, _ = mext.build(mf)
    exts, pref, _ = mext.solve(th)
    sk, _ = mext.summarize(th, exts, pref)
    sk = sk or set()
    def has(t):
        l = mext.lit_from_text(th, t)
        return l is not None and l in sk
    probs = []
    if len(exts) != n_ext:
        probs.append(f'Extension 数 {len(exts)} ≠ {n_ext}')
    if n_pref is not None and sum(pref) != n_pref:
        probs.append(f'preferred 数 {sum(pref)} ≠ {n_pref}')
    probs += [f'懐疑的帰結に「{t}」がない' for t in must if not has(t)]
    probs += [f'懐疑的帰結に「{t}」がある' for t in mustnot if has(t)]
    for E in exts:
        if not mext.is_extension(th, E):
            probs.append('列挙した集合が Extension でない')
    print(('OK  ' if not probs else 'NG  ') + fn + ('' if not probs else ': ' + '; '.join(probs)))
    fail += bool(probs)
sys.exit(1 if fail else 0)
