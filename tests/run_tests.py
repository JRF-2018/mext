#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""構文チェッカの回帰テスト: tests/expected.json に書いたエラー数・警告数と一致するかを確かめる"""
import json, os, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from mext.matcha_check import check_text

expected = json.load(open(os.path.join(HERE, 'expected.json'), encoding='utf-8'))
files = sorted(glob.glob(os.path.join(HERE, 'corpus*', '*.matcha')) + glob.glob(os.path.join(HERE, '..', 'examples', '*.matcha')))
fail = 0
for f in files:
    key = os.path.relpath(f, os.path.join(HERE, '..'))
    _, diags, _ = check_text(open(f, encoding='utf-8').read())
    got = {'error': sum(d.level == 'error' for d in diags), 'warning': sum(d.level == 'warning' for d in diags)}
    exp = expected.get(key, {'error': 0, 'warning': 0})
    ok = got == {'error': exp['error'], 'warning': exp['warning']}
    if not ok:
        fail += 1
        print(f'NG  {key}: 期待 {exp} / 実際 {got}')
        for d in diags:
            print('      ' + str(d))
print(f'{len(files)} ファイル中 {len(files) - fail} 件が期待どおり')
sys.exit(1 if fail else 0)
