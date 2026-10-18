# -*- coding: utf-8 -*-
"""Inline-код с вложенными обратными кавычками (Host(`x`)) переписывает в двойные кавычки ``Host(`x`)``. Блоки кода не трогает."""
import re, sys
call = r'!?\w+\((?:`[^`\n]*`(?:, )?)+\)'
pat = re.compile(r'(?<![`\w])`(' + call + r'(?: (?:&&|\|\|) ' + call + r')*)`(?!`)')
for f in sys.argv[1:]:
    out, fence, n = [], False, 0
    for ln in open(f, encoding='utf-8').read().split('\n'):
        if ln.startswith('```'):
            fence = not fence
        if not fence and not ln.startswith('```'):
            ln, k = pat.subn(lambda m: '``' + m.group(1) + '``', ln)
            n += k
        out.append(ln)
    open(f, 'w', encoding='utf-8').write('\n'.join(out))
    print(f, n)
