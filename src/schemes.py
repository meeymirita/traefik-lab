# -*- coding: utf-8 -*-
"""Схемы Traefik Lab: python3 traefik/src/schemes.py [имя] -> traefik/src/schemes/<имя>.html (вставляются в методичку блоком ```svg @имя)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../fixes/common/_tools'))
from svgkit import Svg  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schemes')
S = {}


def scheme(f):
    S[f.__name__.replace('_', '-')] = f
    return f


@scheme
def address_flow():
    s = Svg(660, 190, 'Пять стадий: DNS, TCP, TLS, HTTP-запрос, HTTP-ответ, и типичная ошибка на каждой', pid='af')
    names = [('1  DNS', 'имя → IP'), ('2  TCP', 'соединение'), ('3  TLS', 'сертификат'), ('4  Запрос', 'GET /menu, Host'), ('5  Ответ', '200 + страница')]
    errs = ['Could not resolve — host', 'Connection — refused', 'certificate — verify failed', '404 — нет такого пути', '502 — сервис упал']
    w, g = 108, 28
    for i, (a, b) in enumerate(names):
        x = 4 + i * (w + g)
        s.box(x, 30, w, 62, [a, b], fill=.08 + i * .03, bold=True, size=12)
        if i < 4:
            s.arrow(x + w, 61, x + w + g, 61)
        s.line(x + w / 2, 92, x + w / 2, 122, dash=True, op=.6)
        s.box(x, 122, w, 46, errs[i].split(' — ') if ' — ' not in errs[i] else [errs[i].split(' — ')[0], errs[i].split(' — ')[1]], fill=.03, dash=True, size=10, op=.9)
    s.text(330, 16, 'Что происходит, когда открываешь адрес', size=13, weight='700')
    s.text(330, 184, 'снизу — как выглядит поломка на каждой стадии', size=11, op=.8)
    return s.html()


@scheme
def one_door():
    s = Svg(700, 300, 'Без прокси клиент ходит к каждому сервису по своему порту; с прокси — к одному входу, который разводит запросы', pid='od')
    # левая половина: без прокси
    s.text(160, 18, 'Без прокси', size=14, weight='700')
    s.box(10, 118, 80, 44, ['Клиент'], fill=.1, bold=True)
    for i, (n, p) in enumerate([('сайт', ':8080'), ('API', ':3000'), ('Adminer', ':8081')]):
        y = 40 + i * 78
        s.box(210, y, 130, 46, [n, p], fill=.07 + i * .02)
        s.arrow(90, 140, 208, y + 23)
    s.text(150, 290, 'три адреса, три порта, открыто наружу', size=11, op=.8)
    # правая половина: с прокси
    s.text(540, 18, 'С прокси', size=14, weight='700')
    s.box(375, 118, 80, 44, ['Клиент'], fill=.1, bold=True)
    s.box(480, 98, 86, 84, ['Traefik', ':80 / :443'], fill=.2, bold=True)
    s.arrow(455, 140, 478, 140)
    for i, (n, h) in enumerate([('сайт', 'shop.localhost'), ('API', '/api'), ('Adminer', 'adminer.…')]):
        y = 40 + i * 78
        s.box(590, y, 100, 46, [n, h], fill=.07 + i * .02, size=11)
        s.arrow(566, 140, 588, y + 23)
    s.text(540, 290, 'один вход; сервисы наружу не публикуются', size=11, op=.8)
    return s.html()


@scheme
def shop_ports():
    s = Svg(660, 250, 'Стенд CoffeeShop до прокси: сайт, API и Adminer на трёх портах, база только внутри сети', pid='sp')
    s.box(10, 90, 90, 46, ['Браузер'], fill=.1, bold=True)
    items = [('web  (nginx)', 'localhost:8080', 25), ('api  (Node.js)', 'localhost:3000', 95), ('adminer', 'localhost:8081', 165)]
    for n, p, y in items:
        s.box(210, y, 170, 56, [n, p], fill=.08)
        s.arrow(100, 113, 208, y + 28)
    s.box(480, 95, 150, 56, ['db  (PostgreSQL)', 'только внутри сети'], fill=.16, dash=True)
    s.arrow(380, 123, 478, 123, 'запросы к базе', ly=112)
    s.text(330, 238, 'сайт просит меню у «/api/menu» на том же адресе — а там 404: у nginx нет такого пути', size=11, op=.85)
    return s.html()


@scheme
def static_dynamic():
    s = Svg(700, 280, 'Статическая конфигурация читается один раз при старте, динамическая приходит из провайдеров на лету', pid='sd')
    s.box(10, 28, 190, 70, ['traefik.yml', '«устав»', 'entryPoints, providers,', 'api, log'], fill=.08, size=11)
    s.box(10, 170, 190, 70, ['Docker: контейнеры', 'с метками «приказы»', 'traefik.http.routers…'], fill=.08, size=11)
    s.box(290, 40, 400, 200, [], fill=.04, dash=True)
    s.text(490, 62, 'Traefik', size=14, weight='700')
    s.box(305, 80, 120, 44, ['entryPoints', ':80  :443'], fill=.14, size=11)
    s.box(445, 80, 120, 44, ['routers', 'rule → service'], fill=.14, size=11)
    s.box(575, 80, 105, 44, ['middlewares', 'по пути'], fill=.14, size=11)
    s.box(305, 150, 120, 44, ['providers', 'откуда приказы'], fill=.2, size=11)
    s.box(445, 150, 235, 44, ['services', 'куда пересылать'], fill=.14, size=11)
    s.text(490, 226, 'меняются без перезапуска: routers, middlewares, services', size=11, op=.85)
    s.arrow(200, 63, 303, 100)
    s.arrow(200, 205, 303, 176)
    s.text(105, 118, 'читается один раз, при старте', size=11, op=.85)
    s.text(105, 132, 'после правки — перезапуск', size=11, op=.85)
    s.text(105, 258, 'приходит на лету, без перезапуска', size=11, op=.85)
    return s.html()


@scheme
def router_model():
    s = Svg(700, 190, 'Путь запроса внутри Traefik: entryPoint, router, middlewares, service, контейнеры', pid='rm')
    s.box(4, 60, 80, 56, ['Запрос', 'Host + путь'], fill=.1, bold=True, size=11)
    xs = [112, 232, 352, 472]
    labels = [('entryPoint', 'вход :80 «web»'), ('router', 'rule: Host()'), ('middlewares', 'цепочка, не всегда'), ('service', 'куда пересылать')]
    fills = [.14, .2, .1, .14]
    for i, (a, b) in enumerate(labels):
        s.box(xs[i], 60, 108, 56, [a, b], fill=fills[i], bold=True, size=11, dash=(i == 2))
    s.box(596, 60, 100, 56, ['Контейнер', 'whoami :80'], fill=.08, size=11)
    s.arrow(84, 88, 110, 88)
    for i in range(3):
        s.arrow(xs[i] + 108, 88, xs[i + 1] - 2, 88)
    s.arrow(580, 88, 594, 88)
    s.text(166, 140, 'какая дверь', size=10, op=.8)
    s.text(286, 140, 'совпало ли правило', size=10, op=.8)
    s.text(406, 140, 'что сделать по пути', size=10, op=.8)
    s.text(526, 140, 'к какому адресу', size=10, op=.8)
    s.text(350, 18, 'Если ни один роутер не подошёл — 404 page not found', size=12, op=.9)
    s.text(350, 172, 'Метки Docker описывают router, middlewares и (если нужно) service', size=11, op=.8)
    return s.html()


@scheme
def docker_events():
    s = Svg(700, 210, 'Traefik подписан на события Docker и пересобирает маршруты при запуске и остановке контейнеров', pid='de')
    s.box(10, 70, 150, 70, ['Контейнер', 'с метками', 'traefik.enable=true'], fill=.08, size=11)
    s.box(230, 70, 130, 70, ['Docker', 'демон + docker.sock'], fill=.14, bold=True, size=11)
    s.box(430, 70, 120, 70, ['Провайдер', 'Docker', '(внутри Traefik)'], fill=.2, size=11)
    s.box(590, 70, 100, 70, ['Роутеры,', 'сервисы,', 'middlewares'], fill=.14, size=11)
    s.arrow(160, 105, 228, 105, 'start / stop', ly=96)
    s.arrow(360, 105, 428, 105, 'events', ly=96)
    s.arrow(550, 105, 588, 105)
    s.text(350, 28, 'Запустил контейнер → событие → маршрут появился', size=13, weight='700')
    s.text(350, 170, 'Остановил → событие → маршрут исчез. Перезапуск Traefik не нужен.', size=12, op=.9)
    s.text(350, 192, 'Видят только контейнеры с traefik.enable=true (при exposedByDefault: false)', size=11, op=.8)
    return s.html()


@scheme
def shop_routes():
    s = Svg(700, 270, 'CoffeeShop за Traefik: сайт, API по пути /api со срезанием префикса и Adminer по поддомену; база закрыта', pid='sr')
    s.box(10, 100, 90, 50, ['Браузер'], fill=.1, bold=True)
    s.box(150, 90, 130, 70, ['Traefik', ':80', 'единственный вход'], fill=.22, bold=True, size=11)
    s.arrow(100, 125, 148, 125)
    s.box(360, 20, 170, 50, ['web (nginx) :80', 'shop.localhost'], fill=.08, size=11)
    s.box(360, 100, 170, 50, ['api (Node.js) :3000', 'shop.localhost/api'], fill=.08, size=11)
    s.box(360, 180, 170, 50, ['adminer :8080', 'adminer.shop.localhost'], fill=.08, size=11)
    s.arrow(280, 112, 358, 45)
    s.arrow(280, 125, 358, 125, 'срезать /api', ly=116)
    s.arrow(280, 138, 358, 205)
    s.box(590, 100, 100, 50, ['db', 'postgres'], fill=.16, dash=True, size=11)
    s.arrow(530, 125, 588, 125, '', both=True)
    s.arrow(530, 205, 640, 152, '', both=True)
    s.text(420, 255, 'Сеть proxy: Traefik + web, api, adminer.  Сеть back: api, adminer, db.', size=11, op=.85)
    return s.html()


@scheme
def middleware_chain():
    s = Svg(700, 230, 'Две цепочки из одних и тех же middleware в разном порядке дают разный путь у бэкенда', pid='mc')
    def row(y, title, a, b, c, d, e):
        s.text(10, y - 8, title, size=12, anchor='start', weight='700')
        s.box(10, y, 100, 44, ['Запрос', a], fill=.1, size=11)
        s.box(190, y, 130, 44, ['stripprefix', b], fill=.18, size=11, bold=True)
        s.box(400, y, 130, 44, ['addprefix /v2', c], fill=.18, size=11, bold=True)
        s.box(590, y, 100, 44, ['whoami', d], fill=.08, size=11)
        s.arrow(110, y + 22, 188, y + 22)
        s.arrow(320, y + 22, 398, y + 22)
        s.arrow(530, y + 22, 588, y + 22)
        s.text(255, y + 62, e, size=10, op=.85)
    row(34, 'Порядок 1: strip, потом add', '/one/menu', 'срезал /one → /menu', 'добавил → /v2/menu', '/v2/menu', '')
    row(140, 'Порядок 2: add, потом strip', '/two/menu', 'add: → /v2/two/menu', 'strip /two: не найден', '/v2/two/menu', '')
    return s.html()


@scheme
def protect():
    s = Svg(700, 250, 'Общие middleware из файла: заголовки и сжатие для сайта, пароль для дашборда и Adminer', pid='pr')
    s.box(10, 100, 90, 50, ['Браузер'], fill=.1, bold=True)
    s.box(140, 85, 120, 80, ['Traefik', 'dynamic/', 'middlewares.yml'], fill=.2, bold=True, size=11)
    s.arrow(100, 125, 138, 125)
    rows = [(25, 'сайт shop.localhost', 'web-chain: заголовки + сжатие', .08), (95, 'API /api', 'stripprefix', .08), (165, 'Adminer / дашборд', 'admin-auth: пароль 🔒', .2)]
    for y, a, b, f in rows:
        s.box(340, y, 190, 56, [a, b], fill=f, size=11)
        s.arrow(260, 125, 338, y + 28)
    s.box(580, 95, 110, 56, ['база', 'не публикуется'], fill=.12, dash=True, size=11)
    s.arrow(530, 123, 578, 123, both=True)
    s.text(350, 240, 'Один пользователь в файле — одна проверка пароля на две двери', size=11, op=.85)
    return s.html()


@scheme
def rate_limit():
    s = Svg(700, 230, 'Ведро жетонов: average за period капает жетоны, burst — вместимость ведра; запрос без жетона получает 429', pid='rl')
    s.text(350, 18, 'Жетоны капают: average штук за period', size=12, weight='700')
    s.arrow(350, 26, 350, 66)
    s.box(250, 70, 200, 70, ['Ведро жетонов', 'вместимость = burst'], fill=.15, bold=True, size=12)
    s.box(10, 85, 110, 44, ['Запросы'], fill=.1, bold=True)
    s.arrow(120, 107, 248, 107, 'берут по жетону', ly=96)
    s.arrow(450, 90, 580, 60, '')
    s.arrow(450, 125, 580, 160, '')
    s.box(582, 38, 108, 44, ['200', 'жетон был'], fill=.08, size=11)
    s.box(582, 140, 108, 44, ['429', 'жетонов нет'], fill=.22, size=11, bold=True)
    s.text(350, 210, 'average=1, period=1m, burst=3: три запроса сразу, дальше — по одному в минуту', size=11, op=.85)
    return s.html()


@scheme
def circuit_breaker():
    s = Svg(700, 230, 'Три состояния предохранителя: замкнут, разомкнут, пробный; переходы по доле ошибок и по таймерам', pid='cb')
    s.box(10, 80, 140, 60, ['Замкнута', 'запросы идут', 'к сервису'], fill=.08, bold=True, size=11)
    s.box(280, 80, 140, 60, ['Разомкнута', 'Traefik сам', 'отвечает 503'], fill=.22, bold=True, size=11)
    s.box(550, 80, 140, 60, ['Пробная', 'пропускает', 'часть запросов'], fill=.12, bold=True, size=11)
    s.arrow(150, 110, 278, 110)
    s.text(214, 96, 'ошибок > порога', size=10, op=.9)
    s.arrow(420, 110, 548, 110)
    s.text(484, 96, 'прошло fallbackDuration', size=10, op=.9)
    s.path('M620,142 C620,200 80,200 80,142', arrow=True)
    s.text(350, 206, 'пробные запросы успешны → снова замкнута', size=11, op=.9)
    s.path('M620,78 C620,30 350,30 350,78', arrow=True, dash=True)
    s.text(485, 24, 'неудачны → снова разомкнута', size=11, op=.9)
    return s.html()


@scheme
def forward_auth():
    s = Svg(700, 260, 'forwardAuth: Traefik спрашивает сервис авторизации и только при 2xx пускает запрос к приложению', pid='fa')
    s.box(10, 100, 90, 50, ['Клиент'], fill=.1, bold=True)
    s.box(200, 100, 120, 50, ['Traefik'], fill=.2, bold=True)
    s.box(450, 15, 190, 56, ['Сервис авторизации', 'GET /verify'], fill=.12, size=11)
    s.box(450, 170, 190, 56, ['Приложение', 'получает X-User'], fill=.08, size=11)
    s.arrow(100, 115, 198, 115)
    s.text(150, 106, '1 запрос', size=10, op=.9)
    s.arrow(320, 108, 448, 52, both=True)
    s.text(300, 62, '2 «можно ли?»', size=10, op=.9)
    s.text(300, 76, '← 200 + X-User', size=10, op=.9)
    s.arrow(320, 142, 448, 198)
    s.text(420, 176, '3 если 2xx', size=10, op=.9)
    s.arrow(200, 140, 102, 140, dash=True)
    s.text(150, 160, '401/403 — сразу клиенту', size=10, op=.9)
    s.text(350, 250, 'Приложение не знает, как проверяется доступ: оно доверяет заголовку после проверки', size=11, op=.85)
    return s.html()


@scheme
def load_balancer():
    s = Svg(700, 230, 'Балансировщик Traefik раздаёт запросы трём репликам сервиса по кругу', pid='lb')
    s.box(10, 90, 90, 50, ['Клиенты'], fill=.1, bold=True)
    s.box(170, 80, 130, 70, ['Traefik', 'сервис coffee-api', 'round robin'], fill=.2, bold=True, size=11)
    s.arrow(100, 115, 168, 115)
    for i, y in enumerate([15, 80, 145]):
        s.box(440, y, 150, 56, ['api-%d' % (i + 1), 'реплика'], fill=.08 + i * .03, size=11, bold=True)
        s.arrow(300, 115, 438, y + 28)
    s.text(630, 43, '1, 4, 7…', size=11, op=.9, anchor='start')
    s.text(630, 108, '2, 5, 8…', size=11, op=.9, anchor='start')
    s.text(630, 173, '3, 6, 9…', size=11, op=.9, anchor='start')
    s.text(350, 222, 'Запрос №1 → api-1, №2 → api-2, №3 → api-3, №4 снова api-1', size=11, op=.85)
    return s.html()


@scheme
def canary():
    s = Svg(700, 230, 'Canary: weighted-сервис делит трафик между старой и новой версией по весам 90 и 10', pid='cn')
    s.box(10, 90, 90, 50, ['Клиенты'], fill=.1, bold=True)
    s.box(150, 70, 160, 90, ['Traefik', 'shop-canary', '(weighted)'], fill=.2, bold=True, size=11)
    s.arrow(100, 115, 148, 115)
    s.box(430, 25, 160, 56, ['v1  (старая)', 'вес 90'], fill=.08, size=11, bold=True)
    s.box(430, 150, 160, 56, ['v2  (новая)', 'вес 10'], fill=.22, size=11, bold=True)
    s.arrow(310, 100, 428, 55)
    s.arrow(310, 130, 428, 178)
    s.text(380, 60, '90%', size=11, op=.9)
    s.text(380, 175, '10%', size=11, op=.9)
    s.bar(610, 33, 70, 40, '90%', fill=.18)
    s.bar(610, 158, 70, 40, '10%', fill=.35)
    s.text(350, 222, 'Правишь файл canary.yml → доли меняются без перезапуска; откат — вес 0 у v2', size=11, op=.85)
    return s.html()


@scheme
def blue_green():
    s = Svg(700, 230, 'Blue/green: весь трафик идёт на одну версию, переключение — смена весов 100/0 на 0/100', pid='bg')
    s.text(170, 18, 'До переключения', size=13, weight='700')
    s.box(10, 70, 80, 44, ['Клиенты'], fill=.1, bold=True, size=11)
    s.box(130, 36, 90, 44, ['blue', 'вес 100'], fill=.2, bold=True, size=11)
    s.box(130, 120, 90, 44, ['green', 'вес 0'], fill=.04, dash=True, size=11)
    s.arrow(90, 85, 128, 58)
    s.arrow(90, 100, 128, 142, dash=True)
    s.text(530, 18, 'После переключения', size=13, weight='700')
    s.box(370, 70, 80, 44, ['Клиенты'], fill=.1, bold=True, size=11)
    s.box(490, 36, 90, 44, ['blue', 'вес 0'], fill=.04, dash=True, size=11)
    s.box(490, 120, 90, 44, ['green', 'вес 100'], fill=.2, bold=True, size=11)
    s.arrow(450, 85, 488, 58, dash=True)
    s.arrow(450, 100, 488, 142)
    s.arrow(250, 92, 350, 92)
    s.text(300, 82, 'одна правка', size=10, op=.9)
    s.text(350, 215, 'Откат — та же правка в обратную сторону', size=11, op=.85)
    return s.html()


@scheme
def tls_handshake():
    s = Svg(700, 300, 'TLS-рукопожатие: приветствие с именем (SNI), сертификат сервера, проверка, общий ключ, зашифрованный HTTP', pid='th')
    s.box(40, 10, 120, 40, ['Клиент'], fill=.12, bold=True)
    s.box(540, 10, 120, 40, ['Traefik :443'], fill=.2, bold=True)
    s.line(100, 50, 100, 290, dash=True, op=.5)
    s.line(600, 50, 600, 290, dash=True, op=.5)
    msgs = [(78, '→', '1  Привет: версии TLS, имя shop.localhost (SNI)'),
            (118, '←', '2  Сертификат сайта (+ открытый ключ)'),
            (158, '→', '3  Проверка: имя, срок, подпись цепочки'),
            (198, '↔', '4  Договорились об общем сеансовом ключе'),
            (248, '↔', '5  Дальше HTTP внутри шифрования 🔒')]
    for y, d, t in msgs:
        if d == '→':
            s.arrow(102, y, 598, y)
        elif d == '←':
            s.arrow(598, y, 102, y)
        else:
            s.arrow(102, y, 598, y, both=True)
        s.text(350, y - 8, t, size=12)
    return s.html()


@scheme
def cert_chain():
    s = Svg(700, 260, 'Цепочка доверия: корневой CA, промежуточный CA и сертификат сайта; у mkcert цепочка короче — локальный CA и сертификат', pid='cc')
    s.text(170, 18, 'Публичный сайт', size=13, weight='700')
    s.box(60, 30, 220, 44, ['Корневой CA', 'уже в системе и браузере'], fill=.2, bold=True, size=11)
    s.box(60, 100, 220, 44, ['Промежуточный CA', 'подписан корневым'], fill=.14, size=11)
    s.box(60, 170, 220, 44, ['Сертификат сайта', 'example.com'], fill=.08, bold=True, size=11)
    s.arrow(170, 74, 170, 98)
    s.arrow(170, 144, 170, 168)
    s.text(530, 18, 'Локально: mkcert', size=13, weight='700')
    s.box(420, 30, 220, 44, ['Локальный CA mkcert', 'rootCA.pem, добавлен командой -install'], fill=.2, bold=True, size=11)
    s.box(420, 120, 220, 44, ['Сертификат shop.pem', 'shop.localhost, *.shop.localhost'], fill=.08, bold=True, size=11)
    s.arrow(530, 74, 530, 118)
    s.text(350, 244, 'Клиент идёт по подписям вверх до знакомого корня — если дошёл, верит', size=11, op=.85)
    return s.html()


@scheme
def mtls():
    s = Svg(700, 250, 'mTLS: сервер показывает сертификат клиенту, клиент показывает свой; доверие к клиентскому CA задаёт Traefik', pid='mt')
    s.box(10, 90, 120, 60, ['Клиент', 'client.pem', 'ключ client-key.pem'], fill=.1, bold=True, size=11)
    s.box(540, 90, 150, 60, ['Traefik', 'опция mtls', 'clients-ca.pem'], fill=.2, bold=True, size=11)
    s.arrow(130, 108, 538, 108)
    s.text(334, 98, 'клиент предъявляет сертификат', size=11, op=.9)
    s.arrow(538, 135, 132, 135, dash=True)
    s.text(334, 160, 'сервер предъявляет свой (shop.pem)', size=11, op=.9)
    s.box(230, 195, 220, 40, ['clients-ca.pem подписал client.pem?'], fill=.14, size=11)
    s.arrow(580, 150, 450, 205, dash=True)
    s.text(350, 20, 'Без клиентского сертификата рукопожатие обрывается', size=12, weight='700')
    s.text(334, 62, 'Подпись проверяется нашим CA клиентов, а не публичным', size=11, op=.85)
    return s.html()


@scheme
def acme_flow():
    s = Svg(700, 290, 'ACME: Traefik регистрирует аккаунт, заказывает сертификат, проходит проверку и получает сертификат', pid='ac')
    s.box(20, 10, 130, 44, ['Traefik'], fill=.2, bold=True)
    s.box(550, 10, 130, 44, ['ACME-сервер', 'Let’s Encrypt'], fill=.12, bold=True, size=11)
    s.line(85, 54, 85, 280, dash=True, op=.5)
    s.line(615, 54, 615, 280, dash=True, op=.5)
    steps = [(80, '→', '1  Аккаунт: ключ и почта'),
             (118, '→', '2  Заказ: «хочу сертификат для shop.example.com»'),
             (156, '←', '3  Задание (challenge): докажи, что имя твоё'),
             (194, '↔', '4  Traefik выполняет, сервер проверяет (HTTP-01 / TLS-ALPN-01 / DNS-01)'),
             (232, '→', '5  Финализация: запрос на сертификат'),
             (268, '←', '6  Готовый сертификат (90 дней); продление — сам')]
    for y, d, t in steps:
        if d == '→':
            s.arrow(87, y, 613, y)
        elif d == '←':
            s.arrow(613, y, 87, y)
        else:
            s.arrow(87, y, 613, y, both=True)
        s.text(350, y - 6, t, size=11)
    return s.html()


@scheme
def protocols():
    s = Svg(700, 270, 'Три вида роутеров Traefik: HTTP смотрит на Host и путь, TCP — на имя SNI, UDP — только на порт входа', pid='pt')
    rows = [(10, 'HTTP', 'видит запрос целиком', 'Host(), PathPrefix(), Header()', 'сайт, API'),
            (100, 'TCP', 'видит порт и имя SNI', 'HostSNI(`имя`) или HostSNI(`*`)', 'PostgreSQL, Redis'),
            (190, 'UDP', 'видит только порт', 'правил нет, порт входа', 'DNS, WireGuard')]
    for y, a, b, c, d in rows:
        s.box(10, y, 90, 56, [a], fill=.2, bold=True, size=13)
        s.box(150, y, 200, 56, [b, c], fill=.08, size=11)
        s.box(430, y, 130, 56, ['сервис', d], fill=.12, size=11)
        s.box(600, y, 90, 56, ['порт', 'входа'], fill=.04, dash=True, size=10)
        s.arrow(100, y + 28, 148, y + 28)
        s.arrow(350, y + 28, 428, y + 28)
    s.text(350, 262, 'Чем меньше роутер «понимает» протокол, тем меньше у него возможностей (middleware есть в основном у HTTP)', size=11, op=.85)
    return s.html()


@scheme
def xff_chain():
    s = Svg(700, 250, 'Цепочка X-Forwarded-For: каждый доверенный прокси дописывает адрес источника; от недоверенного заголовок заменяется', pid='xf')
    s.box(10, 90, 100, 50, ['Клиент', '203.0.113.7'], fill=.1, bold=True, size=11)
    s.box(210, 90, 120, 50, ['Балансировщик', '10.0.0.5'], fill=.14, size=11)
    s.box(430, 90, 100, 50, ['Traefik'], fill=.2, bold=True)
    s.box(590, 90, 100, 50, ['Приложение'], fill=.08, size=11)
    s.arrow(110, 115, 208, 115)
    s.arrow(330, 115, 428, 115)
    s.arrow(530, 115, 588, 115)
    s.text(160, 78, 'X-Forwarded-For: —', size=10, op=.9)
    s.text(380, 78, 'XFF: 203.0.113.7', size=10, op=.9)
    s.text(560, 78, 'XFF: 203.0.113.7, 10.0.0.5', size=10, op=.9, anchor='end')
    s.text(350, 40, 'Доверенный прокси: Traefik сохраняет заголовок и дописывает адрес источника', size=12, weight='700')
    s.box(210, 175, 320, 44, ['Недоверенный источник: заголовок отбрасывается,', 'остаётся только адрес самого источника'], fill=.04, dash=True, size=11)
    s.text(350, 243, 'trustedIPs — только адреса своих прокси; depth — сколько доверенных прокси перед Traefik', size=11, op=.85)
    return s.html()


@scheme
def metrics_flow():
    s = Svg(700, 240, 'Метрики: Traefik отдаёт показания на входе metrics, Prometheus опрашивает и хранит, Grafana рисует графики и оповещения', pid='mf')
    s.box(10, 90, 130, 60, ['Traefik', 'вход metrics :8082'], fill=.2, bold=True, size=11)
    s.box(260, 90, 170, 60, ['Prometheus', 'хранит числа во времени'], fill=.14, bold=True, size=11)
    s.box(550, 20, 140, 60, ['Grafana', 'графики RED'], fill=.1, bold=True, size=11)
    s.box(550, 160, 140, 60, ['Оповещения', '5xx > 5%'], fill=.1, size=11)
    s.arrow(258, 118, 142, 118)
    s.text(200, 106, 'опрос каждые 5 с', size=10, op=.9)
    s.arrow(432, 108, 548, 56)
    s.arrow(432, 135, 548, 185)
    s.text(350, 30, 'Показания: запросы, коды ответов, время', size=12, weight='700')
    s.text(350, 226, 'Журнал доступа отвечает «почему», метрики — «что и когда изменилось»', size=11, op=.85)
    return s.html()


@scheme
def diagnostic_tree():
    s = Svg(700, 330, 'Дерево вопросов: по коду ответа находим слой, где искать причину', pid='dt')
    s.box(270, 8, 160, 40, ['Запрос получил…'], fill=.2, bold=True)
    cols = [(10, '000', 'нет ответа', ['имя, порт,', 'TLS']),
            (150, '404', 'не нашёл роутер', ['правило, вход,', 'приоритет, метки']),
            (290, '401 / 403 / 429', 'отказал middleware', ['пароль, список IP,', 'лимит, mTLS']),
            (430, '502 / 504', 'сервис не отвечает', ['порт, сеть,', 'контейнер упал']),
            (570, '503', 'нет здоровых копий', ['healthcheck,', 'предохранитель'])]
    for x, code, what, where in cols:
        s.arrow(350, 48, x + 60, 100)
        s.box(x, 100, 120, 46, [code, what], fill=.1, bold=True, size=10)
        s.arrow(x + 60, 146, x + 60, 190)
        s.box(x, 190, 120, 56, where, fill=.05, size=10, dash=True)
    s.text(350, 280, 'Первый вопрос всегда один: чей это ответ — Traefik или приложения?', size=12, weight='700')
    s.text(350, 304, 'Смотри: дашборд (роутеры, сервисы), журнал Traefik, журнал доступа (RouterName, DownstreamStatus)', size=11, op=.85)
    return s.html()


@scheme
def final_stack():
    s = Svg(700, 300, 'Итоговый стек: один вход Traefik, общие middleware, сайт, две копии API, Adminer, база во внутренней сети и мониторинг', pid='fs')
    s.box(10, 110, 80, 50, ['Клиенты'], fill=.1, bold=True, size=11)
    s.box(120, 60, 160, 150, ['Traefik', ':80 → :443 (HTTP/3)', 'TLS mkcert', 'журнал JSON', 'метрики :8082'], fill=.2, bold=True, size=11)
    s.arrow(90, 135, 118, 135)
    items = [(20, 'web  (nginx)', 'web-chain'), (84, 'api ×2', 'strip, limit, health'), (148, 'adminer', 'пароль'), (212, 'dashboard', 'пароль')]
    for y, a, b in items:
        s.box(340, y, 150, 50, [a, b], fill=.08, size=11)
        s.arrow(280, 135, 338, y + 25)
    s.box(540, 84, 140, 50, ['db  postgres', 'сеть back'], fill=.14, dash=True, size=11)
    s.arrow(490, 109, 538, 109, both=True)
    s.box(540, 190, 140, 50, ['Prometheus + Grafana', 'опрос :8082'], fill=.1, size=10)
    s.arrow(538, 215, 282, 175, dash=True)
    s.text(350, 280, 'Поднимается одной командой ./up.sh, проверяется ./smoke.sh', size=12, weight='700')
    return s.html()


@scheme
def final_task():
    s = Svg(700, 290, 'Итоговое задание: партнёры по mTLS попадают на партнёрский API с лимитами, выкатка v1/v2 по весам с проверкой метрик', pid='ft')
    s.box(10, 70, 110, 56, ['Партнёр', 'клиентский', 'сертификат'], fill=.1, bold=True, size=11)
    s.box(170, 40, 150, 116, ['Traefik', 'mTLS, TLS 1.3', 'лимит по X-Api-Key', 'retry только GET', 'circuitBreaker'], fill=.2, bold=True, size=11)
    s.arrow(120, 98, 168, 98)
    s.box(390, 14, 130, 50, ['v1  (вес 90)', 'партнёрский API'], fill=.08, size=11)
    s.box(390, 90, 130, 50, ['v2  (вес 10)', 'новая версия'], fill=.14, size=11)
    s.box(390, 166, 130, 44, ['зеркало 20% GET'], fill=.04, dash=True, size=11)
    s.arrow(320, 80, 388, 40)
    s.arrow(320, 98, 388, 114)
    s.arrow(320, 120, 388, 186, dash=True)
    s.box(570, 70, 120, 70, ['Prometheus', 'доля 5xx', 'правило оповещения'], fill=.12, size=10)
    s.arrow(320, 60, 568, 92, dash=True)
    s.box(110, 222, 470, 44, ['rollout.sh: 90/10 → 50/50 → 0/100; если 5xx > 5% — откат на 100/0'], fill=.06, size=11)
    s.arrow(570, 120, 522, 232, dash=True)
    return s.html()


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, f in S.items():
        if len(sys.argv) > 1 and name != sys.argv[1]:
            continue
        open(os.path.join(OUT, name + '.html'), 'w', encoding='utf-8').write(f())
        print('схема:', name)
