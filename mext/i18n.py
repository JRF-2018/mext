# -*- coding: utf-8 -*-
"""出力の言語（日本語・英語）。既定は日本語。環境変数 MEXT_LANG=en か、コマンドの --lang en で英語にする。

文言は、出す箇所ごとに日本語と英語を並べて書く: t('主張 {n} は…', 'Claim {n} …', n=name)
（後から語句を置き換える方式だと、日英の語順の違いで不自然になるため）
"""
import os

LANG = 'en' if os.environ.get('MEXT_LANG', '').lower().startswith('en') else 'ja'


def set_lang(lang):
    global LANG
    LANG = 'en' if (lang or '').lower().startswith('en') else 'ja'


def en():
    return LANG == 'en'


def t(ja, en_, **kw):
    s = en_ if LANG == 'en' else ja
    return s.format(**kw) if kw else s


def join(items):
    """列挙の区切り（日本語は「、」、英語は ", "）"""
    return (', ' if LANG == 'en' else '、').join(items)


def q(text):
    """文言の引用（日本語は「」、英語は “”）"""
    return f'“{text}”' if LANG == 'en' else f'「{text}」'
