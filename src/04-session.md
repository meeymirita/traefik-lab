# Сессия 4 · Middlewares: преобразование запросов
dur: ~4 ч

## 4.1 Модель middleware и порядок цепочки | short: Модель middleware | est: ~40 мин
### intro
**Слова шага:** *middleware*, *цепочка*, *порядок применения*, *`addprefix`*, *`stripprefix`*, *`@docker` / `@file`*.

:::tip Если совсем просто
Middleware — **станция на конвейере**. Запрос едет от входа к сервису, и на каждой станции с ним что-то делают: срезают префикс, добавляют заголовок, проверяют пароль. Станции стоят в порядке, который ты задала, и **порядок важен**: если сначала покрасить, а потом шлифовать, получится не то же самое, что наоборот.
:::

```svg
@middleware-chain
```

**Middleware** — это маленькая обработка, которая подключается к роутеру. Три важных факта:

1. **Объявляется отдельно** (как объект с именем и типом), а **подключается к роутеру** меткой `routers.<имя>.middlewares=имя1,имя2`.
2. **Применяется по порядку слева направо** для запроса. Для ответа порядок обратный.
3. Один middleware можно подключить к нескольким роутерам.

Опыт: одна `whoami`, два роутера с **одними и теми же** двумя middlewares — но в разном порядке. `strip` срезает префикс, `add` дописывает `/v2`:

```bash run
cd ~/traefik-lab/edge
cat > compose.mw1.yaml <<'EOF'
name: mw1

services:
  lab:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      # роутер 1: сначала срезать /one, потом добавить /v2
      - traefik.http.routers.mw-one.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/one`)
      - traefik.http.routers.mw-one.entrypoints=web
      - traefik.http.routers.mw-one.middlewares=strip-one,add-v2
      # роутер 2: сначала добавить /v2, потом срезать /two
      - traefik.http.routers.mw-two.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/two`)
      - traefik.http.routers.mw-two.entrypoints=web
      - traefik.http.routers.mw-two.middlewares=add-v2,strip-two
      - traefik.http.middlewares.strip-one.stripprefix.prefixes=/one
      - traefik.http.middlewares.strip-two.stripprefix.prefixes=/two
      - traefik.http.middlewares.add-v2.addprefix.prefix=/v2
      - traefik.http.services.mw-lab.loadbalancer.server.port=80
      - traefik.http.routers.mw-one.service=mw-lab
      - traefik.http.routers.mw-two.service=mw-lab

networks:
  proxy:
    external: true
EOF
docker compose -f compose.mw1.yaml up -d 2>&1 | tail -1
sleep 3
echo "--- запрос /one/menu: что получила whoami?"
curl -s http://whoami.shop.localhost/one/menu | grep -m1 '^GET'
echo "--- запрос /two/menu: что получила whoami?"
curl -s http://whoami.shop.localhost/two/menu | grep -m1 '^GET'
```

### result
```out auto
```

Один и тот же набор станций, но в разном порядке — разный результат:

- `/one/menu`: сначала `strip-one` срезал `/one` → `/menu`, потом `add-v2` добавил префикс → **`/v2/menu`**.
- `/two/menu`: сначала `add-v2` сделал `/v2/two/menu`, потом `strip-two` попытался срезать `/two` — но путь начинается с `/v2`, срезать нечего → **`/v2/two/menu`**, а лишний `/two` остался.

Ни ошибки, ни предупреждения: Traefik честно выполнил, что ты записала. Вывод: **порядок в списке `middlewares=…` — часть логики, а не просто перечисление**. Заметь ещё две вещи в метках: у объекта `middlewares` есть имя, **тип** (`stripprefix`, `addprefix`) и поле (`prefixes`, `prefix`); а роутеры мы связали с сервисом `mw-lab` явно метками `…routers.<имя>.service=…` — когда у контейнера **несколько роутеров**, Traefik требует указать сервис явно (иначе в журнале ошибка «service is missing»).

### why
Middleware — главный «рабочий» механизм Traefik: после того как запрос нашёл свой роутер, всё остальное — это цепочка. И ошибки в порядке цепочки (как в `/two`) не видны ни в дашборде, ни в журнале ошибок — только в том, что получил бэкенд. Поэтому для проверки middleware мы всегда смотрим **то, что дошло до сервиса** (у нас для этого `whoami` и `/info` у API).

### deep Команды по частям
`grep -m1 '^GET'` — первая строка ответа `whoami`, начинающаяся с `GET`: это строка запроса, которую получил сервис (после всех middlewares). `traefik.http.middlewares.<имя>.<тип>.<поле>=значение` — полная форма метки middleware. В YAML строки с `#` — комментарии, их Compose игнорирует.

### deep Как ещё можно
- **Список в файле:** в файловой конфигурации то же самое выглядит как `middlewares: [strip-one, add-v2]` — порядок тот же.
- **Тест без whoami:** `curl -v` покажет ответ; запрос же, который дошёл до сервиса, видно только в самом сервисе — поэтому для проверок middleware удобно иметь «зеркальный» сервис (как `whoami`).

### deep Если не получилось
- **`404` на оба пути** — не подняты роутеры: проверь в дашборде, нет ли ошибки роутера (`mw-one`, `mw-two`), и что `whoami.shop.localhost` разрешается.
- **В дашборде `service is missing`** — у контейнера несколько роутеров, а сервис не указан: добавь `…routers.<имя>.service=mw-lab`.
- **Предыдущий стенд ещё работает** — если остались роутеры из шага 3.3 (`rules-*`), они могут перехватить запрос: `docker compose -f compose.rules.yaml down`.

### quiz
- В каком порядке Traefik применяет middlewares из списка `middlewares=a,b,c` и почему порядок важен?
- Из каких трёх частей состоит метка middleware и как её подключить к роутеру?
- Почему результат цепочки проверяют на стороне сервиса, а не в дашборде?

### links
- https://doc.traefik.io/traefik/middlewares/overview/ | обзор middlewares | Traefik: middlewares overview
- https://doc.traefik.io/traefik/middlewares/http/addprefix/ | AddPrefix | Traefik: AddPrefix

## 4.2 Изменение пути: StripPrefix, AddPrefix, ReplacePath, RedirectRegex | short: Изменение пути | est: ~45 мин
### intro
**Слова шага:** *`stripPrefix`*, *`addPrefix`*, *`replacePath`*, *`replacePathRegex`*, *`redirectRegex`*, *постоянный и временный редирект*, *`$$`*.

:::tip Если совсем просто
Пять способов поменять адрес, по которому приходит запрос: срезать начало, дописать начало, заменить целиком, переписать по шаблону — или вовсе отправить посетителя на другой адрес (редирект). Выбирай по ситуации.
:::

| Middleware | Что делает | Пример |
|---|---|---|
| `stripPrefix` | срезает начало пути | `/api/menu` → `/menu` |
| `addPrefix` | дописывает начало | `/menu` → `/v1/menu` |
| `replacePath` | заменяет путь целиком | `/anything` → `/fixed` |
| `replacePathRegex` | переписывает по регулярному выражению | `/old/12` → `/new/12` |
| `redirectRegex` | отправляет клиента на **другой адрес** (301/302) | `http://…/old/x` → `http://…/new/x` |

Первые четыре меняют путь **внутри**: клиент ничего не замечает, а бэкенд получает другой адрес. Последний — **снаружи**: клиент получает ответ `301` с заголовком `Location` и сам идёт по новому адресу. Проверим все пять на `whoami` с разными префиксами:

```bash run
cd ~/traefik-lab/edge
docker compose -f compose.mw1.yaml down 2>&1 | tail -1
cat > compose.mw2.yaml <<'EOF'
name: mw2

services:
  lab:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.services.mw2.loadbalancer.server.port=80
      # strip
      - traefik.http.routers.mw2-strip.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/strip`)
      - traefik.http.routers.mw2-strip.entrypoints=web
      - traefik.http.routers.mw2-strip.service=mw2
      - traefik.http.routers.mw2-strip.middlewares=m-strip
      - traefik.http.middlewares.m-strip.stripprefix.prefixes=/strip
      # add
      - traefik.http.routers.mw2-add.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/add`)
      - traefik.http.routers.mw2-add.entrypoints=web
      - traefik.http.routers.mw2-add.service=mw2
      - traefik.http.routers.mw2-add.middlewares=m-add
      - traefik.http.middlewares.m-add.addprefix.prefix=/v1
      # replace
      - traefik.http.routers.mw2-rep.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/rep`)
      - traefik.http.routers.mw2-rep.entrypoints=web
      - traefik.http.routers.mw2-rep.service=mw2
      - traefik.http.routers.mw2-rep.middlewares=m-rep
      - traefik.http.middlewares.m-rep.replacepath.path=/fixed
      # replace by regex ($1 в Compose пишется как $$1)
      - traefik.http.routers.mw2-rx.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/old`)
      - traefik.http.routers.mw2-rx.entrypoints=web
      - traefik.http.routers.mw2-rx.service=mw2
      - traefik.http.routers.mw2-rx.middlewares=m-rx
      - traefik.http.middlewares.m-rx.replacepathregex.regex=^/old/(.*)
      - traefik.http.middlewares.m-rx.replacepathregex.replacement=/new/$$1
      # redirect
      - traefik.http.routers.mw2-go.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/go`)
      - traefik.http.routers.mw2-go.entrypoints=web
      - traefik.http.routers.mw2-go.service=mw2
      - traefik.http.routers.mw2-go.middlewares=m-go
      - traefik.http.middlewares.m-go.redirectregex.regex=^http://whoami.shop.localhost/go/(.*)
      - traefik.http.middlewares.m-go.redirectregex.replacement=http://whoami.shop.localhost/moved/$$1
      - traefik.http.middlewares.m-go.redirectregex.permanent=true

networks:
  proxy:
    external: true
EOF
docker compose -f compose.mw2.yaml up -d 2>&1 | tail -1
sleep 3
g() { printf '%-18s -> ' "$1"; curl -s "http://whoami.shop.localhost$1" | grep -m1 '^GET'; }
g /strip/menu
g /add/menu
g /rep/anything
g /old/12
echo "--- редирект (клиент получает 301 и сам идёт дальше):"
curl -s -o /dev/null -D - http://whoami.shop.localhost/go/coffee | grep -iE '^(HTTP|location)'
```

### result
```out auto
```

Четыре «внутренних» преобразования дали ожидаемый путь: `/strip/menu` → `/menu`, `/add/menu` → `/v1/add/menu` (адрес дописан **перед** исходным путём, поэтому префикс `/add` остался), `/rep/anything` → `/fixed`, `/old/12` → `/new/12`. Пятый — настоящий **редирект**: ответ `301 Moved Permanently` и заголовок `Location` с новым адресом. Различие важно: после `stripPrefix` клиент видит «свой» адрес, а после редиректа **адрес в браузере меняется**.

Обрати внимание на `$$1`: в регулярных выражениях «захваченную группу» обозначают `$1`, но в Compose одиночный `$` — подстановка переменной, поэтому в файле пишется `$$1`. Забыть удвоение — классическая ошибка (мы воспроизведём её в шаге 4.7).

### why
Эти пять преобразований покрывают почти все задачи «бэкенд хочет не тот адрес»: сервис живёт на корне, а ты публикуешь его по `/api`; сервис переехал; старая ссылка должна продолжать работать. Особенно полезен `stripPrefix`: он позволяет публиковать любое приложение по любому пути, не меняя его код.

### deep Команды по частям
Функция `g() { … }` печатает путь и первую строку запроса `GET …`, которую получила `whoami` (после middlewares). `curl -s -o /dev/null -D -` — тело выбросить, заголовки ответа напечатать в стандартный вывод (`-D -`). `grep -iE '^(HTTP|location)'` оставляет строку статуса и `Location`. Поле `permanent=true` делает редирект `301` (постоянный, браузер запоминает), без него — `302` (временный).

### deep Как ещё можно
- **`stripPrefixRegex`** — срезать по регулярке (например, `^/[a-z]+/v[0-9]+` — «любое имя и версия»).
- **`redirectScheme`** — перенаправить `http` на `https` (шаг 4.3) — это частный случай редиректа.
- **Редирект «www → без www»:** `redirectregex` с регуляркой на `Host` — типовое применение.

### deep Если не получилось
- **`/old/12` приходит как `/old/12`** — в метке `replacement` потерялся `$$`: Compose подставил пустую переменную; в журнале `docker compose` предупреждение `variable is not set`.
- **Редирект ведёт на `http://…/moved/` без остатка** — в регулярке `regex` нет группы `(.*)` или пишется `$1` вместо `$$1`.
- **`404` на какой-то из путей** — проверь, что у каждого роутера есть свой `service`, и что прежние стенды остановлены.

### quiz
- Чем `stripPrefix` отличается от `redirectRegex` с точки зрения клиента?
- Почему `addPrefix` для запроса `/add/menu` дал `/v1/add/menu`, а не `/v1/menu`?
- Зачем в метках Compose писать `$$1`?

### links
- https://doc.traefik.io/traefik/middlewares/http/stripprefix/ | StripPrefix | Traefik: StripPrefix
- https://doc.traefik.io/traefik/middlewares/http/redirectregex/ | RedirectRegex | Traefik: RedirectRegex

## 4.3 redirectScheme и headers: безопасность и CORS | short: Заголовки и redirectScheme | est: ~45 мин
### intro
**Слова шага:** *`redirectScheme`*, *`headers`*, *`customResponseHeaders`*, *security headers*, *CORS*, *preflight*.

:::tip Если совсем просто
`headers` — это «штамп» на ответе. Можно поставить штампы безопасности («не вставляй меня во фрейм», «не угадывай тип файла»), удалить лишние («кто я по версии сервера») и разрешить чужим сайтам обращаться к нашему API (CORS — «правила гостей»).
:::

**`redirectScheme`** отправляет клиента с `http` на `https`: `scheme=https`. Сейчас у нас нет HTTPS (сессия 7), поэтому увидим только сам редирект — ответ `301` с адресом `https://…`.

**`headers`** меняет заголовки запроса и ответа. Самые полезные поля:

| Поле | Что делает |
|---|---|
| `customRequestHeaders.X-Name=значение` | добавить заголовок в **запрос** к бэкенду |
| `customResponseHeaders.X-Name=значение` | добавить заголовок в **ответ** клиенту (пустое значение — **удалить**) |
| `frameDeny=true` | запретить встраивать сайт во фрейм (`X-Frame-Options: DENY`) |
| `contentTypeNosniff=true` | `X-Content-Type-Options: nosniff` |
| `referrerPolicy=no-referrer` | не передавать адрес страницы-источника |
| `accessControlAllowOriginList`, `accessControlAllowMethods`, `accessControlMaxAge` | **CORS** — разрешить браузерным страницам с чужих адресов обращаться к API |

CORS нужен, когда страница с одного адреса (`http://shop.localhost`) запрашивает данные по другому (`http://api.example`): браузер сначала шлёт «разведочный» запрос `OPTIONS` (*preflight*: «можно ли мне прислать `GET`?») и, получив разрешение, только тогда делает настоящий. Проверим всё на `whoami`:

```bash run
cd ~/traefik-lab/edge
docker compose -f compose.mw2.yaml down 2>&1 | tail -1
cat > compose.mw3.yaml <<'EOF'
name: mw3

services:
  lab:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.services.mw3.loadbalancer.server.port=80
      # редирект http -> https
      - traefik.http.routers.mw3-sec.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/sec`)
      - traefik.http.routers.mw3-sec.entrypoints=web
      - traefik.http.routers.mw3-sec.service=mw3
      - traefik.http.routers.mw3-sec.middlewares=m-https
      - traefik.http.middlewares.m-https.redirectscheme.scheme=https
      - traefik.http.middlewares.m-https.redirectscheme.permanent=true
      # заголовки безопасности и свой штамп
      - traefik.http.routers.mw3-hdr.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/hdr`)
      - traefik.http.routers.mw3-hdr.entrypoints=web
      - traefik.http.routers.mw3-hdr.service=mw3
      - traefik.http.routers.mw3-hdr.middlewares=m-hdr
      - traefik.http.middlewares.m-hdr.headers.framedeny=true
      - traefik.http.middlewares.m-hdr.headers.contenttypenosniff=true
      - traefik.http.middlewares.m-hdr.headers.referrerpolicy=no-referrer
      - traefik.http.middlewares.m-hdr.headers.customresponseheaders.X-Shop=coffee
      - traefik.http.middlewares.m-hdr.headers.customrequestheaders.X-From-Proxy=traefik
      # CORS
      - traefik.http.routers.mw3-cors.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/cors`)
      - traefik.http.routers.mw3-cors.entrypoints=web
      - traefik.http.routers.mw3-cors.service=mw3
      - traefik.http.routers.mw3-cors.middlewares=m-cors
      - traefik.http.middlewares.m-cors.headers.accesscontrolalloworiginlist=http://shop.localhost
      - traefik.http.middlewares.m-cors.headers.accesscontrolallowmethods=GET,OPTIONS
      - traefik.http.middlewares.m-cors.headers.accesscontrolmaxage=600
      - traefik.http.middlewares.m-cors.headers.addvaryheader=true

networks:
  proxy:
    external: true
EOF
docker compose -f compose.mw3.yaml up -d 2>&1 | tail -1
sleep 3
echo "--- редирект на https:"
curl -s -o /dev/null -D - http://whoami.shop.localhost/sec/menu | grep -iE '^(HTTP|location)'
echo "--- заголовки ответа:"
curl -s -o /dev/null -D - http://whoami.shop.localhost/hdr | grep -iE '^(x-shop|x-frame|x-content|referrer)'
echo "--- заголовок запроса, который увидела whoami:"
curl -s http://whoami.shop.localhost/hdr | grep -i '^X-From-Proxy'
echo "--- CORS: разведочный запрос с разрешённого адреса:"
curl -s -o /dev/null -D - -X OPTIONS -H 'Origin: http://shop.localhost' -H 'Access-Control-Request-Method: GET' http://whoami.shop.localhost/cors | grep -iE '^(HTTP|access-control)'
echo "--- CORS: с чужого адреса:"
curl -s -o /dev/null -D - -X OPTIONS -H 'Origin: http://evil.example' -H 'Access-Control-Request-Method: GET' http://whoami.shop.localhost/cors | grep -iE '^(HTTP|access-control)'
```

### result
```out auto
```

Разбор по блокам:

- **Редирект** — `301` и `Location: https://whoami.shop.localhost/sec/menu`: схема сменилась на `https`, адрес и путь сохранены.
- **Заголовки безопасности** — в ответе появились `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` и наш штамп `X-Shop: coffee`. Запрос к `whoami` получил дополнительный заголовок `X-From-Proxy: traefik`.
- **CORS с разрешённого адреса** — Traefik **сам ответил на `OPTIONS`** с заголовками `Access-Control-Allow-Origin: http://shop.localhost`, `Access-Control-Allow-Methods`, `Access-Control-Max-Age`, не дойдя до сервиса. 
- **CORS с чужого адреса** — заголовка `Access-Control-Allow-Origin` **нет**: браузер увидит отсутствие разрешения и заблокирует обращение (остальные заголовки CORS при этом присутствуют — важно именно отсутствие `Allow-Origin`).

### why
Заголовки безопасности и CORS — это то, что хочется один раз настроить на входе для всех сервисов, а не в каждом по отдельности. Всё сказанное про порядок из шага 4.1 здесь тоже работает: `headers` обычно ставят **первым** — тогда заголовки добавятся и к ответам, которые закончит сам Traefik (редиректы, ошибки аутентификации).

### deep Команды по частям
`curl -s -o /dev/null -D - -X OPTIONS -H 'Origin: …' -H 'Access-Control-Request-Method: GET' URL` — отправить `OPTIONS` с теми заголовками, что ставит браузер при разведочном запросе, и показать заголовки ответа. `grep -iE '^(a|b)'` — регистр не важен (`-i`), нужны строки, начинающиеся с перечисленных слов.

### deep Как ещё можно
- **HSTS** (`stsSeconds`, `stsIncludeSubdomains`): заголовок «всегда ходи только по HTTPS» — **действует только при HTTPS-запросе** (в шаге 7.x проверим).
- **`customResponseHeaders.Server=`** — пустое значение удаляет заголовок; так скрывают, чем ты отвечаешь.
- **Любой адрес в CORS:** `accesscontrolalloworiginlist=*` — удобно в разработке, **не рекомендуется** с учётными данными.

### deep Если не получилось
- **Нет заголовков безопасности** — middleware `m-hdr` не подключён к роутеру `mw3-hdr`: сверь имя в `routers.…middlewares`.
- **`OPTIONS` вернул `404`** — путь `/cors` не совпал; в запросе должен быть `Host: whoami.shop.localhost`.
- **`Access-Control-Allow-Origin` нет и для разрешённого адреса** — значение в `accesscontrolalloworiginlist` не совпадает с `Origin` посимвольно (протокол, порт).

### quiz
- Что делает `redirectScheme` и что остаётся в адресе после редиректа?
- Зачем нужен предварительный запрос `OPTIONS` и кто на него отвечает в нашей схеме?
- Как удалить заголовок ответа с помощью `customResponseHeaders`?

### links
- https://doc.traefik.io/traefik/middlewares/http/headers/ | Headers | Traefik: Headers
- https://developer.mozilla.org/ru/docs/Web/HTTP/CORS | CORS | MDN: CORS

## 4.4 compress, basicAuth, digestAuth | short: compress и basicAuth | est: ~50 мин
### intro
**Слова шага:** *`compress`*, *`gzip`*, *`basicAuth`*, *`htpasswd`*, *bcrypt*, *`usersFile`*, *`digestAuth`*.

:::tip Если совсем просто
`compress` — «упаковщик»: ответ сжимается перед отправкой, если клиент сказал, что умеет распаковывать. `basicAuth` — «вахтёр с журналом»: без логина и пароля не пускает. Пароли хранятся не открытым текстом, а в виде **хэша** — «отпечатка», по которому пароль не восстановить.
:::

**`compress`** сжимает ответы (gzip, brotli, zstd) для клиентов, которые прислали `Accept-Encoding`. По умолчанию сжимает только ответы **больше 1024 байт** — сжимать мелочь невыгодно. Для опыта порог снижен, чтобы увидеть эффект на маленьком ответе.

**`basicAuth`** запрашивает логин и пароль (в браузере всплывает окно). Список пользователей — строки `имя:хэш`. Хэш делает утилита **`htpasswd`** (пакет `apache2-utils`; на Mac есть в системе): `htpasswd -nbB имя пароль` (`-n` вывести на экран, `-b` пароль из аргумента, `-B` алгоритм bcrypt). **`digestAuth`** — старый вариант с передачей не пароля, а его «отпечатка» (не рекомендуется: bcrypt в `basicAuth` проще и надёжнее при HTTPS).

Теперь самое важное: **хэш содержит символы `$`** — например `mira:$2y$05$abc…`. А Compose, как мы видели, считает `$` началом подстановки. Поэтому есть два надёжных способа:

1. **Удвоить `$`** в самой метке: `mira:$$2y$$05$$abc…`.
2. **Положить хэш в `.env` в одинарных кавычках** и подставить `${AUTH_USERS}` — Compose не трогает содержимое одинарных кавычек. Так и сделаем:

```bash run
cd ~/traefik-lab/edge
docker compose -f compose.mw3.yaml down 2>&1 | tail -1
echo "--- пароль превращается в хэш (у тебя будет другая «соль», хэш другой):"
htpasswd -nbB mira coffee-secret | sed -E 's/(\$2y\$05\$.{6}).*/\1…/'
printf "AUTH_USERS='%s'\n" "$(htpasswd -nbB mira coffee-secret)" > .env
cat > compose.mw4.yaml <<'EOF'
name: mw4

services:
  lab:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.services.mw4.loadbalancer.server.port=80
      - traefik.http.routers.mw4-zip.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/zip`)
      - traefik.http.routers.mw4-zip.entrypoints=web
      - traefik.http.routers.mw4-zip.service=mw4
      - traefik.http.routers.mw4-zip.middlewares=m-zip
      - traefik.http.middlewares.m-zip.compress.minresponsebodybytes=10
      - traefik.http.routers.mw4-auth.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/secret`)
      - traefik.http.routers.mw4-auth.entrypoints=web
      - traefik.http.routers.mw4-auth.service=mw4
      - traefik.http.routers.mw4-auth.middlewares=m-auth
      - traefik.http.middlewares.m-auth.basicauth.users=${AUTH_USERS}
      - traefik.http.middlewares.m-auth.basicauth.removeheader=true

networks:
  proxy:
    external: true
EOF
docker compose -f compose.mw4.yaml up -d 2>&1 | tail -1
sleep 3
echo "--- без Accept-Encoding / с Accept-Encoding: gzip:"
curl -s -D - -o /dev/null http://whoami.shop.localhost/zip | grep -i '^content-encoding' || echo "(без сжатия)"
curl -s -D - -o /dev/null -H 'Accept-Encoding: gzip' http://whoami.shop.localhost/zip | grep -i '^content-encoding'
echo "--- basicAuth: без пароля / неверный / верный:"
curl -s -o /dev/null -D - http://whoami.shop.localhost/secret | grep -iE '^(HTTP|www-authenticate)'
curl -s -o /dev/null -w 'неверный пароль -> HTTP %{http_code}\n' -u mira:wrong http://whoami.shop.localhost/secret
curl -s -o /dev/null -w 'верный пароль  -> HTTP %{http_code}\n' -u mira:coffee-secret http://whoami.shop.localhost/secret
echo "--- что видит бэкенд (removeheader=true): заголовок Authorization есть?"
curl -s -u mira:coffee-secret http://whoami.shop.localhost/secret | grep -ci '^authorization' || true
```

### result
```out auto
```

- `compress`: без `Accept-Encoding` ответ идёт без сжатия (в первой проверке строки нет), с `Accept-Encoding: gzip` — `Content-Encoding: gzip`.
- `basicAuth`: без пароля — `401 Unauthorized` и заголовок `WWW-Authenticate: Basic realm="traefik"` (именно по нему браузер показывает окно входа); неверный пароль — снова `401`; верный — `200`.
- `removeheader=true` не пускает заголовок `Authorization` к бэкенду: ему незачем знать пароль (счётчик `0`).

Хэш в `.env` выглядит так: `AUTH_USERS='mira:$2y$05$…'` — **одинарные кавычки обязательны**. Строка в файле `compose.mw4.yaml` — просто `…users=${AUTH_USERS}`, без удвоений.

### why
Заметь, как мало потребовалось, чтобы закрыть сервис паролем: одна метка. Это сильная сторона прокси: защита **вне** приложения, ему не нужно знать, что оно закрыто. Важное правило с хэшами: **никогда не клади настоящие пароли в git**; в `.env` — только то, что в `.gitignore` (в `starter/` мы его уже исключали).

### deep Команды по частям
`htpasswd -nbB mira coffee-secret` — печатает `mira:$2y$05$…`: пользователь, двоеточие, bcrypt-хэш (в `$2y$` — версия алгоритма, `05` — «стоимость» вычисления). `sed -E 's/(\$2y\$05\$.{6}).*/\1…/'` — обрезаем хэш при показе, чтобы не печатать его целиком. `printf "AUTH_USERS='%s'\n" "$(…)"` — записывает строку `AUTH_USERS='…'` в `.env`. `-u mira:coffee-secret` у `curl` — готовый заголовок `Authorization: Basic …`.

### deep Как ещё можно
- **`usersFile`:** `basicauth.usersfile=/auth/users` — хэши в отдельном файле (монтируешь внутрь Traefik): `$` не нужно экранировать вообще, а пользователей можно менять без правки меток. Мы воспользуемся файловым подходом в шаге 4.6.
- **Bcrypt vs. MD5:** старые примеры в интернете показывают `htpasswd -nb` (MD5, `$apr1$`) — это работает, но слабее; используй `-B`.
- **`digestAuth`** — оставлен для совместимости; в современных схемах вместо него — `forwardAuth` (сессия 5) или Basic поверх HTTPS.

### deep Если не получилось
- **`401` даже с верным паролем** — хэш в метке испорчен: проверь, что `.env` лежит рядом с `compose.mw4.yaml` и значение в одинарных кавычках; Compose показывает подстановку командой `docker compose -f compose.mw4.yaml config | grep basicauth`.
- **Предупреждение `variable "05" is not set`** — `$` в хэше не экранирован (см. шаг 4.7).
- **`htpasswd: command not found`** — на Mac он есть; в Linux — пакет `apache2-utils` (`apt install apache2-utils`).

### quiz
- Что делает `compress` и почему маленькие ответы по умолчанию не сжимаются?
- Почему в `basicAuth` хранят хэш, а не пароль, и какой алгоритм берут?
- Какие два способа помогают поместить хэш с `$` в `compose.yaml`?

### links
- https://doc.traefik.io/traefik/middlewares/http/basicauth/ | BasicAuth | Traefik: BasicAuth
- https://doc.traefik.io/traefik/middlewares/http/compress/ | Compress | Traefik: Compress

## 4.5 Цепочки и общий файл middlewares | short: chain и файл middlewares | est: ~50 мин
### intro
**Слова шага:** *`chain`*, *файловый провайдер*, *`@file`*, *переиспользование*, *`dynamic/`*, *перезапуск и горячая загрузка*.

:::tip Если совсем просто
Когда на каждый сервис вешаешь одни и те же пять станций («заголовки, сжатие, ограничение…»), хочется записать их **один раз** под именем «стандартный набор» и ссылаться. Это `chain`. А чтобы такие общие наборы не размазывать по меткам разных проектов, их кладут в **общий файл** — и Traefik читает его как ещё один источник.
:::

**`chain`** — middleware, которая состоит из других middleware: `chain.middlewares=a,b,c`. Роутер подключает одну цепочку, а внутри выполняются три. Удобно, когда у нескольких сервисов «одинаковый набор».

Общие middleware удобнее хранить не в метках одного проекта (чужой проект на них не сошлётся без путаницы), а в **файле**, который читает файловый провайдер. Подключаем его в `traefik.yml` (это статическая конфигурация — после правки Traefik перезапускаем) и добавляем в `compose.yaml` Traefik папку `dynamic/`:

```bash run
cd ~/traefik-lab/edge
docker compose -f compose.mw4.yaml down 2>&1 | tail -1
mkdir -p traefik/dynamic
cat > traefik/traefik.yml <<'EOF'
entryPoints:
  web:
    address: ":80"

providers:
  docker:
    exposedByDefault: false
    network: proxy
  file:
    directory: /etc/traefik/dynamic   # общие middlewares, TLS и т.п.
    watch: true                       # файлы перечитываются на лету

api:
  dashboard: true

log:
  level: INFO
  noColor: true

accessLog: {}
EOF
cat > traefik/dynamic/middlewares.yml <<'EOF'
http:
  middlewares:
    secure-headers:
      headers:
        frameDeny: true
        contentTypeNosniff: true
        referrerPolicy: no-referrer
        customResponseHeaders:
          X-Powered-By: ""

    zip:
      compress: {}

    # «стандартный набор» для публичных страниц: порядок важен — сначала заголовки
    web-chain:
      chain:
        middlewares:
          - secure-headers
          - zip
EOF
cat > compose.yaml <<'EOF'
name: edge

services:
  traefik:
    image: traefik:v3.7
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./traefik/traefik.yml:/etc/traefik/traefik.yml:ro
      - ./traefik/dynamic:/etc/traefik/dynamic:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.dashboard.rule=Host(`traefik.shop.localhost`)
      - traefik.http.routers.dashboard.entrypoints=web
      - traefik.http.routers.dashboard.service=api@internal

  whoami:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.whoami.rule=Host(`whoami.localhost`)
      - traefik.http.routers.whoami.entrypoints=web

networks:
  proxy:
    name: proxy
EOF
docker compose up -d 2>&1 | tail -2
sleep 4
echo "--- middlewares, которые видит Traefik (источник — файл):"
curl -s http://traefik.shop.localhost/api/http/middlewares | jq -r '.[] | select(.provider == "file") | [.name, .type, .status] | @tsv' | sort
```

### result
```out auto
```

В списке появились три объекта с суффиксом **`@file`**: `secure-headers@file`, `zip@file`, `web-chain@file` (тип `chain`). Теперь любой контейнер любого проекта может сослаться на них: `…routers.<имя>.middlewares=web-chain@file`. Суффикс обязателен, если объект из **другого** провайдера: метки Docker дают `@docker`, файл — `@file`.

Файл мы теперь можем править **без перезапуска**: из-за `watch: true` Traefik заметит изменение и перечитает. Для проверки применим цепочку к `whoami` и посмотрим ответ:

```bash run
cd ~/traefik-lab/edge
cat > compose.mw5.yaml <<'EOF'
name: mw5

services:
  lab:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.mw5.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/std`)
      - traefik.http.routers.mw5.entrypoints=web
      - traefik.http.routers.mw5.middlewares=web-chain@file

networks:
  proxy:
    external: true
EOF
docker compose -f compose.mw5.yaml up -d 2>&1 | tail -1
sleep 3
curl -s -o /dev/null -D - http://whoami.shop.localhost/std | grep -iE '^(HTTP|x-frame|x-content|referrer)'
docker compose -f compose.mw5.yaml down 2>&1 | tail -1
```

```out auto
```

Ответ получил все заголовки из `secure-headers`: всю цепочку подключила **одна** метка. Роутер даже не знает, что внутри два middleware. Именно такой «стандартный набор» мы навесим на сайт CoffeeShop в шаге 4.6.

### why
Для небольшого стенда хватит и меток. Но как только сервисов становится несколько, общий файл избавляет от копипасты и от ошибок вида «в одном проекте забыли заголовок». А ещё он решает проблему имён из шага 3.6: общие объекты живут в одном месте и в одном пространстве имён (`@file`).

### deep Команды по частям
`providers.file.directory` — папка с файлами (все `*.yml`/`*.yaml`/`*.toml` в ней); `watch: true` — следить за изменениями. В файле структура начинается с `http:` → `middlewares:` — то же дерево, что и в метках, только в виде YAML. `chain.middlewares` — список имён в нужном порядке. `jq … select(.provider == "file")` — оставить объекты, пришедшие из файлового провайдера.

### deep Как ещё можно
- **Один файл — один смысл:** `middlewares.yml`, `tls.yml`, `routers-external.yml` — легче читать и менять.
- **Один файл вместо папки:** `providers.file.filename: /etc/traefik/dynamic.yml` — для самых маленьких стендов.
- **Шаблоны (Go templates)** в файлах динамической конфигурации — в Traefik они есть, но делают конфигурацию сложнее; мы их не используем.

### deep Если не получилось
- **`Cannot read dynamic configuration`** / ошибка в журнале при правке — опечатка в YAML: Traefik **оставит старую рабочую** конфигурацию и напишет ошибку; смотри `docker compose logs traefik`.
- **Файловые middlewares не видны** — не примонтирована папка `dynamic` (проверь `volumes`) или в `traefik.yml` нет `providers.file`: после правки `traefik.yml` перезапусти Traefik (`docker compose up -d` пересоздаст контейнер при изменении `compose.yaml`, а при правке только `traefik.yml` — `docker compose restart traefik`).
- **На Mac при правке файла `watch` не срабатывает** — в Docker Desktop изменение смонтированного файла иногда не доходит до контейнера; перезапусти Traefik.

### quiz
- Что такое `chain` и зачем его делать?
- Чем объект `zip@file` отличается от `zip@docker` и когда нужен суффикс?
- Какие правки требуют перезапуска Traefik, а какие применяются на лету?

### links
- https://doc.traefik.io/traefik/middlewares/http/chain/ | Chain | Traefik: Chain
- https://doc.traefik.io/traefik/providers/file/ | файловый провайдер | Traefik: File provider

## 4.6 Защита дашборда и Adminer | short: Защита дашборда и Adminer | est: ~50 мин
### intro
**Слова шага:** *закрытая зона*, *`basicAuth` в файле*, *общий пользователь*, *`admin-auth@file`*, *приёмка сессии 4*.

:::tip Если совсем просто
Сейчас дашборд и Adminer открыты любому, кто знает адрес. Ставим вахтёра: добавляем пользователя в общий файл и подключаем его к обоим роутерам. Одна проверка паролей — на двух дверях.
:::

```svg
@protect
```

Сначала добавим пользователя в общий файл. Пароль в файле хранится как bcrypt-хэш (в YAML `$` писать **не нужно** экранировать — Compose этот файл не читает). Затем подключим `admin-auth` к роутеру дашборда (в `edge/compose.yaml`), а в проекте CoffeeShop — к Adminer, и подключим «стандартный набор» к сайту:

```bash run
cd ~/traefik-lab/edge
cat >> traefik/dynamic/middlewares.yml <<EOF

    # пользователи админ-зон (хэш bcrypt, пароль: coffee-secret)
    admin-auth:
      basicAuth:
        removeHeader: true
        users:
          - "$(htpasswd -nbB mira coffee-secret)"
EOF
cat > compose.yaml <<'EOF'
name: edge

services:
  traefik:
    image: traefik:v3.7
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./traefik/traefik.yml:/etc/traefik/traefik.yml:ro
      - ./traefik/dynamic:/etc/traefik/dynamic:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.dashboard.rule=Host(`traefik.shop.localhost`)
      - traefik.http.routers.dashboard.entrypoints=web
      - traefik.http.routers.dashboard.service=api@internal
      - traefik.http.routers.dashboard.middlewares=admin-auth@file

  whoami:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.whoami.rule=Host(`whoami.localhost`)
      - traefik.http.routers.whoami.entrypoints=web

networks:
  proxy:
    name: proxy
EOF
docker compose up -d 2>&1 | tail -2
sleep 4
cd ~/traefik-lab/coffeeshop
cat > compose.mw.yaml <<'EOF'
services:
  web:
    labels:
      - traefik.http.routers.coffee-web.middlewares=web-chain@file
  api:
    labels:
      - traefik.http.routers.coffee-api.middlewares=coffee-strip
  adminer:
    labels:
      - traefik.http.routers.coffee-adminer.middlewares=admin-auth@file
EOF
printf 'COMPOSE_FILE=compose.yaml:compose.strip.yaml:compose.mw.yaml\n' >> .env
docker compose config --services | tr '\n' ' '; echo
docker compose up -d 2>&1 | tail -3
sleep 4
t() { printf '%-44s -> ' "$1"; shift; curl -s -o /dev/null -w 'HTTP %{http_code}\n' "$@"; }
t "дашборд без пароля"       http://traefik.shop.localhost/dashboard/
t "дашборд с паролем"        -u mira:coffee-secret http://traefik.shop.localhost/dashboard/
t "adminer без пароля"       http://adminer.shop.localhost/
t "adminer с паролем"        -u mira:coffee-secret http://adminer.shop.localhost/
t "сайт (без пароля)"        http://shop.localhost/
t "API через /api (без пароля)" http://shop.localhost/api/menu
echo "--- заголовки безопасности на сайте:"
curl -s -o /dev/null -D - http://shop.localhost/ | grep -iE '^(x-frame|x-content|referrer)'
```

### result
```out auto
```

Приёмка сессии 4 выполнена: **`/api` без префикса у бэкенда**, **Adminer и дашборд под паролем**, сайт открыт всем и получает заголовки безопасности и сжатие. Обрати внимание на `.env`: строка **`COMPOSE_FILE=…`** говорит Compose, какие файлы всегда объединять — поэтому `docker compose up -d` теперь работает без десятка `-f`. Файлов станет больше (по одному на сессию); в итоговом шаге 10.5 мы соберём стек в одну аккуратную папку.

Адреса в браузере: **http://traefik.shop.localhost/dashboard/** и **http://adminer.shop.localhost/** теперь спрашивают логин `mira` и пароль `coffee-secret` (учебный пароль; в настоящем стеке его, конечно, меняют).

### why
Обрати внимание, что **ни `web`, ни `api`, ни Adminer не менялись**: мы закрыли Adminer паролем, не тронув ни его конфигурацию, ни образ. Это сильнейший аргумент за reverse proxy. И главное правило: **всё административное (дашборд, Adminer, метрики) закрывай паролем с первого дня**, даже в разработке.

### deep Команды по частям
`cat >> файл <<EOF` (**без кавычек** вокруг `EOF`) — дописать в конец файла и дать оболочке подставить `$(htpasswd …)`: в YAML-файле хэш оказывается в кавычках, `$` в нём остаются как есть. `COMPOSE_FILE=compose.yaml:compose.strip.yaml:compose.mw.yaml` — файлы Compose через двоеточие (на Windows через `;`). `docker compose config --services` — перечисляет сервисы итоговой конфигурации; её же можно распечатать целиком командой `docker compose config`, чтобы увидеть результат слияния файлов.

### deep Как ещё можно
- **Один пароль на всё** — как у нас: `admin-auth@file`. Для разных людей — несколько строк в `users` или отдельный файл `usersFile`.
- **Вместо пароля — IP-фильтр:** разрешить админ-зоны только с определённых адресов — `ipAllowList` (сессия 5).
- **Единая авторизация (SSO)** через `forwardAuth` (сессия 5) — когда пользователей много.

### deep Если не получилось
- **Дашборд по-прежнему без пароля** — файл `middlewares.yml` не перечитан или роутер не получил `middlewares=admin-auth@file`: проверь в дашборде карточку роутера `dashboard@docker`.
- **`401` с верным паролем** — при дописывании в файл хэш мог попасть неверно: открой `traefik/dynamic/middlewares.yml`, строка `users` должна выглядеть как `- "mira:$2y$05$…"` в одну строку.
- **`docker compose` ругается на `COMPOSE_FILE`** — какого-то из файлов нет рядом: проверь имена и отсутствие пробелов.

### quiz
- Какие три объекта защищены одним и тем же `admin-auth@file` и что для этого пришлось менять в самих сервисах?
- Что делает переменная `COMPOSE_FILE` в `.env`?
- Почему административные зоны закрывают паролем даже на локальной машине?

### links
- https://doc.traefik.io/traefik/middlewares/http/basicauth/ | BasicAuth | Traefik: BasicAuth
- https://docs.docker.com/compose/how-tos/environment-variables/envvars/#compose_file | COMPOSE_FILE | Compose: COMPOSE_FILE

## 4.7 🔨 Знак доллара в хэше пароля «съедает» Compose | short: 🔨 $ в хэше | est: ~35 мин
### intro
**Слова шага:** *интерполяция Compose*, *`$$`*, *`variable is not set`*, *одинарные кавычки*, *диагностика через `docker compose config`*.

:::tip Если совсем просто
Compose — «заботливый секретарь»: увидев в файле `$что-то`, он спешит подставить значение переменной. Но в bcrypt-хэше `$` — просто символы. Секретарь «исправит» хэш, и пароль перестанет подходить. Научимся ловить это за минуту.
:::

Воспроизведём типичную ошибку: хэш вставили в метку **как есть**, с одинарными `$`:

```bash run
cd ~/traefik-lab/edge
H=$(htpasswd -nbB mira coffee-secret)
cat > compose.hell.yaml <<EOF
name: hell

services:
  lab:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.hell.rule=Host(\`whoami.shop.localhost\`) && PathPrefix(\`/hell\`)
      - traefik.http.routers.hell.entrypoints=web
      - traefik.http.routers.hell.middlewares=hell-auth
      - traefik.http.middlewares.hell-auth.basicauth.users=$H

networks:
  proxy:
    external: true
EOF
echo "--- что говорит Compose:"
docker compose -f compose.hell.yaml config 2>&1 | grep -E 'warning|users' | cut -c1-120
```

### result
```out auto
```

Compose предупреждает: `The "…" variable is not set. Defaulting to a blank string` — имя «переменной» (набор случайных символов) на самом деле **кусок твоего хэша**: Compose принял его за переменную окружения и подставил пустую строку. В итоге в метку попадает **испорченный** хэш, и с верным паролем будет `401`. Увидеть, что получил Traefik, можно командой `docker compose config` — она печатает итоговую конфигурацию после подстановок.

**Починка — удвоить каждый `$`** (один из двух способов из шага 4.4; второй — через `.env` в одинарных кавычках):

```bash run
cd ~/traefik-lab/edge
H2=$(htpasswd -nbB mira coffee-secret | sed 's/\$/$$/g')
cat > compose.hell.yaml <<EOF
name: hell

services:
  lab:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.hell.rule=Host(\`whoami.shop.localhost\`) && PathPrefix(\`/hell\`)
      - traefik.http.routers.hell.entrypoints=web
      - traefik.http.routers.hell.middlewares=hell-auth
      - traefik.http.middlewares.hell-auth.basicauth.users=$H2

networks:
  proxy:
    external: true
EOF
docker compose -f compose.hell.yaml up -d 2>&1 | tail -1
sleep 3
curl -s -o /dev/null -w 'верный пароль -> HTTP %{http_code}\n' -u mira:coffee-secret http://whoami.shop.localhost/hell
curl -s -o /dev/null -w 'без пароля    -> HTTP %{http_code}\n' http://whoami.shop.localhost/hell
docker compose -f compose.hell.yaml down 2>&1 | tail -1
```

```out auto
```

С удвоенными `$` пароль работает. Запомни приёмы диагностики, они пригодятся не только для хэшей:

1. **`docker compose config`** — смотри, что реально получилось после подстановок; ищи в нём свою метку.
2. **Предупреждения Compose** (`variable … is not set`) — всегда повод проверить, не съел ли он твои `$`.
3. **Дашборд → Middlewares** — открой нужный middleware, посмотри поле `users`: если хэш обрезан или пуст — причина здесь.

### why
Эта ошибка «молчаливая»: Traefik исправно работает, только пароль никто не может ввести, и поиск причины в самом Traefik бесполезен. Зато как только ты знаешь, что `$` — служебный символ Compose, она занимает минуту. Тот же приём нужен для регулярных выражений с `$1` (шаг 4.2).

### deep Команды по частям
`sed 's/\$/$$/g'` — заменить в тексте каждый `$` на два `$`. Heredoc без кавычек (`<<EOF`) позволяет подставить переменную `$H` в файл; обратные кавычки внутри экранированы (`\``), иначе оболочка попыталась бы выполнить команду. `docker compose config | head -4` — первые строки итоговой конфигурации.

### deep Если не получилось
- **Compose вообще не ругается, но пароль не подходит** — «съелась» только часть хэша; сравни хэш из `htpasswd` с тем, что видишь в дашборде.
- **`curl` с верным паролем даёт `404`** — не поднялся роутер: проверь имя сети и что стенды предыдущих шагов остановлены.
- **В метке стоит `$$`, но пароль всё равно не подходит** — ты вставила хэш уже с удвоенными `$` в `.env` (а там удваивать **не нужно**): в `.env` в одинарных кавычках — обычные `$`, а `$$` — только прямо в `compose.yaml`.

### quiz
- Почему Compose портит bcrypt-хэш и какие два надёжных способа этого избежать?
- Какая команда показывает итоговые метки после подстановок?
- Где ещё в метках встречается `$`, который надо удваивать?

### links
- https://docs.docker.com/reference/compose-file/interpolation/ | интерполяция в Compose | Compose: interpolation
- https://doc.traefik.io/traefik/middlewares/http/basicauth/#users | поле users | Traefik: BasicAuth users
