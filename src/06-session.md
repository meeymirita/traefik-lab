# Сессия 6 · Балансировка и выкатка
dur: ~4 ч

## 6.1 Несколько копий сервиса и round robin | short: Несколько копий | est: ~40 мин
### intro
**Слова шага:** *реплика*, *балансировщик нагрузки*, *round robin*, *`--scale`*, *сервис с несколькими адресами*.

:::tip Если совсем просто
Одна касса на весь магазин — очередь. Открываем три кассы, а администратор у входа направляет каждого следующего покупателя к следующей кассе по кругу: первый — в первую, второй — во вторую, третий — в третью, четвёртый — снова в первую. Это **round robin** («по кругу»), и Traefik делает это сам, как только видит несколько контейнеров одного сервиса.
:::

```svg
@load-balancer
```

Раньше у каждого сервиса был один контейнер — один «адрес» за роутером. Теперь запустим **три копии** API (их называют *репликами*). Заводить новые роутеры не нужно: Traefik видит, что у сервиса `coffee-api` теперь несколько контейнеров с одинаковыми метками, и сам распределяет запросы между ними. Compose умеет запускать нужное число копий флагом `--scale`:

```bash run
cd ~/traefik-lab/coffeeshop
docker compose up -d --scale api=3 2>&1 | tail -4
sleep 6
tapi() { curl -s -u mira:coffee-secret "http://traefik.shop.localhost/api/$1"; }
echo "--- адреса сервиса coffee-api глазами Traefik:"
tapi http/services/coffee-api@docker | jq -r '.loadBalancer.servers[].url' | sort
echo "--- 30 запросов: кто отвечал?"
for i in $(seq 1 30); do curl -s http://shop.localhost/api/info | jq -r .hostname; done | sort | uniq -c
```

### result
```out auto
```

В сервисе теперь **три адреса** (по IP каждого контейнера), а 30 запросов распределились поровну: по 10 на каждую реплику (имена — это идентификаторы контейнеров, у тебя будут другие). Мы не меняли ни роутер, ни Traefik — лишь запустили больше копий.

Запись `--scale api=3` годится для опытов. Чтобы три копии запускались всегда, в Compose пишут `deploy.replicas: 3` — так мы поступим в следующем шаге.

### why
Балансировка — главная причина, по которой «один вход» вообще нужен: сервис можно масштабировать **горизонтально** (больше копий), не меняя клиентов, и временно выключать копии для обновления. Стандартный режим Traefik — *weighted round robin* с одинаковыми весами; кроме него есть «липкие» сессии (6.3) и ручные веса (6.4).

### deep Команды по частям
`docker compose up -d --scale api=3` — запустить сервис `api` в трёх экземплярах (остальные сервисы не меняются). Функция `tapi()` — маленькая обёртка: запрос к API Traefik с паролем из шага 4.6 (дашборд теперь закрыт паролем). `jq -r '.loadBalancer.servers[].url'` — список адресов сервиса. `for i in $(seq 1 30); do …; done | sort | uniq -c` — 30 запросов, затем подсчёт, сколько раз встретилось каждое имя.

### deep Как ещё можно
- **Постоянное число реплик:** `deploy: { replicas: 3 }` в `compose.yaml` — тогда `docker compose up -d` всегда держит три копии.
- **Docker Swarm и Kubernetes** делают то же на уровне оркестратора; Traefik видит копии так же — по меткам или по ресурсам Kubernetes.
- **Имена контейнеров:** при `--scale` у сервиса не должно быть `container_name` — имена должны быть разными.

### deep Если не получилось
- **Адрес один, а не три** — Traefik не успел увидеть новые контейнеры; подожди 5–10 секунд и повтори запрос к API.
- **`Conflict. The container name … is already in use`** — у сервиса задан `container_name`: убери его.
- **Распределение неровное (например, 12/9/9)** — в этом нет ошибки: порядок зависит от момента запуска; на большом числе запросов доли выравниваются.
- **`429` на часть запросов** — это лимитер из шага 5.5 (20 запросов в секунду); добавь `sleep 0.1` между запросами.

### quiz
- Что такое реплика и откуда Traefik знает, что их несколько?
- Как работает round robin и почему ни роутер, ни Traefik не пришлось менять?
- Чем `--scale` отличается от `deploy.replicas`?

### links
- https://doc.traefik.io/traefik/routing/services/#load-balancing | балансировка | Traefik: load balancing
- https://docs.docker.com/reference/cli/docker/compose/up/ | docker compose up | docker compose up

## 6.2 Healthcheck: исключаем больную копию | short: Healthcheck | est: ~50 мин
### intro
**Слова шага:** *healthcheck*, *`healthcheck.path`*, *`interval`*, *`timeout`*, *`serverStatus`*, *«больной» экземпляр*.

:::tip Если совсем просто
Администратор у входа раз в пару секунд заглядывает в каждую кассу: «вы работаете?». Если касса не отвечает, он перестаёт направлять к ней покупателей — пока она не оправится. Без этого каждый третий покупатель встречал бы закрытое окошко.
:::

Балансировщик без проверок направляет запросы **и на сломанные копии**: каждая третья попытка заканчивается ошибкой. **Healthcheck** («проверка здоровья») — периодический запрос Traefik к каждой копии: если ответ `2xx`/`3xx`, копия здорова, иначе её **временно исключают** из ротации и продолжают проверять, пока она не вернётся. Включается метками сервиса:

- `healthcheck.path=/health` — какой адрес опрашивать (адрес самой копии, **без** срезания префикса);
- `healthcheck.interval=2s` — как часто;
- `healthcheck.timeout=1s` — сколько ждать ответа.

Включим проверку для API и закрепим три копии в файле, а затем «заразим» одну копию — для этого у API есть адрес `POST /sick`:

```bash run
cd ~/traefik-lab/coffeeshop
cat > compose.s6.yaml <<'EOF'
services:
  api:
    deploy:
      replicas: 3
    labels:
      - traefik.http.services.coffee-api.loadbalancer.healthcheck.path=/health
      - traefik.http.services.coffee-api.loadbalancer.healthcheck.interval=2s
      - traefik.http.services.coffee-api.loadbalancer.healthcheck.timeout=1s
EOF
sed 's|^COMPOSE_FILE=.*|&:compose.s6.yaml|' .env > .env.new && mv .env.new .env
docker compose up -d 2>&1 | tail -3
sleep 6
tapi() { curl -s -u mira:coffee-secret "http://traefik.shop.localhost/api/$1"; }
echo "--- заражаем копию №2 (POST /sick прямо в контейнер, минуя Traefik):"
docker compose exec --index 2 api node -e "fetch('http://localhost:3000/sick', {method: 'POST'}).then(r => r.text()).then(console.log)"
sleep 5
echo "--- состояние адресов (UP / DOWN):"
tapi http/services/coffee-api@docker | jq -r '.serverStatus | to_entries[] | [.key, .value] | @tsv' | sort
echo "--- 30 запросов: кто отвечал?"
for i in $(seq 1 30); do curl -s http://shop.localhost/api/info | jq -r .hostname; done | sort | uniq -c
```

### result
```out auto
```

Один из трёх адресов получил статус **`DOWN`**, и теперь запросы идут только на две здоровые копии: по 15 на каждую. Ни одного запроса к больной копии, ни одной ошибки у клиента. Вылечим копию и убедимся, что она вернулась в ротацию:

```bash run
cd ~/traefik-lab/coffeeshop
docker compose exec --index 2 api node -e "fetch('http://localhost:3000/heal', {method: 'POST'}).then(r => r.text()).then(console.log)"
sleep 5
for i in $(seq 1 30); do curl -s http://shop.localhost/api/info | jq -r .hostname; done | sort | uniq -c
```

```out auto
```

Снова три копии, запросы разделились почти поровну (в нашем прогоне 11, 10 и 9: порядок круга зависит от момента, когда копия вернулась): Traefik сам заметил, что `/health` вернул `200`, и вернул копию в ротацию. Вручную ничего включать не пришлось.

### why
Healthcheck превращает отказ одной копии из «каждый третий клиент видит ошибку» в «никто ничего не замечает». Это основа надёжности: без проверки балансировщик только **распределяет** нагрузку, а с проверкой — **защищает** от неисправных копий.

### deep Команды по частям
`docker compose exec --index 2 api node -e "…"` — выполнить команду внутри второй копии сервиса `api`; `fetch` — встроенный в Node 24 HTTP-клиент, `localhost:3000` — это сам контейнер (мимо Traefik). `jq -r '.serverStatus | to_entries[] | [.key, .value] | @tsv'` — таблица «адрес — статус» из словаря. `deploy.replicas: 3` фиксирует число копий в файле.

### deep Как ещё можно
- **Healthcheck самого Docker:** `healthcheck:` в `compose.yaml` — другая проверка (Docker перезапускает или помечает контейнер), и она не заменяет проверку Traefik: у Traefik цель — **исключить** копию из балансировки.
- **Другие параметры:** `healthcheck.scheme`, `healthcheck.port` (опрашивать другой порт), `healthcheck.hostname`, `healthcheck.headers`, `healthcheck.status` (ожидаемый код ответа).
- **Лёгкий `/health`:** адрес должен быть быстрым и независимым от тяжёлых зависимостей, иначе медленная база «выключит» все копии сразу.

### deep Если не получилось
- **Статус всех адресов `UP`** — Traefik ещё не успел опросить (подожди 3–5 секунд) или `healthcheck.path` указан неверно; сверь метку в карточке сервиса в дашборде.
- **Все копии `DOWN`** — путь `/health` на твоём API не отвечает `2xx`; проверь `curl` в контейнер напрямую (`docker compose exec api node -e "fetch('http://localhost:3000/health').then(r=>console.log(r.status))"`).
- **`--index 2` — ошибка `no container found`** — реплик меньше двух: проверь `docker compose ps api`.

### quiz
- Что делает Traefik с копией, которая не прошла healthcheck, и когда она возвращается?
- Почему путь для `healthcheck` берётся без срезания префикса?
- Чем проверка Traefik отличается от `healthcheck` в Compose?

### links
- https://doc.traefik.io/traefik/routing/services/#health-check | health check | Traefik: health check
- https://docs.docker.com/reference/compose-file/services/#healthcheck | healthcheck в Compose | Compose: healthcheck

## 6.3 Липкие сессии (sticky) | short: Sticky sessions | est: ~40 мин
### intro
**Слова шага:** *sticky session*, *cookie*, *`sticky.cookie.name`*, *состояние на сервере*, *`httpOnly`*, *`secure`*.

:::tip Если совсем просто
Обычно покупатель идёт к любой свободной кассе. Но если у кассира **записана ваша корзина в блокнот**, возвращаться нужно к тому же кассиру. «Липкая сессия» — это браслет на руке покупателя: «вас обслуживает касса №2». Браслет — cookie, которую выдаёт Traefik.
:::

Если сервис хранит данные пользователя **в памяти копии** (корзина, сессия, незаконченная загрузка), то запросы одного пользователя должны всегда попадать на **ту же копию**. Это обеспечивают **sticky sessions**: Traefik при первом запросе выдаёт cookie с идентификатором копии и дальше, видя cookie, отправляет запросы туда же. Включается меткой `sticky.cookie.name`. Проверим на трёх копиях `whoami` (они показывают свой `Hostname`):

```bash run
cd ~/traefik-lab/edge
cat > compose.s63.yaml <<'EOF'
name: s63

services:
  who:
    image: traefik/whoami
    networks: [proxy]
    deploy:
      replicas: 3
    labels:
      - traefik.enable=true
      - traefik.http.routers.s63.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/sticky`)
      - traefik.http.routers.s63.entrypoints=web
      - traefik.http.services.s63.loadbalancer.server.port=80
      - traefik.http.services.s63.loadbalancer.sticky.cookie.name=shop_srv
      - traefik.http.services.s63.loadbalancer.sticky.cookie.httponly=true

networks:
  proxy:
    external: true
EOF
docker compose -f compose.s63.yaml up -d 2>&1 | tail -1
sleep 4
echo "--- 9 запросов БЕЗ cookie (каждый запрос — «новый покупатель»):"
for i in $(seq 1 9); do curl -s http://whoami.shop.localhost/sticky | grep -m1 '^Hostname'; done | sort | uniq -c
echo "--- заголовок Set-Cookie, который выдал Traefik:"
curl -s -c /tmp/jar.txt -o /dev/null -D - http://whoami.shop.localhost/sticky | grep -i '^set-cookie' | sed -E 's/(shop_srv=)[^;]+/\1…/'
echo "--- 9 запросов С cookie (один покупатель):"
for i in $(seq 1 9); do curl -s -b /tmp/jar.txt http://whoami.shop.localhost/sticky | grep -m1 '^Hostname'; done | sort | uniq -c
```

### result
```out auto
```

Без cookie запросы растекаются поровну по трём копиям. Ответ Traefik содержит `Set-Cookie: shop_srv=…; HttpOnly` — идентификатор копии. С этой cookie (`-b /tmp/jar.txt`) **все девять запросов попадают на одну копию**, как бы ни работал round robin.

У липких сессий есть цена: **нагрузка перестаёт выравниваться** (самые активные пользователи «прилипли» к своей копии), а при падении «своей» копии пользователь теряет данные (и переезжает на другую). Поэтому правильная архитектура — хранить состояние **вне копии** (в Redis или базе), а sticky оставлять для случаев, когда это невозможно.

### why
Sticky sessions — «костыль» для приложений, которые хранят состояние в памяти процесса. Знать про них нужно: ты встретишь такие приложения. Но если пишешь новое — состояние сессии клади в общее хранилище, и липкость не понадобится.

### deep Команды по частям
`curl -c /tmp/jar.txt` — сохранить cookie ответа в файл; `curl -b /tmp/jar.txt` — отправить cookie из файла. `sed -E 's/(shop_srv=)[^;]+/\1…/'` — скрыть значение cookie при показе. `sticky.cookie.name` — имя cookie; `sticky.cookie.httponly=true` — недоступна из JavaScript страницы.

### deep Как ещё можно
- **`sticky.cookie.secure=true`** — cookie выдаётся только по HTTPS (включим после сессии 7).
- **`sticky.cookie.samesite`**, **`maxage`** — ограничения для межсайтовых запросов и срок жизни cookie.
- **Балансировка по IP-хэшу** (nginx `ip_hash`) в Traefik отсутствует: используй cookie.

### deep Если не получилось
- **С cookie всё равно разные копии** — cookie не отправляется: проверь, что файл `/tmp/jar.txt` не пуст (`cat /tmp/jar.txt`) и что имя хоста запроса совпадает с тем, на котором cookie выдана.
- **`Hostname` один и без cookie** — `deploy.replicas: 3` не применился (старая версия Compose): запусти `docker compose -f compose.s63.yaml up -d --scale who=3`.

### quiz
- Для чего нужны sticky sessions и как Traefik запоминает копию?
- Какой недостаток у липких сессий и как его обойти в проектировании?
- Какое значение имеют флаги `httpOnly` и `secure` у такой cookie?

### links
- https://doc.traefik.io/traefik/routing/services/#sticky-sessions | sticky sessions | Traefik: sticky sessions
- https://developer.mozilla.org/ru/docs/Web/HTTP/Cookies | cookie | MDN: cookie

## 6.4 Weighted round robin: canary 90/10 | short: Canary | est: ~55 мин
### intro
**Слова шага:** *canary-выкатка*, *веса*, *`weighted`*, *файловый провайдер*, *`name@docker`*, *горячая перезагрузка*.

:::tip Если совсем просто
Канарейка в шахте: птицу пускают первой, чтобы проверить воздух. Так и с новой версией: сначала отправляем ей **малую долю** трафика (10%). Если всё хорошо — увеличиваем; если нет — возвращаем 0%, и пострадали единицы.
:::

```svg
@canary
```

Выкатывать новую версию сразу всем рискованно. **Canary** — когда старая и новая версии работают **одновременно**, а Traefik делит между ними трафик **по весам**. Для этого нужен специальный сервис типа `weighted` — он описывается **не метками, а файлом** (файловый провайдер из шага 4.5). Схема:

1. Две копии приложения как два **отдельных сервиса** Traefik: `canary-v1` (старая), `canary-v2` (новая) — их метки в Compose.
2. Файл `traefik/dynamic/canary.yml` описывает составной сервис `shop-canary` с весами.
3. Роутер ссылается на этот составной сервис: `routers.canary.service=shop-canary@file`.

Для опыта возьмём две `whoami`, которые называют себя `v1` и `v2` (`--name`):

```bash run
cd ~/traefik-lab/edge
docker compose -f compose.s63.yaml down 2>&1 | tail -1
cat > compose.s64.yaml <<'EOF'
name: s64

services:
  v1:
    image: traefik/whoami
    command: ["--name", "v1"]
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.services.canary-v1.loadbalancer.server.port=80
      - traefik.http.routers.canary.rule=Host(`canary.shop.localhost`)
      - traefik.http.routers.canary.entrypoints=web
      - traefik.http.routers.canary.service=shop-canary@file
  v2:
    image: traefik/whoami
    command: ["--name", "v2"]
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.services.canary-v2.loadbalancer.server.port=80

networks:
  proxy:
    external: true
EOF
cat > traefik/dynamic/canary.yml <<'EOF'
http:
  services:
    shop-canary:
      weighted:
        services:
          - name: canary-v1@docker
            weight: 90
          - name: canary-v2@docker
            weight: 10
EOF
docker compose -f compose.s64.yaml up -d 2>&1 | tail -1
sleep 5
share() { for i in $(seq 1 100); do curl -s http://canary.shop.localhost/ | grep -m1 '^Name'; done | sort | uniq -c | tr '\n' ' '; echo; }
echo "--- 100 запросов при весах 90 / 10:"
share
echo "--- меняем веса на 50 / 50 (правим файл, Traefik не перезапускаем):"
sed 's/weight: 90/weight: 50/; s/weight: 10/weight: 50/' traefik/dynamic/canary.yml > /tmp/canary.yml && cat /tmp/canary.yml > traefik/dynamic/canary.yml
sleep 3
share
```

### result
```out auto
```

При весах `90 / 10` из ста запросов около 90 ушло на `v1` и около 10 на `v2` (Traefik распределяет по весам практически точно). После правки файла на `50 / 50` — **без перезапуска Traefik** — доли выровнялись: файловый провайдер с `watch: true` подхватил изменение сразу.

**Как выкатывать на практике** (набросок): выкатил `v2` с весом `1–5`, смотришь на ошибки и задержки (метрики и журнал — сессия 10); всё хорошо — `10 → 25 → 50 → 100`; плохо — вес `0` на `v2`, пострадали единицы. Откат — одна правка файла.

### why
Canary и blue/green — главные приёмы **выкатки без простоя**. Пользователи не видят остановки сервиса, а плохая версия задевает лишь малую долю. И главное: **откат** — это не «развернуть всё обратно», а «поставить вес 0».

### deep Команды по частям
`weighted.services` — список «имя сервиса — вес»; `name: canary-v1@docker` ссылается на сервис, созданный метками Docker (суффикс обязателен — мы обращаемся из файлового провайдера к докеровскому). `share()` — функция: 100 запросов и подсчёт, сколько раз встретилось каждое `Name:`. `sed … > /tmp/canary.yml && cat /tmp/canary.yml > traefik/dynamic/canary.yml` — переписать файл **на месте** (не заменяя сам файл новым: монтирование Docker следит за тем же файлом, и `watch` срабатывает надёжнее).

### deep Как ещё можно
- **Canary по заголовку:** вместо долей — отдельный роутер ``Header(`X-Canary`, `1`)`` для тестировщиков (шаг 3.2) — новая версия только для тех, кто попросит.
- **Sticky внутри weighted:** чтобы один пользователь не «прыгал» между версиями, на составном сервисе включают `sticky.cookie` (иначе пользователь может видеть то v1, то v2).
- **Argo Rollouts и Flagger** в Kubernetes автоматизируют ту же схему по метрикам.

### deep Если не получилось
- **Всегда `v1`** — вес `v2` равен нулю, файл не подхвачен или не смонтирована папка `dynamic`; проверь в дашборде сервис `shop-canary@file`.
- **`404`** — не создался роутер `canary`: проверь, что `v1` имеет метку `traefik.enable=true` и сервис ссылается на `shop-canary@file` (с суффиксом).
- **После правки файла ничего не меняется (Docker Desktop на Mac)** — изменения смонтированных файлов иногда не доходят до контейнера сразу: перезапусти Traefik (`docker compose -f ../edge/compose.yaml restart traefik`) или подожди несколько секунд.

### quiz
- Как Traefik делит трафик между двумя версиями приложения и где задаются веса?
- Почему составной сервис описывается файлом, а не метками?
- Чем откат canary отличается от откатa «развернуть старую версию заново»?

### links
- https://doc.traefik.io/traefik/routing/services/#weighted-round-robin-service | weighted round robin | Traefik: weighted round robin
- https://martinfowler.com/bliki/CanaryRelease.html | canary release | Fowler: Canary Release

## 6.5 Mirroring: теневой трафик | short: Mirroring | est: ~40 мин
### intro
**Слова шага:** *mirroring*, *теневой трафик*, *`mirrors`*, *`percent`*, *побочные эффекты*, *нагрузочное тестирование на реальных данных*.

:::tip Если совсем просто
Mirroring — «кино на запись»: настоящие покупатели обслуживаются как обычно, а **копии их запросов** тихо уходят на новую версию, чтобы посмотреть, как она справилась. Ответы новой версии выбрасываются — покупатель их не видит.
:::

**Mirroring** («зеркалирование») пересылает **копию** части запросов на дополнительный сервис. Клиент получает ответ только от основного, ответ зеркала отбрасывается. Зачем: проверить новую версию на **реальном** трафике, не рискуя клиентами (смотрим на ошибки и время ответа новой версии). Описывается файлом: сервис типа `mirroring` с основным сервисом и списком `mirrors` с долями в процентах. Опыт: основной — `nginx` (счётчик запросов в его журнале), «тень» — второй `nginx`; считаем, сколько запросов получил каждый:

```bash run
cd ~/traefik-lab/edge
docker compose -f compose.s64.yaml down 2>&1 | tail -1
rm -f traefik/dynamic/canary.yml
cat > compose.s65.yaml <<'EOF'
name: s65

services:
  main:
    image: nginx:1.30-alpine
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.services.mir-main.loadbalancer.server.port=80
      - traefik.http.routers.mirror.rule=Host(`beta.shop.localhost`)
      - traefik.http.routers.mirror.entrypoints=web
      - traefik.http.routers.mirror.service=shop-mirror@file
  shadow:
    image: nginx:1.30-alpine
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.services.mir-shadow.loadbalancer.server.port=80

networks:
  proxy:
    external: true
EOF
cat > traefik/dynamic/mirror.yml <<'EOF'
http:
  services:
    shop-mirror:
      mirroring:
        service: mir-main@docker
        mirrors:
          - name: mir-shadow@docker
            percent: 30
EOF
docker compose -f compose.s65.yaml up -d 2>&1 | tail -1
sleep 5
for i in $(seq 1 50); do curl -s -o /dev/null http://beta.shop.localhost/; done
sleep 2
echo "основной получил запросов: $(docker compose -f compose.s65.yaml logs main 2>&1 | grep -c 'GET / ')"
echo "«тень» получила запросов:  $(docker compose -f compose.s65.yaml logs shadow 2>&1 | grep -c 'GET / ')"
```

### result
```out auto
```

Основной получил **все 50** запросов, «тень» — только копии примерно 30% от них (около 15). Клиент (`curl`) получил ответ только от основного. Если «теневая» версия ломается или тормозит, клиенты этого не заметят — но ты увидишь это в её журнале и метриках.

**Осторожно, побочные эффекты.** Зеркало получает копии **настоящих запросов**, включая `POST` и `DELETE`. Если тень записывает в ту же базу, что и основной сервис, заказы продублируются. Зеркалируют обычно только безопасные запросы (`GET`) или направляют тень в **отдельную копию данных**.

### why
Mirroring — самый безопасный способ «протестировать на живых данных»: в отличие от canary, клиенты вообще не видят новой версии. Он хорош, когда нужно проверить производительность и ошибки нового релиза, не рискуя ответами.

### deep Команды по частям
`mirroring.service` — основной сервис (его ответ идёт клиенту); `mirrors` — зеркала, у каждого `name` и `percent` — какую долю запросов копировать. `docker compose logs main | grep -c 'GET / '` — число строк журнала доступа `nginx` с таким запросом. `rm -f traefik/dynamic/canary.yml` — убираем файл предыдущего опыта (иначе в нём осталась бы ссылка на исчезнувшие сервисы).

### deep Как ещё можно
- **Зеркалировать только `GET`:** выделить отдельный роутер с правилом ``Method(`GET`)`` и именно на него навесить mirroring.
- **`mirrorBody`, `maxBodySize`** — копировать ли тела запросов и до какого размера (по умолчанию копируются).
- **Реальное нагрузочное тестирование** новой версии — mirroring с долей 100% на копию стенда.

### deep Если не получилось
- **Тень получила 0** — файл `mirror.yml` не подхвачен или сервис `mir-shadow@docker` не создан: проверь список сервисов в дашборде.
- **Строки журнала нет** — `nginx` пишет журнал в стандартный вывод контейнера; убедись, что команда `docker compose … logs` относится к нужному файлу `compose.s65.yaml`.
- **Количество «теней» сильно отличается от 30%** — на 50 запросах это нормально; увеличь число запросов.

### quiz
- Кто получает ответ при mirroring и что происходит с ответом зеркала?
- Чем mirroring отличается от canary с весами?
- Какие запросы опасно зеркалировать и почему?

### links
- https://doc.traefik.io/traefik/routing/services/#mirroring-service | mirroring | Traefik: mirroring
- https://istio.io/latest/docs/tasks/traffic-management/mirroring/ | traffic mirroring | Istio: mirroring

## 6.6 Blue/green и постепенный перевод трафика | short: Blue/green | est: ~45 мин
### intro
**Слова шага:** *blue/green*, *переключатель*, *вес 0/100*, *пошаговый перевод*, *откат*, *выкатка без простоя*.

:::tip Если совсем просто
Blue/green — два одинаковых зала в ресторане: в «синем» сейчас гости, «зелёный» — готовим новое меню. Когда готово, **переводим гостей разом** (весы 0/100). Что-то пошло не так — обратно (100/0). Canary — то же, но гостей переводят постепенно.
:::

```svg
@blue-green
```

**Blue/green** — две полные копии приложения («синяя» — текущая, «зелёная» — новая). Весь трафик идёт на одну, вторая стоит наготове. Переключение — смена весов на `0 / 100`: мгновенно, одним изменением файла, и столь же мгновенный откат. Мы уже умеем это делать (шаг 6.4): `weighted` с весами `100 / 0` и `0 / 100`. Посмотрим серию переключений — **пошаговый перевод** трафика на новую версию с контролем на каждом шаге:

```bash run
cd ~/traefik-lab/edge
docker compose -f compose.s65.yaml down 2>&1 | tail -1
rm -f traefik/dynamic/mirror.yml
docker compose -f compose.s64.yaml up -d 2>&1 | tail -1
set_weights() {
  cat > traefik/dynamic/canary.yml <<EOF
http:
  services:
    shop-canary:
      weighted:
        services:
          - name: canary-v1@docker
            weight: $1
          - name: canary-v2@docker
            weight: $2
EOF
}
share() { for i in $(seq 1 40); do curl -s http://canary.shop.localhost/ | grep -m1 '^Name'; done | sort | uniq -c | tr '\n' ' '; echo; }
sleep 4
for w in "100 0" "75 25" "50 50" "0 100"; do
  set_weights $w
  sleep 3
  printf 'веса %-7s -> ' "$w"
  share
done
echo "--- откат одной правкой:"
set_weights 100 0
sleep 3
printf 'веса 100 0  -> '; share
```

### result
```out auto
```

Видно, как доля `v2` растёт ступенями `0 → 25 → 50 → 100`, и как последняя правка возвращает всё на `v1`. В настоящей выкатке на каждой ступени ты смотришь на ошибки и задержки (журнал и метрики — сессия 10), и только если всё хорошо, идёшь дальше.

Чем blue/green отличается от canary:

| | Canary | Blue/green |
|---|---|---|
| Доли | малая → большая, постепенно | 0 / 100 разом |
| Риск | пострадает малая доля | пострадают все, но откат мгновенный |
| Ресурсы | старой хватит с запасом | нужны две полные копии |
| Когда | есть метрики для оценки по ходу | нужна проверка «до переключения» (прогнали тесты на «зелёной») |

### why
Выкатка без простоя — умение, которое отличает «выкладываем ночью и молимся» от «выкатываем в рабочее время». Traefik даёт для этого один приём — веса; остальное — дисциплина: проверять метрики на каждой ступени и держать откат под рукой (вес 0).

### deep Команды по частям
`set_weights()` — функция, которая перезаписывает файл с весами из двух аргументов (`$1`, `$2`). Heredoc без кавычек (`<<EOF`) подставляет значения. Цикл `for w in "100 0" "75 25" …; do set_weights $w` разворачивает строку в два аргумента. `printf 'веса %-7s -> ' "$w"` — выровненная подпись перед результатом.

### deep Как ещё можно
- **Автоматизация:** в CI/CD шаги `10% → 25% → 50% → 100%` делает скрипт, который сам смотрит на метрики (процент ошибок) и откатывает.
- **Kubernetes:** Argo Rollouts / Flagger управляют весами Traefik автоматически (отдельная Kubernetes-лаба).
- **Тест на «зелёной» до переключения:** отдельный роутер по заголовку (`X-Env: green`) — команда проверяет новую версию, пока клиенты ещё на старой.

### deep Если не получилось
- **Доли не меняются после правки** — файл не перечитан; подожди несколько секунд или перезапусти Traefik (см. шаг 6.4).
- **`404` на `canary.shop.localhost`** — не запущен `compose.s64.yaml` или нет файла `canary.yml` (в этом шаге его создаёт функция `set_weights`).
- **Вместо `v1`/`v2` другие имена** — это остатки прошлых опытов: убери их (`docker compose -f compose.s65.yaml down`).

### quiz
- Чем blue/green отличается от canary по рискам и по ресурсам?
- Какой одной правкой откатывается выкатка?
- Что нужно смотреть на каждом шаге перевода трафика?

### links
- https://martinfowler.com/bliki/BlueGreenDeployment.html | blue-green deployment | Fowler: BlueGreenDeployment
- https://doc.traefik.io/traefik/routing/services/ | сервисы | Traefik: services

## 6.7 🔨 Все экземпляры unhealthy: 503 | short: 🔨 Все unhealthy | est: ~40 мин
### intro
**Слова шага:** *`503 Service Unavailable`*, *`no available server`*, *`serverStatus`*, *каскадный отказ*, *лёгкий `/health`*.

:::tip Если совсем просто
Если администратор у входа видит, что **все** кассы закрыты, ему некуда направлять людей — он честно говорит «извините, мест нет». Это `503`. Проверка здоровья правильно исключила больных, но больны **все**, и сервис недоступен целиком. Научимся быстро отличать эту ситуацию от других и искать причину.
:::

Воспроизведём: «заразим» все три копии API и посмотрим, что увидит клиент:

```bash run
cd ~/traefik-lab/edge
docker compose -f compose.s64.yaml down 2>&1 | tail -1
rm -f traefik/dynamic/canary.yml
cd ~/traefik-lab/coffeeshop
tapi() { curl -s -u mira:coffee-secret "http://traefik.shop.localhost/api/$1"; }
for i in 1 2 3; do docker compose exec --index $i api node -e "fetch('http://localhost:3000/sick', {method: 'POST'})"; done
sleep 5
echo "--- что видит клиент:"
curl -s -w '\nHTTP %{http_code}\n' http://shop.localhost/api/menu
echo "--- статус адресов:"
tapi http/services/coffee-api@docker | jq -r '.serverStatus | to_entries[] | [.key, .value] | @tsv' | sort
```

### result
```out auto
```

Клиент получает **`503`** с коротким текстом `no available server`. Роутер на месте, сервис на месте, контейнеры работают — но **все адреса помечены `DOWN`**, и отправлять запросы некуда. Алгоритм поиска причины:

1. **Посмотри статус адресов** (дашборд → Services → `coffee-api`, либо `serverStatus` в API — как выше). Все `DOWN` — значит дело в проверке, а не в маршрутизации.
2. **Проверь `/health` сам**, в обход Traefik: открой его напрямую в контейнере. Если он отдаёт `500`/не отвечает — проблема в приложении. Если `200` — проблема в параметрах проверки (путь, порт, `timeout`).
3. **Подумай, от чего зависит `/health`.** Если он проверяет базу, а база упала, «больными» станут все копии сразу, хотя сами они в порядке. Поэтому `/health` для балансировщика делают **лёгким** (процесс жив), а полную проверку зависимостей выносят в отдельный адрес.

**Починка** (в нашем случае — вылечить копии):

```bash run
cd ~/traefik-lab/coffeeshop
for i in 1 2 3; do docker compose exec --index $i api node -e "fetch('http://localhost:3000/heal', {method: 'POST'})"; done
sleep 5
curl -s -o /dev/null -w 'после лечения: HTTP %{http_code}\n' http://shop.localhost/api/menu
```

```out auto
```

Сервис вернулся: как только хотя бы один адрес прошёл проверку, Traefik начал направлять запросы на него.

### why
Healthcheck — палка о двух концах. Он спасает от отдельных больных копий, но если проверка слишком придирчива или зависит от общего компонента, она **выключает сервис целиком** — а Traefik не виноват: он исполнил приказ. Две защиты: лёгкий `/health` (только «процесс жив») и отдельный `/ready` для готовности к работе с зависимостями — тема из Kubernetes (liveness и readiness).

### deep Команды по частям
`docker compose exec --index $i api node -e "fetch(…)"` — в цикле заражаем (и затем лечим) каждую копию по её номеру. `curl -s -w '\nHTTP %{http_code}\n'` — тело ответа и код после него. Тело `no available server` — служебный текст Traefik: так он отвечает, когда у сервиса нет ни одного здорового адреса.

### deep Если не получилось
- **Клиент получает `200`** — копии не заразились: проверь `docker compose ps api` (три ли копии) и что в `compose.s6.yaml` включён `healthcheck`.
- **После лечения всё ещё `503`** — подожди интервал проверки (2 секунды) и повтори: Traefik заметит выздоровление при следующем опросе.
- **В дашборде нет `serverStatus`** — для сервиса не включён healthcheck: без него Traefik считает все адреса здоровыми.

### quiz
- Что означает `503 no available server` и как отличить его от `502`?
- Какой путь поиска причины: что проверить первым, что вторым?
- Почему `/health` для балансировщика должен быть лёгким и не зависеть от базы?

### links
- https://doc.traefik.io/traefik/routing/services/#health-check | health check | Traefik: health check
- https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/ | liveness и readiness | Kubernetes: probes
