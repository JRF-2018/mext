#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
matcha_check.py -- Matcha / Matcha-D の決定論的な構文チェッカ

Matcha (https://www.elecode.jp/matcha) は花房孟胤氏による法的推論の形式言語である。
公式の BNF は公開されていないため、このチェッカの文法は Elecode のページと
花房氏の連載「法律には形式言語がない」の用例から本レポートが読み取ったものである。

Matcha-D は本レポートによる最小拡張:
    >> 結論 as ラベル         … 主張（＝デフォルト）に名前を付ける（as は Matcha 既存）
    ... !> $ラベル            … この主張はラベルの主張の「例外」である（例外が勝つ）
    >> not 結論 / >> !結論    … 結論の古典否定（>> の直後に置いたときだけ演算子。両者は同じ意味）
    :: 優先 $d2 > $d1         … 例外関係とは別に優先順位だけを宣言する注釈行（任意）

使い方:
    python3 matcha_check.py FILE.matcha            # エラー・警告の一覧（エラーがあれば終了コード 1）
    python3 matcha_check.py --tree FILE.matcha     # 構文木を人が読める形で表示
    python3 matcha_check.py --json FILE.matcha     # 構文木を JSON で出力

依存ライブラリなし（Python 3.8 以降）。
"""
import sys
import re
import json
import argparse

# ---------------------------------------------------------------------------
# 全角記号の正規化（1 文字 → 1 文字なので桁位置は変わらない）
# 全角の括弧（）は法文中で普通に使われる（「建造物」（１０８条）など）ので変換しない。
# ---------------------------------------------------------------------------
FULLWIDTH = {
    '＃': '#', '％': '%', '＾': '^', '＠': '@', '＆': '&', '｜': '|', '＄': '$',
    '？': '?', '！': '!', '＋': '+', '：': ':', '＜': '<', '＞': '>', '＝': '=',
    '～': '~', '〜': '~',
}
FW_TABLE = str.maketrans(FULLWIDTH)

# 2 文字の演算子（長いものから照合）
OPS2 = ['<=', '>>', '~>', '=>', '!>']
# 1 文字の演算子
OPS1 = ['&', '|', '@', '^', ':']
# テキストの読み取りを止める演算子の先頭
STOP2 = set(OPS2)
STOP1 = set(OPS1)

LABEL_CHARS = r'[^\s<>=~!&|@^:()「」$]+'
AS_RE = re.compile(r'\s+as\s+(' + LABEL_CHARS + r')\s*(?=$|<=|>>|~>|=>|!>|&|\||@|\^|:|\))')
AS_LINE_START_RE = re.compile(r'as\s+(' + LABEL_CHARS + r')\s*(?=$|<=|>>|~>|=>|!>|&|\||@|\^|:|\))')
PRIORITY_RE = re.compile(r'^優先\s+\$(' + LABEL_CHARS + r')\s*>\s*\$(' + LABEL_CHARS + r')\s*$')


class Tok:
    __slots__ = ('type', 'value', 'line', 'col', 'indent', 'first', 'extra')

    def __init__(self, type_, value, line, col, indent=0, first=False, extra=None):
        self.type = type_      # NL, SECTION, PRIORITY, OP, LPAREN, RPAREN, QUOTE, SIGIL, MARK, REF, AS, NOT, TEXT, EOF
        self.value = value
        self.line = line
        self.col = col
        self.indent = indent   # NL: その行のインデント幅
        self.first = first     # その行の最初のトークンか
        self.extra = extra     # QUOTE: 」の後の接尾テキスト

    def __repr__(self):
        return f'Tok({self.type},{self.value!r},L{self.line}:{self.col})'


class Diag:
    def __init__(self, level, line, col, msg, file=None):
        self.level, self.line, self.col, self.msg, self.file = level, line, col, msg, file

    def __str__(self):
        where = f'{self.file}:' if self.file else ''
        return f'{self.level}: {where}L{self.line}:{self.col}: {self.msg}'

    def to_json(self):
        d = {'level': self.level, 'line': self.line, 'col': self.col, 'msg': self.msg}
        if self.file:
            d['file'] = self.file
        return d


def indent_width(s):
    w = 0
    for ch in s:
        if ch == ' ':
            w += 1
        elif ch == '\t':
            w += 4
        elif ch == '　':
            w += 2
        else:
            break
    return w


def strip_line_comment(s):
    """// 以降をコメントとして除く（行頭か空白の直後の // のみ。URL の :// は残す）"""
    m = re.search(r'(^|\s)//', s)
    return s[:m.start()] if m else s


# ---------------------------------------------------------------------------
# 字句解析
# ---------------------------------------------------------------------------
class Lexer:
    def __init__(self, text, diags):
        self.text = text
        self.diags = diags
        self.toks = []

    def err(self, line, col, msg):
        self.diags.append(Diag('error', line, col, msg))

    def run(self):
        paren_depth = 0
        for lineno, raw in enumerate(self.text.splitlines(), 1):
            raw = raw.translate(FW_TABLE)
            body = strip_line_comment(raw).rstrip()
            if not body.strip():
                continue
            ind = indent_width(body)
            stripped = body.lstrip(' \t　')
            col0 = len(body) - len(stripped)
            self.toks.append(Tok('NL', None, lineno, col0 + 1, indent=ind))
            if stripped.startswith('::'):
                content = stripped[2:].strip()
                m = PRIORITY_RE.match(content)
                if m:
                    self.toks.append(Tok('PRIORITY', (m.group(1), m.group(2)), lineno, col0 + 1, first=True))
                else:
                    self.toks.append(Tok('SECTION', content, lineno, col0 + 1, first=True))
                continue
            paren_depth = self.lex_line(stripped, lineno, col0, paren_depth)
        self.toks.append(Tok('EOF', None, len(self.text.splitlines()) + 1, 1))
        return self.toks

    def lex_line(self, s, lineno, col0, paren_depth):
        i = 0
        n = len(s)
        expect_elem = True     # 要素の先頭（#, %, ?, 「, $, (, +, ! が記号として働く位置）
        after_concl = False    # 直前が >> か（not の判定用）
        first = True

        def emit(t, v, pos, extra=None):
            nonlocal first
            self.toks.append(Tok(t, v, lineno, col0 + pos + 1, first=first, extra=extra))
            first = False

        while i < n:
            ch = s[i]
            if ch in ' \t　':
                i += 1
                continue
            two = s[i:i + 2]
            # --- as ラベル（行頭の継続行）
            if expect_elem or first:
                m = AS_LINE_START_RE.match(s, i)
                if m and (first or s[i - 1:i].isspace()):
                    emit('AS', m.group(1), i)
                    i = m.end()
                    expect_elem = False
                    continue
            # --- not（>> の直後のみ）
            if after_concl:
                after_concl = False
                m = re.match(r'not(\s+|$)', s[i:])
                if m:
                    emit('NOT', 'not', i)
                    i += m.end()
                    continue
                if ch == '!' and s[i:i + 2] != '!>':    # >> !結論 は >> not 結論 と同じ
                    emit('NOT', '!', i)
                    i += 1
                    continue
            # --- 2 文字演算子
            if two in STOP2:
                emit('OP', two, i)
                i += 2
                expect_elem = two in ('<=', '~>', '=>', '!>')
                after_concl = (two == '>>')
                continue
            # --- 括弧
            if ch == '(' and expect_elem:
                emit('LPAREN', '(', i)
                paren_depth += 1
                i += 1
                continue
            if ch == ')':
                if paren_depth > 0:
                    emit('RPAREN', ')', i)
                    paren_depth -= 1
                else:
                    self.err(lineno, col0 + i + 1, '対応する ( のない ) があります')
                i += 1
                expect_elem = False
                continue
            # --- 1 文字演算子
            if ch in STOP1:
                emit('OP', ch, i)
                i += 1
                expect_elem = ch in ('&', '|', ':')
                continue
            # --- 成否の印 + / !
            if expect_elem and ch in '+!' and i + 1 < n and s[i + 1] in '#%?「$(':
                emit('MARK', ch, i)
                i += 1
                continue
            # --- 「要件」（」の後の接尾テキスト「でない」等も拾う）
            if expect_elem and ch == '「':
                depth, j = 0, i
                while j < n:
                    if s[j] == '「':
                        depth += 1
                    elif s[j] == '」':
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                if j >= n:
                    self.err(lineno, col0 + i + 1, '「 が閉じられていません')
                    emit('QUOTE', s[i + 1:], i, extra='')
                    return paren_depth
                inner = s[i + 1:j]
                if s[j + 1:j + 2] == '「' or s[j + 1:].lstrip()[:1] == '「':
                    k, suffix = j + 1, ''      # 「A」「B」のように並んだ場合は接尾テキストとしない
                else:
                    k, suffix = self.read_text(s, j + 1, 0)
                emit('QUOTE', inner, i, extra=suffix)
                i = k
                expect_elem = s[k:].lstrip()[:1] == '「'   # 区切りなしで「」が続く場合もトークンを分ける
                continue
            # --- 記号 # % ?
            if expect_elem and ch in '#%?':
                emit('SIGIL', ch, i)
                i += 1
                expect_elem = False
                continue
            # --- $ラベル参照
            if ch == '$':
                m = re.match(LABEL_CHARS, s[i + 1:])
                if not m:
                    self.err(lineno, col0 + i + 1, '$ の後にラベル名がありません')
                    i += 1
                    continue
                emit('REF', m.group(0), i)
                i += 1 + m.end()
                expect_elem = False
                continue
            # --- テキスト
            j, text = self.read_text(s, i, 0)
            if text:
                emit('TEXT', text, i)
            # as ラベル（テキストの後）
            m = AS_RE.match(s, j)
            if m:
                emit('AS', m.group(1), j)
                j = m.end()
            if j == i:   # 進まない場合の保険
                j = i + 1
            i = j
            expect_elem = False
        return paren_depth

    def read_text(self, s, i, _):
        """演算子・as の手前までをテキストとして読む。テキスト内の ( ) は対応を取って中身ごと読む。"""
        n = len(s)
        j = i
        depth = 0
        while j < n:
            two = s[j:j + 2]
            ch = s[j]
            if depth == 0:
                if two in STOP2 or ch in STOP1:
                    break
                if ch == ')':
                    break
                if ch.isspace() and AS_RE.match(s, j):
                    break
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            j += 1
        return j, s[i:j].strip()


# ---------------------------------------------------------------------------
# 構文木
# ---------------------------------------------------------------------------
class Node:
    def __init__(self, kind, tok, line_indent, is_root):
        self.kind = kind            # document section claim req issue plain ref fact group priority
        self.line = tok.line if tok else 0
        self.col = tok.col if tok else 0
        self.line_indent = line_indent
        self.is_root = is_root
        self.mark = None            # '+' / '!' / None
        self.head = None            # 主張名・要件名・問題提起・事実の文言
        self.quote = False          # 「」で書かれた要件か
        self.suffix = None          # 」の後の接尾テキスト
        self.basis = None           # ^根拠
        self.facts = None           # <= 事実
        self.body = None            # : 言い換え・下位要件
        self.reason = None          # ~> 理由
        self.norm = None            # => 規範
        self.application = None     # issue の : （あてはめ）
        self.conclusion = None      # >> 結論 {'text','negated','line'}
        self.label = None           # as ラベル
        self.excepts = []           # !> $ラベル
        self.eval = None            # @評価（fact / group）
        self.op = None              # group: AND / OR
        self.items = []             # group / section / document の子
        self.seps = []

    SLOTS = ('facts', 'body', 'reason', 'norm', 'application')

    def to_json(self):
        d = {'kind': self.kind, 'line': self.line}
        for k in ('mark', 'head', 'suffix', 'basis', 'label', 'eval', 'op'):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        if self.quote:
            d['quote'] = True
        if self.conclusion:
            d['conclusion'] = self.conclusion
        if self.excepts:
            d['excepts'] = self.excepts
        for k in self.SLOTS:
            v = getattr(self, k)
            if v is not None:
                d[k] = v.to_json()
        if self.items:
            d['items'] = [x.to_json() for x in self.items]
        return d

    def children(self):
        for k in self.SLOTS:
            v = getattr(self, k)
            if v is not None:
                yield v
        for x in self.items:
            yield x

    def walk(self):
        yield self
        for c in self.children():
            yield from c.walk()


# どの種類の要素がどの後置演算子を受け付けるか
ACCEPT = {
    'claim': {'<=', ':', '>>', 'AS', '!>'},
    'req':   {':', '<=', '>>', 'AS', '!>'},
    'plain': {':', '<=', '>>', 'AS', '!>'},
    'ref':   {':', '<=', '>>', 'AS', '!>'},
    'issue': {'<=', '~>', '=>', ':', '>>', 'AS', '!>'},
    'fact':  {'@', 'AS'},
    'group': {'@'},
}
CONT_OPS = {'<=', ':', '~>', '=>', '>>', '@', '!>'}


class Parser:
    def __init__(self, toks, diags):
        self.toks = toks
        self.p = 0
        self.diags = diags
        self.cur_indent = 0

    # --- 補助
    def peek(self, k=0):
        q = self.p + k
        return self.toks[q] if q < len(self.toks) else self.toks[-1]

    def adv(self):
        t = self.toks[self.p]
        self.p += 1
        if t.type == 'NL':
            self.cur_indent = t.indent
        return t

    def is_op(self, t, *vals):
        return t.type == 'OP' and t.value in vals

    def optype(self, t):
        """後置演算子としての種類（OP の値、AS）"""
        if t.type == 'OP':
            return t.value
        if t.type == 'AS':
            return 'AS'
        return None

    def err(self, t, msg):
        self.diags.append(Diag('error', t.line, t.col, msg))

    def warn(self, t, msg):
        self.diags.append(Diag('warning', t.line, t.col, msg))

    # --- 文書全体
    def parse_document(self):
        doc = Node('document', None, 0, True)
        while self.peek().type != 'EOF':
            t = self.peek()
            if t.type == 'NL':
                lst = self.parse_list('elem', 'block', t.indent)
                doc.items.extend(lst.items if lst.kind == 'group' and lst.op == 'AND' and not lst.eval else [lst])
                if self.peek().type == 'NL' and self.peek().indent < t.indent:
                    continue
                if self.peek().type not in ('NL', 'EOF'):
                    bad = self.adv()
                    self.err(bad, f'ここに {bad.value!r} は置けません')
            else:
                bad = self.adv()
                self.err(bad, f'ここに {bad.value!r} は置けません')
        return doc

    # --- 要素の並び
    def parse_list(self, ctx, mode, block_indent=None):
        """mode='block': インデントで区切られた並び / mode='paren': ( ... ) の中"""
        start = self.peek()
        grp = Node('group', start, self.cur_indent, False)
        pending = None
        last_end_line = None
        while True:
            t = self.peek()
            if t.type == 'EOF':
                break
            if t.type == 'RPAREN':
                break
            if t.type == 'NL':
                if mode == 'block' and t.indent < block_indent:
                    break
                self.adv()
                last_end_line = None if last_end_line is None else -1   # 改行を見た印
                continue
            if self.is_op(t, '&', '|'):
                nxt = self.peek(1)
                if mode == 'block' and nxt.type == 'NL' and nxt.indent < block_indent:
                    break   # 行末の & が外側の並びに属する場合（カント例）
                if pending is not None:
                    self.err(t, f'区切り {pending} の後に続けて {t.value} があります')
                pending = t.value
                self.adv()
                continue
            if t.type == 'SECTION':
                item = self.parse_section()
            elif t.type == 'PRIORITY':
                self.adv()
                item = Node('priority', t, self.cur_indent, True)
                item.head = list(t.value)
            elif self.optype(t) in CONT_OPS or t.type in ('AS', 'NOT'):
                self.err(t, f'{t.value} を受け取れる要素が直前にありません')
                self.adv()
                continue
            else:
                item = self.parse_item(ctx)
                if item is None:
                    self.err(t, f'要素を期待しましたが {t.value!r} がありました')
                    self.adv()
                    continue
            if grp.items:
                if pending is None:
                    if last_end_line is not None and last_end_line != -1:
                        self.err(t, '要素の間に & / | / 改行 のいずれかが必要です')
                    grp.seps.append('NL')
                else:
                    grp.seps.append(pending)
            elif pending is not None:
                self.warn(t, f'並びの先頭に {pending} があります')
            pending = None
            grp.items.append(item)
            last_end_line = self.toks[self.p - 1].line if self.p > 0 else None
        if pending is not None and mode == 'paren':
            self.warn(start, f'並びの末尾に {pending} があります')
        ops = set(grp.seps)
        if '&' in ops and '|' in ops:
            self.err(start, '同じ並びに & と | が混在しています（括弧でまとめてください）')
        if '|' in ops and 'NL' in ops:
            self.warn(start, '| と改行（AND の省略）が混在しています')
        grp.op = 'OR' if '|' in ops else 'AND'
        return grp

    def parse_section(self):
        t = self.adv()
        sec = Node('section', t, self.cur_indent, True)
        sec.head = t.value
        base = self.cur_indent
        nxt = self.peek()
        if nxt.type == 'NL' and nxt.indent > base:
            lst = self.parse_list('elem', 'block', nxt.indent)
            sec.items = lst.items
            sec.seps = lst.seps
        return sec

    # --- 要素
    def parse_item(self, ctx):
        t = self.peek()
        is_root = t.first
        line_indent = self.cur_indent
        mark = None
        if t.type == 'MARK':
            mark = t.value
            self.adv()
            t = self.peek()
        node = None
        if t.type == 'SIGIL' and t.value == '#':
            self.adv()
            node = Node('claim', t, line_indent, is_root)
            node.head = self.take_text()
            self.take_basis(node)
        elif t.type == 'SIGIL' and t.value == '%':
            self.adv()
            node = Node('req', t, line_indent, is_root)
            node.head = self.take_text()
            if not node.head:
                self.err(t, '% の後に要件・定義の文言がありません')
            self.take_basis(node)
        elif t.type == 'QUOTE':
            self.adv()
            node = Node('req', t, line_indent, is_root)
            node.quote = True
            node.head = t.value
            node.suffix = t.extra or None
            self.take_basis(node)
        elif t.type == 'SIGIL' and t.value == '?':
            self.adv()
            node = Node('issue', t, line_indent, is_root)
            node.head = self.take_text()
        elif t.type == 'REF':
            self.adv()
            node = Node('ref', t, line_indent, is_root)
            node.head = t.value
        elif t.type == 'LPAREN':
            self.adv()
            node = self.parse_list(ctx, 'paren')
            node.line, node.col, node.line_indent, node.is_root = t.line, t.col, line_indent, is_root
            if not node.items:
                self.warn(t, '中身のない ( ) です')
            if self.peek().type == 'RPAREN':
                self.adv()
            else:
                self.err(t, '( が閉じられていません')
        elif t.type == 'TEXT':
            self.adv()
            node = Node('fact' if ctx == 'fact' else 'plain', t, line_indent, is_root)
            node.head = t.value
        else:
            if mark:
                self.err(t, f'{mark} の後に要素がありません')
            return None
        node.mark = mark
        if mark and node.kind in ('fact', 'group'):
            self.warn(t, f'事実・括弧に成否の印 {mark} が付いています')
        self.parse_postfix(node)
        return node

    def take_text(self):
        if self.peek().type == 'TEXT':
            return self.adv().value
        return ''

    # 条文の引用の終わり（「563条3項」「415条1項但書」など）の後にひらがなで続く文言は、根拠ではなく要件の一部
    BASIS_SPLIT = re.compile(r'^(.*?(?:条|項|号|本文|但書|ただし書|前段|後段|柱書))([ぁ-ゖ].*)$')

    def take_basis(self, node):
        if self.is_op(self.peek(), '^'):
            t = self.adv()
            if self.peek().type == 'TEXT':
                node.basis = self.adv().value
                m = self.BASIS_SPLIT.match(node.basis)
                if m and node.kind == 'req':
                    node.basis = m.group(1)
                    node.suffix = (node.suffix or '') + m.group(2)
            else:
                self.err(t, '^ の後に根拠がありません')

    def accepts(self, node, op, nxt=None):
        if op not in ACCEPT.get(node.kind, set()):
            return False
        if op == '<=':
            if node.facts is not None:
                return False
            if node.kind == 'issue' and (node.reason or node.norm or node.application):
                return False
            return True
        if op == ':':
            if node.kind == 'issue':
                return node.application is None
            if node.body is not None:
                return False
            if node.kind in ('req', 'plain', 'ref') and node.facts is not None:
                return False   # 「要件」: %定義 <= 事実 の順。<= の後の : は外側へ
            return True
        if op == '~>':
            return node.reason is None and node.norm is None
        if op == '=>':
            return node.norm is None
        if op == '>>':
            return node.conclusion is None
        if op == '@':
            return node.eval is None
        if op == 'AS':
            return node.label is None
        if op == '!>':
            return True
        return False

    def parse_postfix(self, node):
        while True:
            t = self.peek()
            if t.type == 'NL':
                nt = self.peek(1)
                op = self.optype(nt)
                if op in CONT_OPS or op == 'AS':
                    if self.accepts_cont(node, op, t.indent):
                        self.adv()          # 継続行として NL を読み捨てる
                        node._cont = True
                        continue
                break
            op = self.optype(t)
            if op is None:
                break
            # 行内の >> と ": >>" は行の根の要素（またはその継続行）だけが受け取る
            if op == '>>' and not (node.is_root or getattr(node, '_cont', False)):
                break
            if op == ':' and self.is_op(self.peek(1), '>>'):
                if not (node.is_root or getattr(node, '_cont', False)) or node.conclusion is not None:
                    break
                self.adv()
                continue          # 次の周回で >> を処理
            if not self.accepts(node, op):
                break
            self.adv()
            if op == '<=':
                node.facts = self.parse_operand('fact', t)
            elif op == ':':
                v = self.parse_operand('elem', t)
                if node.kind == 'issue':
                    node.application = v
                else:
                    node.body = v
            elif op == '~>':
                node.reason = self.parse_operand('fact', t)
            elif op == '=>':
                node.norm = self.parse_operand('elem', t)
            elif op == '@':
                if self.peek().type == 'TEXT':
                    node.eval = self.adv().value
                else:
                    self.err(t, '@ の後に評価がありません')
            elif op == '>>':
                neg = False
                if self.peek().type == 'NOT':
                    self.adv()
                    neg = True
                if self.peek().type == 'TEXT':
                    txt = self.adv().value
                else:
                    txt = ''
                    self.err(t, '>> の後に結論がありません')
                node.conclusion = {'text': txt, 'negated': neg, 'line': t.line}
            elif op == 'AS':
                node.label = t.value
            elif op == '!>':
                if self.peek().type == 'REF':
                    node.excepts.append(self.adv().value)
                    while self.is_op(self.peek(), '&') and self.peek(1).type == 'REF':
                        self.adv()
                        node.excepts.append(self.adv().value)
                else:
                    self.err(t, '!> の後には $ラベル が必要です')

    def accepts_cont(self, node, op, indent):
        if not self.accepts(node, op):
            return False
        if op == '>>':
            # 根の要素で、継続行のインデントが自分の行以上
            return node.is_root and indent >= node.line_indent
        return indent >= node.line_indent

    def parse_operand(self, ctx, optok):
        t = self.peek()
        if t.type == 'NL':
            if t.indent > self.cur_indent:
                self.adv()
                lst = self.parse_list(ctx, 'block', t.indent)
                return self.unwrap(lst)
            nt = self.peek(1)
            if nt.type in ('EOF', 'RPAREN') or self.optype(nt) in CONT_OPS:
                self.err(optok, f'{optok.value} の後に何もありません')
                return None
            # 同じインデントの次行を 1 要素として受け取る（カント例の「? 天才とは =>」など）
            self.warn(optok, f'{optok.value} の後の内容が次の行に同じ深さで書かれています（字下げを推奨）')
            self.adv()
            return self.parse_item(ctx)
        if t.type in ('EOF', 'RPAREN') or (self.optype(t) in CONT_OPS and t.type == 'OP' and t.value != '('):
            self.err(optok, f'{optok.value} の後に何もありません')
            return None
        if ctx == 'fact':
            return self.parse_fact_expr()
        item = self.parse_item(ctx)
        if item is None:
            self.err(t, f'{optok.value} の後に要素を期待しましたが {t.value!r} がありました')
        return item

    def parse_fact_expr(self):
        first = self.parse_item('fact')
        if first is None:
            return None
        items, seps = [first], []
        while True:
            t = self.peek()
            if not self.is_op(t, '&', '|'):
                break
            nt = self.peek(1)
            # 行末の & や、後ろが要件（「 % + ! ?）の & は外側の並びの区切り
            if nt.type in ('NL', 'RPAREN', 'EOF', 'QUOTE', 'MARK') or (nt.type == 'SIGIL' and nt.value in '%?'):
                break
            self.adv()
            it = self.parse_item('fact')
            if it is None:
                self.err(t, f'{t.value} の後に事実がありません')
                break
            seps.append(t.value)
            items.append(it)
        if len(items) == 1:
            return first
        g = Node('group', first and self.toks[self.p - 1], first.line_indent, False)
        g.line, g.col = first.line, first.col
        g.items, g.seps = items, seps
        if '&' in seps and '|' in seps:
            self.err(t, '同じ並びに & と | が混在しています')
        g.op = 'OR' if '|' in seps else 'AND'
        return g

    @staticmethod
    def unwrap(lst):
        return lst.items[0] if len(lst.items) == 1 else lst


# ---------------------------------------------------------------------------
# 意味的な検査（ラベル、成否の印の整合性など）
# ---------------------------------------------------------------------------
def effective_mark(node):
    if node is None:
        return None
    if node.mark:
        return node.mark
    if node.kind == 'issue' and node.norm is not None:
        return effective_mark(node.norm)
    return None


def check_semantics(doc, diags):
    def Dn(level, n, msg):
        return Diag(level, n.line, n.col, msg, getattr(n, 'file', None))

    labels = {}
    for n in doc.walk():
        if n.label:
            if n.label in labels:
                diags.append(Dn('error', n, f'ラベル {n.label} が重複しています（L{labels[n.label].line}）'))
            else:
                labels[n.label] = n
    for n in doc.walk():
        if n.kind == 'ref' and n.head not in labels:
            diags.append(Dn('error', n, f'$${n.head} は定義されていません'.replace('$$', '$')))
        for e in n.excepts:
            if e not in labels:
                diags.append(Dn('error', n, f'!> の対象 ${e} は定義されていません'))
            elif labels[e] is n:
                diags.append(Dn('error', n, f'自分自身 ${e} を例外の対象にしています'))
        if n.kind == 'priority':
            for e in n.head:
                if e not in labels:
                    diags.append(Dn('error', n, f'優先の対象 ${e} は定義されていません'))
        if n.kind == 'issue' and n.norm is None and n.conclusion is None and n.application is None and n.reason is None:
            diags.append(Dn('warning', n, '論点（?）に規範（=>）も結論（>>）もありません'))
        if n.kind == 'fact' and n.label and re.fullmatch(r'[a-z]+', n.label):
            # 英文の行末の「… as drivers」は、ラベル付けとして読まれ、事実の文が切れる
            diags.append(Dn('warning', n, f'事実「{n.head}」の後の「as {n.label}」がラベル付けとして読まれました。'
                                          '英文の中の as なら、文を言い換えて行末に「as 単語」が来ないようにしてください'))
        if n.kind in ('fact', 'plain', 'claim', 'req', 'issue') and n.head:
            if re.search(r'\b(AND|OR|NOT)\b', n.head):
                diags.append(Dn('warning', n, 'AND/OR/NOT が文言中にあります。Matcha の論理演算子は & と | です'))
        # 成否の印の伝播
        m = effective_mark(n)
        if m and n.kind in ('claim', 'req', 'plain', 'ref'):
            sub = n.body if n.body is not None else None
            if sub is not None:
                kids = sub.items if sub.kind == 'group' else [sub]
                op = sub.op if sub.kind == 'group' else 'AND'
                km = [effective_mark(k) for k in kids if k.kind not in ('fact',)]
                km = [x for x in km if x]
                if not km:
                    continue
                if op == 'AND':
                    if m == '+' and '!' in km:
                        diags.append(Dn('warning', n, '成立（+）とされていますが、AND の下位要件に不成立（!）があります'))
                    if m == '!' and '!' not in km and len(km) == len(kids):
                        diags.append(Dn('warning', n, '不成立（!）とされていますが、AND の下位要件はすべて成立（+）です'))
                else:
                    if m == '+' and all(x == '!' for x in km) and len(km) == len(kids):
                        diags.append(Dn('warning', n, '成立（+）とされていますが、OR の選択肢がすべて不成立（!）です'))
                    if m == '!' and '+' in km:
                        diags.append(Dn('warning', n, '不成立（!）とされていますが、OR の選択肢に成立（+）があります'))
    excepts = [(n.label, e) for n in doc.walk() for e in n.excepts if n.label]
    # 相互例外の検出（PROLEG の相互例外のように複数の Extension を生む）
    pairs = set(excepts)
    for a, b in pairs:
        if (b, a) in pairs and a < b:
            n = labels[a]
            diags.append(Dn('info', n, f'${a} と ${b} は互いに例外です（複数の Extension がありえます）'))
    return labels


# ---------------------------------------------------------------------------
# 表示
# ---------------------------------------------------------------------------
def fmt_head(n):
    m = n.mark or ''
    if n.kind == 'claim':
        s = f'{m}#{n.head}'
    elif n.kind == 'req':
        s = f'{m}「{n.head}」{n.suffix or ""}' if n.quote else f'{m}%{n.head}'
    elif n.kind == 'issue':
        s = f'{m}? {n.head}'
    elif n.kind == 'ref':
        s = f'{m}${n.head}'
    elif n.kind == 'fact':
        s = f'[事実] {n.head}'
    elif n.kind == 'plain':
        s = f'{m}{n.head}'
    elif n.kind == 'section':
        s = f':: {n.head}'
    elif n.kind == 'priority':
        s = f':: 優先 ${n.head[0]} > ${n.head[1]}'
    elif n.kind == 'group':
        s = f'{m}({n.op})'
    else:
        s = n.kind
    if n.basis:
        s += f' ^{n.basis}'
    if n.eval:
        s += f' @{n.eval}'
    if n.label:
        s += f'  as {n.label}'
    return s


def render_tree(n, depth=0, prefix='', out=None):
    if out is None:
        out = []
    pad = '  ' * depth
    if n.kind == 'document':
        for c in n.items:
            render_tree(c, 0, '', out)
        return out
    out.append(f'L{n.line:<4}{pad}{prefix}{fmt_head(n)}')
    slots = [('facts', '<= '), ('body', ': '), ('reason', '~> '), ('norm', '=> '), ('application', ': ')]
    for k, p in slots:
        v = getattr(n, k)
        if v is not None:
            render_tree(v, depth + 1, p, out)
    if n.kind in ('group', 'section'):
        for c in n.items:
            render_tree(c, depth + 1, '', out)
    if n.conclusion:
        c = n.conclusion
        out.append(f'L{c["line"]:<4}{pad}  >> {"not " if c["negated"] else ""}{c["text"]}')
    for e in n.excepts:
        out.append(f'L{n.line:<4}{pad}  !> ${e}')
    return out


def parse_text(text, file=None):
    """字句解析と構文解析だけを行う（意味の検査はしない）。file を指定すると各ノードと診断に記録する"""
    diags = []
    toks = Lexer(text, diags).run()
    doc = Parser(toks, diags).parse_document()
    for d in diags:
        d.file = file
    if file:
        for n in doc.walk():
            n.file = file
    return doc, diags


def check_text(text):
    doc, diags = parse_text(text)
    labels = check_semantics(doc, diags)
    diags.sort(key=lambda d: (d.line, d.col))
    return doc, diags, labels


def check_files(named_texts):
    """複数のファイルを、ラベルの名前空間を共有して検査する。named_texts: [(ファイル名, テキスト), ...]
    戻り値: (各ファイルの構文木のリスト, 診断, ラベル)"""
    docs, diags = [], []
    for name, text in named_texts:
        doc, ds = parse_text(text, name)
        docs.append(doc)
        diags += ds
    combined = Node('document', None, 0, True)
    for d in docs:
        combined.items.extend(d.items)
    labels = check_semantics(combined, diags)
    diags.sort(key=lambda d: (d.file or '', d.line, d.col))
    return docs, diags, labels


def main(argv=None):
    ap = argparse.ArgumentParser(description='Matcha / Matcha-D 構文チェッカ')
    ap.add_argument('files', nargs='+')
    ap.add_argument('--tree', action='store_true', help='構文木を表示')
    ap.add_argument('--json', action='store_true', help='構文木を JSON で出力')
    ap.add_argument('--quiet', action='store_true', help='エラーと警告の件数だけを表示')
    ap.add_argument('--shared-labels', action='store_true',
                    help='複数のファイルを一つの理論として、ラベルの名前空間を共有して検査する')
    args = ap.parse_args(argv)
    status = 0
    results = []
    if args.shared_labels:
        named = [(f, open(f, encoding='utf-8').read()) for f in args.files]
        docs, diags, labels = check_files(named)
        nerr = sum(d.level == 'error' for d in diags)
        nwarn = sum(d.level == 'warning' for d in diags)
        if args.json:
            print(json.dumps({'files': args.files, 'ok': nerr == 0, 'diagnostics': [d.to_json() for d in diags],
                              'labels': sorted(labels), 'ast': [d.to_json() for d in docs]}, ensure_ascii=False, indent=1))
            return 1 if nerr else 0
        print(f'== {len(args.files)} ファイル（ラベル共有）: エラー {nerr} 件, 警告 {nwarn} 件')
        if not args.quiet:
            for d in diags:
                print('  ' + str(d))
        if args.tree:
            for f, doc in zip(args.files, docs):
                print(f'  -- {f}')
                print('\n'.join('  ' + x for x in render_tree(doc)))
        return 1 if nerr else 0
    for path in args.files:
        with open(path, encoding='utf-8') as f:
            text = f.read()
        doc, diags, labels = check_text(text)
        nerr = sum(d.level == 'error' for d in diags)
        nwarn = sum(d.level == 'warning' for d in diags)
        if nerr:
            status = 1
        if args.json:
            results.append({'file': path, 'ok': nerr == 0, 'diagnostics': [d.to_json() for d in diags],
                            'labels': sorted(labels), 'ast': doc.to_json()})
            continue
        print(f'== {path}: エラー {nerr} 件, 警告 {nwarn} 件')
        if not args.quiet:
            for d in diags:
                print('  ' + str(d))
        if args.tree:
            print('\n'.join('  ' + x for x in render_tree(doc)))
    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], ensure_ascii=False, indent=1))
    return status


if __name__ == '__main__':
    sys.exit(main())
