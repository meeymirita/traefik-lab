# Сессия 2 · Установка и первый маршрут
dur: ~3,5 ч

## 2.1 Две конфигурации: статическая и динамическая | short: Статическая и динамическая | est: ~30 мин
### intro
**Слова шага:** *статическая конфигурация*, *динамическая конфигурация*, *провайдер (provider)*, *entryPoint*, *router*, *service*, *middleware*.

:::tip Если совсем просто
Представь ресторан. **Устав** (статическая конфигурация) читают один раз при открытии: часы работы, какие входы в здании, откуда принимать заказы. Изменить устав — значит закрыться и открыться заново. **Приказы** (динамическая конфигурация) приходят в течение дня: «столик 5 — вегетарианцы», «блюдо дня сменилось». Их выполняют на лету, не закрывая зал. У Traefik ровно так: устав — файл `traefik.yml`, приказы — метки на твоих контейнерах.
:::

```svg
@static-dynamic
```

Traefik получает настройки из **двух разных источников**, и путать их — самая частая ошибка новичка.

**Статическая конфигурация** задаётся **один раз при запуске** и меняется только перезапуском. В ней: какие **входы** слушает Traefik (*entryPoints* — порты вроде `:80`, `:443`), откуда брать динамическую конфигурацию (**провайдеры**: Docker, файлы, Kubernetes), включён ли дашборд, куда писать логи. Источник — файл `traefik.yml`, флаги командной строки или переменные окружения (в одном месте, не вперемешку).

**Динамическая конфигурация** описывает **маршруты** и меняется **на лету**, без перезапуска. Из неё строятся четыре вещи:

- **Router** (маршрутизатор) — правило «если запрос такой (`Host`, путь…), то отправь его вон туда»;
- **Middleware** (промежуточная обработка) — что сделать по пути: убрать префикс, проверить пароль, ограничить скорость;
- **Service** (сервис) — куда в итоге переслать: список адресов бэкенда;
- а также **TLS** — сертификаты.

Путь запроса такой: *entryPoint → router → (middlewares) → service*. Источник динамической конфигурации — провайдер: для Docker это **метки (labels)** контейнеров, для файлового провайдера — YAML-файлы.

Посмотрим на Traefik в деле. Версия и первая справка — запуск одноразового контейнера:

```bash run
docker run --rm traefik:v3.7 version
```

### result
```out auto
```

Видишь версию, дату сборки и версию Go, на которой написан Traefik. Мы запустили его командой `version`, но дальше он будет работать как постоянный сервис.

### why
Когда что-то не работает, первый вопрос: *это ошибка устава или приказа?* Не слушает порт или нет дашборда — статика. Есть Traefik, но `404` на конкретный адрес — динамика (правило роутера, метка, порт сервиса). Это делит поиск причины пополам.

### deep Почему так сделано
Статическое нужно знать до запуска: какие порты открыть, к каким источникам подключиться. Динамическое меняется каждый раз, когда ты запускаешь или останавливаешь сервис. Отдельные источники позволяют менять маршруты сотню раз в день, не трогая сам Traefik.

### deep Три способа задать статику
Только **один** из них за раз: файл (`/etc/traefik/traefik.yml`), флаги (`--entryPoints.web.address=:80`) или переменные окружения (`TRAEFIK_ENTRYPOINTS_WEB_ADDRESS=:80`). Если указать несколько, Traefik использует **только первый найденный** (файл → флаги → окружение) — и это тихо ломает ожидания. Мы используем файл.

### quiz
- Чем статическая конфигурация отличается от динамической и где каждая задаётся?
- Из каких четырёх частей состоит путь запроса внутри Traefik?
- Что означает «провайдер» и какие провайдеры ты уже знаешь?

### links
- https://doc.traefik.io/traefik/getting-started/configuration-overview/ | обзор конфигурации | Traefik: configuration overview
- https://doc.traefik.io/traefik/routing/overview/ | обзор маршрутизации | Traefik: routing overview

## 2.2 Файл traefik.yml: каждое поле | short: Файл traefik.yml | est: ~40 мин
### intro
**Слова шага:** *`entryPoints`*, *`providers`*, *`api`*, *`dashboard`*, *`log`*, *`accessLog`*, *сеть `proxy`*.

:::tip Если совсем просто
`traefik.yml` — это «устав»: короткий список «на каких дверях стоим, откуда берём приказы, пишем ли журнал». Всего четыре блока.
:::

Traefik мы запускаем **отдельным проектом** Compose — `edge` («край», точка входа). Он будет один на все проекты: CoffeeShop и любые другие подключатся к нему через общую сеть `proxy`. Структура:

```text
~/traefik-lab/
├── coffeeshop/          # из сессии 1 (пока работает как раньше)
└── edge/
    ├── compose.yaml     # сам Traefik + пробный сервис whoami
    └── traefik/
        └── traefik.yml  # статическая конфигурация
```

Создаём статическую конфигурацию. Каждое поле разобрано в комментариях:

```bash run
mkdir -p ~/traefik-lab/edge/traefik && cd ~/traefik-lab/edge
cat > traefik/traefik.yml <<'EOF'
# Входы: на каких портах Traefik принимает трафик
entryPoints:
  web:
    address: ":80"

# Источники динамической конфигурации
providers:
  docker:
    exposedByDefault: false   # маршруты только у тех контейнеров, где traefik.enable=true
    network: proxy            # по какой сети ходить к сервисам

# Дашборд и API (сам по себе он не открыт — маршрут к нему зададим меткой)
api:
  dashboard: true

# Журнал самого Traefik (не путать с журналом запросов)
log:
  level: INFO
  noColor: true   # без цветовых кодов (в файлах и при копировании они мусор)

# Журнал запросов: одна строка на запрос
accessLog: {}
EOF
cat traefik/traefik.yml | grep -vE '^\s*#|^$' | head -20
```

### result
```out auto
```

Разберём поля:

- **`entryPoints.web.address: ":80"`** — вход с именем `web` на порту 80 (имя выбираешь сама, дальше на него ссылаются роутеры). Позже добавим `websecure` на 443.
- **`providers.docker`** — «смотри в Docker». `exposedByDefault: false` — **важнейшая настройка безопасности**: Traefik не публикует контейнер, пока на нём явно не написано `traefik.enable=true`. Без неё Traefik выставил бы наружу даже базу данных. `network: proxy` — к бэкендам ходить по сети с именем `proxy`.
- **`api.dashboard: true`** — включить встроенный дашборд. Сам по себе он никому не доступен: маршрут к нему мы объявим отдельно (шаг 2.5), так что его можно закрыть паролем.
- **`log.level`** — подробность журнала Traefik: `DEBUG` (всё), `INFO`, `WARN`, `ERROR`. **`noColor: true`** убирает цветовые коды из журнала: по умолчанию Traefik красит уровни, и при чтении `docker compose logs` в файл или в чат вместо цвета остаются символы вида `[32m`.
- **`accessLog`** — журнал запросов; пустой `{}` включает его с настройками по умолчанию (подробно — сессия 10).

### why
Статический файл мал специально: чем меньше настроек «на всю жизнь», тем реже ты перезапускаешь входную дверь. Всё остальное — динамика. Главная ловушка — `exposedByDefault`: оставь её в `false` с первого дня.

### deep Как ещё можно
- **Формат TOML** — Traefik читает и `traefik.toml`, это тот же устав другим синтаксисом.
- **Флаги в `command:`** — `--providers.docker.exposedByDefault=false` в `compose.yaml` вместо файла; удобно для коротких стендов, для чего-то серьёзнее лучше файл.
- **Переменные окружения** — `TRAEFIK_PROVIDERS_DOCKER_EXPOSEDBYDEFAULT=false`; полезны для секретов.

### deep Если не получилось
- **Traefik потом пишет `command traefik error: yaml: line N: …`** — ошибка отступов в YAML: в YAML отступы — пробелы (не табы), вложенность одной парой пробелов.
- **Меняешь файл, а ничего не происходит** — статика читается один раз; после правки перезапусти Traefik: `docker compose restart traefik`.

### quiz
- За что отвечают блоки `entryPoints`, `providers`, `api`, `log`?
- Зачем нужна настройка `exposedByDefault: false`?
- Почему после правки `traefik.yml` нужен перезапуск, а после правки меток контейнера — нет?

### links
- https://doc.traefik.io/traefik/reference/static-configuration/file/ | справочник статической конфигурации | Traefik: static configuration (file)
- https://doc.traefik.io/traefik/providers/docker/ | провайдер Docker | Traefik: Docker provider

## 2.3 Запуск Traefik в Docker и docker.sock | short: Запуск Traefik | est: ~45 мин
### intro
**Слова шага:** *`docker.sock`*, *`:ro`*, *сеть `proxy`*, *`404 page not found`*, *docker-socket-proxy*.

:::tip Если совсем просто
Чтобы Traefik узнавал о новых контейнерах, ему нужно «подглядывать» за Docker. Для этого мы даём ему **служебный ключ** — файл `docker.sock`. Это как дать швейцару список жильцов: удобно, но если швейцара обмануть, он может открыть всё здание. Поэтому ключ даём **только на чтение** и знаем про риск.
:::

Описываем Traefik в `compose.yaml`. Пока только он один:

```bash run
cd ~/traefik-lab/edge
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
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks: [proxy]

networks:
  proxy:
    name: proxy
EOF
docker compose up -d 2>&1 | tail -3
sleep 2
docker compose ps --format 'table {{.Service}}\t{{.Status}}\t{{.Ports}}'
echo "--- запрос к Traefik (маршрутов ещё нет):"
curl -s -w '\nHTTP %{http_code}\n' http://localhost/
echo "--- журнал Traefik (INF и ERR):"
docker compose logs --no-log-prefix traefik 2>&1 | grep -E ' (INF|ERR) ' | head -3 | cut -c1-120
```

### result
```out auto
```

Что мы получили:

- **`HTTP 404` и текст `404 page not found`** — это «подпись» Traefik: он работает, но не знает, куда направить запрос (маршрутов нет). Если ты видишь такой ответ, значит запрос **дошёл до Traefik** — ломается уже динамика.
- В журнале — строка с версией Traefik. Если бы он не смог подключиться к Docker (нет доступа к сокету), здесь была бы строка `ERR` с причиной. (Предупреждение `WRN … encoded characters`, которое ты, возможно, видишь выше в полном журнале, — штатное: Traefik 3.7 напоминает про новые настройки разбора адреса, на наш стенд оно не влияет.)
- Порт опубликован как `0.0.0.0:80->80/tcp`.

**Про `docker.sock`.** Строка `/var/run/docker.sock:/var/run/docker.sock:ro` монтирует служебный сокет Docker внутрь контейнера. `:ro` — только чтение файла, **но это не делает доступ безопасным**: через сокет всё равно можно вызывать любые команды Docker API (запустить привилегированный контейнер = получить root на хозяине). Поэтому:

- Не монтируй сокет в контейнеры, которым нельзя доверять; Traefik — один из немногих допустимых случаев.
- Не публикуй порт самого Docker-демона (`2375`) наружу.
- В серьёзной эксплуатации между Traefik и сокетом ставят **docker-socket-proxy** — маленький прокси, который разрешает только чтение списка контейнеров и запрещает остальное. Конфигурация ниже — для понимания; в нашем прогоне она не запускалась:

```yaml
services:
  socket-proxy:
    image: tecnativa/docker-socket-proxy
    environment: { CONTAINERS: 1 }          # разрешить только чтение контейнеров
    volumes: ["/var/run/docker.sock:/var/run/docker.sock:ro"]
    networks: [socket]
  traefik:
    # в traefik.yml: providers.docker.endpoint: "tcp://socket-proxy:2375"
    networks: [proxy, socket]
```

### why
Сокет Docker — самая «острая» вещь в этой лабе. Привычка помнить, что он даёт, поможет не создавать дыры. А ответ `404 page not found` — первый признак «Traefik жив»: когда он появится в будущем, ты сразу будешь знать, на какой ступени лесенки диагностики находишься.

### deep Команды по частям
`docker compose up -d 2>&1 | tail -3`: запуск в фоне; `2>&1 |` отправляет и обычный вывод, и ошибки в `tail`, который оставляет последние три строки. `docker compose ps --format 'table …'` — таблица сервисов. `curl -s -w '\nHTTP %{http_code}\n'` — тихий запрос и печать кода после тела. `docker compose logs --no-log-prefix traefik` — журнал сервиса без приставки с именем контейнера; `grep -E ' (INF|ERR) '` оставляет строки уровней INFO и ERROR; `cut -c1-120` обрезает длинные строки.

### deep Как ещё можно
- **Порт `80` занят на Mac:** используй `"8000:80"` и обращайся на `http://localhost:8000`; тогда имена вроде `shop.localhost` нужно писать с `:8000`.
- **Без публикации 80:** можно гонять Traefik через `host`-сеть (на Linux) — на Mac Docker Desktop такая сеть иная.
- **Без Compose:** `docker run -d -p 80:80 -v …traefik.yml:/etc/traefik/traefik.yml:ro -v /var/run/docker.sock:/var/run/docker.sock:ro --network proxy traefik:v3.7` — то же самое одной командой.

### deep Если не получилось
- **`Bind for 0.0.0.0:80 failed: port is already allocated`** — порт 80 занят (другой Docker-проект или программа): найди через `lsof -i :80`, остановь или смени порт на `8000:80`.
- **В журнале `Cannot connect to the Docker daemon`** — не смонтирован сокет или неверный путь. На Mac с Docker Desktop путь `/var/run/docker.sock` работает; с Colima или Rancher Desktop он другой — смотри `docker context ls`.
- **`yaml: unmarshal errors`** в журнале — опечатка в `traefik.yml` (шаг 2.2).

### quiz
- Что значит ответ `404 page not found` на запрос к только что запущенному Traefik?
- Почему `:ro` на `docker.sock` не делает его безопасным?
- Что такое docker-socket-proxy и какую проблему он решает?

### links
- https://doc.traefik.io/traefik/providers/docker/#docker-api-access | доступ к Docker API | Traefik: Docker API access
- https://github.com/Tecnativa/docker-socket-proxy | docker-socket-proxy | GitHub: docker-socket-proxy

## 2.4 Первый сервис whoami и первый маршрут | short: Первый маршрут | est: ~45 мин
### intro
**Слова шага:** *`whoami`*, *метки (labels)*, *`traefik.enable`*, *router*, *rule*, *`Host()`*, *`entrypoints`*.

:::tip Если совсем просто
`whoami` — крошечный сервис, который на любой запрос отвечает «вот кто я и вот что ты мне прислал». Идеальный подопытный. Мы приколем к нему **записку (метки)**: «меня включить, принимать на входе `web`, отдавать запросы с именем `whoami.localhost`». Traefik прочитает записку и сам проложит маршрут.
:::

```svg
@router-model
```

Добавляем `whoami` в `compose.yaml` рядом с Traefik. Контейнер в сети `proxy`, на нём три метки:

```bash run
cd ~/traefik-lab/edge
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
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks: [proxy]

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
docker compose up -d 2>&1 | tail -3
sleep 2
echo "--- запрос с правильным именем:"
curl -s http://whoami.localhost/
echo "--- запрос с другим именем (на тот же Traefik):"
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://localhost/
```

### result
```out auto
```

Первый запрос вернул ответ `whoami`: имя контейнера (`Hostname`), его адрес в сети, **заголовки запроса** — включая те, что добавил Traefik: `X-Forwarded-For` (IP клиента), `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Forwarded-Port`, `X-Forwarded-Server`, `X-Real-Ip` — и `RemoteAddr` (кто пришёл к `whoami`: это Traefik). Второй запрос, на другое имя, получил `404`: Traefik не нашёл подходящего роутера. **Имя решает.**

Теперь разберём три метки по именам. Это первая запись, которую ты будешь читать десятки раз:

```text
traefik.http.routers.whoami.rule=Host(`whoami.localhost`)
│       │    │       │      │
│       │    │       │      └─ что настраиваем: правило
│       │    │       └──────── имя роутера (любое, ты выбираешь)
│       │    └──────────────── тип объекта: routers
│       └───────────────────── протокол: http (есть ещё tcp, udp)
└───────────────────────────── префикс всех меток Traefik
```

- **`traefik.enable=true`** — включить публикацию этого контейнера (иначе `exposedByDefault: false` его пропустит).
- **`...routers.whoami.rule=Host(...)`** — правило: «принимать запросы, где `Host` равен `whoami.localhost`».
- **`...routers.whoami.entrypoints=web`** — слушать только вход `web` (порт 80).

А **сервис** (куда пересылать) мы не писали — Traefik создал его сам (`whoami-edge@docker`: так будет видно в дашборде): взял единственный открытый порт контейнера (80 у `whoami`) и сам прокинул запросы туда. Если портов несколько или ни одного, нужна метка `loadbalancer.server.port` (шаг 3.4).

### why
Это вся магия Traefik в трёх строках: **запустил контейнер с метками — маршрут появился. Остановил — исчез.** Ничего не перезагружали и никакой конфиг руками не правили. Этот механизм мы будем использовать до конца лабы.

### deep Команды по частям
`docker compose up -d` после правки файла пересоздаёт только изменившиеся сервисы (Traefik не трогается, `whoami` создаётся новым). `curl -s http://whoami.localhost/` — запрос на имя, у которого в сессии 1 мы научились находить адрес. В списке заголовков ответа `whoami` порядок строк у тебя может быть другой.

### deep Как ещё можно
- **Файловый провайдер:** тот же роутер можно описать в YAML-файле (`http.routers.whoami`), без меток: так делают для сервисов вне Docker (сессия 9).
- **Кавычки в метках:** в правилах `Host()` значения пишутся в **обратных кавычках** (`` ` ``). В YAML они не конфликтуют, но при записи в оболочке (`docker run --label '…'`) их нужно заключать в одинарные кавычки.

### deep Если не получилось
- **`404 page not found` для `whoami.localhost`** — самая вероятная причина: контейнер не в сети `proxy`, нет `traefik.enable=true` или опечатка в имени. Проверь `docker compose logs traefik` — Traefik пишет, что именно ему не понравилось. (Подробно — шаг 2.7.)
- **Ответ не от `whoami`, а `Bad Gateway`** — у Traefik нет доступа к контейнеру по сети; проверь, что в `networks` указан `proxy`.
- **`curl: (6) Could not resolve host: whoami.localhost`** — твоя система не знает правила `.localhost`: добавь `127.0.0.1 whoami.localhost` в `/etc/hosts` (шаг 1.6).

### quiz
- Какие три метки делают контейнер доступным через Traefik?
- Откуда у маршрута взялся сервис, если мы его не описывали?
- Что вернёт Traefik на запрос с неизвестным `Host` и почему?

### links
- https://doc.traefik.io/traefik/routing/providers/docker/ | метки Docker | Traefik: Docker routing
- https://github.com/traefik/whoami | whoami | GitHub: traefik/whoami

## 2.5 Дашборд: читаем роутеры, сервисы, middlewares | short: Дашборд | est: ~40 мин
### intro
**Слова шага:** *дашборд*, *`api@internal`*, *имя с суффиксом `@docker`*, *статус роутера*, *`rawdata`*.

:::tip Если совсем просто
Дашборд — **«доска объявлений» Traefik**: на ней видно все входы, все маршруты, все сервисы и все ошибки конфигурации. Когда маршрут «не работает», сначала смотрим туда: он показывает, **как Traefik понял твои метки**.
:::

Мы включили дашборд в `traefik.yml` (`api.dashboard: true`), но снаружи он не доступен: чтобы его открыть, нужен **маршрут** к специальному внутреннему сервису **`api@internal`**. Это тот же механизм меток, только на самом Traefik: он «обращается к самому себе»:

```bash run
cd ~/traefik-lab/edge
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
docker compose up -d 2>&1 | tail -3
sleep 3
curl -s -o /dev/null -w 'дашборд: HTTP %{http_code}\n' http://traefik.shop.localhost/dashboard/
echo "--- роутеры глазами Traefik (то, что показывает вкладка HTTP → Routers):"
curl -s http://traefik.shop.localhost/api/http/routers | jq -r '.[] | [.name, .rule // "-", .status, .service] | @tsv' | sort
echo "--- сервисы:"
curl -s http://traefik.shop.localhost/api/http/services | jq -r '.[] | [.name, .status, ((.loadBalancer.servers // []) | map(.url) | join(","))] | @tsv' | sort
```

### result
```out auto
```

Откроем это в браузере (на твоём Mac): **http://traefik.shop.localhost/dashboard/** — слэш в конце обязателен. На главной видно число роутеров, сервисов и middlewares и входы (`web`). Вкладка **HTTP → Routers** — таблица, в точности как выше: имя с суффиксом `@docker` (создан из меток Docker) или `@internal` (встроенный), правило, вход, сервис и **статус** (`enabled` — рабочий, `disabled` или с ошибкой — не работает). Кликни на роутер: откроется карточка со схемой *entryPoint → router → service*.

В таблице видны два суффикса: **`@docker`** — объект создан провайдером Docker, **`@internal`** — служебный. В конфигурации ссылаться на объект из другого провайдера нужно с суффиксом (так мы указали `api@internal`).

В сервисах виден адрес контейнера `whoami` в сети `proxy` (`http://172.x.x.x:80`) — это **автоматически** подобранный сервис из шага 2.4.

### why
Дашборд превращает «магию из меток» в таблицу. Когда ты ошибся в метке, Traefik не падает — он просто не создаёт роутер или создаёт с ошибкой, и **единственное место, где это видно**, — дашборд и журнал. Привычка заглядывать туда после каждого изменения избавит от слепых поисков.

### deep Команды по частям
`curl -s …/api/http/routers | jq -r '.[] | [..] | @tsv'`: API Traefik отдаёт JSON; `jq` разбирает его: `.[]` — по каждому объекту списка, `[.name, .rule // "-", .status, .service]` — список полей (оператор `//` подставляет `-`, если поля нет), `@tsv` — вывести через табуляцию, `-r` — без кавычек. `sort` — упорядочить. `/api/rawdata` отдаёт всю конфигурацию целиком.

### deep Как ещё можно
- **Открыть дашборд без маршрута:** в `traefik.yml` задать `api.insecure: true` — тогда он открывается на порту `8080` прямо у Traefik. Удобно для опытов, **опасно** на сервере: он не защищён паролем.
- **Закрыть паролем:** добавить middleware `basicAuth` — шаг 4.6.
- **Только консоль:** `curl http://traefik.shop.localhost/api/rawdata | jq` покажет то же самое в виде JSON.

### deep Если не получилось
- **`404` при открытии `/dashboard/`** — нет слэша в конце (`/dashboard` без слэша редиректит) или опечатка в `Host`. Проверь правило в `docker compose logs traefik`.
- **Роутер есть в списке, но статус не `enabled`** — смотри строку с ошибкой на его карточке: чаще всего ссылка на несуществующий сервис или middleware.
- **Дашборд открылся без паролей любому** — да, мы пока не закрывали его: до шага 4.6 держи стенд только на своём компьютере.

### quiz
- Что означают суффиксы `@docker` и `@internal` в именах объектов?
- Зачем роутеру дашборда указывать `service=api@internal`?
- Какой источник правды о том, как Traefik понял твои метки: файл `compose.yaml` или дашборд, и почему?

### links
- https://doc.traefik.io/traefik/operations/dashboard/ | дашборд | Traefik: dashboard
- https://doc.traefik.io/traefik/operations/api/ | API Traefik | Traefik: API

## 2.6 Как ещё запустить: флаги, окружение, Podman | short: Другие способы запуска | est: ~35 мин
### intro
**Слова шага:** *флаги командной строки*, *переменные окружения*, *rootless*, *Podman*, *один способ за раз*.

:::tip Если совсем просто
Один и тот же «устав» можно подать тремя способами: переписать на бумаге (файл), продиктовать вслух (флаги) или повесить объявлением на стену (переменные окружения). Главное правило: **используй один способ за раз**.
:::

Мы запускали Traefik с файлом `traefik.yml`. Есть ещё два способа, и важно уметь читать чужие `compose.yaml`, где они встречаются чаще файла. Проверим флаги: запустим **временный** Traefik рядом (не затрагивая основной) без файла и без Docker-провайдера и спросим у него версию API:

```bash run
docker run -d --name tf-flags -p 8099:8080 traefik:v3.7 --api.insecure=true --providers.docker=false --entryPoints.web.address=:80 > /dev/null
sleep 2
curl -s http://localhost:8099/api/version | jq .
echo "--- то же через переменные окружения:"
docker run -d --name tf-env -p 8098:8080 -e TRAEFIK_API_INSECURE=true -e TRAEFIK_ENTRYPOINTS_WEB_ADDRESS=:80 traefik:v3.7 > /dev/null
sleep 2
curl -s http://localhost:8098/api/entrypoints | jq -r '.[] | [.name, .address] | @tsv'
docker rm -f tf-flags tf-env
```

### result
```out auto
```

Оба временных Traefik заработали без единого файла (в списке входов, кроме нашего `web`, виден служебный `traefik` на порту `8080` — это вход для небезопасного API, который включила настройка `api.insecure`): в первом всё передано **флагами** (`--api.insecure=true`: имя поля с точками — это вложенность YAML, `api: insecure: true`), во втором — **переменными окружения** (`TRAEFIK_` + путь в верхнем регистре через подчёркивание). Порт `8080` внутри контейнера — тот самый небезопасный дашборд-API (поэтому опубликован на отдельные порты хозяина и только на время опыта).

**Правило «один способ».** Если смешать способы (часть в файле, часть флагами), Traefik **не слияет** их: он берёт первый найденный источник и игнорирует остальные. Вывод: выбирай один способ и держись его. В лабе — файл.

**Podman и rootless Docker.** Это альтернативы, где демон работает без прав root. Для Traefik меняется одно: путь к сокету (`/run/user/1000/podman/podman.sock` вместо `/var/run/docker.sock`) и, часто, невозможность занять порт ниже 1024 (`80` и `443`) без настройки системы. В прогоне методички эти варианты не запускались — у нас обычный Docker.

### why
В чужих проектах Traefik почти всегда запущен флагами в `command:` или переменными. Увидев `--providers.docker.exposedbydefault=false`, ты должна сразу узнать знакомое поле `providers.docker.exposedByDefault` из `traefik.yml`.

### deep Команды по частям
`docker run -d --name tf-flags -p 8099:8080 traefik:v3.7 --api.insecure=true …`: всё после имени образа — флаги **самому Traefik**, а не Docker. `jq .` — красиво напечатать JSON. `docker rm -f` останавливает и удаляет оба временных контейнера.

### deep Как ещё можно
- **Бинарный файл:** Traefik — один исполняемый файл (Go), можно скачать с GitHub Releases и запускать без Docker: `./traefik --configFile=traefik.yml`.
- **Helm-чарт** для Kubernetes — в Kubernetes-лабе.
- **Systemd-служба** на сервере без Docker — тот же бинарный файл под управлением systemd.

### deep Если не получилось
- **`port is already allocated` для 8098/8099** — возьми любые свободные порты слева в `-p`.
- **Пустой ответ от `curl`** — Traefik не успел стартовать: подожди ещё секунду-две.

### quiz
- Какими тремя способами можно задать статическую конфигурацию и какое правило про их сочетание?
- Как флаг `--api.insecure=true` связан с полем в `traefik.yml`?
- Что меняется в запуске Traefik под rootless Docker или Podman?

### links
- https://doc.traefik.io/traefik/getting-started/configuration-overview/#the-static-configuration | статическая конфигурация | Traefik: static configuration
- https://doc.traefik.io/traefik/reference/static-configuration/env/ | переменные окружения | Traefik: environment variables

## 2.7 🔨 Роутер есть, а 404: enable, порт, сеть | short: 🔨 Роутер есть, а 404 | est: ~50 мин
### intro
**Слова шага:** *диагностика меток*, *`404` / `502` / `504`*, *`traefik.enable`*, *`loadbalancer.server.port`*, *журнал Traefik*.

:::tip Если совсем просто
Сломаем маршрут тремя типичными способами и по ответу Traefik поймём, **что именно** забыто. Это самая частая беда новичков: «я всё написал, а 404».
:::

Поднимем три «больных» экземпляра `whoami`. У каждого одна ошибка:

- **`old.shop.localhost`** — забыли `traefik.enable=true`;
- **`new.shop.localhost`** — указан не тот порт сервиса;
- **`beta.shop.localhost`** — контейнер не в сети `proxy`.

```bash run
cd ~/traefik-lab/edge
cat > compose.broken.yaml <<'EOF'
name: broken

services:
  a-old:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.http.routers.a-old.rule=Host(`old.shop.localhost`)
      - traefik.http.routers.a-old.entrypoints=web

  b-new:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.b-new.rule=Host(`new.shop.localhost`)
      - traefik.http.routers.b-new.entrypoints=web
      - traefik.http.services.b-new.loadbalancer.server.port=8080

  c-beta:
    image: traefik/whoami
    labels:
      - traefik.enable=true
      - traefik.http.routers.c-beta.rule=Host(`beta.shop.localhost`)
      - traefik.http.routers.c-beta.entrypoints=web

networks:
  proxy:
    external: true
EOF
docker compose -f compose.broken.yaml up -d 2>&1 | tail -3
sleep 3
for h in old new beta; do
  curl -s -o /dev/null -w "$h.shop.localhost -> HTTP %{http_code}\n" --max-time 45 http://$h.shop.localhost/
done
```

### result
```out auto
```

Три разных симптома (последний появляется не сразу: Traefik ждёт соединения около 30 секунд). Разберём, как понять причину **по порядку**:

**Шаг 1. Есть ли роутер в дашборде?** Смотрим список роутеров, как в шаге 2.5, и ищем наших:

```bash run
curl -s http://traefik.shop.localhost/api/http/routers | jq -r '.[] | select(.name | test("old|new|beta")) | [.name, .status] | @tsv'
echo "--- журнал Traefik про проблемы:"
docker logs edge-traefik-1 2>&1 | grep -E 'Could not find network|Defaulting to first' | cut -c1-170
```

```out auto
```

- **`old` → `404`**, а в списке роутеров **его нет**: без `traefik.enable=true` Traefik контейнер даже не рассматривал. Лечение: добавить метку.
- **`new` → `502 Bad Gateway`**, роутер **есть**: Traefik нашёл правило, но по сервису никого нет — он стучится на порт `8080`, а `whoami` слушает `80`. Лечение: убрать метку порта (Traefik возьмёт порт контейнера сам) или поставить `80`.
- **`beta` → `504 Gateway Timeout`** (через ~30 секунд), роутер **есть**. В журнале два предупреждения: `Could not find network named "proxy" for container …` и `Defaulting to first available network …`. Контейнер не в сети `proxy`, поэтому Traefik взял **первую попавшуюся сеть** контейнера — но Traefik в ней не состоит, достучаться он не может и ждёт. Лечение: добавить `networks: [proxy]`.

**Починка.** Переписываем файл целиком, исправив все три:

```bash run
cd ~/traefik-lab/edge
cat > compose.broken.yaml <<'EOF'
name: broken

services:
  a-old:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.a-old.rule=Host(`old.shop.localhost`)
      - traefik.http.routers.a-old.entrypoints=web

  b-new:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.b-new.rule=Host(`new.shop.localhost`)
      - traefik.http.routers.b-new.entrypoints=web
      - traefik.http.services.b-new.loadbalancer.server.port=80

  c-beta:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.c-beta.rule=Host(`beta.shop.localhost`)
      - traefik.http.routers.c-beta.entrypoints=web

networks:
  proxy:
    external: true
EOF
docker compose -f compose.broken.yaml up -d 2>&1 | tail -3
sleep 3
for h in old new beta; do
  curl -s -o /dev/null -w "$h.shop.localhost -> HTTP %{http_code}\n" --max-time 10 http://$h.shop.localhost/
done
docker compose -f compose.broken.yaml down 2>&1 | tail -1
```

```out auto
```

Все три отвечают `200`, после чего стенд для поломок убран. Запомни таблицу «симптом → что искать»:

| Ответ | Роутер в дашборде | Причина |
|---|---|---|
| `404 page not found` | **нет** | нет `traefik.enable`, опечатка в имени метки, роутер с ошибкой (смотри дашборд) |
| `404 page not found` | **есть** | правило не совпало с запросом (имя, путь, вход) |
| `502 Bad Gateway` | есть | сервис есть, но **не отвечает**: неверный порт, приложение не стартовало |
| `504 Gateway Timeout` | есть | Traefik **не может достучаться** до сервиса: контейнер не в общей сети (`Could not find network…`) или медленный бэкенд |

### why
Эта таблица — половина ежедневной работы с Traefik. Три вопроса, которые разрешают почти любой случай: **есть ли роутер** (дашборд), **что пишет журнал Traefik** (`docker logs`), **отвечает ли сам сервис напрямую** (как мы делали в шаге 1.5).

### deep Команды по частям
`for h in old new beta; do …; done` — цикл по трём именам; `$h` подставляется в строку; `--max-time 45` (в починке 10) — ждать ответа не дольше указанного числа секунд. `jq … select(.name | test("old|new|beta"))` — оставить только роутеры, имя которых подходит под шаблон. `grep -E 'ERR|WRN'` — только строки ошибок и предупреждений. `docker compose -f … down` — убрать контейнеры этого файла (внешняя сеть `proxy` остаётся, она принадлежит проекту `edge`).

### deep Если не получилось
- **Для `new` вышел `404`, а не `502`** — метка порта не применилась; смотри роутеры в дашборде: если роутера нет, ищи причину в журнале.
- **Журнал пуст** — уровень `INFO` не показывает часть сообщений; временно поставь `log.level: DEBUG` в `traefik.yml` и перезапусти Traefik.
- **`network proxy declared as external, but could not be found`** — проект `edge` не запущен: `cd ~/traefik-lab/edge && docker compose up -d`.

### quiz
- По каким трём признакам различаются `404` без роутера, `404` с роутером и `502`?
- Почему для `old.shop.localhost` Traefik вообще не создал роутер?
- Какие три проверки делаешь по порядку, когда «опять 404»?

### links
- https://doc.traefik.io/traefik/routing/providers/docker/#traefikenable | traefik.enable | Traefik: traefik.enable
- https://doc.traefik.io/traefik/routing/services/#servers | порт сервиса | Traefik: servers
