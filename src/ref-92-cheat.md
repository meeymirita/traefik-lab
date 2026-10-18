# 1 · Шпаргалка: метки, правила, middleware, команды | short: Шпаргалка | kind: ref
**Структура метки**

| Часть | Пример |
|---|---|
| роутер | ``traefik.http.routers.<имя>.rule=Host(`shop.localhost`)`` |
| вход и TLS | `…routers.<имя>.entrypoints=websecure`, `…routers.<имя>.tls=true`, `…routers.<имя>.tls.certresolver=le` |
| middleware на роутере | `…routers.<имя>.middlewares=a,b@file` |
| middleware (объект) | `traefik.http.middlewares.<имя>.<тип>.<поле>=значение` |
| сервис | `traefik.http.services.<имя>.loadbalancer.server.port=3000` |
| TCP / UDP | ``traefik.tcp.routers.<имя>.rule=HostSNI(`*`)``, `traefik.udp.routers.<имя>.entrypoints=dns` |
| общие | `traefik.enable=true`, `traefik.docker.network=proxy` |

**Правила роутера (v3)**

| Правило | Пример |
|---|---|
| `Host`, `HostRegexp` | ``Host(`a.com`, `b.com`)``, ``HostRegexp(`^[a-z]+\.a\.com$`)`` |
| `Path`, `PathPrefix`, `PathRegexp` | ``PathPrefix(`/api`)`` |
| `Header`, `HeaderRegexp` | ``Header(`X-Debug`, `1`)`` |
| `Method`, `Query`, `ClientIP` | ``Method(`POST`)``, ``Query(`beta`, `1`)`` |
| комбинация | ``Host(`a`) && (PathPrefix(`/x`) || !Method(`GET`))`` |
| приоритет | по умолчанию — длина правила; свой — `…routers.<имя>.priority=1000` |

**Middlewares (HTTP)**

| Тип | Что делает | Шаг |
|---|---|---|
| `stripprefix`, `addprefix`, `replacepath`, `replacepathregex` | меняют путь | 4.1–4.2 |
| `redirectregex`, `redirectscheme` | редирект | 4.2–4.3, 7.4 |
| `headers` | заголовки безопасности, CORS | 4.3 |
| `compress`, `basicauth`, `digestauth` | сжатие, пароль | 4.4 |
| `chain` | набор middleware | 4.5 |
| `ratelimit`, `inflightreq`, `ipallowlist` | защита от нагрузки и по IP | 5.1–5.2 |
| `retry`, `circuitbreaker` | устойчивость | 5.3 |
| `forwardauth` | внешняя проверка доступа | 5.4 |

**Сервисы:** `loadbalancer.healthcheck.path/interval/timeout` (6.2), `loadbalancer.sticky.cookie.name` (6.3), `weighted` и `mirroring` — только в файле (6.4–6.5).

**Статическая конфигурация (`traefik.yml`)**

```yaml
entryPoints:     { web: {address: ":80"}, websecure: {address: ":443", http3: {}} }
providers:       { docker: {exposedByDefault: false, network: proxy}, file: {directory: /etc/traefik/dynamic, watch: true} }
certificatesResolvers: { le: {acme: {email: …, storage: …, httpChallenge: {entryPoint: web}}} }
api: {dashboard: true}
accessLog: {format: json}
metrics: {prometheus: {entryPoint: metrics}}
```

**Команды**

| Команда | Что делает |
|---|---|
| `docker compose up -d` / `down` | поднять / убрать стек |
| `docker compose logs --no-log-prefix traefik` | журнал Traefik |
| `curl -s -u user:pass https://traefik.shop.localhost/api/http/routers \| jq` | роутеры (то же, что дашборд) |
| `…/api/http/services/<имя>@docker` | сервис и состояние адресов |
| `curl -sv https://…` | TLS и заголовки запроса и ответа |
| `curl -s -o /dev/null -w '%{http_code}\n' URL` | только код ответа |
| `docker compose config` | итоговая конфигурация после подстановок |
| `mkcert -install`, `mkcert имя …` | локальный CA и сертификаты |
| `htpasswd -nbB имя пароль` | хэш для `basicAuth` (в Compose — `$$`) |
| `./diagnose.sh URL`, `./smoke.sh` | дерево вопросов, проверка стека |

**Порты и процессы лабы**

| Порт | Кто слушает | Откуда |
|---|---|---|
| 80, 443/tcp, 443/udp | Traefik (входы `web`, `websecure`, HTTP/3) | 2.3, 7.3, 8.5 |
| 5432, 5433 | Traefik → PostgreSQL (TCP-роутеры) | 9.2 |
| 5353/udp | Traefik → CoreDNS (UDP-роутер) | 9.3 |
| 8082 | метрики Traefik (внутри сети) | 10.2 |
| 9090, 3001 | Prometheus, Grafana | 10.2 |
| 16686 | Jaeger | 10.3 |
| 8443, 15000, 8055 | учебный ACME-стенд (Pebble) | 8.2 |
| 3000, 8080, 8081 | сервисы CoffeeShop без прокси (только в 1.5) | 1.5 |
