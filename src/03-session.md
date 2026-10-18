# Сессия 3 · Docker provider и правила маршрутизации
dur: ~4 ч

## 3.1 Как Traefik находит контейнеры | short: Как Traefik находит контейнеры | est: ~35 мин
### intro
**Слова шага:** *события Docker (events)*, *провайдер*, *метки (labels)*, *`exposedByDefault`*, *горячая перезагрузка*.

:::tip Если совсем просто
Traefik — как администратор, который подписан на **рассылку «в здании что-то изменилось»**. Появился новый арендатор (контейнер) и повесил на дверь табличку (метки) — администратор тут же прочитал её и записал в журнал приёма. Арендатор съехал — запись исчезла. Никто не говорил ему «перечитай список».
:::

```svg
@docker-events
```

Провайдер Docker делает две вещи:

1. **При старте** читает список всех запущенных контейнеров через `docker.sock` и разбирает их метки.
2. **Дальше слушает поток событий** Docker API (`start`, `stop`, `die`…) и при каждом событии пересобирает конфигурацию. Поэтому маршрут появляется почти сразу после запуска контейнера и пропадает после остановки — **перезапускать Traefik не нужно**.

Для каждого контейнера Traefik решает: **публиковать или нет**. Если `exposedByDefault: false` (как у нас), он берёт только контейнеры с меткой `traefik.enable=true`. Посмотрим сами: запустим пробный контейнер с метками, проверим, что роутер появился, остановим и проверим, что он исчез. Заодно спросим у Docker, какие события он при этом разослал:

```bash run
cd ~/traefik-lab/edge
docker run -d --name probe --network proxy \
  --label traefik.enable=true \
  --label 'traefik.http.routers.probe.rule=Host(`whoami.shop.localhost`)' \
  --label traefik.http.routers.probe.entrypoints=web \
  traefik/whoami > /dev/null
sleep 2
echo "--- роутер после запуска:"
curl -s http://traefik.shop.localhost/api/http/routers | jq -r '.[] | select(.name | startswith("probe")) | [.name, .status] | @tsv'
curl -s http://whoami.shop.localhost/ | head -2
docker rm -f probe > /dev/null
sleep 2
echo "--- роутер после остановки:"
curl -s http://traefik.shop.localhost/api/http/routers | jq -r '.[] | select(.name | startswith("probe")) | .name'
echo "--- что сообщал Docker (события этого контейнера):"
docker events --since 2m --until 0s --filter container=probe --format '{{.Type}} {{.Action}}' | head -8
```

### result
```out auto
```

Сразу после запуска роутер `probe@docker` появился и ответил как `whoami`; после `docker rm -f` его в списке больше нет (пустой вывод). События Docker показывают, на что подписан Traefik: создание, подключение к сети, запуск, затем остановка и удаление. Каждое из них — повод пересобрать маршруты.

### why
Именно поэтому в Docker Compose с Traefik **не нужен «reload»**: `docker compose up -d` с новыми метками сам даёт событие, и Traefik подхватывает изменения за доли секунды. А ещё это значит, что на правильно размеченные контейнеры достаточно смотреть дашбордом: он всегда отражает текущее состояние.

### deep Команды по частям
`docker run -d --name probe --network proxy --label … traefik/whoami`: `--network proxy` подключает контейнер к нашей сети, каждый `--label k=v` — одна метка (значения с обратными кавычками берём в одинарные, чтобы оболочка их не трактовала). `docker events --since 2m --until 0s --filter container=probe --format '…'`: события за последние две минуты по контейнеру `probe`; без `--until` команда ждала бы новые события бесконечно. `select(.name | startswith("probe"))` — оставить роутеры, чьё имя начинается с «probe».

### deep Как ещё можно
- **Следить вживую:** `docker events --filter type=container` в отдельном окне, а в другом запускать и убивать контейнеры — видишь тот же поток, на который подписан Traefik.
- **Смотреть решения Traefik:** `docker compose logs -f traefik` с уровнем `DEBUG` показывает, какой контейнер он принял, а какой пропустил и почему.

### deep Если не получилось
- **Роутер не появился** — вернись к лесенке из шага 2.7: есть ли `traefik.enable=true`, в нужной ли сети контейнер, нет ли опечатки в метках.
- **`docker events` ничего не печатает** — события хранятся ограниченное время; запусти пробный контейнер ещё раз и спроси сразу.

### quiz
- Откуда Traefik узнаёт, что контейнер запустился или остановился?
- Почему после `docker compose up -d` с новыми метками не нужно перезапускать Traefik?
- Что решает `exposedByDefault`: какие контейнеры Traefik учитывает?

### links
- https://doc.traefik.io/traefik/providers/docker/ | провайдер Docker | Traefik: Docker provider
- https://docs.docker.com/reference/cli/docker/system/events/ | события Docker | docker events

## 3.2 Правила: Host, Path, Header, Method, Query | short: Правила роутера | est: ~50 мин
### intro
**Слова шага:** *`rule`*, *`Host()`*, *`HostRegexp()`*, *`Path()`/`PathPrefix()`*, *`Header()`*, *`Method()`*, *`Query()`*, *`&&` / `||`*.

:::tip Если совсем просто
Правило роутера — **«фильтр на входе»**: «пропусти запрос, если имя такое-то **и** путь начинается так-то **и** метод `POST`». Можно комбинировать условия через `&&` («и») и `||` («или»). Какой роутер подошёл — туда и уйдёт запрос.
:::

В поле `rule` ты описываешь условия на запрос. Самые частые:

| Правило | Совпадает, если… | Пример |
|---|---|---|
| `Host(…)` | заголовок `Host` равен значению | ``Host(`shop.localhost`)`` |
| `HostRegexp(…)` | `Host` подходит под регулярное выражение | ``HostRegexp(`^admin[0-9]*\.shop\.localhost$`)`` |
| `Path(…)` | путь **точно** равен | ``Path(`/health`)`` |
| `PathPrefix(…)` | путь **начинается** с | ``PathPrefix(`/api`)`` |
| `Header(…)` | заголовок запроса имеет такое значение | ``Header(`X-Debug`, `1`)`` |
| `Method(…)` | HTTP-метод | ``Method(`POST`)`` |
| `Query(…)` | в строке запроса есть параметр | ``Query(`beta`, `1`)`` |

В Traefik v3 правило для заголовков называется **`Header`** (в единственном числе; `Headers` — это не правило: роутер с ним получает статус `disabled` и ошибку `unsupported function: Headers`). Условия соединяются: `&&` — «и», `||` — «или», скобки — как в математике. Значения всегда пишутся в **обратных кавычках**. Теперь опыт: одна и та же машина `whoami` повторена шесть раз, каждая с **своим правилом** и **своим именем** (`--name`), и мы увидим, какая ответила.

```bash run
cd ~/traefik-lab/edge
cat > compose.rules.yaml <<'EOF'
name: rules

x-whoami: &w
  image: traefik/whoami
  networks: [proxy]

services:
  host:
    <<: *w
    command: ["--name", "HOST"]
    labels:
      - traefik.enable=true
      - traefik.http.routers.rules-host.rule=Host(`whoami.shop.localhost`)
      - traefik.http.routers.rules-host.entrypoints=web
  api:
    <<: *w
    command: ["--name", "API"]
    labels:
      - traefik.enable=true
      - traefik.http.routers.rules-api.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/api`)
      - traefik.http.routers.rules-api.entrypoints=web
  post:
    <<: *w
    command: ["--name", "POST"]
    labels:
      - traefik.enable=true
      - traefik.http.routers.rules-post.rule=Host(`whoami.shop.localhost`) && Method(`POST`)
      - traefik.http.routers.rules-post.entrypoints=web
  debug:
    <<: *w
    command: ["--name", "DEBUG"]
    labels:
      - traefik.enable=true
      - traefik.http.routers.rules-debug.rule=Host(`whoami.shop.localhost`) && Header(`X-Debug`, `1`)
      - traefik.http.routers.rules-debug.entrypoints=web
  beta:
    <<: *w
    command: ["--name", "BETA"]
    labels:
      - traefik.enable=true
      - traefik.http.routers.rules-beta.rule=Host(`whoami.shop.localhost`) && Query(`beta`, `1`)
      - traefik.http.routers.rules-beta.entrypoints=web
  regex:
    <<: *w
    command: ["--name", "REGEX"]
    labels:
      - traefik.enable=true
      - traefik.http.routers.rules-regex.rule=HostRegexp(`^admin[0-9]*\.shop\.localhost$$`)
      - traefik.http.routers.rules-regex.entrypoints=web

networks:
  proxy:
    external: true
EOF
docker compose -f compose.rules.yaml up -d 2>&1 | tail -2
sleep 3
t() { printf '%-46s -> ' "$1"; shift; curl -s "$@" | grep -m1 '^Name' || echo "(нет ответа)"; }
t "Host"                          http://whoami.shop.localhost/
t "Host + /api/x"                 http://whoami.shop.localhost/api/x
t "Host + POST"                   -X POST http://whoami.shop.localhost/
t "Host + заголовок X-Debug: 1"   -H 'X-Debug: 1' http://whoami.shop.localhost/
t "Host + ?beta=1"                'http://whoami.shop.localhost/?beta=1'
t "admin.shop.localhost (regexp)" http://admin.shop.localhost/
```

### result
```out auto
```

Каждый запрос попал туда, куда нужно: имя в строке `Name:` показывает, **какой роутер выиграл**. Обрати внимание на два места в таблице правил:

- **`$$` в метке `HostRegexp`.** Compose сам обрабатывает `$`: одиночный `$` он принимает за подстановку переменной. Чтобы в итоговой метке остался один `$` (конец строки в регулярном выражении), в файле пишут `$$`. Это то же самое, что в шаге 1.5 с `$${POSTGRES_USER}`.
- **Синтаксис Traefik v3.** В v3 `HostRegexp` принимает **обычное регулярное выражение** (`^admin[0-9]*\.shop\.localhost$`). Старая запись v2 с фигурными скобками (`{subdomain:[a-z]+}.example.com`) больше не работает — ловушка при переезде с v2.

### why
Правила — «язык» Traefik. Научившись читать `Host(...) && PathPrefix(...)`, ты читаешь маршрут любого проекта. А комбинируя условия, можно разводить трафик очень тонко: по имени, пути, заголовку, методу — например, отправлять запросы с заголовком `X-Debug: 1` на отладочную копию сервиса.

### deep Команды по частям
`x-whoami: &w` — «якорь» YAML: общий кусок, который подставляется в сервисы через `<<: *w` (чтобы не повторять `image` и `networks` шесть раз). `command: ["--name", "HOST"]` — аргументы для `whoami`, он печатает их в строке `Name:`. Функция `t() { … }` — маленький помощник: печатает подпись и первую строку `Name:` из ответа (`grep -m1`). Параметры `curl` после подписи — аргументы запроса (`-X POST`, `-H`).

### deep Как ещё можно
- **Несколько значений сразу:** ``Host(`a.localhost`, `b.localhost`)`` — любое из имён (в v3 это допустимо).
- **Отрицание:** ``!Path(`/private`)`` — «всё, кроме этого пути».
- **Пути с регуляркой:** ``PathRegexp(`^/orders/[0-9]+$$`)``.
- **Скобки:** `Host(`a.localhost`) && (PathPrefix(`/a`) || PathPrefix(`/b`))`.

### deep Если не получилось
- **Для одного из запросов `(нет ответа)`** — роутер не создался: открой список роутеров (`/api/http/routers`) и найди его статус и ошибку.
- **В метке с регулярным выражением вместо `$$` стоит один `$`** — Compose попытается подставить переменную и выдаст предупреждение `variable is not set`; удвой `$`.
- **В логе `invalid rule syntax`** — потерялась обратная кавычка или скобка в правиле.

### quiz
- Чем `Path()` отличается от `PathPrefix()`?
- Как записать правило «имя `shop.localhost` и метод `POST`»?
- Что изменилось в `HostRegexp` между Traefik v2 и v3 и зачем в Compose удваивают `$`?

### links
- https://doc.traefik.io/traefik/routing/routers/#rule | правила роутеров | Traefik: router rule
- https://doc.traefik.io/traefik/migration/v2-to-v3/ | миграция v2 → v3 | Traefik: migration v2 → v3

## 3.3 Приоритеты и конфликты правил | short: Приоритеты | est: ~40 мин
### intro
**Слова шага:** *`priority`*, *длина правила*, *конфликт роутеров*, *более специфичное правило*.

:::tip Если совсем просто
Когда подходят сразу несколько роутеров, их нужно выстроить в очередь. По умолчанию Traefik считает, что **чем подробнее (длиннее) правило, тем оно важнее**. Но иногда он ошибается — тогда тебе нужно самой проставить номерки (`priority`).
:::

Если запросу подходят несколько роутеров, Traefik выбирает **один** — с наибольшим **приоритетом**. По умолчанию приоритет равен **длине строки правила** (в символах): специфичное правило обычно длиннее общего и побеждает. Но «длиннее» не всегда значит «важнее» — посмотрим на нашем стенде. Запрос `POST /api/x` подходит сразу двум роутерам из шага 3.2: `API` (`Host && PathPrefix`) и `POST` (`Host && Method`). Кто выиграет?

```bash run
cd ~/traefik-lab/edge
t() { printf '%-46s -> ' "$1"; shift; curl -s "$@" | grep -m1 '^Name' || echo "(нет ответа)"; }
t "POST /api/x (по длине правил)" -X POST http://whoami.shop.localhost/api/x
echo "--- длины правил (это и есть приоритеты по умолчанию):"
curl -s http://traefik.shop.localhost/api/http/routers | jq -r '.[] | select(.name | startswith("rules-")) | [.priority, .name] | @tsv' | sort -rn
```

### result
```out auto
```

Выиграл `API`: его правило длиннее (``PathPrefix(`/api`)`` занимает больше символов, чем ``Method(`POST`)``), значит приоритет выше. Но нам, допустим, нужно, чтобы **все `POST`** всегда обрабатывал отдельный сервис. Укажем приоритет явно меткой `priority` на роутере `POST`. Добавляем её через **второй файл Compose**: он объединяется с первым (метки складываются), и править исходный файл не нужно:

```bash run
cd ~/traefik-lab/edge
cat > compose.rules.priority.yaml <<'EOF'
services:
  post:
    labels:
      - traefik.http.routers.rules-post.priority=1000
EOF
docker compose -f compose.rules.yaml -f compose.rules.priority.yaml up -d 2>&1 | tail -2
sleep 3
t() { printf '%-46s -> ' "$1"; shift; curl -s "$@" | grep -m1 '^Name' || echo "(нет ответа)"; }
t "POST /api/x (priority=1000 у POST)" -X POST http://whoami.shop.localhost/api/x
t "GET  /api/x (как раньше)"           http://whoami.shop.localhost/api/x
```

```out auto
```

Теперь `POST` побеждает даже на пути `/api/x`, а `GET` на тот же путь по-прежнему уходит в `API`. Явное число приоритета перекрывает длину правила. Практическое правило: **числа не нужны, пока длина правил сама расставляет специфичное выше общего; как только эта логика ошибается — добавь `priority`.**

### why
Конфликт приоритетов — коварная ошибка: ничего не падает, просто часть запросов приходит «не туда». Знание, что приоритет по умолчанию равен длине правила, объясняет большинство таких случаев. Типичный пример: общий роутер `Host(...)` с длинным регулярным выражением внезапно «перехватывает» запросы у более точного, но более короткого правила.

### deep Команды по частям
`jq -r '.[] | select(.name | startswith("rules-")) | [.priority, .name] | @tsv'` — для каждого роутера с именем на `rules-` печатаем приоритет и имя через табуляцию; `sort -rn` — по убыванию как число. Второй файл Compose (`-f a.yaml -f b.yaml`) объединяется с первым: списки (`labels`) дополняются, одиночные значения перекрываются.

### deep Как ещё можно
- **Файловый провайдер и приоритеты** — те же поля; `priority: 1000` в YAML роутера.
- **Меньше конфликтов:** лучше делать правила взаимоисключающими (например, добавлять `&& !Method(`POST`)`), чем лечить числами.

### deep Если не получилось
- **`POST` всё равно попадает в `API`** — метка не применилась: проверь, что запускал `up -d` с обоими файлами; в дашборде у `rules-post` должно быть `priority: 1000`.
- **Приоритеты в списке одинаковые** — правила одной длины; конфликт решается по имени роутера (см. 🔨 в шаге 3.7).

### quiz
- Как Traefik по умолчанию выбирает между подходящими роутерами?
- Когда длина правила вводит в заблуждение и что тогда делать?
- Зачем второй файл Compose с одной меткой, а не правка первого?

### links
- https://doc.traefik.io/traefik/routing/routers/#priority | приоритет роутера | Traefik: priority
- https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/ | слияние файлов Compose | Compose: merge

## 3.4 Сети и порты сервиса | short: Сети и порты | est: ~40 мин
### intro
**Слова шага:** *`traefik.docker.network`*, *несколько сетей*, *`loadbalancer.server.port`*, *`EXPOSE`*, *таймаут соединения*.

:::tip Если совсем просто
Если у контейнера несколько «входов» (сетей) и несколько «дверей» (портов), Traefik нужно подсказать, **через какой вход и в какую дверь** стучаться. Иначе он выберет сам — и может выбрать не ту.
:::

У контейнера бывает **несколько сетей**: например, `api` ходит к базе по сети `back` и принимает запросы от Traefik по сети `proxy`. У каждой сети свой IP-адрес. Traefik должен знать, **какой из них использовать**. Есть два способа: поле `providers.docker.network` в `traefik.yml` (глобально, у нас `proxy`) и метка `traefik.docker.network=…` (для конкретного контейнера). Проверим на опыте: контейнер в двух сетях, сначала с правильной подсказкой, потом с неправильной:

```bash run
cd ~/traefik-lab/edge
docker network create back-demo > /dev/null
docker run -d --name multi --network back-demo --label traefik.enable=true \
  --label 'traefik.http.routers.multi.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/multi`)' \
  --label traefik.http.routers.multi.entrypoints=web --label traefik.docker.network=proxy \
  traefik/whoami > /dev/null
docker network connect proxy multi
sleep 3
echo "--- адреса контейнера в его сетях:"
docker inspect multi --format '{{range $n, $v := .NetworkSettings.Networks}}{{$n}}={{$v.IPAddress}} {{end}}'
echo "--- адрес, который выбрал Traefik:"
curl -s http://traefik.shop.localhost/api/http/services | jq -r '.[] | select(.name == "multi@docker") | .loadBalancer.servers[].url'
curl -s -o /dev/null -w 'ответ: HTTP %{http_code}\n' http://whoami.shop.localhost/multi
```

### result
```out auto
```

Traefik выбрал адрес из сети `proxy`, ответ `200`. А теперь «забудем» про общую сеть: пусть метка указывает на `back-demo` — сеть, в которой **Traefik не состоит**:

```bash run
docker rm -f multi > /dev/null
docker run -d --name multi --network back-demo --label traefik.enable=true \
  --label 'traefik.http.routers.multi.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/multi`)' \
  --label traefik.http.routers.multi.entrypoints=web --label traefik.docker.network=back-demo \
  traefik/whoami > /dev/null
docker network connect proxy multi
sleep 3
echo "--- адрес, который выбрал Traefik теперь:"
curl -s http://traefik.shop.localhost/api/http/services | jq -r '.[] | select(.name == "multi@docker") | .loadBalancer.servers[].url'
curl -s -o /dev/null -w 'ответ: HTTP %{http_code} (ждали не больше 4 с)\n' --max-time 4 http://whoami.shop.localhost/multi
docker rm -f multi > /dev/null; docker network rm back-demo > /dev/null
```

```out auto
```

Теперь Traefik взял адрес из `back-demo` — он **существует, но недоступен** Traefik (они в разных сетях), поэтому запрос не получает ответа (`000` — у `curl` истёк наш лимит 4 секунды; сам Traefik ждёт до 30 секунд и затем отвечает `504 Gateway Timeout`). Вывод: **если контейнер в нескольких сетях, Traefik должен знать, какая из них общая с ним**.

**Порт сервиса.** Вторая подсказка — `traefik.http.services.<имя>.loadbalancer.server.port=<порт>`. Traefik берёт порт сам, **только если у контейнера ровно один открытый порт** (`EXPOSE` в образе). Если портов несколько или приложение слушает не тот порт, который объявлен образом, — укажи явно. Проверим, что без метки порта Traefik стучится не туда:

```bash run
docker run -d --name p8081 --network proxy --label traefik.enable=true \
  --label 'traefik.http.routers.p8081.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/p`)' \
  --label traefik.http.routers.p8081.entrypoints=web \
  traefik/whoami --port 8081 > /dev/null
sleep 3
curl -s -o /dev/null -w 'без метки порта: HTTP %{http_code}\n' http://whoami.shop.localhost/p
docker rm -f p8081 > /dev/null
docker run -d --name p8081 --network proxy --label traefik.enable=true \
  --label 'traefik.http.routers.p8081.rule=Host(`whoami.shop.localhost`) && PathPrefix(`/p`)' \
  --label traefik.http.routers.p8081.entrypoints=web \
  --label traefik.http.services.p8081.loadbalancer.server.port=8081 \
  traefik/whoami --port 8081 > /dev/null
sleep 3
curl -s -o /dev/null -w 'с меткой порта 8081: HTTP %{http_code}\n' http://whoami.shop.localhost/p
docker rm -f p8081 > /dev/null
```

```out auto
```

Без метки Traefik взял порт из образа (80) — приложение же слушает `8081`, поэтому `502 Bad Gateway`. С меткой — `200`.

### why
Две подсказки — `traefik.docker.network` и `loadbalancer.server.port` — решают почти все «непонятные» `502` и таймауты в связках с несколькими сетями. Правило для CoffeeShop: контейнеры, которые Traefik должен видеть, подключаем к сети `proxy`, базу оставляем только во внутренней сети `back`.

### deep Команды по частям
`docker network create back-demo` — отдельная сеть для опыта. `docker run --network back-demo … ` подключает контейнер при запуске к одной сети, а `docker network connect proxy multi` — присоединяет ещё к одной. `docker inspect --format '{{range $n, $v := .NetworkSettings.Networks}}…{{end}}'` — Go-шаблон: перебирает сети контейнера и печатает имя=IP. `--max-time 4` — ограничение `curl` на всё время запроса.

### deep Как ещё можно
- **Одна сеть для всего:** если контейнер подключён только к `proxy`, никаких подсказок не нужно. Но тогда база тоже в `proxy` и видна всем контейнерам этой сети.
- **Порт из метки без сервиса:** метку `…server.port` можно писать и без отдельного объявления сервиса — Traefik создаёт сервис с именем контейнера.

### deep Если не получилось
- **Сначала в списке сервисов пусто** — Traefik не успел увидеть контейнер; подожди секунду и повтори запрос к API.
- **В первом опыте `ответ: HTTP 502`** — контейнер `multi` слушает порт `80`, а ты ничего не меняла в портах; значит что-то с сетью: повтори `docker network connect proxy multi` и проверь `docker inspect multi`.

### quiz
- Зачем указывать `traefik.docker.network`, если контейнер подключён к нескольким сетям?
- Когда Traefik сам находит порт сервиса, а когда нужна метка `loadbalancer.server.port`?
- Какой симптом у «Traefik выбрал не ту сеть» и у «Traefik стучится не в тот порт»?

### links
- https://doc.traefik.io/traefik/routing/providers/docker/#traefikdockernetwork | traefik.docker.network | Traefik: docker.network
- https://doc.traefik.io/traefik/routing/providers/docker/#port-detection | определение порта | Traefik: port detection

## 3.5 CoffeeShop за Traefik | short: CoffeeShop за Traefik | est: ~60 мин
### intro
**Слова шага:** *сквозной проект*, *`StripPrefix`*, *`PathPrefix(/api)`*, *внутренняя сеть `back`*, *закрытые порты*.

:::tip Если совсем просто
Наконец-то делаем то, ради чего всё затевалось: **одна дверь вместо трёх**. Сайт — по главному адресу, API — по тому же адресу, но с пути `/api`, Adminer — по отдельному поддомену. И порты наружу закрываем.
:::

```svg
@shop-routes
```

Таблица маршрутов, которую мы строим:

| Запрос | Куда |
|---|---|
| `http://shop.localhost/` | сайт (`web`, порт 80) |
| `http://shop.localhost/api/…` | API (`api`, порт 3000) |
| `http://adminer.shop.localhost/` | Adminer (порт 8080) |
| база | **никуда**: только внутри сети `back` |

Переписываем `compose.yaml` проекта CoffeeShop: убираем публикацию портов `ports:`, добавляем сети (`proxy` — внешняя, из проекта `edge`; `back` — внутренняя) и метки. Сначала **без** одной детали — чтобы увидеть, что без неё сломается:

```bash run
cd ~/traefik-lab/coffeeshop
docker compose down 2>&1 | tail -1
cat > compose.yaml <<'EOF'
name: coffeeshop

services:
  db:
    image: postgres:18
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - pgdata:/var/lib/postgresql
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 2s
      timeout: 3s
      retries: 15
    networks: [back]

  api:
    build: ./api
    environment:
      DB_HOST: db
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
      DB_NAME: ${DB_NAME}
    depends_on:
      db:
        condition: service_healthy
    networks: [back, proxy]
    labels:
      - traefik.enable=true
      - traefik.docker.network=proxy
      - traefik.http.routers.coffee-api.rule=Host(`shop.localhost`) && PathPrefix(`/api`)
      - traefik.http.routers.coffee-api.entrypoints=web
      - traefik.http.services.coffee-api.loadbalancer.server.port=3000

  web:
    build: ./web
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.coffee-web.rule=Host(`shop.localhost`)
      - traefik.http.routers.coffee-web.entrypoints=web
      - traefik.http.services.coffee-web.loadbalancer.server.port=80

  adminer:
    image: adminer:5
    networks: [back, proxy]
    labels:
      - traefik.enable=true
      - traefik.docker.network=proxy
      - traefik.http.routers.coffee-adminer.rule=Host(`adminer.shop.localhost`)
      - traefik.http.routers.coffee-adminer.entrypoints=web
      - traefik.http.services.coffee-adminer.loadbalancer.server.port=8080

networks:
  proxy:
    external: true
  back:

volumes:
  pgdata:
EOF
docker compose up -d --build > /dev/null 2>&1
sleep 8
docker compose ps --format 'table {{.Service}}\t{{.Status}}\t{{.Ports}}'
echo "--- сайт:"
curl -s -o /dev/null -w 'shop.localhost/ -> HTTP %{http_code}\n' http://shop.localhost/
echo "--- adminer:"
curl -s -o /dev/null -w 'adminer.shop.localhost/ -> HTTP %{http_code}\n' http://adminer.shop.localhost/
echo "--- API через /api:"
curl -s -w 'HTTP %{http_code}\n' http://shop.localhost/api/menu | grep -oE 'Cannot GET [^<]*|HTTP [0-9]+'
```

### result
```out auto
```

Сайт и Adminer открываются, **порты в `PORTS` пустые** — наружу больше ничего не торчит. А вот API через `/api` отвечает ошибкой: Traefik **переслал запрос как есть** — с путём `/api/menu`, а у нашего API есть только `/menu`. Express отвечает страницей ошибки `Cannot GET /api/menu` (код `404`). Увидеть, **что именно получил бэкенд**, поможет наш служебный адрес `/info`: он возвращает путь, с которым к нему пришли.

Починка — маленькая **middleware** с именем `stripprefix` («срезать префикс»): она убирает `/api` из пути **до** передачи запроса API. Подробно middlewares — следующая сессия; пока подключим готовую. Добавим две метки через второй файл Compose:

```bash run
cd ~/traefik-lab/coffeeshop
cat > compose.strip.yaml <<'EOF'
services:
  api:
    labels:
      - traefik.http.middlewares.coffee-strip.stripprefix.prefixes=/api
      - traefik.http.routers.coffee-api.middlewares=coffee-strip
EOF
docker compose -f compose.yaml -f compose.strip.yaml up -d > /dev/null 2>&1
sleep 4
echo "--- меню через /api:"
curl -s http://shop.localhost/api/menu; echo
echo "--- что видит API (путь, который до него дошёл):"
curl -s http://shop.localhost/api/info | jq '{path, host: .headers.host, forwarded_host: .headers["x-forwarded-host"], proto: .headers["x-forwarded-proto"]}'
echo "--- создаём заказ через сайт:"
curl -s -X POST -H 'Content-Type: application/json' -d '{"menu_id":2}' http://shop.localhost/api/orders; echo
echo "--- старые порты закрыты:"
curl -s -o /dev/null -w 'localhost:3000 -> HTTP %{http_code}\n' --max-time 3 http://localhost:3000/menu
curl -s -o /dev/null -w 'localhost:8080 -> HTTP %{http_code}\n' --max-time 3 http://localhost:8080/
```

```out auto
```

Теперь всё работает. Меню приходит по `http://shop.localhost/api/menu`, заказ создаётся, а API видит путь **`/info`** (без `/api`) — это работа `stripprefix`; заголовок `Host` у API остался оригинальным, а Traefik добавил `X-Forwarded-*`. Порты `3000` и `8080` больше не отвечают (код `000` — соединение отклонено): единственная дверь теперь — Traefik.

Откроем в браузере **http://shop.localhost** — меню загружается, кнопка «Заказать» работает. Это приёмка сессии 3: три сервиса за одним входом, маршруты по таблице.

### why
Важное решение этого шага — **что публиковать, а что нет**. Раньше у `web`, `api` и `adminer` были порты на хозяине; теперь не опубликован ни один. Поэтому обойти Traefik нельзя: все средства защиты, которые мы добавим на входе (пароль, ограничение скорости, HTTPS), действуют на любой запрос. База вообще не видна никому, кроме `api` и `adminer`.

### deep Команды по частям
`docker compose down` — убирает контейнеры (тома остаются: данные базы сохраняются). В новой версии файла сервисы переехали в сети `back` и `proxy`: `proxy` — **внешняя** (`external: true`): создана проектом `edge`, `coffeeshop` её только использует. `-f compose.yaml -f compose.strip.yaml` — два файла с объединением меток. `jq '{path, host: …}'` — собрать новый объект из выбранных полей.

### deep Как ещё можно
- **Не срезать префикс, а научить API:** сделать в API маршруты `/api/menu`. Минус: API привязывается к тому, как его публикуют. `stripprefix` — типовое решение.
- **API на отдельном поддомене** (`api.shop.localhost`) вместо `/api` — тогда срезать нечего, но нужен CORS и ещё одно имя (в `connect`-списке лабы его нет — настрой `/etc/hosts`).
- **Всё в одном файле:** метки `stripprefix` можно было сразу вписать в `compose.yaml`. Мы вынесли в отдельный файл, чтобы показать, как выглядит проблема.

### deep Если не получилось
- **`network proxy declared as external, but could not be found`** — проект `edge` не запущен: `cd ~/traefik-lab/edge && docker compose up -d`.
- **`api` не стартует, `ECONNREFUSED` к базе** — база перешла в сеть `back` вместе с `api`; убедись, что у обоих `networks: [back, …]`, и подожди 10–15 секунд.
- **Меню на странице не загружается, а `curl` работает** — браузер кэширует прежний ответ `404`: обнови страницу без кэша (`Cmd+Shift+R`).

### quiz
- Почему API через Traefik вернул `404`, пока мы не добавили `stripprefix`?
- Что изменилось с точки зрения безопасности, когда мы убрали `ports:` у сервисов?
- Какие сети у `api` и зачем ему обе?

### links
- https://doc.traefik.io/traefik/middlewares/http/stripprefix/ | StripPrefix | Traefik: StripPrefix
- https://docs.docker.com/reference/compose-file/networks/#external | внешние сети в Compose | Compose: external networks

## 3.6 Как читать и писать метки | short: Устройство меток | est: ~40 мин
### intro
**Слова шага:** *имя метки*, *имя объекта*, *уникальность имён*, *`docker inspect`*, *`@docker`*.

:::tip Если совсем просто
Метка — это «адрес» настройки в виде пути через точки: *traefik → http → routers → <имя> → rule*. Если научиться читать этот путь, любая метка читается за секунду. А ещё имена объектов **общие на весь Traefik** — как номера квартир в доме: два одинаковых номера путают почтальона.
:::

Метки выглядят пугающе, но устроены просто:

```text
traefik . http . routers . coffee-api . rule = Host(`shop.localhost`)
   │        │       │          │         │            │
   │        │       │          │         │            └ значение
   │        │       │          │         └ настройка (поле)
   │        │       │          └ имя объекта: вы выбираете сами
   │        │       └ тип: routers | services | middlewares
   │        └ протокол: http | tcp | udp
   └ префикс для Traefik
```

Для middleware между именем и настройкой добавляется ещё **тип**: `traefik.http.middlewares.coffee-strip.stripprefix.prefixes=/api` — «middleware с именем `coffee-strip`, типа `stripprefix`, поле `prefixes`». Чтобы убедиться, что Traefik получил именно то, что мы написали, **посмотрим метки у готового контейнера**:

```bash run
cd ~/traefik-lab/coffeeshop
docker inspect coffeeshop-api-1 --format '{{json .Config.Labels}}' | jq 'with_entries(select(.key | startswith("traefik")))'
```

### result
```out auto
```

Вот что на самом деле лежит у контейнера: пары «ключ — значение» (служебные метки Compose мы отфильтровали). Это **единственные** данные, которые Traefik берёт у Docker.

**Имена объектов общие.** Все роутеры, сервисы и middlewares всех контейнеров попадают в один общий каталог (с суффиксом `@docker`). Если два контейнера объявят роутер с одним и тем же именем, но с разными правилами, Traefik не знает, чьё правило настоящее, и **отключает оба** (в журнале появляется ошибка). Проверим:

```bash run
cd ~/traefik-lab/edge
for n in 1 2; do
  docker run -d --name dup$n --network proxy --label traefik.enable=true \
    --label "traefik.http.routers.web.rule=Host(\`dup$n.shop.localhost\`)" \
    --label traefik.http.routers.web.entrypoints=web traefik/whoami > /dev/null
done
sleep 3
docker logs edge-traefik-1 2>&1 | grep -i 'multiple times' | sed -E 's/^[0-9T:.Z+-]+ //' | cut -c1-90 | tail -1
curl -s http://traefik.shop.localhost/api/http/routers/web@docker | jq -r '[.name, .status] | @tsv'
docker rm -f dup1 dup2 > /dev/null
```

```out auto
```

Traefik записал ошибку `HTTP router defined multiple times with different configurations`, а в дашборде у `web@docker` статус **не `enabled`** (роутер отключён — оба контейнера остались без маршрута). **Правило хорошего тона:** добавляй к имени объекта префикс проекта: `coffee-web`, `coffee-api`, `shop-admin`. Мы так и делаем: имена `coffee-api`, `coffee-strip` не пересекутся с чужими.

### why
Метки — это **весь интерфейс** между твоим сервисом и Traefik. Если ты умеешь читать метки на чужом контейнере (`docker inspect`) и понимаешь, что имена общие, ты разберёшься с любым стеком, который тебе достанется.

### deep Команды по частям
`docker inspect NAME --format '{{json .Config.Labels}}'` — все метки контейнера одним JSON. `jq 'with_entries(select(.key | startswith("traefik")))'` — оставить только пары, где ключ начинается с `traefik`. В цикле `for n in 1 2` запускаются два контейнера, а в метке `"…dup$n…"` оболочка подставляет номер; обратные кавычки в двойных кавычках экранированы `\``.

### deep Как ещё можно
- **Сразу несколько роутеров и сервисов на одном контейнере:** например, `coffee-api-http` и `coffee-api-admin` — для разных правил; сервис между ними разделяется меткой `…routers.<имя>.service=<имя сервиса>`.
- **Метки через YAML-словарь:** в Compose `labels:` можно писать и как список `- k=v`, и как словарь `k: v` — Traefik безразлично. Список надёжнее для значений с `=`.

### deep Если не получилось
- **Предупреждения в логе нет** — уровень `INFO` может скрыть часть сообщений; поставь `log.level: DEBUG` или поищи в дашборде статус роутера.
- **Метки «пропали» после `docker compose up`** — Compose показывает метки из последней **применённой** версии файла; проверь, не забыла ли ты `-f` со вторым файлом.

### quiz
- Как по метке `traefik.http.services.api.loadbalancer.server.port=3000` определить тип объекта, его имя и настройку?
- Почему два контейнера нельзя называть роутер одним и тем же именем?
- Как посмотреть, какие метки Traefik реально получил от контейнера?

### links
- https://doc.traefik.io/traefik/routing/providers/docker/ | метки Docker | Traefik: Docker labels
- https://doc.traefik.io/traefik/providers/overview/#provider-namespace | пространства имён провайдеров | Traefik: provider namespace

## 3.7 🔨 Два роутера с одним правилом: кто выигрывает | short: 🔨 Два роутера, одно правило | est: ~40 мин
### intro
**Слова шага:** *равные приоритеты*, *неопределённый порядок*, *`priority`*, *канарейка по ошибке*.

:::tip Если совсем просто
Два повара получили одинаковый заказ. Кто готовит? Если не сказать — решит случай. На входе ресторана так делать нельзя: Traefik выбирает одного, и **ты не знаешь, какого**. Научимся это замечать и исправлять.
:::

Типичная история: разработчик копирует блок меток из одного проекта в другой и забывает поменять имя роутера **и** правило. Или две команды независимо «заняли» один адрес. Воспроизведём: две `whoami` с **одинаковым правилом** (`Host(whoami.shop.localhost) && PathPrefix(/dup)`) и разными именами:

```bash run
cd ~/traefik-lab/edge
for n in A B; do
  docker run -d --name twin$n --network proxy --label traefik.enable=true \
    --label "traefik.http.routers.twin$n.rule=Host(\`whoami.shop.localhost\`) && PathPrefix(\`/dup\`)" \
    --label traefik.http.routers.twin$n.entrypoints=web traefik/whoami --name $n > /dev/null
done
sleep 3
echo "--- кто отвечает на 6 одинаковых запросов:"
for i in 1 2 3 4 5 6; do curl -s http://whoami.shop.localhost/dup | grep -m1 '^Name'; done | sort | uniq -c
echo "--- приоритеты в дашборде:"
curl -s http://traefik.shop.localhost/api/http/routers | jq -r '.[] | select(.name | startswith("twin")) | [.priority, .name] | @tsv' | sort
```

### result
```out auto
```

Оба роутера получили **одинаковый приоритет** (длина правила одна), а ответы приходят **только от одного** — Traefik при равенстве выбирает по стабильному, но неочевидному признаку (имя роутера). Это не балансировка: второй роутер просто мёртвый груз. Главное — **ты не просила именно этого, а Traefik ничего не сообщил**: ошибки нет.

**Починка:**

1. Определи, **что хотелось**: развести два сервиса по разным условиям (правилам) — это правильный путь; или разделить нагрузку между копиями — тогда это один роутер и один сервис с несколькими адресами (сессия 6); или дать одному приоритет — `priority`.
2. Самый честный вариант — **сделать правила разными**. Для опыта сделаем явный приоритет у `B`:

```bash run
docker rm -f twinB > /dev/null
docker run -d --name twinB --network proxy --label traefik.enable=true \
  --label "traefik.http.routers.twinB.rule=Host(\`whoami.shop.localhost\`) && PathPrefix(\`/dup\`)" \
  --label traefik.http.routers.twinB.entrypoints=web --label traefik.http.routers.twinB.priority=500 \
  traefik/whoami --name B > /dev/null
sleep 3
for i in 1 2 3 4 5 6; do curl -s http://whoami.shop.localhost/dup | grep -m1 '^Name'; done | sort | uniq -c
docker rm -f twinA twinB > /dev/null
docker compose -f compose.rules.yaml -f compose.rules.priority.yaml down 2>&1 | tail -1
```

```out auto
```

Теперь отвечает один, и мы **знаем какой** — тот, у кого явный приоритет. Запомни порядок диагностики для «странно отвечает не тот сервис»: 1) список роутеров в дашборде; 2) приоритеты и правила у подозреваемых; 3) нет ли двух роутеров с одинаковым правилом.

### why
Самые опасные ошибки маршрутизации не дают исключений: сервис отвечает, просто **не тот**. Проверка «нет ли дубликатов правил» должна быть частью любого ревью меток. Позже (сессия 10) мы увидим, как найти такой дубль по журналу доступа: в нём указано, какой роутер обработал запрос.

### deep Команды по частям
`curl -s … | grep -m1 '^Name'` — взять первую строку `Name:` из ответа. Цикл `for i in 1 2 3 4 5 6` повторяет запрос шесть раз; `sort | uniq -c` считает, сколько раз встретилась каждая строка. `docker compose … down` в конце убирает стенд правил из шагов 3.2–3.3.

### deep Если не получилось
- **Ответы чередуются между A и B** — правило не совпало ровно: проверь, что оба правила одинаковой длины и совпадают посимвольно; при отличиях на символ приоритет разный.
- **Только `A`, даже после приоритета у `B`** — метка не применилась: проверь `docker inspect twinB` и дашборд.

### quiz
- Почему два роутера с одним правилом — не балансировка?
- Что в дашборде подскажет, что приоритеты равны?
- Какие три способа решить конфликт и какой самый честный?

### links
- https://doc.traefik.io/traefik/routing/routers/#priority | приоритет роутера | Traefik: priority
- https://doc.traefik.io/traefik/routing/routers/ | роутеры | Traefik: routers
