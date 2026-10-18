# Сессия 1 · Азбука: прокси, HTTP, TLS
dur: ~3,5 ч

## 1.1 Что происходит от ввода адреса до страницы | short: От адреса до страницы | est: ~40 мин
### intro
**Слова шага:** *DNS*, *IP-адрес*, *порт*, *TCP*, *TLS*, *HTTP-запрос*, *заголовок `Host`*, *домен*.

:::tip Если совсем просто
Адрес в браузере — это как «улица Кофейная, дом 5, квартира 3». Сначала по названию улицы узнают, **в какой город ехать** (DNS: имя → IP-адрес). Потом **приезжают к дому** (TCP-соединение на порт). Потом **закрывают за собой дверь на замок** (TLS), чтобы никто не подслушал. И только потом **говорят, к кому пришли** (HTTP-запрос: «мне квартиру `shop.localhost`»). Эта последняя фраза — заголовок `Host` — и есть то, чем Traefik отличает один сайт от другого.
:::

```svg
@address-flow
```

Когда ты вводишь `https://example.com/menu`, браузер делает по порядку пять вещей:

1. **DNS.** Компьютер не знает, где находится `example.com`: ему нужен **IP-адрес** (например, `93.184.216.34`). Он спрашивает DNS-сервер — «телефонную книгу интернета» — и получает адрес.
2. **TCP.** Браузер открывает соединение с этим IP на **порту** (для `https` — 443, для `http` — 80). Порт — это «номер двери» на сервере: на одном IP может слушать много программ, каждая на своём порту.
3. **TLS.** Поверх соединения договариваются о шифровании: сервер показывает **сертификат** (паспорт сайта), браузер его проверяет. Дальше всё шифруется. (Подробно — в сессии 7.)
4. **HTTP-запрос.** Браузер отправляет текст: «`GET /menu`, заголовок `Host: example.com`». `Host` нужен, потому что на одном IP и одном порту может жить сотня сайтов.
5. **HTTP-ответ.** Сервер возвращает код (`200` — хорошо, `404` — нет такой страницы, `502` — сломался сервер за прокси) и тело страницы.

Посмотрим все пять стадий настоящими командами. `dig` показывает ответ DNS, а `curl -v` (*verbose*, «подробно») — ход TCP, TLS и HTTP. Мы оставляем только ключевые строки:

```bash run
dig +short example.com A
curl -sv https://example.com -o /dev/null 2>&1 | grep -iE '^\* (connected to|established connection|SSL connection using|  subject:|  issuer:)|^> (GET|Host:)|^< HTTP'
```

### result
```out auto
```

Читаем сверху вниз. Первые строки — IP-адреса, которые дал DNS (у тебя, скорее всего, будут другие: у больших сайтов их много). `Connected to …` (в новых версиях `curl` — `Established connection to …`) — шаг TCP: соединились с IP на порту 443. `SSL connection using TLSv1.3` — договорились о шифровании, `subject` и `issuer` — для кого выдан сертификат и кто его выдал. Строки с `>` — **то, что отправил curl** (метод и путь, заголовок `Host`), строка с `<` — **то, что ответил сервер** (`HTTP/2 200`).

Запомни одну мысль на всю лабу: **IP-адрес приводит на сервер, порт — к программе, а заголовок `Host` и путь решают, какой именно сайт отвечает.** Traefik — это программа, которая читает именно `Host` и путь и по ним разводит запросы.

### why
Почти любую проблему с сайтом можно локализовать, зная эти пять стадий. «Не открывается совсем» — скорее всего, остановились на стадии 1 или 2 (имя не нашлось или порт закрыт). «Предупреждение о сертификате» — стадия 3. «404 или 502» — стадии 4–5. Дальше в лабе мы будем постоянно спрашивать: *на какой стадии сломалось?* — и это сразу сужает поиск.

### deep Команды по частям
`dig +short example.com A`: `dig` — клиент DNS; `+short` — печатать только ответ; `A` — тип записи «имя → IPv4-адрес». `curl -sv https://example.com -o /dev/null`: `-s` — не показывать индикатор загрузки, `-v` — подробный ход соединения, `-o /dev/null` — тело страницы выбросить. `2>&1` — подробности `curl` печатает в поток ошибок, это перенаправляет их в обычный вывод, чтобы `grep` их видел. `grep -E '…'` оставляет только строки, подходящие под шаблон.

### deep Как ещё можно
- **Без терминала:** в браузере открой инструменты разработчика (F12 → вкладка Network), перезагрузи страницу и нажми на запрос: во вкладке *Headers* видны запрос и ответ, во вкладке *Timing* — время на DNS, соединение, TLS.
- **Только IP:** `ping example.com` (на Mac) покажет адрес, но не умеет `Host` и порты.
- **Другой DNS-сервер:** `dig @1.1.1.1 example.com` — спросить конкретный сервер.

### deep Если не получилось
- **`dig: command not found`** — на Mac он есть из коробки; если нет, `nslookup example.com` делает то же самое.
- **`curl: (6) Could not resolve host`** — не работает DNS или нет интернета (стадия 1).
- **Некоторые строки не появились** — формулировки зависят от версии `curl` (`Connected to` или `Established connection to`, разный отступ у `subject`); посмотри весь вывод без `grep`: `curl -sv https://example.com -o /dev/null`.

### quiz
- В каком порядке происходят DNS, TCP, TLS и HTTP при открытии `https://`-страницы?
- Чем порт отличается от IP-адреса и зачем нужен заголовок `Host`?
- На какой стадии останавливается запрос, если в ответ приходит «Could not resolve host»?

### links
- https://developer.mozilla.org/ru/docs/Web/HTTP/Overview | Обзор HTTP | MDN: обзор HTTP
- https://developer.mozilla.org/ru/docs/Web/HTTP/Headers/Host | заголовок Host | MDN: Host

## 1.2 Reverse proxy: один вход для многих сервисов | short: Reverse proxy | est: ~35 мин
### intro
**Слова шага:** *proxy (прокси)*, *reverse proxy (обратный прокси)*, *forward proxy (прямой прокси)*, *upstream (бэкенд)*, *TLS termination*, *балансировщик*.

:::tip Если совсем просто
Reverse proxy — **администратор на входе в бизнес-центр**. Все посетители идут к нему одному, называют, к кому пришли («в компанию `shop`»), и он провожает их в нужный кабинет. Посетители не знают номеров кабинетов и не бродят по коридорам. В кабинетах — ваши сервисы: сайт, API, база.
:::

```svg
@one-door
```

Допустим, у кофейни три программы: сайт, API и Adminer (веб-интерфейс к базе). Каждая слушает свой порт: `8080`, `3000`, `8081`. Для посетителя это неудобно: он должен помнить номера, а ещё нельзя повесить на все три один HTTPS-сертификат и одну защиту. К тому же порты `3000` и `8081` приходится открывать наружу — а наружу хочется показывать только один.

Решение — **reverse proxy** (обратный прокси). Это программа, которая:

- слушает **один** порт (80 и 443) и принимает **все** запросы;
- по `Host` и пути определяет, **какому сервису** он адресован;
- пересылает запрос туда (сервис называют *upstream* — «вышестоящий» или просто *бэкенд*) и возвращает ответ посетителю.

Заодно прокси удобно делать другие вещи «на входе»: шифровать (*TLS termination* — расшифровывать HTTPS на входе, а внутри сети говорить по простому HTTP), проверять пароль, считать запросы, делить нагрузку между копиями сервиса (*load balancing*, балансировка).

**Чем он отличается от forward proxy.** *Forward proxy* (прямой прокси) стоит **на стороне клиента**: твой компьютер говорит ему «сходи на сайт X за меня» (так работают корпоративные прокси) — сервер видит прокси, а не тебя. *Reverse proxy* стоит **на стороне сервера**: клиент даже не знает, что за ним несколько программ — он думает, что говорит с одним сайтом.

### result
Сравни две половины схемы глазами: слева клиент идёт к трём сервисам напрямую (три адреса, три порта, три сертификата), справа — к одному входу. Именно эту картину мы строим в лабе: к концу сессии 3 весь CoffeeShop открывается через `http://shop.localhost`, без единого номера порта.

### why
Прокси — это **точка контроля**. Всё, что хочется сделать для всех сервисов сразу (шифрование, защита паролем, ограничение скорости, логи), делается в одном месте, а не в каждом сервисе по отдельности. Кроме того, внутренние сервисы можно вообще не публиковать наружу: их видит только прокси.

### deep Как это связано с «шлюзом»
Когда прокси умеет ещё и проверять токены, ограничивать запросы и преобразовывать пути, его называют **API-шлюзом** (*API gateway*). Traefik — это reverse proxy со многими функциями шлюза, но без собственной бизнес-логики.

### deep Если не получилось понять разницу
Спроси себя: «кто знает про прокси — клиент или сервер?» Если клиент настраивает его у себя (адрес прокси в настройках сети) — это forward. Если клиент ничего не настраивал, а прокси просто стоит перед сервером — это reverse.

### quiz
- Какие проблемы решает один общий вход вместо трёх открытых портов?
- Чем reverse proxy отличается от forward proxy: чья «сторона» и кто знает о нём?
- Что такое TLS termination и где HTTPS заканчивается?

### links
- https://doc.traefik.io/traefik/ | документация Traefik | Traefik Docs
- https://developer.mozilla.org/ru/docs/Web/HTTP/Proxy_servers_and_tunneling | прокси и туннелирование | MDN: прокси-серверы

## 1.3 Traefik, nginx, Caddy: когда что | short: Traefik, nginx, Caddy | est: ~30 мин
### intro
**Слова шага:** *динамическая конфигурация*, *провайдер*, *автообнаружение*, *автоматический HTTPS*, *конфигурационный файл*.

:::tip Если совсем просто
nginx — **опытный повар с рецептами в блокноте**: что записали, то и приготовит; новый заказ — дописать в блокнот и сказать «перечитай». Caddy — **повар, который сам заказывает продукты (сертификаты)**: пишешь короткий рецепт, остальное он сделает сам. Traefik — **повар, который смотрит на доску заказов**: появился новый столик (контейнер) с запиской «меня обслуживать так-то» — он сам всё подстроит, не перезапуская кухню.
:::

Три программы решают одну задачу — reverse proxy. Различаются тем, **как они узнают, что куда пересылать**.

| | nginx 1.30 | Caddy 2 | Traefik v3 |
|---|---|---|---|
| Как описывается маршрут | файл `nginx.conf` | `Caddyfile` (короткий) или JSON | **метки (labels) на контейнерах**, YAML-файлы, ресурсы Kubernetes |
| Новый сервис появился | дописать в конфиг + `nginx -s reload` | дописать в `Caddyfile` + reload | **подхватывается сам**, без перезапуска |
| HTTPS и сертификаты | вручную или `certbot` | автоматически | автоматически (Let’s Encrypt) |
| Дашборд | нет в открытой версии | нет (есть админ-API) | **есть** (веб-интерфейс) |
| Лучше всего подходит | статика, высокая нагрузка, один-два сервиса | простой сервер «поставил и забыл» | **контейнеры и Kubernetes**, где сервисы часто появляются и исчезают |
| Цена | конфиг нужно править руками | меньше готовых «умных» функций вокруг контейнеров | своя терминология и «магия» из меток, которую надо уметь читать |

Правило большого пальца:

- один-два сайта на одном сервере — **Caddy** (если ты прошла Caddy-лабу, ты это уже знаешь);
- максимально быстрая раздача статики и тонкая настройка кэша — **nginx**;
- много контейнеров, которые поднимаются и гасятся (Docker Compose, Kubernetes), и не хочется править конфиг при каждом — **Traefik**.

Все три — хорошие инструменты. В лабе мы учим Traefik, потому что в связке «контейнеры + Kubernetes» он встречается очень часто (в K3s он стоит по умолчанию).

### result
Запускать здесь нечего: это шаг-сравнение. Но возьми таблицу с собой: на собеседовании вопрос «чем Traefik отличается от nginx» задают регулярно, и правильный ответ — «**конфигурация берётся из окружения, а не только из файла**».

### why
Знать три инструмента — значит выбирать по задаче, а не по привычке. Ошибка новичка — ставить Traefik на статический лендинг (лишний слой) или править `nginx.conf` вручную в стеке из пятидесяти контейнеров.

### deep Откуда у Traefik «магия»
Traefik подключается к источникам конфигурации — **провайдерам** (*providers*): Docker, файлы, Kubernetes и другие. Он слушает события («контейнер запущен», «контейнер остановлен») и пересобирает маршруты сам. Об этом — сессии 2 и 3.

### deep Что читать, чтобы сравнить глубже
- Документация по провайдерам Traefik — список всех источников конфигурации.
- Твоя Caddy-лаба: модель «конфигурационного файла» там описана подробно.

### quiz
- Чем принципиально отличается способ задания маршрутов в nginx и Traefik?
- Когда Traefik — лишний слой, а когда — естественный выбор?
- Что значит, что Traefik «подхватывает сервисы сам»?

### links
- https://doc.traefik.io/traefik/providers/overview/ | провайдеры конфигурации | Traefik: Providers
- https://doc.traefik.io/traefik/getting-started/concepts/ | основные понятия | Traefik: Concepts

## 1.4 Минимум Docker для этой лабы | short: Минимум Docker | est: ~40 мин
### intro
**Слова шага:** *образ (image)*, *контейнер*, *Docker Compose*, *сеть Docker*, *публикация порта*, *`docker.sock`*.

:::tip Если совсем просто
**Образ** — рецепт с готовыми продуктами в герметичной упаковке. **Контейнер** — блюдо, приготовленное по этому рецепту: запущенная программа в своей «кухне», которая не мешает соседним. **Compose** — меню на столик: один файл, в котором записано, какие блюда (контейнеры) подать вместе и как соединить их общей посудой (сетью).
:::

Если ты прошла Docker-лабу, смело пролистай до шага 1.5 — тут только то, что нужно для Traefik. Иначе — вот минимум.

- **Образ** — неизменяемый «пакет» с программой и всем, что ей нужно (`nginx:1.30-alpine`, `postgres:18`). Имя состоит из названия и **тега** (версии).
- **Контейнер** — запущенная копия образа: изолированный процесс со своими файлами и сетью.
- **Публикация порта** (`-p 8088:80`): «всё, что приходит на порт 8088 моего компьютера, отдай порту 80 контейнера». Без неё контейнер снаружи недоступен.
- **Сеть Docker.** Контейнеры в одной сети видят друг друга **по имени** (контейнер `db` доступен другим как хост `db`). Это важно для Traefik: он общается с сервисами по сети, а не через опубликованные порты.
- **Docker Compose** — файл `compose.yaml`, где описан весь стек: сервисы, сети, тома, переменные. Запуск — `docker compose up -d`.
- **`docker.sock`** — «служебный вход» Docker: через этот файл программа может спросить демон о запущенных контейнерах. Traefik читает его, чтобы узнавать о новых контейнерах (риски — в шаге 2.3).

Проверим, что всё работает, и сделаем маленький эксперимент: запустим nginx, откроем порт, обратимся и уберём за собой.

```bash run
docker version --format 'клиент {{.Client.Version}}, сервер {{.Server.Version}}'
docker compose version
docker run --rm alpine:3.22 echo "привет из контейнера"
docker run -d --name hello -p 8088:80 nginx:1.30-alpine
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
curl -sI http://localhost:8088 | head -3
docker rm -f hello
```

### result
```out auto
```

Вывод по строкам: версии клиента, сервера и Compose; фраза из одноразового контейнера (`--rm` — удалить после завершения); таблица запущенных контейнеров, где в колонке `PORTS` видна публикация порта 8088 хозяина на порт 80 контейнера; первые строки ответа nginx (`HTTP/1.1 200 OK`); и последним `docker rm -f hello` печатает имя удалённого контейнера.

### why
Traefik сам работает в контейнере и общается с твоими сервисами через сети Docker. Поэтому три вещи надо знать наизусть: **что такое порт контейнера и порт хозяина**, **что контейнеры в одной сети видят друг друга по имени**, и **что Compose описывает всё одним файлом**.

### deep Команды по частям
`docker run --rm alpine:3.22 echo …`: запустить контейнер из образа `alpine:3.22`, выполнить команду `echo` и удалить контейнер (`--rm`). `docker run -d --name hello -p 8088:80 nginx:1.30-alpine`: `-d` — в фоне, `--name hello` — имя, `-p 8088:80` — «порт хозяина:порт контейнера». `docker ps --format '…'` — таблица запущенных контейнеров с выбранными колонками (`\t` — разделитель). `curl -sI` — запросить только заголовки (`-I`), без индикатора (`-s`). `docker rm -f` — остановить и удалить.

### deep Как ещё можно
- **Docker Desktop:** вкладка Containers показывает то же самое мышкой, а у каждого контейнера есть кнопка открытия порта в браузере.
- **Другие движки:** Colima, OrbStack, Podman (команды `podman` почти те же) — в лабе используем Docker.

### deep Если не получилось
- **`Cannot connect to the Docker daemon` / `failed to connect to the docker API`** — Docker Desktop не запущен: открой приложение и дождись зелёного значка.
- **`port is already allocated`** — порт 8088 занят другой программой: возьми другой (`-p 8090:80`) и подставь его в `curl`.
- **`Conflict. The container name "/hello" is already in use`** — остался контейнер от прошлой попытки: `docker rm -f hello`.

### quiz
- В чём разница между образом и контейнером?
- Что делает `-p 8088:80` и какой из двух портов — портом хозяина?
- Почему контейнеры в одной сети Docker могут обращаться друг к другу по имени?

### links
- https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/ | что такое контейнер | Docker: что такое контейнер
- https://docs.docker.com/compose/intro/compose-application-model/ | модель Compose | Compose: application model

## 1.5 Стенд: CoffeeShop без прокси | short: Стенд CoffeeShop | est: ~60 мин
### intro
**Слова шага:** *сквозной проект*, *`compose.yaml`*, *`.env`*, *режим «с нуля»*, *режим «продолжение»*, *служебные адреса*.

:::tip Если совсем просто
Строим кофейню «как есть»: три входа с улицы (сайт, API, Adminer) на трёх разных дверях. Проверяем, что все работают. Потом, в следующих сессиях, объединим двери в одну.
:::

```svg
@shop-ports
```

Это шаг, где появляются **все файлы лабы**. Работаем в одной папке `~/traefik-lab` (тильда `~` — твоя домашняя папка). Структура после шага:

```text
~/traefik-lab/
└── coffeeshop/
    ├── .env                  # пароль базы
    ├── compose.yaml          # весь стек
    ├── db/init.sql           # таблицы и меню
    ├── api/
    │   ├── Dockerfile
    │   ├── package.json
    │   └── server.js         # API на Node.js
    └── web/
        ├── Dockerfile
        └── index.html        # сайт
```

**Режим «продолжение».** Если ты прошла Docker-лабу, у тебя есть свой проект. Его можно взять вместо файлов ниже, но проверь три вещи: сервисы называются `db`, `api`, `web`; API отвечает на `/menu` и `/health`; в нём нет привязки к порту сайта `80`. Если что-то не совпадает — проще создать файлы из этого шага, они небольшие.

Сначала создаём папки, файл `.env` и SQL базы:

```bash run
mkdir -p ~/traefik-lab/coffeeshop/{db,api,web} && cd ~/traefik-lab/coffeeshop
cat > .env <<'EOF'
DB_USER=coffee
DB_PASSWORD=change-me
DB_NAME=coffee
EOF
cat > db/init.sql <<'EOF'
CREATE TABLE menu (
  id    serial PRIMARY KEY,
  name  text NOT NULL,
  price integer NOT NULL
);
CREATE TABLE orders (
  id         serial PRIMARY KEY,
  menu_id    integer NOT NULL REFERENCES menu(id),
  idem_key   text UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO menu (name, price) VALUES ('Эспрессо', 150), ('Капучино', 220), ('Латте', 240);
EOF
ls -a . db
```

### result
```out auto
```

Теперь API. Он небольшой, но кроме меню и заказов в нём есть **служебные адреса для опытов**: на них мы будем тренировать балансировку, ретраи и проверки здоровья.

| Адрес | Что делает | Где понадобится |
|---|---|---|
| `GET /health` | `200 ok` (или `500`, если «заболел») | сессия 6, healthcheck |
| `GET /menu`, `GET /orders`, `POST /orders` | меню и заказы (у `POST` есть необязательный заголовок `Idempotency-Key`) | везде, шаг 5.6 |
| `GET /info` | кто ответил: имя хоста, версия, IP клиента, заголовки | сессии 3, 6, 9 |
| `GET /slow?ms=300` | отвечает с задержкой | сессия 5 |
| `GET /flaky?rate=0.5` | случайно отвечает `503` | сессия 5 |
| `GET /drop?rate=0.5` | случайно **обрывает соединение** без ответа | сессия 5 |
| `POST /orders?fail=after` / `?drop=after` | записывает заказ, но затем отвечает `503` / обрывает соединение | сессия 5 |
| `POST /sick`, `POST /heal` | «заболеть» и «выздороветь» | сессия 6 |

```bash run
cd ~/traefik-lab/coffeeshop
cat > api/package.json <<'EOF'
{
  "name": "coffeeshop-api",
  "private": true,
  "type": "module",
  "dependencies": { "express": "^5.1.0", "pg": "^8.13.0" }
}
EOF
cat > api/server.js <<'EOF'
import express from 'express'
import pg from 'pg'
import os from 'node:os'

const app = express()
app.use(express.json())

const VERSION = process.env.APP_VERSION || 'v1'
let sick = false

const pool = new pg.Pool({
  host: process.env.DB_HOST || 'db',
  user: process.env.DB_USER || 'coffee',
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME || 'coffee',
})

app.get('/health', (req, res) =>
  sick ? res.status(500).json({ status: 'sick' }) : res.json({ status: 'ok' }))
app.post('/sick', (req, res) => { sick = true; res.json({ status: 'sick' }) })
app.post('/heal', (req, res) => { sick = false; res.json({ status: 'ok' }) })

app.get('/info', (req, res) => {
  const h = req.headers
  res.json({
    service: 'api', version: VERSION, hostname: os.hostname(),
    path: req.originalUrl, remoteAddress: req.socket.remoteAddress,
    headers: {
      host: h['host'], 'x-forwarded-for': h['x-forwarded-for'], 'x-forwarded-proto': h['x-forwarded-proto'],
      'x-forwarded-host': h['x-forwarded-host'], 'x-real-ip': h['x-real-ip'], 'user-agent': h['user-agent'],
    },
  })
})

app.get('/slow', (req, res) => {
  const ms = Number(req.query.ms || 300)
  setTimeout(() => res.json({ slept: ms, hostname: os.hostname() }), ms)
})

app.get('/flaky', (req, res) => {
  const rate = Number(req.query.rate || 0.5)
  if (Math.random() < rate) return res.status(503).json({ error: 'flaky' })
  res.json({ ok: true, hostname: os.hostname() })
})

app.get('/drop', (req, res) => {
  const rate = Number(req.query.rate || 0.5)
  if (Math.random() < rate) return req.socket.destroy()
  res.json({ ok: true, hostname: os.hostname() })
})

app.get('/menu', async (req, res) => {
  const { rows } = await pool.query('SELECT id, name, price FROM menu ORDER BY id')
  res.json(rows)
})

app.post('/orders', async (req, res) => {
  const key = req.get('Idempotency-Key') || null
  let { rows } = await pool.query(
    'INSERT INTO orders (menu_id, idem_key) VALUES ($1, $2) ON CONFLICT (idem_key) DO NOTHING RETURNING id, menu_id, created_at',
    [req.body.menu_id, key])
  if (rows.length === 0) {   // такой ключ уже встречался: отдаём прежний заказ, а не создаём второй
    ;({ rows } = await pool.query('SELECT id, menu_id, created_at FROM orders WHERE idem_key = $1', [key]))
  }
  if (req.query.fail === 'after') return res.status(503).json({ error: 'сбой после записи' })
  if (req.query.drop === 'after') return req.socket.destroy()
  res.status(201).json(rows[0])
})

app.get('/orders', async (req, res) => {
  const { rows } = await pool.query(
    'SELECT o.id, m.name, m.price FROM orders o JOIN menu m ON m.id = o.menu_id ORDER BY o.id')
  res.json(rows)
})

app.listen(3000, () => console.log(`CoffeeShop API ${VERSION} слушает порт 3000`))
EOF
cat > api/Dockerfile <<'EOF'
FROM node:24-alpine
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev --no-fund --no-audit
COPY server.js ./
USER node
CMD ["node", "server.js"]
EOF
ls api
```

```out auto
```

Теперь сайт — одна страница, которая спрашивает у API меню и показывает кнопки заказа. Важная деталь: страница обращается к API по **относительному адресу `/api/menu`** — то есть «на тот же сайт, по пути `/api`». Пока прокси нет, такого адреса у сайта нет, и меню не загрузится — так и задумано, это наша проблема, которую решит Traefik. Заодно пишем `compose.yaml` — весь стек в одном файле:

```bash run
cd ~/traefik-lab/coffeeshop
cat > web/index.html <<'EOF'
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>CoffeeShop</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 520px; margin: 40px auto; padding: 0 16px }
    li { margin: 8px 0 } button { margin-left: 8px }
  </style>
</head>
<body>
  <h1>☕ CoffeeShop</h1>
  <ul id="menu">загружаю меню…</ul>
  <p id="msg"></p>
  <script>
    const msg = document.getElementById('msg')
    fetch('/api/menu')
      .then(r => { if (!r.ok) throw new Error('API ответил ' + r.status); return r.json() })
      .then(items => {
        document.getElementById('menu').innerHTML = items
          .map(i => `<li>${i.name} — ${i.price} ₽ <button data-id="${i.id}">Заказать</button></li>`).join('')
      })
      .catch(e => { document.getElementById('menu').textContent = 'Не удалось загрузить меню: ' + e.message })
    document.addEventListener('click', e => {
      if (!e.target.dataset.id) return
      fetch('/api/orders', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ menu_id: Number(e.target.dataset.id) }) })
        .then(r => r.json()).then(o => { msg.textContent = 'Заказ №' + o.id + ' принят' })
    })
  </script>
</body>
</html>
EOF
cat > web/Dockerfile <<'EOF'
FROM nginx:1.30-alpine
COPY index.html /usr/share/nginx/html/index.html
EOF
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
    ports:
      - "3000:3000"

  web:
    build: ./web
    ports:
      - "8080:80"

  adminer:
    image: adminer:5
    ports:
      - "8081:8080"

volumes:
  pgdata:
EOF
docker compose config -q && echo "compose.yaml корректен"
```

```out auto
```

Запускаем. Флаг `--build` соберёт образы `api` и `web`, `-d` оставит всё в фоне. Первый запуск скачивает образы, это занимает пару минут:

```bash run
cd ~/traefik-lab/coffeeshop
docker compose up -d --build > /dev/null 2>&1
sleep 8
docker compose ps --format 'table {{.Service}}\t{{.Status}}\t{{.Ports}}'
echo "--- сайт (порт 8080):"
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://localhost:8080/
echo "--- API напрямую (порт 3000):"
curl -s http://localhost:3000/menu; echo
echo "--- Adminer (порт 8081):"
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://localhost:8081/
echo "--- меню через сайт (как его просит страница):"
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://localhost:8080/api/menu
```

```out auto
```

Первые три проверки успешны: сайт, API и Adminer работают, **но у каждого свой порт**. Последняя даёт `404`: страница просит меню по `/api/menu`, а у nginx такого пути нет. Если открыть `http://localhost:8080` в браузере, вместо меню будет надпись «Не удалось загрузить меню: API ответил 404». Это и есть задача на следующие сессии: один вход, в котором `/` ведёт на сайт, а `/api` — на API.

### why
Мы специально собрали стенд **до** Traefik и убедились, что он работает по отдельности. Если потом что-то сломается, мы будем знать: проблема не в самих сервисах, а в маршрутизации. Это главное правило диагностики: сначала проверить сервис в обход прокси, потом — через прокси.

### deep Что в файлах важного
- В `compose.yaml` нет явной сети — Compose сам создаст общую сеть проекта, и сервисы будут видеть друг друга по именам `db`, `api`, `web`, `adminer`.
- `${DB_PASSWORD}` берётся из файла `.env` рядом с `compose.yaml`. Пароль в учебном проекте простой; в настоящем никогда не клади его в git.
- `$${POSTGRES_USER}` в `healthcheck` — удвоенный `$`: так Compose понимает, что подставлять нужно не ему, а оболочке внутри контейнера.
- В `api/Dockerfile` нет `package-lock.json`: для учебного проекта это упрощение; в рабочем коммить его и используй `npm ci`.

### deep Как ещё можно
- **Без Compose:** три `docker run` с общей сетью (`docker network create`) — но Traefik-лаба построена на Compose, потому что метки удобно писать в одном файле.
- **Свой API:** если у тебя уже есть API на другом языке — подойдёт, если у него есть `/health` и он отдаёт JSON; служебные адреса `/info`, `/slow`, `/flaky` нужны для опытов, их придётся добавить.

### deep Если не получилось
- **`bind: address already in use` на 8080/8081/3000** — порт занят другой программой на Mac: `lsof -i :8080` покажет какой; в `compose.yaml` поменяй левую цифру (`"8090:80"`) и в командах используй новый порт.
- **`api` перезапускается, в логах `ECONNREFUSED`** — база ещё не готова; `depends_on` с `service_healthy` обычно это решает, подожди 10–15 секунд и проверь `docker compose logs api`.
- **`password authentication failed`** — пароль в `.env` изменили после первого запуска: данные в томе старые. Убери стек вместе с томом: `docker compose down -v` и запусти заново.

### quiz
- Почему мы проверяем сервисы напрямую, до подключения Traefik?
- Почему страница получает `404` на `/api/menu` и чего ей не хватает?
- Какие три порта открыты у стенда сейчас и сколько должно остаться после подключения прокси?

### links
- https://docs.docker.com/compose/how-tos/environment-variables/ | переменные и .env в Compose | Compose: environment variables
- https://hub.docker.com/_/adminer | образ Adminer | Docker Hub: adminer

## 1.6 Имена на локальной машине: hosts, *.localhost, Host | short: Имена на локальной машине | est: ~40 мин
### intro
**Слова шага:** *`/etc/hosts`*, *`*.localhost`*, *`--resolve`*, *заголовок `Host`*, *виртуальный хост*.

:::tip Если совсем просто
Traefik смотрит на **имя в адресе**, а не на номер порта. Значит, на своём компьютере нам нужны **имена**: `shop.localhost`, `adminer.shop.localhost`. Компьютеру нужно подсказать, что все эти имена ведут на него самого. Есть три способа, от простого к «ручному».
:::

Раз Traefik различает сервисы по `Host`, нам нужны разные имена, которые указывают на наш Mac. Настоящих доменов у нас нет, поэтому есть три способа.

**Способ 1: имена `*.localhost`.** По стандарту любое имя, оканчивающееся на `.localhost`, обязано вести на твой собственный компьютер (`127.0.0.1`). Современные браузеры и `curl` так и делают: `shop.localhost`, `adminer.shop.localhost` работают **без настройки**. В лабе используем именно их. Одно уточнение: некоторые программы (старые версии `curl`, `ping`, часть языков) этого правила не знают — если имя не нашлось, переходи к способу 2.

**Способ 2: файл `/etc/hosts`.** Это «записная книжка» компьютера, которую он читает раньше, чем спросит DNS. Добавляешь строку `127.0.0.1 shop.example.test` (нужен `sudo`), и имя работает везде. Файл чистится вручную — не забывай убирать записи, которые больше не нужны.

**Способ 3: `curl --resolve` и заголовок `Host`.** Для проверок без правки системы: `curl --resolve shop.example.test:8080:127.0.0.1 http://shop.example.test:8080/` говорит `curl`: «имя `shop.example.test` на порту 8080 считай адресом `127.0.0.1`». Или совсем просто: подключаться по IP, но `Host` подставить вручную: `curl -H 'Host: shop.example.test' http://127.0.0.1:8080/`.

Проверим, как это выглядит. Сначала имя `*.localhost`, затем явный заголовок `Host`. Обрати внимание: nginx сайта **не смотрит** на `Host`, он отвечает одинаково на любое имя (у него единственный сайт). Traefik будет другим — он разведёт запросы по имени:

```bash run
curl -s -o /dev/null -w 'shop.localhost:8080 -> HTTP %{http_code}\n' http://shop.localhost:8080/
curl -s -o /dev/null -w 'localhost:8080 с Host: whatever.example -> HTTP %{http_code}\n' -H 'Host: whatever.example' http://localhost:8080/
curl -s -o /dev/null -w 'adminer.shop.localhost:8081 -> HTTP %{http_code}\n' http://adminer.shop.localhost:8081/
```

### result
```out auto
```

Все три запроса дают `200`: имена `*.localhost` работают, а nginx и Adminer не интересуются заголовком `Host`. Для Traefik имя будет решающим — это мы увидим в сессии 2.

### why
Когда в следующих сессиях Traefik вернёт `404`, надо уметь быстро понять: **запрос вообще дошёл до Traefik под правильным именем?** Привычка проверять `curl -v` и видеть, какой `Host` ушёл на сервер, экономит часы.

### deep Команды по частям
`curl -s -o /dev/null -w '…%{http_code}\n' URL`: `-s` — без индикатора, `-o /dev/null` — тело выбросить, `-w` — после запроса напечатать строку по шаблону (`%{http_code}` — код ответа). `-H 'Host: …'` — подменить заголовок: запрос пойдёт на адрес из URL, но сервер увидит другое имя.

### deep Как ещё можно
- **Wildcard-DNS:** сервисы вроде `nip.io` и `sslip.io` отвечают IP-адресом из самого имени: `shop.127.0.0.1.nip.io` → `127.0.0.1`. Удобно для демонстраций, но зависит от интернета.
- **dnsmasq на Mac:** локальный DNS-сервер с правилом `address=/.test/127.0.0.1` отдаёт любые `*.test`.
- **Правка /etc/hosts:** `sudo sh -c 'echo "127.0.0.1 shop.example.test" >> /etc/hosts'` (в прогоне методички не запускалось — это правка системы); убрать — `sudo nano /etc/hosts`.

### deep Если не получилось
- **`curl: (6) Could not resolve host: shop.localhost`** — твоя версия не знает правила `.localhost`: добавь строку в `/etc/hosts` (способ 2) или используй `--resolve`.
- **В браузере `shop.localhost` не открывается, а в `curl` открывается** — браузер мог закэшировать ошибку: открой окно инкогнито или очисти кэш DNS (`sudo dscacheutil -flushcache`).
- **`ERR_CONNECTION_REFUSED`** — имя нашлось, но на порту никого нет (стадия 2): проверь, что стек запущен.

### quiz
- Какими тремя способами можно добиться, чтобы имя вроде `shop.localhost` вело на твой компьютер?
- Что делает `curl -H 'Host: …' http://127.0.0.1:8080/` и когда это полезно?
- Почему для Traefik важно имя в адресе, а не только порт?

### links
- https://datatracker.ietf.org/doc/html/rfc6761#section-6.3 | RFC 6761: особые имена, localhost | RFC 6761 §6.3
- https://everything.curl.dev/usingcurl/connections/name | имена и разрешение в curl | Everything curl: имена

## 1.7 🔨 Сайт не открывается по имени | short: 🔨 Не открывается по имени | est: ~35 мин
### intro
**Слова шага:** *диагностика сверху вниз*, *стадия 1 (имя)*, *стадия 2 (порт)*, *код выхода curl*.

:::tip Если совсем просто
Сломаем доступ тремя способами подряд и научимся по сообщению понимать, **на какой стадии** он сломался: имя не нашлось, порт закрыт или сервер ответил «не то».
:::

Первая половина шага — поломка, вторая — починка. Цель: по тексту ошибки назвать стадию, не гадая. Три «поломки»:

```bash run
echo "1) имя, которого нет:"
curl -sS -o /dev/null http://coffee.nosuch.invalid:8080/ ; echo "код выхода curl: $?"
echo "2) порт, на котором никто не слушает:"
curl -sS -o /dev/null http://localhost:8099/ ; echo "код выхода curl: $?"
echo "3) сайт работает, но путь не тот:"
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://localhost:8080/menu
```

### result
```out auto
```

Читаем:

1. `Could not resolve host` (код `6`) — **стадия 1**: имя не нашлось. Лечение: правильно записать имя, проверить `/etc/hosts` или DNS.
2. `Failed to connect … Could not connect to server` (в старых `curl` — `Couldn't connect to server`, код `7`) — **стадия 2**: имя нашлось, но по порту никто не отвечает. Лечение: запущен ли контейнер (`docker compose ps`), верен ли порт.
3. `HTTP 404` — **стадии 1–3 прошли**, сервер ответил, но не знает такого пути. Лечение: правильный путь или правило маршрутизации.

**Починка** — это порядок вопросов. Всегда иди сверху вниз и останавливайся на первом «нет»:

1. Имя находится? (`curl -v` покажет `Trying …`; или `dig`, `getent hosts имя`)
2. Порт открыт? (`curl -v` покажет `Connected to` или `Connection refused`)
3. Ответил ли сервер? (код `200`/`404`/`502`…)
4. Если ответил — что в ответе (заголовки, тело) и что пишет сервис в `docker compose logs`?

### why
Эту «лесенку» мы будем использовать в каждой сессии. Когда придёт Traefik с его `404 page not found` или `502 Bad Gateway`, ты уже будешь знать, что каждый код живёт на своей ступени, и сможешь спросить не «почему не работает», а «на какой ступени остановился».

### deep Команды по частям
`curl -sS` — `-s` скрывает индикатор, `-S` всё же показывает **ошибку** (без `-S` при `-s` сообщение пропадает). `$?` — код выхода последней команды; у `curl` он значим: `6` — не нашёл имя, `7` — не соединился, `28` — таймаут, `35` — ошибка TLS. `echo "…: $?"` печатает его сразу после запуска.

### deep Если не получилось
- **Для имени из пункта 1 вышел `HTTP 200`** — твой провайдер подменяет несуществующие домены страницей-рекламой. Имена на `.invalid` по стандарту не существуют, но не все провайдеры это соблюдают; тогда проверь на мобильном интернете.
- **В пункте 2 вышел `200`** — на порту 8099 что-то запущено; возьми любой свободный.

### quiz
- По какому сообщению `curl` понятно, что остановка на стадии 1, а по какому — на стадии 2?
- Что значит `404` с точки зрения стадий: до какой он дошёл?
- Какова последовательность вопросов, если «сайт не открывается»?

### links
- https://everything.curl.dev/cmdline/exitcode | коды выхода curl | Everything curl: коды выхода
- https://developer.mozilla.org/ru/docs/Web/HTTP/Status | коды ответов HTTP | MDN: коды состояния
