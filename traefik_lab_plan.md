# 🧪 Traefik Lab — большая лаба

> Плана из интернета для этой лабы не было: план составлен из готовой `traefik.html` (пробелы определены по счёту ключевых слов в тексте) и документации Traefik. Общие правила — `plan/README.md` родительского репозитория `anitech-performance`: режимы «с нуля»/«продолжение», **стандарт подробности («каждое слово объяснено»)**, размер.

**Место в последовательности: №3 из 5** (после Docker); общий порядок прохождения и создания — `plan/README.md`, раздел «Последовательность работ».

## Что делаем с готовой лабой
Готовая `traefik.html` (3 сессии, ~10 ч) **переписывается в большую** (10 сессий, ~40 ч) в том же репозитории. Сохраняется ядро: модель EntryPoint → Router → Middleware → Service, labels, dashboard, цепочка middlewares, mkcert, Let’s Encrypt (staging), canary. Добавляются азбука, разбор каждого слова и недостающие темы: `retry`, `circuitBreaker`, `inFlightReq`, `ipAllowList`, sticky, mirroring, access log, метрики, DNS-challenge и wildcard, TLS options и mTLS, TCP/UDP, HTTP/3, proxy protocol, плагины, миграция v2 → v3.

## Паспорт

| | |
|---|---|
| Режим | **продолжение Docker-лабы** (берёт её CoffeeShop) **или самостоятельная**: в `starter/` лежат исходники CoffeeShop и `compose.yaml`; Docker объясняется в сессии 1 ровно в объёме, нужном для лабы |
| Размер | 10 сессий × ~4 ч = **~40 ч**, ~65 шагов |
| Сквозной проект | **CoffeeShop за Traefik**: API + frontend + PostgreSQL + Adminer, маршруты по домену и пути, защита, балансировка, TLS |
| Версия | **Traefik v3.7** (решение 03.10.2026) |
| Выход | `starter/` для Kubernetes-лабы: стек CoffeeShop и образ API |

## Сессии

### Сессия 1 · Азбука: прокси, HTTP, TLS (~4 ч)
**Слова:** HTTP-запрос/ответ, порт, DNS, домен, `Host`, TLS/сертификат, reverse proxy, forward proxy, балансировщик.
- 1.1 Что происходит от ввода адреса до страницы (DNS → TCP → TLS → HTTP)
- 1.2 Reverse proxy: проблема «много сервисов — один порт 443»; forward vs reverse
- 1.3 Traefik vs nginx vs Caddy: когда что (честно, с таблицей)
- 1.4 Минимум Docker для лабы (образ, контейнер, Compose, сети) — для режима «с нуля»; в режиме «продолжение» — проверка стартового состояния
- 1.5 Стенд: структура папок, режимы прохождения, как запустить CoffeeShop без Traefik и убедиться, что он работает
- 1.6 Домены на локальной машине: `/etc/hosts`, `*.localhost`, `curl --resolve`
- 🔨 «сайт не открывается по имени» — hosts/DNS/порт
- **Приёмка:** CoffeeShop отвечает по `http://shop.localhost:PORT`-подобным адресам без прокси

### Сессия 2 · Установка и первый маршрут (~4 ч)
**Слова:** статическая и динамическая конфигурация, provider, entryPoint, router, service, `whoami`.
- 2.1 Две конфигурации: статическая (при старте) и динамическая (на лету) — аналогия «устав и приказы»
- 2.2 `traefik.yml`: `entryPoints`, `providers`, `api`, `log` — каждое поле
- 2.3 Запуск Traefik в Docker, сокет Docker (риски: доступ к `docker.sock`, `:ro`, socket-proxy)
- 2.4 Первый сервис `whoami` и первый роутер по labels
- 2.5 Dashboard: что на нём видно, как читать роутеры/сервисы/middlewares
- 2.6 Podman/rootless — как ещё запустить
- 🔨 роутер есть, а 404: порт, сеть, `exposedByDefault`
- **Приёмка:** `whoami` доступен по имени через Traefik, виден в dashboard

### Сессия 3 · Docker provider и правила маршрутизации (~4 ч)
**Слова:** label, rule, `Host()`, `PathPrefix()`, `Headers()`, priority, entryPoint, network.
- 3.1 Как Traefik находит контейнеры (events Docker API), `exposedByDefault`, `traefik.enable`
- 3.2 Правила: `Host`, `HostRegexp`, `Path`, `PathPrefix`, `Headers`, `Method`, `Query`; сочетание `&&`/`||`
- 3.3 Приоритеты и конфликты правил (`priority`)
- 3.4 Несколько сетей, `traefik.docker.network`, порт сервиса `loadbalancer.server.port`
- 3.5 CoffeeShop: frontend по `Host`, API по `PathPrefix(/api)`, Adminer по поддомену
- 3.6 `traefik.http.routers.<имя>` — разбор именования label’ов
- 🔨 два роутера с одинаковым правилом — кто выигрывает
- **Приёмка:** три сервиса за одним адресом, маршруты по таблице

### Сессия 4 · Middlewares: преобразование запросов (~4 ч)
**Слова:** middleware, цепочка, `StripPrefix`, `AddPrefix`, `redirectScheme`, `headers`, `compress`, `basicAuth`.
- 4.1 Модель middleware и порядок цепочки
- 4.2 `StripPrefix`/`AddPrefix`/`ReplacePath`/`RedirectRegex`
- 4.3 `redirectScheme` (HTTP→HTTPS), `headers` (security headers, CORS)
- 4.4 `compress`, `basicAuth` (генерация хеша через `htpasswd`, **эскейп `$` в Compose**), `digestAuth`
- 4.5 `chain`: именованные цепочки и повторное использование
- 4.6 Защита dashboard и Adminer
- 🔨 `$` в хеше пароля «съедает» Compose
- **Приёмка:** `/api` без префикса у бэкенда, Adminer под паролем

### Сессия 5 · Надёжность и защита (~4 ч)
**Слова:** `rateLimit`, `inFlightReq`, `ipAllowList`, `retry`, `circuitBreaker`, `forwardAuth`.
- 5.1 `rateLimit` (`average`, `burst`, `period`, источник IP)
- 5.2 `inFlightReq`, `ipAllowList` (в v3 — не `ipWhiteList`), `ipStrategy`
- 5.3 `retry` и `circuitBreaker`: когда помогают и когда вредят (идемпотентность)
- 5.4 `forwardAuth`: внешний сервис проверки доступа
- 5.5 Нагрузочная проверка (`hey`/`ab`/`k6` — по выбору), чтение результатов
- 🔨 retry на не-идемпотентный POST — двойной заказ
- **Приёмка:** лишняя нагрузка получает 429, закрытая зона — 403, нестабильный бэкенд скрыт ретраями

### Сессия 6 · Балансировка и выкатка (~4 ч)
**Слова:** load balancer, round robin, weighted, sticky, healthcheck, canary, mirroring.
- 6.1 Несколько реплик, как Traefik их находит (`--scale`)
- 6.2 Healthcheck (`healthcheck.path/interval/timeout`), исключение больного экземпляра
- 6.3 Sticky sessions (cookie)
- 6.4 Weighted round robin: **canary** 90/10 (файловый провайдер)
- 6.5 Mirroring: теневой трафик на новую версию
- 6.6 Blue/green и постепенный перевод трафика
- 🔨 «все экземпляры unhealthy» — 503
- **Приёмка:** canary меняет долю трафика, больной экземпляр исключается

### Сессия 7 · TLS, часть 1: локальные сертификаты (~4 ч)
**Слова:** сертификат, цепочка, CA, приватный ключ, SAN, `mkcert`, TLS options.
- 7.1 Как работает TLS (рукопожатие, сертификат, цепочка доверия) — простыми словами
- 7.2 `mkcert`: установка локального CA, выпуск сертификата, где он лежит
- 7.3 Подключение сертификата (`tls.certificates`), `tls=true` на роутере
- 7.4 Редирект HTTP→HTTPS на уровне entryPoint
- 7.5 TLS options: `minVersion`, `cipherSuites`, `sniStrict`
- 7.6 **mTLS**: `clientAuth`, свой CA, клиентский сертификат, `curl --cert`
- 🔨 «certificate verify failed» / «unknown authority»
- **Приёмка:** `https://shop.localhost` без предупреждения; mTLS-зона отвечает только с сертификатом

### Сессия 8 · TLS, часть 2: Let’s Encrypt (~4 ч)
**Слова:** ACME, challenge, HTTP-01, TLS-ALPN-01, DNS-01, wildcard, staging, `acme.json`.
- 8.1 ACME-протокол простыми словами; лимиты Let’s Encrypt
- 8.2 `certificatesResolvers`, HTTP-01 в staging, `acme.json` (права `600`)
- 8.3 TLS-ALPN-01 и DNS-01: когда нужен какой; wildcard
- 8.4 DNS-провайдер: переменные окружения для токена (**токен — не в файлах репозитория**); если реального домена нет — разбор «на сухую» по конфигу и логам
- 8.5 HTTP/3 (QUIC): `http3`, UDP-порт, проверка `curl --http3`
- 8.6 Свой сервер: что менять при переходе с локальной машины (чтение и подготовка, без выкладки — правило «на сервер из лабы ничего не выкладывать»)
- 🔨 `acme.json` с неверными правами / лимит запросов
- **Приёмка:** сертификат staging получен (или сухой разбор пройден), HTTP/3 проверен

### Сессия 9 · TCP/UDP, файловый провайдер, IP клиента (~4 ч)
**Слова:** TCP-роутер, `HostSNI`, UDP, file provider, proxy protocol, `forwardedHeaders`, плагин, Yaegi.
- 9.1 Файловый провайдер: сервис вне Docker (на хосте), горячая перезагрузка
- 9.2 TCP-роутеры: PostgreSQL через Traefik (`HostSNI`, TLS passthrough/termination)
- 9.3 UDP-роутеры (DNS-сервис как пример)
- 9.4 Реальный IP клиента за несколькими прокси: `forwardedHeaders.trustedIPs`, proxy protocol
- 9.5 Плагины (Yaegi): как подключить, риски
- 9.6 Миграция v2 → v3: что сломалось (`ipWhiteList` → `ipAllowList`, синтаксис правил) и как переносить
- 🔨 подделка `X-Forwarded-For`
- **Приёмка:** `psql` через Traefik, в логе API реальный IP клиента

### Сессия 10 · Наблюдаемость и итоговый проект (~4 ч)
**Слова:** access log, метрики, Prometheus, Grafana, трассировка, SLO.
- 10.1 Access log: JSON, фильтры, поля, ротация; как найти один запрос
- 10.2 Метрики Prometheus (`metrics.prometheus`), Prometheus и Grafana в Compose (тяжело — предупредить)
- 10.3 Трассировка (обзор: OpenTelemetry)
- 10.4 Диагностика: «дерево вопросов» от 404/502/504 до причины
- 10.5 Итог: CoffeeShop за Traefik со всем: домены, middleware, балансировка, TLS, метрики
- 🔨 **Production Hell** без подсказок: 5 поломок (priority, TLS options, trustedIPs, entryPoint, healthcheck)
- **Приёмка:** стек поднимается одной командой; дашборды показывают трафик

**Справка:** симптом → причина → что делать (`404`, `502`, `504`, `Bad Gateway`, `no available server`, `certificate`…), команды, порты и процессы, глоссарий, 50 вопросов, «что дальше» (Kubernetes + Traefik как Ingress).

## Решения владельца (11.10.2026)
Переписать `traefik.html` в большую (10 сессий) — принято. DNS-challenge без домена — «на сухую»; нагрузочный инструмент — по умолчанию `k6` (уже знаком по лабе производительности Laravel); оба пункта делегированы, можно поменять.
