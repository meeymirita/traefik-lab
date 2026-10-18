# -*- coding: utf-8 -*-
"""Оставляет в каждом шаге один раздел `### result` (остальные заголовки убирает, содержимое сливается). Запуск: python3 traefik/src/_merge_results.py NN-session.md"""
import re, sys
for f in sys.argv[1:]:
    s = open(f, encoding='utf-8').read()
    out = []
    for st in re.split(r'(?m)^(?=## \d)', s):
        parts = re.split(r'(?m)^### result\n', st)
        if len(parts) > 2:
            st = parts[0] + '### result\n' + ''.join(parts[1:])
        out.append(st)
    open(f, 'w', encoding='utf-8').write(''.join(out))
