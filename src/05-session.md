# Сессия 5 · Надёжность и защита
dur: ~4 ч

## 5.1 rateLimit: не больше N запросов в секунду | short: rateLimit | est: ~45 мин
### intro
**Слова шага:** *`rateLimit`*, *`average`*, *`burst`*, *`period`*, *токен-бакет*, *`429 Too Many Requests`*, *`sourceCriterion`*.

:::tip Если совсем просто
Представь кассу с **ведром жетонов**. Каждый запрос забирает один жетон. Жетоны капают в ведро с постоянной скоростью (`average` за `period`), а ведро не вмещает больше, чем `burst`. Пока жетоны есть — обслуживаем, кончились — вежливо отвечаем «подождите» (`429`).
:::

```svg
@rate-limit
```

**`rateLimit`** защищает сервис от «слишком много запросов» — от случайного бесконечного цикла в чьём-то коде до грубого перебора паролей. Три числа:

| Поле | Что значит |
|---|---|
| `average` | сколько запросов **в среднем** разрешено за `period` |
| `period` | на какой отрезок времени считается `average` (по умолчанию `1s`) |
| `burst` | сколько запросов можно **сразу пачкой**, если накопился запас жетонов |

По умолчанию лимит считается **на каждый IP-адрес отдельно** (`sourceCriterion` — «кого считаем»: можно по заголовку или по `Host`). Опыты ставим на отдельных копиях нашего API (образ `coffeeshop-api` из сессии 1, в базу ему ходить не нужно): у каждого опыта свой небольшой файл Compose и свой проект (`s5a`, `s5b`…), а предыдущий проект перед новым мы останавливаем. Для первого опыта возьмём **очень строгий** лимит: `average=1` за минуту и `burst=3`: ровно три запроса пройдут сразу, остальные получат отказ:

```bash run
cd ~/traefik-lab/edge
cat > compose.s5a.yaml <<'EOF'
name: s5a

x-lab: &lab
  image: coffeeshop-api
  networks: [proxy]

services:
  rl:
    <<: *lab
    labels:
      - traefik.enable=true
      - traefik.http.routers.s5-rl.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/rl`)
      - traefik.http.routers.s5-rl.entrypoints=web
      - traefik.http.routers.s5-rl.middlewares=s5-rl-limit,s5-rl-strip
      - traefik.http.middlewares.s5-rl-limit.ratelimit.average=1
      - traefik.http.middlewares.s5-rl-limit.ratelimit.period=1m
      - traefik.http.middlewares.s5-rl-limit.ratelimit.burst=3
      - traefik.http.middlewares.s5-rl-strip.stripprefix.prefixes=/rl
      - traefik.http.services.s5-rl.loadbalancer.server.port=3000

networks:
  proxy:
    external: true
EOF
docker compose -f compose.s5a.yaml up -d 2>&1 | tail -1
sleep 4
echo "--- 8 запросов подряд:"
for i in 1 2 3 4 5 6 7 8; do curl -s -o /dev/null -w "запрос $i -> HTTP %{http_code}\n" http://whoami.shop.localhost/rl/health; done
echo "--- заголовки отказа:"
curl -s -o /dev/null -D - http://whoami.shop.localhost/rl/health | grep -iE '^(HTTP|retry-after|x-retry-after)'
```

### result
```out auto
```

Первые три запроса прошли (`200`) — это `burst=3`. Остальные получили `429 Too Many Requests` и заголовок `Retry-After` с числом секунд, через которое можно повторить. Клиент, который читает этот заголовок, сам «успокоится».

Как выбирать числа: `average` — типичная **нормальная** нагрузка на одного пользователя (для человека, листающего меню, — единицы в секунду; для скрипта — по условию), `burst` — запас на «всплеск» (страница вдруг запрашивает десять картинок сразу). Если `burst` меньше `average`, любой короткий всплеск будет резаться.

### why
Лимит на входе — самая дешёвая защита сервиса: он не доходит до приложения и базы. Но и самая опасная настройка, если числа взяты «с потолка»: слишком строгий лимит режет настоящих пользователей. Поэтому цифры проверяют нагрузочным тестом (шаг 5.5), а не угадывают.

### deep Команды по частям
`ratelimit.average=1`, `ratelimit.period=1m`, `ratelimit.burst=3` — три числа лимитера. `x-lab: &lab` — якорь Compose, чтобы не повторять `image` и `networks` в каждом сервисе. `for i in 1 2 … ; do curl … -w "запрос $i -> HTTP %{http_code}\n" …; done` — серия запросов; `-D -` печатает заголовки ответа, `grep -iE` оставляет строки с нужными именами.

### deep Как ещё можно
- **Кого считаем:** `sourceCriterion.requestHeaderName=X-Api-Key` — лимит на каждый ключ API, `sourceCriterion.requestHost=true` — на каждое имя хоста, `ipStrategy.depth=N` — IP из `X-Forwarded-For` (нужно, если перед Traefik стоит ещё прокси, шаг 9.4).
- **Лимиты по зонам:** разные `rateLimit` на разные роутеры: строгий на `/login`, мягкий на `/menu`.
- **Хранение состояния:** счётчики хранятся **в памяти каждого Traefik** — при нескольких копиях Traefik лимиты считаются у каждой независимо (общий лимит делают на Redis/внешнем шлюзе, а не в Traefik).

### deep Если не получилось
- **Все 8 запросов прошли с `200`** — лимит не применился: проверь, что middleware подключён к роутеру (`middlewares=s5-rl-limit,s5-rl-strip`) и что `period` записан как `1m`, а не `1`.
- **Сразу `404`** — не запущен проект `edge` или не создана сеть `proxy`; образ `coffeeshop-api` нужно собрать (шаг 1.5).
- **`429` на самый первый запрос** — до тебя этот лимитер уже исчерпали (например, повторный запуск опыта): подожди минуту или пересоздай контейнер (`docker compose -f compose.s5a.yaml up -d --force-recreate rl`).

### quiz
- Что означают `average`, `period` и `burst` и как они связаны с ведром жетонов?
- Какой ответ получит клиент при превышении лимита и как он узнает, когда повторять?
- Почему лимит в Traefik нельзя считать общим для всех копий Traefik?

### links
- https://doc.traefik.io/traefik/middlewares/http/ratelimit/ | RateLimit | Traefik: RateLimit
- https://developer.mozilla.org/ru/docs/Web/HTTP/Status/429 | код 429 | MDN: 429 Too Many Requests

## 5.2 inFlightReq и ipAllowList | short: inFlightReq и ipAllowList | est: ~45 мин
### intro
**Слова шага:** *`inFlightReq`*, *параллельные запросы*, *`ipAllowList`*, *`sourceRange`*, *CIDR*, *`ipWhiteList` (в v2)*, *`403 Forbidden`*.

:::tip Если совсем просто
`rateLimit` считает, **сколько приходит за секунду**. `inFlightReq` считает, **сколько обрабатывается одновременно**: «у меня две кассы, третий — подождите». А `ipAllowList` — **список допущенных по адресам**: «пускаем только своих».
:::

**`inFlightReq`** ограничивает число запросов, которые **одновременно выполняются**. Это защита от долгих запросов, которые забивают сервис: десять «тяжёлых» отчётов одновременно — и обычные запросы стоят. Сверх лимита — `429`.

**`ipAllowList`** (в Traefik **v3** — именно так; в v2 он назывался `ipWhiteList`: старое имя v3 пока принимает, но считает устаревшим и пишет предупреждение `deprecated`) пускает только клиентов из перечисленных диапазонов адресов в записи **CIDR**: `192.168.0.0/16` («все адреса, начинающиеся с `192.168.`»), `10.0.0.0/8`, `203.0.113.7/32` (один адрес). Остальным — `403 Forbidden`. Опыт: запускаем три контейнера в отдельном файле:

```bash run
cd ~/traefik-lab/edge
docker compose -f compose.s5a.yaml down 2>&1 | tail -1
cat > compose.s5b.yaml <<'EOF'
name: s5b

services:
  inflight:
    image: coffeeshop-api
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.s5-inflight.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/inflight`)
      - traefik.http.routers.s5-inflight.entrypoints=web
      - traefik.http.routers.s5-inflight.middlewares=s5-inflight-limit,s5-inflight-strip
      - traefik.http.middlewares.s5-inflight-limit.inflightreq.amount=2
      - traefik.http.middlewares.s5-inflight-strip.stripprefix.prefixes=/inflight
      - traefik.http.services.s5-inflight.loadbalancer.server.port=3000
  allow:
    image: coffeeshop-api
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.s5-allow.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/allow`)
      - traefik.http.routers.s5-allow.entrypoints=web
      - traefik.http.routers.s5-allow.middlewares=s5-allow-ip,s5-allow-strip
      - traefik.http.middlewares.s5-allow-ip.ipallowlist.sourcerange=10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
      - traefik.http.middlewares.s5-allow-strip.stripprefix.prefixes=/allow
      - traefik.http.services.s5-allow.loadbalancer.server.port=3000
  deny:
    image: coffeeshop-api
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.s5-deny.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/deny`)
      - traefik.http.routers.s5-deny.entrypoints=web
      - traefik.http.routers.s5-deny.middlewares=s5-deny-ip,s5-deny-strip
      - traefik.http.middlewares.s5-deny-ip.ipallowlist.sourcerange=203.0.113.0/24
      - traefik.http.middlewares.s5-deny-strip.stripprefix.prefixes=/deny
      - traefik.http.services.s5-deny.loadbalancer.server.port=3000

networks:
  proxy:
    external: true
EOF
docker compose -f compose.s5b.yaml up -d 2>&1 | tail -1
sleep 4
echo "--- пять одновременных долгих запросов (по 1,5 с) при inFlightReq.amount=2:"
( for i in 1 2 3 4 5; do curl -s -o /dev/null -w '%{http_code}\n' 'http://whoami.shop.localhost/inflight/slow?ms=1500' & done; wait ) | sort | uniq -c
echo "--- ipAllowList: «свои» (частные сети) и «чужие» (203.0.113.0/24):"
curl -s -o /dev/null -w 'allow -> HTTP %{http_code}\n' http://whoami.shop.localhost/allow/health
curl -s -o /dev/null -w 'deny  -> HTTP %{http_code}\n' http://whoami.shop.localhost/deny/health
```

### result
```out auto
```

- `inFlightReq`: из пяти одновременных запросов **два** прошли (`200`), **три** получили `429`. Как только первые два закончились, следующие запросы снова проходят.
- `ipAllowList`: наш клиент приходит из частной сети Docker, поэтому в списке `10.0.0.0/8,172.16.0.0/12,192.168.0.0/16` он «свой» (`200`), а при списке `203.0.113.0/24` — «чужой» (`403`).

**Какой адрес видит Traefik?** Адрес **клиента, который соединился с Traefik** — в нашей схеме это адрес шлюза Docker-сети, а не твой «настоящий» IP: на Mac с Docker Desktop приходит адрес виртуальной машины Docker. В боевой схеме, когда запросы идут из интернета, виден настоящий адрес — **если** перед Traefik нет другого прокси. Если есть, нужны `ipStrategy` и `trustedIPs` (шаг 9.4).

### why
Три защитных механизма отвечают на **три разные беды**: `rateLimit` — слишком частые запросы, `inFlightReq` — слишком много одновременных (особенно долгих), `ipAllowList` — не те адреса. Их часто ставят вместе: админка — только с адресов офиса и не больше 5 запросов в секунду.

### deep Команды по частям
`( … & … ; wait ) | sort | uniq -c` — пять `curl` запускаются в фоне (`&`), `wait` ждёт всех, результаты кодов сортируются и подсчитываются. `docker compose -f compose.s5a.yaml down` — убрать предыдущий опыт, чтобы они не мешали друг другу.

### deep Как ещё можно
- **Исключения для админки:** `ipAllowList` + `basicAuth` в одной цепочке: сначала пускаем нужные сети, потом спрашиваем пароль.
- **`ipStrategy.excludedIPs`** — пропустить известные адреса прокси и взять первый «внешний» адрес из `X-Forwarded-For`.
- **Блок-лист (запретить конкретные адреса)** в самом Traefik делается через правило роутера: `!ClientIP(…)` (в v3 есть `ClientIP()` в правилах).

### deep Если не получилось
- **`429` для всех пяти запросов** — `amount` взят слишком маленький или запросы уже висели с прошлого раза; подожди 2–3 секунды и повтори.
- **`allow` вернул `403`** — адрес клиента вне перечисленных диапазонов (например, у Colima или OrbStack другой диапазон сети): посмотри адрес клиента командой `curl -s http://whoami.shop.localhost/allow/info | jq .remoteAddress` на другом роутере или в журнале доступа и добавь нужную подсеть.
- **В Traefik v2 тот же опыт назывался `ipwhitelist`** — в v3 это имя устарело: оно ещё работает, но в журнале появится предупреждение `deprecated`; в новых конфигурациях используй `ipallowlist`.

### quiz
- Чем `inFlightReq` отличается от `rateLimit`?
- Что означает запись `10.0.0.0/8` в `sourceRange`?
- Как называется `ipWhiteList` из Traefik v2 в v3?

### links
- https://doc.traefik.io/traefik/middlewares/http/inflightreq/ | InFlightReq | Traefik: InFlightReq
- https://doc.traefik.io/traefik/middlewares/http/ipallowlist/ | IPAllowList | Traefik: IPAllowList

## 5.3 retry и circuitBreaker | short: retry и circuitBreaker | est: ~55 мин
### intro
**Слова шага:** *`retry`*, *`attempts`*, *ошибка соединения*, *мёртвая реплика*, *`circuitBreaker`*, *`expression`*, *«разомкнутая цепь»*.

:::tip Если совсем просто
`retry` — «позвони ещё раз, если не дозвонился»: администратор у входа направил посетителя в кассу, а там заперто — он тут же отправляет к соседней. `circuitBreaker` — **автомат-предохранитель** в щитке: если сервис за стеной ломается слишком часто, автомат выбивает, и новые запросы туда не идут, пока он не «остынет». Так больному сервису дают передохнуть вместо того, чтобы добивать его запросами.
:::

```svg
@circuit-breaker
```

**`retry`** повторяет запрос к **другой** копии, если **не удалось соединиться** с выбранной: соединение отклонено, адрес недоступен, копия «мертва». Поле `attempts` — всего попыток (с первой). Чего он **не делает** (мы проверим на опыте): он не повторяет, если бэкенд **ответил** — даже ошибкой `500`/`503`; и не повторяет, если запрос **уже дошёл** до бэкенда, а соединение оборвалось после этого. Это делает ретрай Traefik безопаснее, чем у многих клиентских библиотек (шаг 5.6).

**`circuitBreaker`** следит за долей ошибок по условию (`expression`):

- `ResponseCodeRatio(500, 600, 0, 600) > 0.5` — доля ответов `5xx` больше половины;
- `NetworkErrorRatio() > 0.3` — доля сетевых ошибок больше 30%;
- `LatencyAtQuantileMS(50.0) > 100` — медианная задержка больше 100 мс.

Пока условие выполнено, цепь **разомкнута**: Traefik сам отвечает `503 Service Unavailable`, **не обращаясь к бэкенду**, в течение `fallbackDuration` (по умолчанию 10 с), затем пробует пропускать часть запросов и, если всё хорошо, замыкает цепь обратно.

Опыт с ретраем: за одним сервисом стоят **две копии** — рабочий API и «мёртвая» (контейнер, в котором ничего не слушает порт 3000, соединение с ним отклоняется). Round robin отправляет каждый второй запрос на мёртвую. Два роутера смотрят на одну и ту же пару: один с `retry`, другой без. Отдельный API с адресом `/flaky?rate=1` (всегда отвечает `503`) проверит предохранитель:

```bash run
cd ~/traefik-lab/edge
docker compose -f compose.s5b.yaml down 2>&1 | tail -1
cat > compose.s5c.yaml <<'EOF'
name: s5c

services:
  ok:
    image: coffeeshop-api
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.services.s5-pair.loadbalancer.server.port=3000
      - traefik.http.routers.s5-retry.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/retry`)
      - traefik.http.routers.s5-retry.entrypoints=web
      - traefik.http.routers.s5-retry.service=s5-pair
      - traefik.http.routers.s5-retry.middlewares=s5-retry-mw,s5-retry-strip
      - traefik.http.middlewares.s5-retry-mw.retry.attempts=3
      - traefik.http.middlewares.s5-retry-mw.retry.initialinterval=50ms
      - traefik.http.middlewares.s5-retry-strip.stripprefix.prefixes=/retry
      - traefik.http.routers.s5-noretry.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/noretry`)
      - traefik.http.routers.s5-noretry.entrypoints=web
      - traefik.http.routers.s5-noretry.service=s5-pair
      - traefik.http.routers.s5-noretry.middlewares=s5-noretry-strip
      - traefik.http.middlewares.s5-noretry-strip.stripprefix.prefixes=/noretry
  dead:
    image: alpine:3.22
    command: ["sleep", "3600"]
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.services.s5-pair.loadbalancer.server.port=3000
  breaker:
    image: coffeeshop-api
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.s5-cb.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/cb`)
      - traefik.http.routers.s5-cb.entrypoints=web
      - traefik.http.routers.s5-cb.middlewares=s5-cb-mw,s5-cb-strip
      - traefik.http.middlewares.s5-cb-mw.circuitbreaker.expression=ResponseCodeRatio(500, 600, 0, 600) > 0.5
      - traefik.http.middlewares.s5-cb-mw.circuitbreaker.fallbackduration=20s
      - traefik.http.middlewares.s5-cb-strip.stripprefix.prefixes=/cb
      - traefik.http.services.s5-cb.loadbalancer.server.port=3000

networks:
  proxy:
    external: true
EOF
docker compose -f compose.s5c.yaml up -d 2>&1 | tail -1
sleep 5
count() { for i in $(seq 1 $2); do curl -s -o /dev/null -w '%{http_code}\n' "$1"; done | sort | uniq -c | tr '\n' ' '; echo; }
echo "--- 60 запросов на пару «рабочая + мёртвая копия» БЕЗ retry:"
count http://whoami.shop.localhost/noretry/health 60
echo "--- те же 60 запросов С retry (3 попытки):"
count http://whoami.shop.localhost/retry/health 60
echo "--- retry, но бэкенд обрывает соединение ПОСЛЕ получения запроса (/drop?rate=1), 20 запросов:"
count 'http://whoami.shop.localhost/retry/drop?rate=1' 20
echo "--- circuitBreaker: бэкенд на каждый запрос отвечает 503 (/flaky?rate=1), 30 запросов; тело ответа:"
for i in $(seq 1 30); do curl -s 'http://whoami.shop.localhost/cb/flaky?rate=1' | cut -c1-30; done | sort | uniq -c
```

### result
```out auto
```

Читаем:

- **Без retry** — каждый второй запрос (`502 Bad Gateway`) попадает на мёртвую копию: Traefik не смог с ней соединиться.
- **С retry** — все `200`: соединиться с мёртвой не вышло, и Traefik тут же повторил запрос на вторую, рабочую. Клиент ничего не заметил.
- **retry, но обрыв после получения запроса** — по-прежнему `502`: запрос уже дошёл до API, поэтому Traefik его **не повторяет** (иначе действие могло бы выполниться дважды). Ретрай лечит «не дозвонились», но не «дозвонились, а дальше сломалось».
- **circuitBreaker** — первые запросы дошли до API (тело `{"error":"flaky"}`), как только доля `5xx` превысила 50%, цепь разомкнулась: дальше Traefik сам отвечает текстом `Service Unavailable`, **не заходя в API**. Именно по телу ответа видно, кто отвечал.

Числа в разделении «доли ответов» у тебя будут близкие, но не обязательно такие же.

### why
Ретраи и предохранитель — «страховка от нестабильного бэкенда», и важно понимать, **от чего именно** они страхуют. Ретрай прячет **недоступную копию** (мёртвый контейнер, перезапуск при выкатке). Предохранитель не лечит, а даёт больному сервису передышку и быстрее отвечает клиентам ошибкой вместо долгого ожидания. Причину надо искать в самом сервисе.

### deep Команды по частям
`count() { for i in $(seq 1 $2); do curl … "$1"; done | sort | uniq -c | tr '\n' ' '; echo; }` — функция: `$1` — адрес, `$2` — число запросов; коды ответов подсчитываются. `retry.attempts=3` — всего 3 попытки (первая + 2 повтора), `retry.initialinterval=50ms` — начальная пауза между попытками (растёт). У мёртвой копии метки сервиса те же, но нет роутера: она входит в тот же сервис `s5-pair` как «ещё один адрес». `circuitbreaker.expression=…` — условие размыкания; `fallbackduration` — сколько цепь остаётся разомкнутой. `cut -c1-30` — оставить первые 30 символов тела ответа.

### deep Как ещё можно
- **`disableRetryOnNetworkError`** — отключить повтор при сетевых ошибках (полезно, если не хочешь, чтобы Traefik вообще что-то повторял).
- **Healthcheck вместо ретрая:** мёртвую копию лучше **исключить заранее** проверкой здоровья (шаг 6.2): тогда на неё не попадёт ни один запрос, а ретрай остаётся страховкой на время между проверками.
- **Условия предохранителя:** `NetworkErrorRatio() > 0.30 || LatencyAtQuantileMS(50.0) > 100` — условия можно комбинировать.

### deep Если не получилось
- **Без retry вышли почти все `200`** — мёртвая копия не попала в сервис: проверь, что у обоих контейнеров одинаковое имя сервиса `s5-pair` (дашборд → Services).
- **Цепь не размыкается** — слишком мало запросов или условие мягкое: уменьши порог (`> 0.3`) или добавь запросов.
- **Все запросы сразу `Service Unavailable`** — цепь уже разомкнута с прошлого запуска; подожди `fallbackduration` (20 секунд) и повтори.

### quiz
- В каком случае `retry` повторяет запрос, а в каком нет?
- Что делает Traefik, когда цепь `circuitBreaker` разомкнута, и как это видно по телу ответа?
- Почему ретрай и предохранитель — не замена починке самого сервиса?

### links
- https://doc.traefik.io/traefik/middlewares/http/retry/ | Retry | Traefik: Retry
- https://doc.traefik.io/traefik/middlewares/http/circuitbreaker/ | CircuitBreaker | Traefik: CircuitBreaker

## 5.4 forwardAuth: внешняя проверка доступа | short: forwardAuth | est: ~50 мин
### intro
**Слова шага:** *`forwardAuth`*, *сервис авторизации*, *`authResponseHeaders`*, *`Authorization: Bearer`*, *`401` / `403`*, *единая точка входа (SSO)*.

:::tip Если совсем просто
У `basicAuth` пароли записаны прямо в вахтёре. Когда пользователей много и проверка сложная (токены, роли, «а не заблокирован ли он»), вахтёр **звонит в отдел безопасности**: «этот человек проходит?» Отдел отвечает «да» (и сообщает, кто он) или «нет». Это `forwardAuth`: Traefik пересылает заголовки запроса отдельному сервису, и тот решает.
:::

```svg
@forward-auth
```

Схема: клиент → Traefik. Прежде чем пустить запрос к сервису, Traefik **делает отдельный запрос** на адрес `forwardAuth.address`, передавая заголовки исходного запроса. Если сервис авторизации ответил **`2xx`** — запрос идёт дальше (а заголовки, перечисленные в `authResponseHeaders`, добавляются, например `X-User`). Любой другой ответ (`401`, `403`, `302`…) Traefik отдаёт клиенту **как есть**, и сервис за ним не видит запроса.

Напишем крошечный сервис авторизации на Node: он принимает `Authorization: Bearer coffee-token`, остальным отвечает `401`. В реальности тут была бы проверка токена, пользователя, ролей:

```bash run
docker compose -f compose.s5c.yaml down 2>&1 | tail -1
mkdir -p ~/traefik-lab/auth && cd ~/traefik-lab/auth
cat > server.js <<'EOF'
import http from 'node:http'

http.createServer((req, res) => {
  if (req.url !== '/verify') { res.statusCode = 404; return res.end() }
  if (req.headers.authorization === 'Bearer coffee-token') {
    res.setHeader('X-User', 'mira')           // кто это: Traefik передаст дальше
    res.statusCode = 200
    return res.end('ok')
  }
  res.statusCode = 401
  res.end('нужен токен')
}).listen(3000, () => console.log('auth слушает :3000'))
EOF
cd ~/traefik-lab/edge
cat > compose.s5d.yaml <<'EOF'
name: s5d

services:
  fa-auth:
    image: node:24-alpine
    working_dir: /app
    command: ["node", "server.js"]
    volumes:
      - ../auth:/app:ro
    networks: [proxy]
  fa-app:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.s5-fa.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/fa`)
      - traefik.http.routers.s5-fa.entrypoints=web
      - traefik.http.routers.s5-fa.middlewares=s5-fa-auth
      - traefik.http.middlewares.s5-fa-auth.forwardauth.address=http://fa-auth:3000/verify
      - traefik.http.middlewares.s5-fa-auth.forwardauth.authresponseheaders=X-User

networks:
  proxy:
    external: true
EOF
docker compose -f compose.s5d.yaml up -d 2>&1 | tail -1
sleep 4
echo "--- без токена:"
curl -s -w ' (HTTP %{http_code})\n' http://whoami.shop.localhost/fa/
echo "--- с неверным токеном:"
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -H 'Authorization: Bearer wrong' http://whoami.shop.localhost/fa/
echo "--- с верным токеном (и заголовок X-User, который добавил Traefik):"
curl -s -H 'Authorization: Bearer coffee-token' http://whoami.shop.localhost/fa/ | grep -E '^(GET|X-User|Authorization)'
```

### result
```out auto
```

- Без токена и с неверным токеном сервис авторизации отвечает `401 Unauthorized` с телом `нужен токен` — **это его ответ**, Traefik просто передал его клиенту; `whoami` запроса не увидел.
- С верным токеном — `200`, запрос дошёл до `whoami`, а в нём появился заголовок **`X-User: mira`**, который прислал сервис авторизации. Приложению не нужно разбирать токен: оно доверяет `X-User` (при условии, что снаружи этот заголовок подделать нельзя — Traefik сам подставляет его **после** проверки).

### why
`forwardAuth` — путь от «пароли в метках» к настоящей авторизации: единая проверка для всех сервисов, SSO (единый вход) через внешнего провайдера (Authelia, Keycloak, OAuth2 Proxy — они умеют отвечать на запросы вида `/verify`). Приложения за Traefik вообще не знают, как проверяется доступ.

### deep Команды по частям
`import http from 'node:http'` — встроенный модуль HTTP-сервера (без зависимостей). `volumes: ../auth:/app:ro` — папка `auth` монтируется только на чтение. `forwardauth.address` — куда Traefik отправляет проверочный запрос; `authresponseheaders` — какие заголовки ответа авторизации скопировать в исходный запрос. `grep -E '^(GET|X-User|Authorization)'` — показать только нужные строки ответа `whoami`.

### deep Как ещё можно
- **`authRequestHeaders`** — передавать сервису авторизации только перечисленные заголовки (по умолчанию уходят все).
- **`trustForwardHeader`** — доверять входящему `X-Forwarded-*` (нужно за другим прокси).
- **Вход через браузерную форму:** сервис авторизации может отвечать `302` на страницу входа — Traefik передаст редирект клиенту.
- **`authResponseHeadersRegex`** — копировать группу заголовков по регулярному выражению (например, `^X-Auth-`).

### deep Если не получилось
- **`500`/`502` на `/fa/`** — Traefik не достучался до сервиса авторизации: проверь `docker compose logs fa-auth` и что он в сети `proxy`.
- **Верный токен даёт `401`** — токен в заголовке записан иначе (регистр слова `Bearer`, лишний пробел).
- **Нет заголовка `X-User` у `whoami`** — не указано `authresponseheaders=X-User` или сервис авторизации его не прислал.

### quiz
- Что делает Traefik при `forwardAuth` и какие ответы сервиса авторизации пропускают запрос дальше?
- Откуда у `whoami` берётся заголовок `X-User`?
- Почему приложение может доверять `X-User`?

### links
- https://doc.traefik.io/traefik/middlewares/http/forwardauth/ | ForwardAuth | Traefik: ForwardAuth
- https://www.authelia.com/integration/proxies/traefik/ | Authelia + Traefik | Authelia: Traefik

## 5.5 Нагрузочная проверка с k6 | short: Нагрузка с k6 | est: ~50 мин
### intro
**Слова шага:** *`k6`*, *виртуальные пользователи (VU)*, *`constant-arrival-rate`*, *`http_req_failed`*, *`p(95)`*, *перцентиль*.

:::tip Если совсем просто
Лимит `20 запросов в секунду` — просто число, пока ты не проверила, что происходит на самом деле. Нагрузочный тест — **«толпа покупателей»**, которую запускаешь по расписанию и считаешь: сколько обслужили, сколько получили отказ, как быстро.
:::

**k6** — инструмент нагрузочных тестов (если ты проходила Laravel Performance Lab, он тебе знаком). Скрипт на JavaScript описывает «сценарий»: сколько запросов в секунду, сколько времени, что считать успехом. Установка на Mac: `brew install k6`.

Поставим на API CoffeeShop лимит: **20 запросов в секунду, всплеск до 40**, и посмотрим, что делает с ним нагрузка **100 запросов в секунду** на 5 секунд. Добавляем лимитер в проект CoffeeShop: новый файл `compose.s5.yaml` и его имя в конец строки `COMPOSE_FILE` в `.env`:

```bash run
cd ~/traefik-lab/edge && docker compose -f compose.s5d.yaml down 2>&1 | tail -1
cd ~/traefik-lab/coffeeshop
cat > compose.s5.yaml <<'EOF'
services:
  api:
    labels:
      - traefik.http.routers.coffee-api.middlewares=coffee-strip,coffee-limit
      - traefik.http.middlewares.coffee-limit.ratelimit.average=20
      - traefik.http.middlewares.coffee-limit.ratelimit.burst=40
      - traefik.http.middlewares.coffee-limit.ratelimit.period=1s
EOF
sed 's|^COMPOSE_FILE=.*|&:compose.s5.yaml|' .env > .env.new && mv .env.new .env
grep COMPOSE_FILE .env
docker compose up -d 2>&1 | tail -2
mkdir -p ~/traefik-lab/k6 && cd ~/traefik-lab/k6
cat > load.js <<'EOF'
import http from 'k6/http'
import { Counter } from 'k6/metrics'

const ok = new Counter('ok_200')
const limited = new Counter('limited_429')

export const options = {
  hosts: { 'shop.localhost': __ENV.TARGET_IP || '127.0.0.1' },   // как «имя → адрес», на Mac это 127.0.0.1
  scenarios: {
    crowd: {
      executor: 'constant-arrival-rate',
      rate: 100, timeUnit: '1s', duration: '5s',
      preAllocatedVUs: 20, maxVUs: 50,
    },
  },
}

export default function () {
  const r = http.get('http://shop.localhost/api/menu')
  if (r.status === 200) ok.add(1)
  if (r.status === 429) limited.add(1)
}
EOF
sleep 3
k6 run --quiet load.js 2>&1 | grep -E 'ok_200|limited_429|http_req_failed|http_reqs|http_req_duration' | sed -E 's/ +/ /g'
```

### result
```out auto
```

Читаем итог:

- **`http_reqs`** — всего запросов (около 500: 100 в секунду × 5 секунд).
- **`ok_200` и `limited_429`** — сколько обслужили и сколько отказали. Допустимое — около `20 × 5 + 40 = 140`; остальные `429`.
- **`http_req_failed`** — доля «неуспешных»: **k6 считает `429` ошибкой**, поэтому она большая. Это не поломка сервиса, а работа лимитера: всегда сверяйся с разбивкой по кодам, а не только с общей долей.
- **`http_req_duration`** — время ответа; `p(95)` означает «95% запросов быстрее этого значения» (перцентиль), по нему судят о задержках лучше, чем по среднему. Отказ `429` отдаётся очень быстро, поэтому среднее время может быть даже меньше обычного.

Числа у тебя будут другими (скорость ноутбука, Docker Desktop), но картина та же: лишнюю нагрузку Traefik срезает на входе, API её не видит. Если на твоём компьютере k6 не может найти имя, в сценарии стоит `hosts` — подмена имени на `127.0.0.1`; на Mac с обычным Docker Desktop это работает.

### why
Это приёмка сессии 5 по первому пункту: **лишняя нагрузка получает `429`**. Но главный навык шага — не «запустить k6», а **читать результат**: смотреть на коды ответов, `http_req_failed`, `p(95)`, а не только на «зелёные галочки». Лимит из головы (20/сек) — гипотеза, которую проверяют нагрузкой; если реальные пользователи придут быстрее, они увидят `429`.

### deep Команды по частям
`k6 run --quiet load.js` — запустить сценарий без интерактивной шкалы. `constant-arrival-rate` — «приходит ровно `rate` запросов в `timeUnit`» (в отличие от «N пользователей, которые ходят непрерывно»), `preAllocatedVUs`/`maxVUs` — сколько виртуальных пользователей держать наготове. `new Counter('…')` — свой счётчик; `grep -E '…' | sed -E 's/ +/ /g'` — оставить нужные строки итога и сжать пробелы. Переменная `TARGET_IP` в сценарии не нужна на Mac (по умолчанию `127.0.0.1`); её использует стенд, на котором прогонялась методичка.

### deep Как ещё можно
- **`hey`** (`brew install hey`): `hey -z 5s -q 100 http://shop.localhost/api/menu` — то же одной командой, без скрипта.
- **`ab` (ApacheBench)** — старый, есть в системе: `ab -n 500 -c 20 http://shop.localhost/api/menu`.
- **`wrk`** — быстрый, но сложнее ставится; подходит для высокой нагрузки.
- **Пороги в k6:** `thresholds: { http_req_failed: ['rate<0.01'] }` — тест «падает», если ошибок больше 1% (удобно в CI).

### deep Если не получилось
- **`ok_200` равно нулю** — `shop.localhost` не разрешается в k6: проверь `hosts` в `options` и что стек CoffeeShop работает (`curl http://shop.localhost/api/menu`).
- **Все ответы `200`, `429` нет** — лимитер не подключён: проверь, что в `.env` проекта `coffeeshop` в `COMPOSE_FILE` есть `compose.s5.yaml`, и `docker compose up -d` выполнялся после.
- **Ноутбук греется** — это нормально для k6 на 100 запросов в секунду; в этой сессии нагрузка короткая (5 секунд).

### quiz
- Что означает `constant-arrival-rate` и чем он отличается от «N пользователей»?
- Почему `http_req_failed` в этом опыте большой и что нужно смотреть кроме неё?
- Что такое `p(95)` и почему он информативнее среднего?

### links
- https://grafana.com/docs/k6/latest/ | документация k6 | k6 docs
- https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/constant-arrival-rate/ | constant-arrival-rate | k6: constant-arrival-rate

## 5.6 🔨 Повтор небезопасного запроса: двойной заказ | short: 🔨 Двойной заказ | est: ~50 мин
### intro
**Слова шага:** *идемпотентность*, *повтор небезопасного запроса*, *двойной заказ*, *`Idempotency-Key`*, *`--retry-all-errors`*.

:::tip Если совсем просто
«Повторить звонок» безопасно, если спрашиваешь «сколько времени?». Но если ты диктуешь заказ пиццы, связь оборвалась **после того, как его записали**, а ты перезвонила и продиктовала снова — получишь две пиццы. Опасен не столько прокси, сколько **клиент, который повторяет на всякий случай** (мобильное приложение, библиотека HTTP). Запросы бывают «безопасно повторяемые» (**идемпотентные**) и нет.
:::

Мы убедились в шаге 5.3, что Traefik сам не повторяет запрос, который уже дошёл до бэкенда. Но клиенты повторяют: у `curl` есть `--retry-all-errors`, у мобильных приложений и SDK — свои повторы. Сломаем это нарочно. У нашего API для опытов есть режим `POST /orders?drop=after`: он **записывает заказ в базу, а затем обрывает соединение** — как будто сеть мигнула уже после выполнения. Клиент видит ошибку и «разумно» повторяет запрос трижды:

```bash run
cd ~/traefik-lab/coffeeshop
before=$(curl -s http://shop.localhost/api/orders | jq length)
echo "заказов до: $before"
curl -s -o /dev/null -X POST -H 'Content-Type: application/json' -d '{"menu_id":1}' \
  --retry 3 --retry-delay 0 --retry-all-errors 'http://shop.localhost/api/orders?drop=after'
after=$(curl -s http://shop.localhost/api/orders | jq length)
echo "заказов после: $after  (клиент «отправил один заказ» и повторил его при ошибке)"
```

### result
```out auto
```

Один «заказ», а в базе их **четыре** (первая попытка и три повтора): каждая попытка дошла до API и создала строку, но ответ не пришёл, поэтому клиент повторял. Traefik тут ни при чём — он передавал запросы, а дублирование вызвано тем, что `POST` не идемпотентен, а клиент повторял его слепо.

**Починка — ключ идемпотентности.** Клиент присылает уникальный идентификатор операции в заголовке `Idempotency-Key`. Сервер при повторе с тем же ключом **не создаёт второй заказ**, а возвращает уже созданный. В нашем API это уже сделано: у таблицы `orders` есть столбец `idem_key` с ограничением уникальности, а `POST /orders` смотрит на заголовок. Повторим тот же сценарий, но с ключом:

```bash run
cd ~/traefik-lab/coffeeshop
before=$(curl -s http://shop.localhost/api/orders | jq length)
echo "заказов до: $before"
curl -s -o /dev/null -X POST -H 'Content-Type: application/json' -H 'Idempotency-Key: order-2026-10-18-0001' -d '{"menu_id":1}' \
  --retry 3 --retry-delay 0 --retry-all-errors 'http://shop.localhost/api/orders?drop=after'
after=$(curl -s http://shop.localhost/api/orders | jq length)
echo "заказов после: $after  (тот же сценарий с Idempotency-Key)"
```

```out auto
```

Теперь четыре попытки дали **один** заказ: первая записала строку с ключом, повторы упёрлись в уникальность ключа и получили тот же заказ. Ответ клиенту по-прежнему обрывается (режим `drop=after` рвёт соединение каждый раз), но данные в порядке.

Памятка «можно ли повторять запрос»:

| Метод | Идемпотентен? | Повтор безопасен? |
|---|---|---|
| `GET`, `HEAD`, `OPTIONS` | да | да |
| `PUT`, `DELETE` | да (по смыслу) | как правило да |
| `POST`, `PATCH` | нет | **нет**, пока нет ключа идемпотентности |

Приёмка сессии 5 выполнена: лишняя нагрузка получает `429` (шаги 5.1 и 5.5), закрытая зона — `403` (5.2), мёртвая копия скрыта ретраем (5.3), а небезопасные повторы клиента закрыты ключом идемпотентности (5.6).

### why
Эта ошибка проходит все тесты (в тестах сеть не рвётся) и проявляется только в проде, когда сеть мигнула: клиентов списывают дважды, заказы дублируются. Привычка спрашивать «а что будет, если запрос выполнится дважды?» перед включением **любого** ретрая (в прокси, в клиентской библиотеке, в очереди сообщений) — одна из самых ценных во всей лабе. Платёжные API (Stripe и другие) требуют `Idempotency-Key` именно поэтому.

### deep Команды по частям
`curl --retry 3 --retry-delay 0 --retry-all-errors` — повторить до трёх раз при **любой** ошибке (без `--retry-all-errors` `curl` повторяет только при ответах `408`/`429`/`5xx` и таймаутах, но не при обрыве соединения), без пауз. `jq length` — число элементов JSON-массива (заказов). В API ключ работает так: `INSERT … ON CONFLICT (idem_key) DO NOTHING` — если такой ключ уже есть, вставка молча пропускается, затем API читает уже созданный заказ.

### deep Как ещё можно
- **Ключ из контекста:** вместо случайного `Idempotency-Key` можно использовать естественный идентификатор (номер корзины), если он уникален для операции.
- **Срок хранения ключей:** в серьёзных API ключи хранят ограниченное время (сутки) и сверяют тело запроса: тот же ключ с другим телом — ошибка.
- **`disableRetryOnNetworkError` в Traefik** — на случай, если не хочешь вообще никаких повторов на стороне прокси.

### deep Если не получилось
- **После опыта без ключа заказов добавилось меньше четырёх** — часть попыток могла не дойти; важно, что их больше одного.
- **С ключом заказов добавилось четыре** — в твоём API нет обработки `Idempotency-Key`: сверь `api/server.js` и `db/init.sql` с шагом 1.5 (столбец `idem_key` в `orders` и `ON CONFLICT`). Для уже созданной базы столбец нужно добавить: `ALTER TABLE orders ADD COLUMN idem_key text UNIQUE`.
- **Лишние заказы мешают** — для чистоты можно очистить таблицу: `docker compose exec db psql -U coffee -d coffee -c 'TRUNCATE orders'`.

### quiz
- Почему повтор `POST` без ключа может создать несколько заказов?
- Как работает `Idempotency-Key` и что делает сервер при повторе с тем же ключом?
- Какие методы безопасно повторять без ключа, а какие нет?

### links
- https://developer.mozilla.org/ru/docs/Glossary/Idempotent | идемпотентность | MDN: идемпотентность
- https://docs.stripe.com/api/idempotent_requests | Idempotency-Key | Stripe: идемпотентные запросы
