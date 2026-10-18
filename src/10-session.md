# Сессия 10 · Наблюдаемость и итоговый проект
dur: ~4 ч

## 10.1 Журнал доступа: JSON, поля, фильтры | short: Журнал доступа | est: ~50 мин
### intro
**Слова шага:** *access log (журнал доступа)*, *JSON-формат*, *поля журнала*, *фильтры*, *`X-Request-Id`*, *ротация*.

:::tip Если совсем просто
Журнал доступа — это **книга посетителей**: на каждого пришедшего одна строка — кто, куда, что получил, как быстро. Когда что-то пошло не так, первым делом открывают эту книгу. Мы научимся записывать её в удобном виде и быстро находить в ней одного посетителя.
:::

Мы включили `accessLog: {}` ещё в шаге 2.2, но читали его мало. Есть **два формата**: обычный текстовый (одна строка в стиле «как у nginx») и **JSON** (одна строка = один объект с полями). JSON удобнее: его читают `jq`, Loki, Elasticsearch. Что полезно в нём искать:

| Поле | Что это |
|---|---|
| `RequestHost`, `RequestPath`, `RequestMethod` | какой адрес и метод запросил клиент |
| `RouterName`, `ServiceName` | **какой роутер и сервис** обработали запрос (пригодится при «странных» ответах, шаг 3.7) |
| `DownstreamStatus` | код ответа **клиенту** (`OriginStatus` — код, который дал бэкенд) |
| `Duration` | сколько длился запрос, **в наносекундах** |
| `ClientHost` | адрес клиента (шаг 9.4) |
| `entryPointName` | через какой вход пришёл |

Поля настраиваются, а лишнее — отфильтровывается: можно записывать **только ошибки** (`statusCodes`), **только медленные** (`minDuration`) или отброшенные повторы (`retryAttempts`). Заголовки по умолчанию **не пишутся** (там пароли!) — нужные включают поимённо. Главный приём: клиент присылает **идентификатор запроса** (`X-Request-Id`), и по нему находят его строку в журнале. Включим JSON и этот заголовок:

```bash run
cd ~/traefik-lab/edge
cat > traefik/traefik.yml <<'EOF'
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
          permanent: true
  websecure:
    address: ":443"
    http3: {}
    forwardedHeaders:
      trustedIPs:
        - "10.99.99.99/32"
  pg:
    address: ":5432"
  pgtls:
    address: ":5433"
  dns:
    address: ":5353/udp"

providers:
  docker:
    exposedByDefault: false
    network: proxy
  file:
    directory: /etc/traefik/dynamic
    watch: true

experimental:
  localPlugins:
    myheader:
      moduleName: github.com/mira/myheader

api:
  dashboard: true

log:
  level: INFO
  noColor: true

accessLog:
  format: json
  fields:
    defaultMode: keep
    headers:
      defaultMode: drop            # заголовки по умолчанию не пишем: там могут быть пароли
      names:
        X-Request-Id: keep         # а этот — пишем
EOF
docker compose restart traefik 2>&1 | tail -1
sleep 5
curl -s -o /dev/null https://shop.localhost/
curl -s -o /dev/null https://shop.localhost/api/menu
curl -s -o /dev/null -H 'X-Request-Id: order-4242' https://shop.localhost/api/nope
curl -s -o /dev/null -u mira:wrong https://adminer.shop.localhost/
sleep 1
echo "--- последние четыре строки журнала доступа (только нужные поля):"
docker compose logs --no-log-prefix traefik 2>&1 | grep '^{' | tail -4 | jq -r '[.RequestHost, .RequestPath, .DownstreamStatus, .RouterName, .ServiceName] | @tsv'
echo "--- найти один запрос по идентификатору:"
docker compose logs --no-log-prefix traefik 2>&1 | grep '^{' | jq -c 'select(.["request_X-Request-Id"] == "order-4242") | {id: .["request_X-Request-Id"], path: .RequestPath, status: .DownstreamStatus, router: .RouterName}'
```

### result
```out auto
```

Видно, **какой роутер и сервис ответили** на каждый запрос и с каким кодом: `/` — сайт, `/api/menu` — API, `/api/nope` — API ответил `404` (такого адреса нет у приложения, а не у Traefik: `RouterName` указывает на `coffee-api`), Adminer с неверным паролем — `401`. По идентификатору `order-4242` найден один запрос. Если приложение тоже **записывает `X-Request-Id`** в свои журналы, по этому одному значению можно собрать картину запроса от входа до базы — это основа расследований.

**Фильтры и ротация.** Чтобы не хранить гигабайты, журнал фильтруют (в настоящем стенде пишут, например, только ошибки и медленные запросы):

```yaml
accessLog:
  format: json
  filePath: /var/log/traefik/access.log
  bufferingSize: 100
  filters:
    statusCodes: ["400-599"]
    minDuration: 500ms
```

Файл журнала **не вращается сам**: его вращает внешняя утилита (`logrotate`), а после ротации Traefik нужно послать сигнал `USR1`, чтобы он открыл новый файл. Когда журнал идёт в стандартный вывод контейнера (как у нас), вращением занимается Docker (`logging.options.max-size` — как в шаге 9.4 Docker-лабы).

### why
Журнал доступа отвечает на вопрос «а что на самом деле происходило», который не покажет ни дашборд, ни метрики. Три поля решают большинство расследований: **`RouterName`** (кто обработал), **`DownstreamStatus`** (что получил клиент) и **`Duration`** (сколько ждал). А идентификатор запроса связывает журнал Traefik с журналами приложения.

### deep Команды по частям
`accessLog.format: json` — JSON вместо текста. `fields.defaultMode: keep` — писать все поля, `fields.headers.defaultMode: drop` — заголовки не писать, `names.X-Request-Id: keep` — кроме этого. `docker compose logs --no-log-prefix traefik | grep '^{'` — оставить только строки журнала доступа (обычный журнал Traefik — текст, а не JSON). `jq -r '[…] | @tsv'` — выбрать поля в таблицу. `select(.["request_X-Request-Id"] == "…")` — отобрать записи с нужным заголовком (имя поля — `request_` + имя заголовка).

### deep Как ещё можно
- **Файл вместо стандартного вывода:** `filePath` и монтирование папки — удобно, если журнал забирает агент (Filebeat, Vector).
- **Нужен идентификатор «из воздуха»:** Traefik сам его не создаёт; его добавляют на балансировщике перед Traefik или плагином (шаг 9.5).
- **Loki/Grafana:** журнал в JSON хорошо ложится в Loki; поля становятся метками для поиска.

### deep Если не получилось
- **`jq: parse error`** — в поток попали обычные текстовые строки: в команде есть `grep '^{'`, оставляющий только JSON.
- **Запись с `X-Request-Id` не найдена** — заголовок не включён в `fields.headers.names` или Traefik не перезапущен после правки.
- **Строк журнала нет** — `accessLog` может быть отключён или фильтры слишком строгие; проверь `traefik.yml` и `docker compose logs traefik`.

### quiz
- Чем JSON-журнал удобнее текстового и какие три поля важнее всего при расследовании?
- Зачем заголовки по умолчанию не пишутся в журнал?
- Как найти в журнале один запрос, если у клиента есть `X-Request-Id`?

### links
- https://doc.traefik.io/traefik/reference/install-configuration/observability/logs-and-accesslogs/ | журналы Traefik | Traefik: logs and access logs
- https://jqlang.github.io/jq/manual/ | руководство по jq | jq: manual

## 10.2 Метрики Prometheus и Grafana | short: Метрики | est: ~70 мин
### intro
**Слова шага:** *метрика*, *Prometheus*, *scrape*, *счётчик (`counter`)*, *гистограмма*, *Grafana*, *дашборд*, *RED (rate, errors, duration)*.

:::tip Если совсем просто
Журнал отвечает «что случилось с этим запросом». Метрики отвечают «**как идут дела вообще**»: сколько запросов в секунду, какая доля ошибок, как быстро отвечаем. Это приборная панель автомобиля: не про каждую кочку, а про общую картину. Prometheus собирает показания приборов, Grafana рисует панель.
:::

```svg
@metrics-flow
```

Traefik умеет отдавать метрики в формате Prometheus на отдельном входе. **Prometheus** сам **опрашивает** (*scrape*) этот адрес раз в несколько секунд и хранит числа во времени; **Grafana** строит по ним графики. Главное, что мы хотим видеть (метод **RED**): **Rate** — запросов в секунду, **Errors** — доля ошибок, **Duration** — время ответа (обычно `p95`).

> ⚠️ **Тяжёлый шаг.** Prometheus и Grafana вместе занимают заметную память и скачивают образы (Grafana — около 400 МБ). Запускай, когда ноутбук свободен; после шага стек можно остановить (`docker compose down`).

Добавляем в Traefik **вход для метрик** (`:8082`, наружу не публикуется — только внутри сети Docker) и блок `metrics.prometheus`, а рядом поднимаем Prometheus и Grafana:

```bash run
cd ~/traefik-lab/edge
cat > traefik/traefik.yml <<'EOF'
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
          permanent: true
  websecure:
    address: ":443"
    http3: {}
    forwardedHeaders:
      trustedIPs:
        - "10.99.99.99/32"
  pg:
    address: ":5432"
  pgtls:
    address: ":5433"
  dns:
    address: ":5353/udp"
  metrics:
    address: ":8082"

providers:
  docker:
    exposedByDefault: false
    network: proxy
  file:
    directory: /etc/traefik/dynamic
    watch: true

experimental:
  localPlugins:
    myheader:
      moduleName: github.com/mira/myheader

metrics:
  prometheus:
    entryPoint: metrics
    addEntryPointsLabels: true
    addRoutersLabels: true
    addServicesLabels: true

api:
  dashboard: true

log:
  level: INFO
  noColor: true

accessLog:
  format: json
  fields:
    defaultMode: keep
    headers:
      defaultMode: drop
      names:
        X-Request-Id: keep
EOF
docker compose restart traefik 2>&1 | tail -1
mkdir -p ~/traefik-lab/monitoring/grafana/provisioning/datasources ~/traefik-lab/monitoring/grafana/provisioning/dashboards ~/traefik-lab/monitoring/grafana/dashboards
cd ~/traefik-lab/monitoring
cat > prometheus.yml <<'EOF'
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: traefik
    static_configs:
      - targets: ["traefik:8082"]      # имя контейнера Traefik в сети proxy
EOF
cat > grafana/provisioning/datasources/prometheus.yml <<'EOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF
cat > grafana/provisioning/dashboards/traefik.yml <<'EOF'
apiVersion: 1
providers:
  - name: traefik
    type: file
    options:
      path: /var/lib/grafana/dashboards
EOF
cat > grafana/dashboards/traefik-red.json <<'EOF'
{
  "title": "Traefik: RED",
  "uid": "traefik-red",
  "schemaVersion": 39,
  "refresh": "5s",
  "time": { "from": "now-15m", "to": "now" },
  "panels": [
    { "type": "timeseries", "title": "Запросов в секунду по сервисам", "gridPos": { "x": 0, "y": 0, "w": 12, "h": 8 },
      "targets": [ { "expr": "sum by (service) (rate(traefik_service_requests_total[1m]))", "legendFormat": "{{service}}" } ] },
    { "type": "timeseries", "title": "Доля ошибок 5xx", "gridPos": { "x": 12, "y": 0, "w": 12, "h": 8 },
      "targets": [ { "expr": "sum(rate(traefik_service_requests_total{code=~\"5..\"}[1m])) / sum(rate(traefik_service_requests_total[1m]))", "legendFormat": "5xx" } ] },
    { "type": "timeseries", "title": "p95 времени ответа, секунды", "gridPos": { "x": 0, "y": 8, "w": 24, "h": 8 },
      "targets": [ { "expr": "histogram_quantile(0.95, sum by (le) (rate(traefik_service_request_duration_seconds_bucket[1m])))", "legendFormat": "p95" } ] }
  ]
}
EOF
cat > compose.yaml <<'EOF'
name: monitoring

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "9090:9090"
    networks: [proxy]

  grafana:
    image: grafana/grafana:latest
    environment:
      GF_AUTH_ANONYMOUS_ENABLED: "true"        # только для учебного стенда
      GF_AUTH_ANONYMOUS_ORG_ROLE: Admin
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
    ports:
      - "3001:3000"
    networks: [proxy]

networks:
  proxy:
    external: true
EOF
docker compose up -d 2>&1 | tail -2
echo "--- создаём трафик: 60 запросов к сайту и API, 10 несуществующих адресов:"
for i in $(seq 1 60); do curl -s -o /dev/null https://shop.localhost/; curl -s -o /dev/null https://shop.localhost/api/menu; done
for i in $(seq 1 10); do curl -s -o /dev/null https://shop.localhost/api/nope; done
sleep 12
echo "--- Prometheus: число запросов по кодам ответа (метрика traefik_service_requests_total):"
curl -s http://localhost:9090/api/v1/query --data-urlencode 'query=sum by (code) (traefik_service_requests_total{service=~"coffee.*"})' | jq -r '.data.result[] | [.metric.code, .value[1]] | @tsv' | sort
```

### result
```out auto
```

Prometheus получил показания Traefik и посчитал запросы **по кодам ответа**: сайт и API дали `200`, несуществующие адреса API — `404`. (Метрики Traefik бывают по входам — `traefik_entrypoint_*`, по роутерам — `traefik_router_*` и по сервисам — `traefik_service_*`; мы включили метки для всех трёх.) Откроем браузером:

- **Prometheus:** `http://localhost:9090` — вкладка Graph, запрос `sum by (code) (rate(traefik_service_requests_total[1m]))`.
- **Grafana:** `http://localhost:3001` — **Dashboards → Traefik: RED**: три графика (запросы в секунду по сервисам, доля ошибок `5xx`, `p95` времени ответа). Дашборд подключён заранее — через **provisioning**: файлы в папке `grafana/`, которые Grafana читает при запуске (так не нужно кликать мышкой каждый раз).

Проверим, что Grafana увидела наш дашборд и источник данных (откроем её API, вместо того чтобы смотреть глазами):

```bash run
sleep 10
curl -s 'http://localhost:3001/api/search?query=Traefik' | jq -r '.[] | [.title, .uid] | @tsv'
curl -s http://localhost:3001/api/datasources | jq -r '.[] | [.name, .type, .url] | @tsv'
```

```out auto
```

Дашборд `Traefik: RED` и источник `Prometheus` на месте. Как читать RED-панель: **запросов в секунду** — норма твоей нагрузки (резкое падение до нуля — тоже тревога), **доля `5xx`** должна быть около нуля (ошибки `4xx` — чаще вина клиента, `5xx` — наша), **`p95`** — «95% запросов быстрее этого значения».

### why
Метрики заменяют «посмотрим журнал, когда пожалуются» на «видим раньше жалоб». Три RED-показателя отвечают на главный вопрос «в порядке ли сервис» за секунды. А когда график показывает, **что** изменилось и **когда**, журнал доступа (10.1) отвечает **почему**: нужная строка ищется по времени и роутеру.

### deep Команды по частям
`metrics.prometheus.entryPoint: metrics` — отдавать метрики на отдельном входе `:8082` (не публикуется наружу, поэтому закрыт от посторонних). `addRoutersLabels` и `addServicesLabels` — добавить метки роутера и сервиса (без них метрики только по входам). `scrape_interval: 5s` — как часто Prometheus опрашивает. `sum by (code) (…)` — суммировать по коду ответа. `rate(…[1m])` — скорость роста счётчика за минуту. `histogram_quantile(0.95, …)` — 95-й перцентиль из гистограммы. `GF_AUTH_ANONYMOUS_*` — вход в Grafana без пароля (**только для учебного стенда!**).

### deep Как ещё можно
- **Готовый дашборд из каталога:** на grafana.com есть дашборд Traefik (ID 17346) — импортируется кнопкой `Import`; в нём больше панелей.
- **Алерты:** `Alertmanager` или встроенные алерты Grafana: «5xx > 5% в течение 5 минут» → сообщение в чат.
- **Другие системы:** Traefik отдаёт метрики также в OpenTelemetry, Datadog, InfluxDB, StatsD.

### deep Если не получилось
- **Prometheus не видит цель (`DOWN` во вкладке Status → Targets)** — Prometheus не в сети `proxy` или Traefik не перезапущен после включения метрик; проверь `docker compose logs prometheus`.
- **Пустой результат запроса** — не прошло 5–10 секунд с первого запроса или трафика ещё не было; повтори запросы.
- **Grafana долго стартует** — первая загрузка занимает до минуты; подожди и повтори запрос к API.
- **Тормозит ноутбук** — останови мониторинг: `cd ~/traefik-lab/monitoring && docker compose down`.

### quiz
- Чем метрики отличаются от журнала доступа и когда нужно что?
- Что означают три буквы RED и как они выражены запросами к Prometheus?
- Зачем метрики отдаются на отдельном входе, не опубликованном наружу?

### links
- https://doc.traefik.io/traefik/reference/install-configuration/observability/metrics/ | метрики Traefik | Traefik: metrics
- https://prometheus.io/docs/prometheus/latest/querying/basics/ | запросы PromQL | Prometheus: querying basics

## 10.3 Трассировка: OpenTelemetry и Jaeger | short: Трассировка | est: ~45 мин
### intro
**Слова шага:** *трассировка (tracing)*, *трейс (trace)*, *спан (span)*, *OpenTelemetry (OTel)*, *OTLP*, *Jaeger*, *семплирование*.

:::tip Если совсем просто
Метрики говорят «в среднем медленно». Журнал говорит «этот запрос был медленный». Трассировка говорит **«в этом запросе 80% времени ушло вот на этот шаг»**: она рисует путь одного запроса через все службы с временем на каждом отрезке — как маршрут посылки с отметками на каждой остановке.
:::

**Трасса** (*trace*) — путь одного запроса через систему; она состоит из **спанов** (*spans*) — отрезков работы со временем начала и конца (например, «Traefik принял запрос», «API сходил в базу»). **OpenTelemetry** — стандарт, по которому приложения и прокси отправляют трассы в хранилище (**OTLP** — формат передачи). Traefik умеет создавать спаны для приёма запроса на входе и для передачи сервису и отправлять их через OTLP. Показывать трассы можно в **Jaeger** (или Tempo, Zipkin).

В нашем стенде спаны создаёт **только Traefik** (приложение мы не меняли), поэтому в трассе видны «вход → роутер → сервис». Если приложение тоже отправляет спаны, в той же трассе появляются и его отрезки — до самой базы. Подключим Jaeger и включим трассировку (статическая настройка — снова перезапуск):

```bash run
cd ~/traefik-lab/edge
awk '/^accessLog:/ {print "tracing:"; print "  serviceName: traefik"; print "  sampleRate: 1.0"; print "  otlp:"; print "    http:"; print "      endpoint: http://jaeger:4318/v1/traces"; print ""} {print}' traefik/traefik.yml > /tmp/traefik.tracing.yml && cat /tmp/traefik.tracing.yml > traefik/traefik.yml
grep -A6 '^tracing' traefik/traefik.yml
mkdir -p ~/traefik-lab/tracing && cd ~/traefik-lab/tracing
cat > compose.yaml <<'EOF'
name: tracing

services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
    networks: [proxy]

networks:
  proxy:
    external: true
EOF
docker compose up -d 2>&1 | tail -1
cd ~/traefik-lab/edge
docker compose restart traefik 2>&1 | tail -1
sleep 12
for i in $(seq 1 5); do curl -s -o /dev/null https://shop.localhost/api/menu; done
sleep 8
echo "--- службы, которые видит Jaeger:"
curl -s http://localhost:16686/api/services | jq -r '.data[]' | sort
echo "--- спаны одной трассы запроса к API:"
curl -s 'http://localhost:16686/api/traces?service=traefik&limit=1' | jq -r '.data[0].spans[] | .operationName' | sort | uniq -c
```

### result
```out auto
```

Jaeger получил трассы от службы `traefik`. В одной трассе — **два спана** (в нашем стенде): `GET` — приём запроса на входе и `ReverseProxy` — передача сервису; у каждого записано время начала и конца. Откроем интерфейс: **`http://localhost:16686`** → служба `traefik` → `Find Traces`: каждая трасса — «лесенка» из спанов с длительностью, а при клике на спан видны атрибуты (адрес, метод, код ответа).

**Семплирование.** Записывать **каждый** запрос в боевой системе дорого. `sampleRate: 1.0` — записывать все (для учебного стенда); в настоящей системе ставят `0.01–0.1` (1–10% запросов) или решают «по хвосту» (сохраняют медленные и ошибочные).

### why
Трассировка нужна, когда запрос проходит **несколько служб** и непонятно, на какой он тормозит: метрики покажут «долго», журнал каждой службы — свои куски, а трасса сводит их воедино. Для одного сервиса за Traefik она избыточна; для десятка микросервисов — один из главных инструментов.

### deep Команды по частям
`awk '/^accessLog:/ {print …} {print}'` — перед строкой `accessLog:` напечатать блок `tracing`, затем каждую строку файла как есть (запись через временный файл и `cat … >` работает одинаково на Mac и Linux). `tracing.serviceName` — под каким именем Traefik виден в Jaeger. `otlp.http.endpoint` — куда отправлять спаны (порт `4318` — стандартный для OTLP по HTTP). Jaeger принимает OTLP «из коробки» в образе `all-in-one`. `curl /api/traces?service=traefik&limit=1` — одна последняя трасса через API Jaeger.

### deep Как ещё можно
- **Заголовки трассировки:** между службами идёт заголовок `traceparent` (стандарт W3C): Traefik создаёт его и передаёт приложению, чтобы то продолжило **ту же** трассу.
- **Grafana Tempo:** современное хранилище трасс, хорошо сочетается с Loki и Prometheus.
- **Не включать вовсе:** для небольших проектов достаточно журнала и метрик.

### deep Если не получилось
- **Список служб пуст** — Traefik не перезапущен после включения `tracing` или Jaeger ещё стартует; подожди 10–20 секунд и повтори запросы.
- **В журнале Traefik ошибки отправки спанов (`connection refused`)** — Traefik не в одной сети с `jaeger` или неверный адрес `endpoint`.
- **Нет образа `jaegertracing/all-in-one`** — возьми любой другой коллектор OTLP; для понимания идеи достаточно текста шага.

### quiz
- Чем трасса отличается от метрики и от строки журнала?
- Что такое спан и что в нашем стенде создаёт спаны?
- Зачем нужно семплирование трасс?

### links
- https://doc.traefik.io/traefik/reference/install-configuration/observability/tracing/ | трассировка в Traefik | Traefik: tracing
- https://opentelemetry.io/docs/concepts/signals/traces/ | трассы в OpenTelemetry | OpenTelemetry: traces

## 10.4 Дерево вопросов: от 404, 502, 504 до причины | short: Дерево вопросов | est: ~55 мин
### intro
**Слова шага:** *диагностика по дереву*, *скрипт-диагност*, *404 / 502 / 503 / 504*, *роутер*, *сервис*, *middleware*.

:::tip Если совсем просто
Когда пациент жалуется «болит», врач не лечит наугад, а идёт по списку вопросов: где, как давно, что принимал. Мы сведём всё, что узнали за десять сессий, в **такой список для Traefik**: на каждый код ответа — свой короткий маршрут к причине.
:::

```svg
@diagnostic-tree
```

Ответ — самая важная улика. Вот дерево, по которому мы работали всю лабу:

| Что видишь | Первый вопрос | Где смотреть |
|---|---|---|
| **нет ответа (`000`)** | дошёл ли запрос до Traefik? | имя (`dig`/`/etc/hosts`), порт (опубликован?), TLS (`curl -v`, шаг 7.7) |
| **`404 page not found`** | есть ли **роутер**, подходящий под запрос? | дашборд → роутеры: правило, вход (`entryPoints`), приоритет; есть ли `traefik.enable`, сеть, имя метки (шаги 2.7, 3.7) |
| **`401` / `403`** | какой **middleware** вернул отказ? | `basicAuth`, `ipAllowList`, `forwardAuth`, mTLS (сессии 4, 5, 7) |
| **`429`** | сработал `rateLimit` / `inFlightReq` | числа лимитов (шаг 5.1) |
| **`502 Bad Gateway`** | отвечает ли **сервис** на своём порту? | порт (`loadbalancer.server.port`), контейнер упал, обрыв соединения (шаги 2.7, 3.4) |
| **`503 no available server`** | есть ли здоровые копии? | `serverStatus` (healthcheck, шаг 6.7), `circuitBreaker` (шаг 5.3) |
| **`504 Gateway Timeout`** | достучался ли Traefik до сервиса по сети? | общая сеть, медленный бэкенд (шаги 2.7, 3.4) |

Чтобы не проходить эти вопросы вручную, соберём **скрипт-диагност**: ему даёшь адрес, он делает запрос, смотрит ответ и показывает, что Traefik знает про этот адрес — роутеры, сервисы, их здоровье:

```bash run
mkdir -p ~/traefik-lab/tools && cd ~/traefik-lab/tools
cat > diagnose.sh <<'EOF'
#!/usr/bin/env bash
# Дерево вопросов Traefik: ./diagnose.sh https://shop.localhost/api/menu
URL=$1
API=${TRAEFIK_API:-https://traefik.shop.localhost}
AUTH=${TRAEFIK_AUTH:-mira:coffee-secret}
HOST=$(printf '%s' "$URL" | sed -E 's#^[a-z]+://([^/:]+).*#\1#')

code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$URL")
echo "1. Ответ на $URL: HTTP $code"

case "$code" in
  000) echo "   → нет ответа: имя ($HOST), порт, TLS. Смотри: curl -v $URL"; exit 1 ;;
  401|403) echo "   → отказал middleware (пароль, список адресов, forwardAuth, mTLS)" ;;
  429) echo "   → сработал лимит запросов (rateLimit / inFlightReq)" ;;
  404) echo "   → ни один роутер не подошёл (или ответило само приложение)" ;;
  502|503|504) echo "   → роутер нашёлся, но сервис не отвечает" ;;
esac

routers=$(curl -s -u "$AUTH" "$API/api/http/routers" | jq -r --arg h "$HOST" '.[] | select(.rule | contains($h)) | [.name, .status, .service, (.entryPoints | join(",")), .provider] | @tsv')
echo "2. Роутеры, в правиле которых есть имя $HOST:"
if [ -z "$routers" ]; then echo "   (нет) → нет метки traefik.enable, неверная сеть или опечатка в Host()"; else printf '%s\n' "$routers" | cut -f1-4 | sed 's/^/   /'; fi

echo "3. Сервисы этих роутеров и состояние адресов:"
printf '%s\n' "$routers" | cut -f3,5 | sort -u | while IFS=$'\t' read -r svc prov; do
  [ -z "$svc" ] && continue
  case "$svc" in *@*) full=$svc ;; *) full="$svc@$prov" ;; esac
  curl -s -u "$AUTH" "$API/api/http/services/$full" | jq -r --arg s "$full" '"   " + $s + ": " + ((.serverStatus // {}) | to_entries | map(.value) | join(" ")) + "   адреса: " + ((.loadBalancer.servers // []) | map(.url) | join(", "))'
done
EOF
chmod +x diagnose.sh
echo "=== здоровая цепочка ==="
./diagnose.sh https://shop.localhost/api/menu
echo
echo "=== адрес, которого нет у приложения (ответит API) ==="
./diagnose.sh https://shop.localhost/api/nope
echo
echo "=== имя без роутера ==="
./diagnose.sh https://nothing.shop.localhost/ || true
```

### result
```out auto
```

В пункте 2 кроме основных роутеров CoffeeShop могут оказаться **остатки прошлых опытов** (у нас — `hostsite@file` из шага 9.1 и `s76@docker` из шага 7.6): скрипт показывает всё, что подходит под имя. Это нормально и даже полезно — так находят забытые стенды (убрать: `docker compose -f compose.s76.yaml down`, удалить файл `hostsite.yml`).

Три запуска — три типичные картины:

- **Здоровая цепочка:** `200`, роутер `enabled`, сервис с адресами в статусе `UP`.
- **`/api/nope`:** код `404`, но **роутер найден** — значит, `404` вернуло **приложение**, а не Traefik. Вывод: Traefik ни при чём, ищи в приложении.
- **Имя без роутера:** `404` и **«роутеров нет»** — ответил сам Traefik. Вывод: у имени нет роутера (метки, сеть, `traefik.enable`).

Различие между «`404` от Traefik» и «`404` от приложения» — самое важное из этого шага. У Traefik тело ответа — `404 page not found` (простой текст); у приложения — свой формат. А если не ясно, смотри **журнал доступа**: у запроса, на который ответил Traefik без роутера, пусто поле `RouterName`.

### why
Скрипт — это ты, оформленная в виде программы: он делает ровно те вопросы, что мы учились задавать. Его можно положить в репозиторий проекта и дать коллегам: «любая жалоба на адрес — сначала `./diagnose.sh URL`». А главное правило диагностики Traefik: **сначала понять, чей это ответ** — Traefik или приложения.

### deep Команды по частям
`curl -s -o /dev/null -w '%{http_code}'` — только код ответа. `sed -E 's#^[a-z]+://([^/:]+).*#\1#'` — вырезать имя хоста из адреса. `jq -r --arg h "$HOST" '.[] | select(.rule | contains($h)) | …'` — отобрать роутеры, в правиле которых встречается имя (`--arg` передаёт переменную оболочки в jq). `while read -r svc; do …; done` — перебрать строки. `serverStatus` у сервиса — словарь «адрес → UP/DOWN» (есть при включённом healthcheck).

### deep Как ещё можно
- **Проверка отдельно от Traefik:** `docker compose exec api node -e "fetch('http://localhost:3000/health')…"` — отвечает ли приложение само.
- **Дашборд вместо скрипта:** те же данные видны в разделах Routers и Services.
- **Журнал доступа:** `jq 'select(.DownstreamStatus >= 500)'` — все ошибки за период.

### deep Если не получилось
- **`jq: command not found`** — `brew install jq`.
- **В пункте 2 «(нет)» для работающего адреса** — адрес защищён паролем дашборда, а `TRAEFIK_AUTH` не подходит: задай `TRAEFIK_AUTH=логин:пароль`.
- **Скрипт «зависает»** — запрос не успел за 10 секунд (`--max-time`): значит, ответ `504`/таймаут; смотри пункт «504» в таблице.

### quiz
- Как отличить `404`, который вернул Traefik, от `404`, который вернуло приложение?
- Какой вопрос задаёшь первым при `502`, а какой при `503`?
- Что показывает пункт «состояние адресов» в скрипте и когда он важен?

### links
- https://doc.traefik.io/traefik/operations/api/ | API Traefik | Traefik: API
- https://sre.google/sre-book/monitoring-distributed-systems/ | четыре золотых сигнала | Google SRE: monitoring

## 10.5 Итоговый проект: CoffeeShop за Traefik со всем | short: Итоговый проект | est: ~90 мин
### intro
**Слова шага:** *итоговый стек*, *`starter/`*, *одна команда запуска*, *`up.sh`*, *`smoke.sh`*, *воспроизводимость*.

:::tip Если совсем просто
За десять сессий у нас накопилась куча файлов: небольшие дополнения и опыты. Теперь соберём **чистую итоговую папку**, в которой всё нужное лежит аккуратно и поднимается **одной командой** на пустой машине. Именно с неё начнёт следующая лаба (Kubernetes) и именно такую папку не стыдно показать коллеге.
:::

```svg
@final-stack
```

Что войдёт в итоговый проект (`~/traefik-lab/starter`):

| Что | Где | Из какой сессии |
|---|---|---|
| Traefik: входы, HTTP→HTTPS, HTTP/3, журнал JSON, метрики | `edge/traefik/traefik.yml` | 2, 7, 8.5, 10.1–10.2 |
| Общие middleware: заголовки, сжатие, пароль админки | `edge/traefik/dynamic/` | 4 |
| TLS: сертификат `mkcert`, опции | `edge/certs`, `dynamic/tls*.yml` | 7 |
| CoffeeShop: сайт, API (2 копии), база, Adminer, метки | `coffeeshop/compose.yaml` | 3, 5, 6 |
| Мониторинг: Prometheus + Grafana | `monitoring/` | 10.2 |
| Запуск и проверка | `up.sh`, `smoke.sh` | 10.5 |

Принципы итоговой папки: **один файл Compose на проект** (без цепочки `COMPOSE_FILE`), **ни одного секрета в файлах** (пароль админки создаёт `up.sh` при первом запуске), **весь стек поднимается одной командой** и **проверяется одной командой**. Сначала собираем файлы Traefik (вход `edge`):

```bash run
mkdir -p ~/traefik-lab/starter/edge/traefik/dynamic ~/traefik-lab/starter/edge/certs && cd ~/traefik-lab/starter/edge
cat > traefik/traefik.yml <<'EOF'
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
          permanent: true
  websecure:
    address: ":443"
    http3: {}
  metrics:
    address: ":8082"

providers:
  docker:
    exposedByDefault: false
    network: proxy
  file:
    directory: /etc/traefik/dynamic
    watch: true

metrics:
  prometheus:
    entryPoint: metrics
    addEntryPointsLabels: true
    addRoutersLabels: true
    addServicesLabels: true

api:
  dashboard: true

log:
  level: INFO
  noColor: true

accessLog:
  format: json
  fields:
    defaultMode: keep
    headers:
      defaultMode: drop
      names:
        X-Request-Id: keep
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
    web-chain:
      chain:
        middlewares: [secure-headers, zip]
    admin-auth:
      basicAuth:
        removeHeader: true
        usersFile: /etc/traefik/dynamic/users.htpasswd    # создаёт up.sh при первом запуске
EOF
cat > traefik/dynamic/tls.yml <<'EOF'
tls:
  certificates:
    - certFile: /certs/shop.pem
      keyFile: /certs/shop-key.pem
  options:
    default:
      minVersion: VersionTLS12
EOF
cat > compose.yaml <<'EOF'
name: edge

services:
  traefik:
    image: traefik:v3.7
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./traefik/traefik.yml:/etc/traefik/traefik.yml:ro
      - ./traefik/dynamic:/etc/traefik/dynamic:ro
      - ./certs:/certs:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.dashboard.rule=Host(`traefik.shop.localhost`)
      - traefik.http.routers.dashboard.entrypoints=websecure
      - traefik.http.routers.dashboard.tls=true
      - traefik.http.routers.dashboard.service=api@internal
      - traefik.http.routers.dashboard.middlewares=admin-auth@file

networks:
  proxy:
    name: proxy
EOF
find . -type f | sort
```

### result
```out auto
```

Заметь, чего **нет** в итоговом Traefik: нет пароля в файлах (`usersFile` читает файл, который создаст `up.sh`), нет `forwardedHeaders` (Traefik смотрит прямо в интернет, значит **никому не доверяет** — шаг 9.7), нет `whoami`. Теперь — приложение CoffeeShop: всё в **одном** файле Compose (метки из сессий 3–6 собраны вместе):

```bash run
cd ~/traefik-lab/starter
mkdir -p coffeeshop
cp -r ~/traefik-lab/coffeeshop/api ~/traefik-lab/coffeeshop/web ~/traefik-lab/coffeeshop/db coffeeshop/
rm -rf coffeeshop/api/node_modules
cat > coffeeshop/.env.example <<'EOF'
DB_USER=coffee
DB_PASSWORD=change-me
DB_NAME=coffee
EOF
cat > coffeeshop/compose.yaml <<'EOF'
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
    deploy:
      replicas: 2
    networks: [back, proxy]
    labels:
      - traefik.enable=true
      - traefik.docker.network=proxy
      - traefik.http.routers.coffee-api.rule=Host(`shop.localhost`) && PathPrefix(`/api`)
      - traefik.http.routers.coffee-api.entrypoints=websecure
      - traefik.http.routers.coffee-api.tls=true
      - traefik.http.routers.coffee-api.middlewares=coffee-strip,coffee-limit
      - traefik.http.middlewares.coffee-strip.stripprefix.prefixes=/api
      - traefik.http.middlewares.coffee-limit.ratelimit.average=20
      - traefik.http.middlewares.coffee-limit.ratelimit.burst=40
      - traefik.http.services.coffee-api.loadbalancer.server.port=3000
      - traefik.http.services.coffee-api.loadbalancer.healthcheck.path=/health
      - traefik.http.services.coffee-api.loadbalancer.healthcheck.interval=2s
      - traefik.http.services.coffee-api.loadbalancer.healthcheck.timeout=1s

  web:
    build: ./web
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.coffee-web.rule=Host(`shop.localhost`)
      - traefik.http.routers.coffee-web.entrypoints=websecure
      - traefik.http.routers.coffee-web.tls=true
      - traefik.http.routers.coffee-web.middlewares=web-chain@file
      - traefik.http.services.coffee-web.loadbalancer.server.port=80

  adminer:
    image: adminer:5
    networks: [back, proxy]
    labels:
      - traefik.enable=true
      - traefik.docker.network=proxy
      - traefik.http.routers.coffee-adminer.rule=Host(`adminer.shop.localhost`)
      - traefik.http.routers.coffee-adminer.entrypoints=websecure
      - traefik.http.routers.coffee-adminer.tls=true
      - traefik.http.routers.coffee-adminer.middlewares=admin-auth@file
      - traefik.http.services.coffee-adminer.loadbalancer.server.port=8080

networks:
  proxy:
    external: true
  back:

volumes:
  pgdata:
EOF
find coffeeshop -type f | sort
```

```out auto
```

Остались два скрипта. **`up.sh`** — одна команда запуска: проверяет, что есть сертификат (создаёт его через `mkcert`, если нет), пароль админки (создаёт, если нет), `.env` (копирует из примера), поднимает Traefik, затем приложение. **`smoke.sh`** — «дымовой тест»: десяток проверок, из которых видно, что стек работает **и что не сломалась защита**:

```bash run
cd ~/traefik-lab/starter
cat > up.sh <<'EOF'
#!/usr/bin/env bash
# Одна команда: сертификат, пароль админки, Traefik, приложение.
set -euo pipefail
cd "$(dirname "$0")"

# 1. Сертификат для локальных имён (нужен mkcert; на чистой машине: mkcert -install)
if [ ! -f edge/certs/shop.pem ]; then
  mkcert -cert-file edge/certs/shop.pem -key-file edge/certs/shop-key.pem shop.localhost '*.shop.localhost' localhost
fi

# 2. Пароль админки (хэш в файл, пароль — на экран один раз; в git не попадает)
if [ ! -f edge/traefik/dynamic/users.htpasswd ]; then
  pw=${ADMIN_PASSWORD:-$(openssl rand -base64 12)}
  htpasswd -nbB admin "$pw" > edge/traefik/dynamic/users.htpasswd
  echo "Создан пользователь админки: admin / $pw   (запиши, повторно не покажу)"
fi

# 3. Параметры приложения
[ -f coffeeshop/.env ] || cp coffeeshop/.env.example coffeeshop/.env

# 4. Запуск
docker compose -f edge/compose.yaml up -d
docker compose -f coffeeshop/compose.yaml up -d --build
echo "Готово: https://shop.localhost  ·  https://adminer.shop.localhost  ·  https://traefik.shop.localhost/dashboard/"
EOF
cat > down.sh <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
docker compose -f coffeeshop/compose.yaml down
docker compose -f edge/compose.yaml down
EOF
cat > smoke.sh <<'EOF'
#!/usr/bin/env bash
# Дымовой тест итогового стека. Переменная ADMIN_AUTH=логин:пароль нужна для проверок админки.
cd "$(dirname "$0")"
AUTH=${ADMIN_AUTH:-}
fail=0
check() {   # check "описание" ожидаемое фактическое
  if [ "$2" = "$3" ]; then echo "ok    $1"; else echo "FAIL  $1 (ожидали $2, получили $3)"; fail=1; fi
}
code() { curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$@"; }

check "HTTP -> HTTPS (301)"                       301 "$(code http://shop.localhost/)"
check "сайт по HTTPS"                              200 "$(code https://shop.localhost/)"
check "меню через /api"                            3   "$(curl -s --max-time 10 https://shop.localhost/api/menu | jq length 2>/dev/null)"
check "API без префикса (путь у бэкенда = /info)"  /info "$(curl -s --max-time 10 https://shop.localhost/api/info | jq -r .path 2>/dev/null)"
check "заголовки безопасности (X-Frame-Options)"   DENY "$(curl -sI --max-time 10 https://shop.localhost/ | tr -d '\r' | awk -F': ' 'tolower($1)=="x-frame-options"{print $2}')"
check "две копии API отвечают (балансировка)"      2   "$(for i in 1 2 3 4 5 6 7 8; do curl -s --max-time 10 https://shop.localhost/api/info | jq -r .hostname 2>/dev/null; done | sort -u | wc -l | tr -d ' ')"
check "Adminer без пароля закрыт"                  401 "$(code https://adminer.shop.localhost/)"
check "дашборд без пароля закрыт"                  401 "$(code https://traefik.shop.localhost/dashboard/)"
if [ -n "$AUTH" ]; then
  check "Adminer с паролем"                        200 "$(code -u "$AUTH" https://adminer.shop.localhost/)"
  check "дашборд с паролем"                        200 "$(code -u "$AUTH" https://traefik.shop.localhost/dashboard/)"
fi
check "подделка X-Forwarded-For не проходит"       ok  "$(curl -s --max-time 10 -H 'X-Forwarded-For: 1.2.3.4' https://shop.localhost/api/info | jq -r 'if (.headers["x-forwarded-for"] // "" | contains("1.2.3.4")) then "ПОДДЕЛКА ПРОШЛА" else "ok" end' 2>/dev/null)"
[ $fail = 0 ] && echo "SMOKE: всё в порядке" || echo "SMOKE: есть ошибки"
exit $fail
EOF
chmod +x up.sh down.sh smoke.sh
ls -l up.sh down.sh smoke.sh | awk '{print $1, $NF}'
```

```out auto
```

Теперь **самое важное — проверка с чистого листа**. Остановим всё, что накопилось за лабу (учебные стенды, прежний `coffeeshop` и `edge`), и поднимем **только итоговый** стек одной командой — как это сделает человек, впервые получивший `starter/`:

```bash run
cd ~/traefik-lab
for d in acme monitoring tracing edge; do (cd $d 2>/dev/null && docker compose down > /dev/null 2>&1); done
(cd coffeeshop && docker compose down -v > /dev/null 2>&1)
echo "учебные стенды остановлены, том базы удалён"
docker rm -f hostsite > /dev/null 2>&1
cd starter
ADMIN_PASSWORD=coffee-secret ./up.sh 2>&1 | grep -vE '^( Container| Network| Volume| Image|#|$)'
sleep 15
echo "--- смоук-тест итогового стека:"
ADMIN_AUTH=admin:coffee-secret ./smoke.sh
```

```out auto
```

Стек поднялся одной командой, и все проверки прошли: HTTPS, редирект, API без префикса, балансировка по двум копиям, защита админки, заголовки безопасности и — отдельной строкой — **подделка `X-Forwarded-For` не проходит** (Traefik смотрит в интернет и никому не доверяет). Пароль админки `up.sh` показывает при первом запуске (в этом прогоне он задан заранее переменной `ADMIN_PASSWORD`; без неё пароль случайный). Для проверок админки пароль передаётся в `ADMIN_AUTH`.

Откроем итог в браузере: **https://shop.localhost** — меню и заказ; **https://adminer.shop.localhost** — по паролю; **https://traefik.shop.localhost/dashboard/** — все роутеры и сервисы на месте. Мониторинг из шага 10.2 подключается так же, как раньше: `cd ~/traefik-lab/monitoring && docker compose up -d`.

### why
Итоговая папка — доказательство, что ты не только «запускала шаги», а **понимаешь всю картину** и можешь воспроизвести её с нуля. Смоук-тест — документ: он перечисляет, что обещает стек (HTTPS, защита, балансировка), и не даст незаметно сломать это при следующем изменении. А следующая лаба (Kubernetes) начнётся именно с этого приложения.

### deep Команды по частям
`set -euo pipefail` в `up.sh` — прервать скрипт при ошибке, при необъявленной переменной и при ошибке в конвейере. `mkcert -cert-file … -key-file … имена` — выпустить сертификат (шаг 7.2). `htpasswd -nbB admin "$pw" > файл` — хэш пароля в файл (`usersFile`, шаг 4.4). `openssl rand -base64 12` — случайный пароль из 12 байт. `docker compose -f … up -d --build` — поднять проект из указанного файла. В `smoke.sh` функция `check` сравнивает ожидаемое и фактическое и запоминает неудачу (`fail=1`), а в конце скрипт возвращает код `0` или `1` — так его можно вызывать из CI.

### deep Как ещё можно
- **Makefile:** `make up`, `make down`, `make smoke` — привычнее некоторым командам, чем скрипты.
- **CI:** запускать `up.sh` и `smoke.sh` в GitHub Actions при каждом изменении — тогда сломанные метки замечают до слияния.
- **Образы в registry:** в боевом стеке `build:` заменяют на `image: ghcr.io/…:версия` (в Docker-лабе — сессия 11, «Релиз из registry»).

### deep Если не получилось
- **`mkcert: command not found`** — `brew install mkcert && mkcert -install` (шаг 7.2).
- **`network proxy declared as external, but could not be found`** — `edge` не запущен: `up.sh` поднимает его первым; запускай именно его.
- **Порты 80/443 заняты** — остановь прежние стенды (`docker compose down` в `~/traefik-lab/edge`).
- **Проверка «две копии API» вернула `1`** — вторая копия ещё стартует (healthcheck): подожди 10–15 секунд и повтори `./smoke.sh`.
- **`FAIL … ожидали 401, получили 000`** — `curl` не доверяет сертификату: установи CA (`mkcert -install`) и открой новый терминал.

### quiz
- Какие четыре принципа сделали итоговую папку «чистой»?
- Зачем нужен `smoke.sh`, если всё и так «видно» в браузере?
- Почему в итоговом Traefik нет `forwardedHeaders`?

### links
- https://docs.docker.com/compose/how-tos/multiple-compose-files/ | несколько файлов Compose | Compose: multiple files
- https://github.com/FiloSottile/mkcert | mkcert | GitHub: mkcert

## 10.6 🔨 Production Hell: пять поломок без подсказок | short: 🔨 Production Hell | est: ~120 мин
### intro
**Слова шага:** *диагностика без подсказок*, *симптом → причина → исправление*, *слои Traefik*, *`smoke.sh`*.

:::tip Если совсем просто
Экзамен. Мы **нарочно сломаем итоговый стек пятью способами** — по одному на каждый «слой» Traefik. Подсказок нет: у тебя есть дерево вопросов (10.4), дашборд, журналы и `smoke.sh`. Цель — снова увидеть `SMOKE: всё в порядке`. Подсказки и разбор — под спойлерами в конце шага. Читать их до попытки — значит украсть у себя урок.
:::

Скрипт ниже применяет **пять поломок** к итоговой папке из шага 10.5. Что он делает, смотреть не нужно — как в жизни, ты видишь только симптомы. Запусти его и затем `./smoke.sh`:

```bash run
cd ~/traefik-lab/starter
cat > hell.sh <<'EOF'
#!/usr/bin/env bash
# Применяет пять поломок. Не читай, пока не починишь (спойлеры — в конце шага).
cd "$(dirname "$0")"
# 1
cat > edge/traefik/dynamic/zz-hell1.yml <<'Y'
http:
  routers:
    catchall:
      rule: "Host(`shop.localhost`) && PathPrefix(`/api`)"
      priority: 9000
      entryPoints: [websecure]
      tls: {}
      service: coffee-web@docker
Y
# 2
mkdir -p edge/certs
cp edge/certs/shop.pem edge/certs/clients-ca.pem
cat > edge/traefik/dynamic/zz-hell2.yml <<'Y'
tls:
  options:
    strict:
      minVersion: VersionTLS12
      clientAuth:
        caFiles: [/certs/clients-ca.pem]
        clientAuthType: RequireAndVerifyClientCert
Y
cat > coffeeshop/compose.hell.yaml <<'Y'
services:
  adminer:
    labels:
      - traefik.http.routers.coffee-adminer.tls.options=strict@file
  api:
    labels:
      - traefik.http.services.coffee-api.loadbalancer.healthcheck.path=/healthz
Y
# 3
awk '{print} /^  websecure:/ {print "    forwardedHeaders:"; print "      insecure: true"}' edge/traefik/traefik.yml > /tmp/traefik.hell.yml && cat /tmp/traefik.hell.yml > edge/traefik/traefik.yml
# 4
cat >> coffeeshop/compose.hell.yaml <<'Y'
  web:
    labels:
      - traefik.http.routers.coffee-web.entrypoints=websecurre
Y
docker compose -f edge/compose.yaml up -d --force-recreate > /dev/null 2>&1
docker compose -f coffeeshop/compose.yaml -f coffeeshop/compose.hell.yaml up -d > /dev/null 2>&1
sleep 12
EOF
chmod +x hell.sh
./hell.sh
./smoke.sh
```

### result
```out auto
```

Тест показывает **не причины, а симптомы** — как и в настоящей поломке. Дальше ты работаешь сама. Правила, как в шагах 1.7 и 2.7:

1. **Не лечи пять поломок разом.** Берёшь один симптом, ищешь причину, чинишь, запускаешь `./smoke.sh` — симптом исчез? Идёшь к следующему.
2. **Иди по дереву вопросов** (10.4): есть ли ответ → какой код → есть ли роутер → что в журнале и дашборде. Скрипт `~/traefik-lab/tools/diagnose.sh` тебе в помощь.
3. **Смотри в трёх местах:** журнал Traefik (`docker compose -f edge/compose.yaml logs traefik`), дашборд (Routers/Services/TLS), журнал доступа (поля `RouterName`, `DownstreamStatus`).
4. **Исправляй в файлах**, а не «руками в контейнере»: после исправления `docker compose … up -d` и `./smoke.sh`.
5. **Цель:** `SMOKE: всё в порядке`.

Пять поломок затрагивают разные слои: **маршрутизацию**, **TLS**, **доверие к заголовкам**, **вход (entryPoint)** и **здоровье сервиса**. Если застряла — открой подсказки по порядку, от общей к конкретной.

### why
Умение чинить чужой (и свой забытый) стенд по симптомам — главное, что отличает того, кто настроил Traefik по инструкции, от того, кто понимает, как он устроен. После этого шага у тебя должен быть **набор рефлексов**: «404 → роутер», «`000` → TLS и порт», «`503` → healthcheck», «странный ответ → приоритет», «безопасность → не доверять заголовкам».

### deep Подсказка 1: с чего начать
Запусти `./smoke.sh` и посмотри, **какие проверки красные**. Красные проверки сгруппируй по слоям: что с сайтом? что с API? что с Adminer? что с безопасностью? Для каждой группы вспомни строку из таблицы дерева вопросов (шаг 10.4). Начни с той, где симптом **яснее всего** (например, ответ `000` или `503` — они указывают на конкретный слой).

### deep Подсказка 2: симптомы по слоям
- **Сайт отдаёт не то** (меню вместо страницы или наоборот, неверный ответ на `/api`) — смотри **роутеры и приоритеты** в дашборде: кто ещё подходит под запрос? (шаги 3.3, 3.7)
- **`000` только на одном адресе, остальные работают** — это TLS на уровне имени: **TLS options** (шаги 7.5–7.6).
- **Проверка про `X-Forwarded-For` красная** — доверие к заголовкам: `forwardedHeaders` на входе (шаги 9.4, 9.7).
- **`404 page not found` для одного сервиса, а роутера в дашборде нет или он в ошибке** — смотри журнал Traefik на строки с `entrypoint` (шаги 2.7).
- **`503 no available server`** — состояние адресов: `serverStatus`, `healthcheck.path` (шаги 6.2, 6.7).

### deep Решение: пять поломок и их исправление
1. **Приоритет (`catchall`).** В файле `edge/traefik/dynamic/zz-hell1.yml` есть лишний роутер с правилом ``Host(`shop.localhost`) && PathPrefix(`/api`)`` и приоритетом `9000`: он **перехватывает запросы к `/api`** и отправляет их на сайт. Симптом: `/api/menu` отдаёт HTML, а не меню. Исправление: удалить файл `zz-hell1.yml` (Traefik подхватит без перезапуска).
2. **TLS options.** Роутер Adminer использует опцию `strict@file` с обязательным клиентским сертификатом (`RequireAndVerifyClientCert`): браузер без сертификата не может соединиться (`000`), остальные адреса работают. Исправление: убрать метку `…coffee-adminer.tls.options=strict@file` (и удалить файл `zz-hell2.yml`).
3. **Доверие к заголовкам.** В `traefik.yml` на входе `websecure` появилось `forwardedHeaders.insecure: true` — **доверять всем**; подделка `X-Forwarded-For` проходит (шаг 9.7). Исправление: удалить эти строки (остальные настройки входа не трогать) и перезапустить Traefik (статическая настройка).
4. **Вход (entryPoint).** У роутера сайта в метке `entrypoints` опечатка `websecurre`: такого входа нет, роутер не создаётся — сайт `404`. В журнале Traefik строка про несуществующий вход. Исправление: вернуть `websecure`.
5. **Healthcheck.** У сервиса API `healthcheck.path=/healthz` — такого адреса у API нет (`404`), все копии помечены `DOWN`, Traefik отвечает `503 no available server`. Исправление: вернуть `/health`.

Все исправления в файлах: убрать `compose.hell.yaml` из запуска, удалить `zz-hell*.yml`, вернуть `traefik.yml`. Применим их разом и убедимся, что тест зелёный:

```bash run
cd ~/traefik-lab/starter
rm -f edge/traefik/dynamic/zz-hell1.yml edge/traefik/dynamic/zz-hell2.yml edge/certs/clients-ca.pem coffeeshop/compose.hell.yaml
grep -v 'forwardedHeaders:' edge/traefik/traefik.yml | grep -v 'insecure: true' > /tmp/traefik.fixed.yml && cat /tmp/traefik.fixed.yml > edge/traefik/traefik.yml
docker compose -f edge/compose.yaml up -d --force-recreate > /dev/null 2>&1
docker compose -f coffeeshop/compose.yaml up -d > /dev/null 2>&1
sleep 15
./smoke.sh
```

```out auto
```

### quiz
- Как по симптому понять, что проблема в **приоритете** роутеров, а не в самом сервисе?
- Почему поломка TLS options проявилась только на одном адресе?
- Как проверить, что Traefik не доверяет подделанному `X-Forwarded-For`?

### links
- https://doc.traefik.io/traefik/routing/routers/#priority | приоритет | Traefik: priority
- https://doc.traefik.io/traefik/https/tls/#tls-options | TLS options | Traefik: TLS options
