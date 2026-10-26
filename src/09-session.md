# Сессия 9 · TCP/UDP, файловый провайдер, IP клиента
dur: ~4 ч

## 9.1 Файловый провайдер: сервис вне Docker | short: Сервис вне Docker | est: ~50 мин
### intro
**Слова шага:** *файловый провайдер*, *`http.routers`*, *`http.services`*, *`loadBalancer.servers`*, *`host.docker.internal`*, *горячая перезагрузка*.

:::tip Если совсем просто
До сих пор мы описывали маршруты «записками на контейнерах». Но бывают сервисы, у которых нет контейнера и, значит, нет места для записки: программа на самом компьютере, старый сервер в соседней комнате. Для них маршрут описывают **в отдельном файле** — как книгу заказов у администратора.
:::

Файловый провайдер мы уже использовали для общих middleware и сертификатов (шаги 4.5 и 7.3). Теперь опишем в нём **целиком маршрут**: роутер и сервис. Для сервиса указывается явный адрес — это может быть что угодно, до чего Traefik дотянется по сети: программа на твоём Mac, другая машина, внешний сайт. Структура файла такая же, как у меток, только в виде YAML:

```yaml
http:
  routers:
    имя-роутера:
      rule: "Host(`…`)"
      entryPoints: [websecure]
      tls: {}
      service: имя-сервиса
  services:
    имя-сервиса:
      loadBalancer:
        servers:
          - url: "http://адрес:порт"
```

Опыт: на Mac запускаешь любую программу на порту `9000` (например, `python3 -m http.server 9000 --directory ~/traefik-lab/hostsite` — **в отдельном терминале**), а Traefik, который работает в контейнере, достучится до неё по специальному имени **`host.docker.internal`** — так контейнер на Docker Desktop обращается к своему хозяину (в Linux это имя нужно подключить строкой `extra_hosts` с значением `host-gateway`, что мы и сделаем). **Примечание про этот прогон:** в стенде, на котором выполнялась методичка, роль «программы на хосте» играл контейнер с общей с хозяином сетью (`--network host`); для Traefik разницы нет.

```bash run hidden
mkdir -p ~/traefik-lab/hostsite
docker rm -f hostsite > /dev/null 2>&1
docker run -d --name hostsite --network host -v ~/traefik-lab/hostsite:/site:ro busybox httpd -f -p 9000 -h /site > /dev/null
```

```bash run
mkdir -p ~/traefik-lab/hostsite && cd ~/traefik-lab/edge
printf '<h1>Сайт, который живёт на хозяине, вне Docker</h1>\n' > ~/traefik-lab/hostsite/index.html
cat > compose.s91.yaml <<'EOF'
services:
  traefik:
    extra_hosts:
      - "host.docker.internal:host-gateway"
EOF
printf 'COMPOSE_FILE=compose.yaml:compose.s91.yaml\n' > .env
docker compose up -d 2>&1 | tail -2
sleep 4
echo "--- до создания файла маршрута:"
curl -s -o /dev/null -w 'host.shop.localhost -> HTTP %{http_code}\n' https://host.shop.localhost/
cat > traefik/dynamic/hostsite.yml <<'EOF'
http:
  routers:
    hostsite:
      rule: "Host(`host.shop.localhost`)"
      entryPoints:
        - websecure
      tls: {}
      service: hostsite
  services:
    hostsite:
      loadBalancer:
        servers:
          - url: "http://host.docker.internal:9000"
EOF
sleep 4
echo "--- после (Traefik не перезапускали):"
curl -s https://host.shop.localhost/
curl -s -o /dev/null -w 'host.shop.localhost -> HTTP %{http_code}\n' https://host.shop.localhost/
```

### result
```out auto
```

До создания файла — `404`, сразу после — ответ программы, которая работает **вне Docker**. Traefik **не перезапускали**: файловый провайдер следит за папкой (`watch: true`) и подхватывает изменения на лету. Убедимся, что маршрут исчезает так же легко, как появился, и что его видно как объект с суффиксом `@file`:

```bash run
cd ~/traefik-lab/edge
tapi() { curl -s -u mira:coffee-secret "https://traefik.shop.localhost/api/$1"; }
echo "--- роутеры из файлового провайдера:"
tapi http/routers | jq -r '.[] | select(.provider == "file") | [.name, .status, .service] | @tsv'
mv traefik/dynamic/hostsite.yml /tmp/hostsite.yml
sleep 4
echo "--- файл убрали:"
curl -s -o /dev/null -w 'host.shop.localhost -> HTTP %{http_code}\n' https://host.shop.localhost/
mv /tmp/hostsite.yml traefik/dynamic/hostsite.yml
sleep 4
curl -s -o /dev/null -w 'файл вернули  -> HTTP %{http_code}\n' https://host.shop.localhost/
```

```out auto
```

Файл убрали — маршрут исчез (`404`), вернули — маршрут появился. Именно так удобно подключать к Traefik **старые** серверы при миграции: пока приложение живёт вне Docker, на нём всё равно можно применить все middleware, TLS и балансировку.

### why
Файловый провайдер — «ручной режим» Traefik. Он нужен, когда у сервиса нет контейнера (программа на хосте, виртуальная машина, внешний сервис), когда конфигурацию хранят в git отдельно от Compose, и для объектов, которые метками описать неудобно (weighted-сервисы, mirroring — шаги 6.4 и 6.5). Метки и файлы **можно смешивать**: роутер из файла может ссылаться на сервис из Docker (`имя@docker`) и наоборот.

### deep Команды по частям
`extra_hosts: ["host.docker.internal:host-gateway"]` — добавить в контейнер имя `host.docker.internal`, которое указывает на хозяина (`host-gateway` — специальное значение «адрес хозяина»; в Docker Desktop это имя уже есть). `tls: {}` — включить TLS у роутера (пустой блок = «со всеми настройками по умолчанию»). `servers: - url: …` — список адресов сервиса; несколько адресов — балансировка, как в шаге 6.1. `jq … select(.provider == "file")` — оставить объекты, пришедшие из файла.

### deep Как ещё можно
- **Несколько файлов:** по файлу на сервис — удобно хранить в git и править независимо.
- **Один файл вместо папки:** `providers.file.filename` — для самого маленького стенда.
- **Внешние провайдеры:** HTTP-провайдер (`providers.http.endpoint`) — Traefik сам скачивает конфигурацию с адреса; Redis, etcd, Consul — из хранилищ ключей.

### deep Если не получилось
- **`502`/`504` на `host.shop.localhost`** — Traefik не достучался до хозяина: проверь, что программа слушает на `0.0.0.0:9000` (а не только `127.0.0.1`, иначе контейнер её не увидит) и что файрвол Mac разрешает входящие соединения.
- **`host.docker.internal` не находится (Linux)** — не добавлен `extra_hosts` или Compose старой версии.
- **Маршрут не появился** — в файле опечатка в YAML: Traefik оставляет старую конфигурацию и пишет ошибку в журнал (`docker compose logs traefik`).

### quiz
- Для каких сервисов нужен файловый провайдер и чем он отличается от меток?
- Как контейнер с Traefik обращается к программе, запущенной на хозяине?
- Что происходит, когда файл маршрута удаляют или возвращают?

### links
- https://doc.traefik.io/traefik/reference/install-configuration/providers/others/file/ | файловый провайдер | Traefik: File provider
- https://docs.docker.com/desktop/features/networking/ | сеть Docker Desktop | Docker Desktop: networking

## 9.2 TCP-роутеры: PostgreSQL через Traefik | short: TCP-роутеры, PostgreSQL | est: ~60 мин
### intro
**Слова шага:** *TCP-роутер*, *`HostSNI`*, *`HostSNI(*)`*, *TLS passthrough и termination*, *`ALPN`*, *`sslnegotiation=direct`*.

:::tip Если совсем просто
HTTP-роутер читает «письмо»: видит адрес, путь, заголовки. TCP-роутер **не читает письма** — он видит только конверт: на какую дверь пришли (порт) и, если соединение шифрованное, на какое имя (SNI). Всё остальное — просто байты, которые он передаёт дальше. Так через Traefik можно пустить базу данных, почту, любой протокол.
:::

```svg
@protocols
```

Не всё в мире — HTTP. **TCP-роутер** работает с любым протоколом поверх TCP (PostgreSQL, Redis, SMTP…). Он решает **только по порту и имени (SNI)**. Правило называется `HostSNI`: ``HostSNI(`имя`)`` — совпадает с именем в начале TLS-рукопожатия, ``HostSNI(`*`)`` — любое соединение, в том числе **без TLS** (потому что имени в нём нет). Два режима с TLS:

- **Termination** — Traefik расшифровывает TLS и передаёт сервису **обычные** байты (нужен сертификат на Traefik, как для HTTPS).
- **Passthrough** (`tls.passthrough=true`) — Traefik не расшифровывает, а **пропускает насквозь** зашифрованный поток к серверу (сертификат нужен самому серверу).

Предупреждение: выставлять базу данных наружу через любой прокси — **риск**. Делай это только осознанно: TLS + `ipAllowList` (у TCP есть свой) + нестандартный порт. У нас — учебный стенд. Добавим в Traefik два новых входа (`pg` на 5432 без TLS и `pgtls` на 5433 с TLS), заодно вход `dns` для UDP (шаг 9.3), и подключим базу CoffeeShop к сети `proxy` с TCP-метками:

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

api:
  dashboard: true

log:
  level: INFO
  noColor: true

accessLog: {}
EOF
cat > traefik/dynamic/tls-options.yml <<'EOF'
tls:
  options:
    default:
      minVersion: VersionTLS12
    mtls:
      minVersion: VersionTLS12
      clientAuth:
        caFiles:
          - /certs/clients-ca.pem
        clientAuthType: RequireAndVerifyClientCert
    pg:
      minVersion: VersionTLS12
      alpnProtocols:
        - postgresql
EOF
cat > compose.s92.yaml <<'EOF'
services:
  traefik:
    ports:
      - "5432:5432"
      - "5433:5433"
      - "5353:5353/udp"
EOF
sed 's|^COMPOSE_FILE=.*|&:compose.s92.yaml|' .env > .env.new && mv .env.new .env
docker compose up -d 2>&1 | tail -2
cd ~/traefik-lab/coffeeshop
cat > compose.s9.yaml <<'EOF'
services:
  db:
    networks: [back, proxy]
    labels:
      - traefik.enable=true
      - traefik.docker.network=proxy
      - traefik.tcp.services.pg.loadbalancer.server.port=5432
      # без TLS: любое соединение на порт 5432 входа pg
      - traefik.tcp.routers.pg.rule=HostSNI(`*`)
      - traefik.tcp.routers.pg.entrypoints=pg
      - traefik.tcp.routers.pg.service=pg
      # с TLS (termination): имя db.shop.localhost на порт 5433 входа pgtls
      - traefik.tcp.routers.pgtls.rule=HostSNI(`db.shop.localhost`)
      - traefik.tcp.routers.pgtls.entrypoints=pgtls
      - traefik.tcp.routers.pgtls.tls=true
      - traefik.tcp.routers.pgtls.tls.options=pg@file
      - traefik.tcp.routers.pgtls.service=pg
EOF
sed 's|^COMPOSE_FILE=.*|&:compose.s9.yaml|' .env > .env.new && mv .env.new .env
docker compose up -d 2>&1 | tail -2
sleep 8
export PGPASSWORD=change-me
echo "--- psql через Traefik, порт 5432 (без TLS):"
psql -h localhost -p 5432 -U coffee -d coffee -Atc 'SELECT count(*) AS позиций_меню FROM menu'
echo "--- psql через Traefik, порт 5433 (TLS на входе, имя db.shop.localhost):"
psql "host=db.shop.localhost port=5433 user=coffee dbname=coffee sslmode=verify-full sslrootcert=system sslnegotiation=direct" -Atc 'SELECT count(*) AS позиций_меню FROM menu'
psql "host=db.shop.localhost port=5433 user=coffee dbname=coffee sslmode=verify-full sslrootcert=system sslnegotiation=direct" -c '\conninfo' | grep -iE 'ssl|protocol'
```

### result
```out auto
```

`psql` на хосте подключился к базе, которая **не опубликована наружу** (у `db` нет `ports`!) — через Traefik, по двум входам:

- **5432, без TLS** — Traefik просто передаёт байты. Подходит для стенда и закрытой сети.
- **5433 с TLS (termination)** — клиент начинает TLS сразу с имени `db.shop.localhost`; Traefik расшифровывает (сертификат от `mkcert` из шага 7.2 покрывает `*.shop.localhost`) и передаёт серверу уже обычные байты. Команда `\conninfo` показывает, что соединение клиента шифрованное (протокол TLS).

Две важные детали второго подключения:

- **`sslnegotiation=direct`** — «начни TLS сразу» (опция клиента PostgreSQL **17 и новее**). Обычный PostgreSQL сначала спрашивает сервер «умеешь ли TLS?» и только потом начинает шифрование, а Traefik ждёт начала рукопожатия сразу — иначе он не увидит имя (SNI).
- **`alpnProtocols: [postgresql]`** в опции `pg` — клиент PostgreSQL при прямом TLS требует, чтобы сервер подтвердил протокол `postgresql` (ALPN). Без этого `psql` отказывается: `ALPN negotiation failed`.

### why
Теперь у Traefik есть «второй язык»: он умеет не только HTTP. А ещё мы увидели ключевое различие: HTTP-роутер выбирает по заголовку `Host` **после** расшифровки, TCP-роутер — по **SNI до** расшифровки, поэтому для TCP без TLS нет имени и годится только ``HostSNI(`*`)`` — «всё подряд на этом порту».

### deep Команды по частям
`traefik.tcp.routers.pg.rule=HostSNI(`*`)` — метки с `tcp` вместо `http`; `traefik.tcp.services.pg.loadbalancer.server.port=5432` — порт сервиса (у TCP-сервисов нет `healthcheck.path`, но есть `proxyProtocol`, `terminationDelay`). `tls=true` у TCP-роутера включает termination (`tls.passthrough=true` — passthrough). `psql -Atc '…'` — `-A` без выравнивания, `-t` только данные, `-c` выполнить команду. `PGPASSWORD` — пароль из окружения (в шаге 1.5 мы задали `change-me`). `sslrootcert=system` — проверять сертификат по системному хранилищу (там лежит CA от `mkcert`).

### deep Как ещё можно
- **Passthrough:** включить TLS на самом PostgreSQL (`ssl=on`, сертификаты) и поставить `tls.passthrough=true` — Traefik пропустит зашифрованный поток, а сертификат сервера будет настоящим серверным (полезно, когда клиент должен проверять именно сертификат базы).
- **Защита TCP:** middleware `ipAllowList` существует и для TCP (`traefik.tcp.middlewares.pg-allow.ipallowlist.sourcerange=…` и `traefik.tcp.routers.pg.middlewares=pg-allow`).
- **Redis, SMTP, MQTT** — любые протоколы по тому же принципу.

### deep Если не получилось
- **`psql: error: connection to server at "localhost" … refused`** — порт 5432 занят локальным PostgreSQL на Mac (`lsof -i :5432`): смени левую цифру в `ports` и используй новый порт.
- **`SSL error: tlsv1 alert …` / `ALPN`** — у клиента `psql` версия ниже 17 (нет `sslnegotiation=direct`): поставь `brew install libpq` и запускай `/opt/homebrew/opt/libpq/bin/psql`, или подключайся без TLS через 5432.
- **`certificate verify failed`** — не установлен CA от `mkcert` (шаг 7.2) или имя в `host=` не из SAN (`db.shop.localhost` покрывает `*.shop.localhost`).
- **`password authentication failed`** — пароль в `PGPASSWORD` не совпал с `.env` проекта CoffeeShop (`DB_PASSWORD`).

### quiz
- Чем TCP-роутер отличается от HTTP-роутера и по чему он выбирает маршрут?
- Что делают termination и passthrough и когда выбирают каждый?
- Зачем нужны `sslnegotiation=direct` и ALPN `postgresql` при TLS на Traefik?

### links
- https://doc.traefik.io/traefik/reference/routing-configuration/tcp/service/ | TCP-маршрутизация | Traefik: TCP routing
- https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNECT-SSLNEGOTIATION | sslnegotiation | PostgreSQL: sslnegotiation

## 9.3 UDP-роутеры: DNS-сервис | short: UDP-роутеры | est: ~40 мин
### intro
**Слова шага:** *UDP*, *UDP-роутер*, *вход `…/udp`*, *`traefik.udp.routers`*, *DNS*, *CoreDNS*, *отсутствие соединения*.

:::tip Если совсем просто
TCP — разговор по телефону: набрали номер, соединились, говорят. UDP — отправка открыток: бросил в ящик, ответ может прийти, может нет. Traefik умеет и «открытки»: на входе по UDP-порту он забирает открытку и пересылает сервису.
:::

**UDP** — протокол без установления соединения: DNS, игры, видео, HTTP/3 (шаг 8.5). У UDP-роутера нет правил по имени (имён нет!): он работает **по порту входа** и пересылает все пакеты одному сервису (или нескольким по кругу). Вход с UDP мы уже добавили в шаге 9.2: `dns: ":5353/udp"`. Подключим DNS-сервер **CoreDNS** с одной записью: имя `shop.internal` указывает на адрес `10.20.30.40`. Метки — как у HTTP, но с `udp`:

```bash run
mkdir -p ~/traefik-lab/edge/coredns && cd ~/traefik-lab/edge
cat > coredns/Corefile <<'EOF'
. {
    hosts {
        10.20.30.40 shop.internal
        fallthrough
    }
    log
}
EOF
cat > compose.s93.yaml <<'EOF'
name: s93

services:
  dns:
    image: coredns/coredns:latest
    command: ["-conf", "/Corefile"]
    volumes:
      - ./coredns/Corefile:/Corefile:ro
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.udp.routers.dns.entrypoints=dns
      - traefik.udp.services.dns.loadbalancer.server.port=53

networks:
  proxy:
    external: true
EOF
docker compose -f compose.s93.yaml up -d 2>&1 | tail -1
sleep 5
echo "--- DNS-запрос к Traefik по UDP 5353:"
dig @localhost -p 5353 +short +time=3 +tries=1 shop.internal
echo "--- а к имени, которого в Corefile нет (CoreDNS ответит ошибкой):"
dig @localhost -p 5353 +time=3 +tries=1 other.internal | grep -E 'status|ANSWER:'
echo "--- журнал CoreDNS видел запрос от Traefik:"
docker compose -f compose.s93.yaml logs --no-log-prefix dns 2>&1 | grep -c 'shop.internal' | sed 's/^/запросов shop.internal в журнале CoreDNS: /'
```

### result
```out auto
```

`dig` обратился к порту `5353` Traefik, тот переслал UDP-пакеты контейнеру CoreDNS и вернул ответ: **`10.20.30.40`**. Второй запрос показал, что CoreDNS отвечает и на неизвестные имена — ошибкой `SERVFAIL` (в нашем `Corefile` нет плагина, у которого можно спросить дальше; настоящий DNS-сервер ответил бы `NXDOMAIN`). В журнале CoreDNS видно, что запросы действительно дошли до него.

**Особенности UDP в Traefik:**

- нет `Host`/пути: роутер выбирается **только по входу**;
- нет TLS и middleware (пока — только балансировка);
- Traefik помнит «сессию» пакетов от одного клиента короткое время (`timeout`, по умолчанию 3 секунды), чтобы ответ вернулся тому, кто спрашивал.

### why
UDP-проксирование нужно нечасто (DNS, VPN вроде WireGuard, syslog, игровые серверы), но когда нужно, приятно, что **тот же Traefik** с тем же дашбордом и той же конфигурацией справляется. В дашборде это отдельная вкладка **UDP**.

### deep Команды по частям
`dig @localhost -p 5353 +short shop.internal` — спросить DNS-сервер по адресу `localhost:5353` об имени; `+short` — только ответ; `+time=3 +tries=1` — ждать ответ не более 3 секунд и одну попытку. `grep -E 'status|ANSWER:'` — строка с кодом ответа и количеством записей. В `Corefile`: блок `.` — «для любого имени»; `hosts { … }` — статические записи; `fallthrough` — если имени нет, спросить дальше (по цепочке плагинов); `log` — писать запросы в журнал.

### deep Как ещё можно
- **Несколько серверов:** добавь второй контейнер с тем же сервисом — Traefik будет раздавать UDP-пакеты по кругу.
- **Файловый провайдер:** `udp: routers: … services: … loadBalancer: servers: - address: "host:53"` — для внешнего DNS-сервера.
- **WireGuard через Traefik:** тот же принцип, порт `51820/udp`.

### deep Если не получилось
- **`dig` ничего не вернул (`connection timed out`)** — UDP-порт не опубликован (`"5353:5353/udp"` в `compose.s92.yaml`) или порт занят; проверь `docker compose ps traefik`.
- **Пустой `+short` вывод** — запись в `Corefile` не подхвачена: перезапусти CoreDNS (`docker compose -f compose.s93.yaml restart`).
- **Образ `coredns/coredns` не скачивается** — подставь другой DNS-сервер (`dnsmasq`) или пропусти опыт: принцип тот же.

### quiz
- Чем UDP отличается от TCP и почему у UDP-роутера нет правил по имени?
- Какие метки нужны, чтобы Traefik пересылал UDP на сервис?
- В каких задачах встречается UDP-проксирование?

### links
- https://doc.traefik.io/traefik/reference/routing-configuration/udp/service/ | UDP-маршрутизация | Traefik: UDP routing
- https://coredns.io/manual/toc/ | CoreDNS | CoreDNS: manual

## 9.4 Реальный IP клиента: forwardedHeaders и proxy protocol | short: IP клиента | est: ~55 мин
### intro
**Слова шага:** *`X-Forwarded-For`*, *`forwardedHeaders.trustedIPs`*, *proxy protocol*, *доверенные прокси*, *клиентский IP*, *`depth`*.

:::tip Если совсем просто
Приложение хочет знать, **кто на самом деле пришёл**: по IP можно ограничить доступ, вести счёт, найти нарушителя. Но когда перед приложением стоит прокси, оно видит только адрес прокси. Поэтому прокси пишет настоящий адрес в заголовок `X-Forwarded-For` — как записку «пришёл вот этот человек». Беда в том, что записку может написать и сам посетитель — поэтому ей верят **только от своих** (доверенных прокси).
:::

```svg
@xff-chain
```

Путь запроса часто выглядит так: **клиент → внешний балансировщик (CDN, облачный LB) → Traefik → приложение**. Каждый прокси **дописывает** адрес того, кто к нему пришёл, в `X-Forwarded-For`: получается цепочка `клиент, балансировщик`. Правила Traefik:

- От **недоверенного** источника заголовок `X-Forwarded-For` **отбрасывается** и заменяется адресом самого источника — подделать его снаружи нельзя.
- От **доверенного** (`forwardedHeaders.trustedIPs`) — Traefik **сохраняет** присланный заголовок и дописывает адрес источника.

Проверим на API (его адрес `/info` показывает заголовки, которые до него дошли). Сначала — без доверенных, «клиент» пытается подставить чужой адрес:

```bash run
cd ~/traefik-lab/coffeeshop
echo "--- клиент прислал X-Forwarded-For: 1.2.3.4 (вход не доверяет никому):"
curl -s -H 'X-Forwarded-For: 1.2.3.4' https://shop.localhost/api/info | jq -c '{xff: .headers["x-forwarded-for"], real_ip: .headers["x-real-ip"]}'
```

### result
```out auto
```

Подделка не прошла: в `x-forwarded-for` — **только настоящий адрес клиента** (в нашем стенде это адрес контейнера-клиента в сети Docker), а присланное `1.2.3.4` отброшено. Теперь представим, что перед Traefik стоит свой балансировщик, чьи адреса из сети `172.16.0.0/12` (и других частных). Объявим их **доверенными** на входе `websecure`:

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
        - "10.0.0.0/8"
        - "172.16.0.0/12"
        - "192.168.0.0/16"
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

api:
  dashboard: true

log:
  level: INFO
  noColor: true

accessLog: {}
EOF
docker compose restart traefik 2>&1 | tail -1
sleep 5
echo "--- тот же запрос, но источник теперь доверенный:"
curl -s -H 'X-Forwarded-For: 1.2.3.4' https://shop.localhost/api/info | jq -c '{xff: .headers["x-forwarded-for"], real_ip: .headers["x-real-ip"]}'
```

```out auto
```

Теперь `x-forwarded-for` — **цепочка**: присланное `1.2.3.4` сохранено, а справа дописан адрес того, кто пришёл к Traefik. Приложение, которому нужен «настоящий клиент», должно брать адрес **с правильной позиции цепочки**, а не слепо первый: если перед Traefik ровно один балансировщик, настоящий клиент — это **предпоследний** адрес (последний — сам балансировщик, его дописал Traefik), а то, что левее, клиент мог написать сам.

**Proxy protocol** — другой способ передать адрес клиента, **на уровне TCP**, а не заголовком HTTP. Балансировщик (HAProxy, облачный LB в режиме TCP) перед каждым соединением дописывает короткую «шапку» с настоящими адресами клиента. Работает и для не-HTTP протоколов (БД, почта). Включается на входе: `entryPoints.websecure.proxyProtocol.trustedIPs: [адреса балансировщика]` (и на самом балансировщике). Ловушка: если включить proxy protocol, а балансировщик его **не** шлёт (или наоборот), соединения рвутся. В прогоне методички proxy protocol не запускался (для него нужен внешний балансировщик).

### why
«Кто пришёл» — основа для ограничения по IP (шаг 5.2), счётчиков, защиты от перебора и журналов. Всё держится на одной идее: **доверяй только цепочке, которую сам построил**. Расширять `trustedIPs` «на всякий случай» опасно — следующий шаг покажет почему (🔨 в шаге 9.7).

### deep Команды по частям
`forwardedHeaders.trustedIPs` — список адресов/подсетей, от которых заголовки `X-Forwarded-*` принимаются на веру. `forwardedHeaders.insecure: true` — доверять **всем** (только для опытов!). `jq -c '{xff: .headers["x-forwarded-for"], …}'` — собрать из ответа API короткий объект. Заголовок `X-Real-Ip` — Traefik кладёт туда адрес непосредственного источника.

### deep Как ещё можно
- **Облачные CDN/LB:** у Cloudflare, AWS ELB и других есть опубликованные диапазоны адресов — их и указывают в `trustedIPs` (и только их).
- **`ipStrategy.depth`** у `ipAllowList`/`rateLimit` — какой по счёту справа адрес из заголовка, **который получил Traefik**, считать клиентом (`depth=1` — самый правый: именно его дописал ближайший к Traefik балансировщик). Приложение за Traefik видит цепочку на один адрес длиннее: Traefik дописывает адрес источника сам.
- **Заголовок `Forwarded`** (RFC 7239) — стандартная замена `X-Forwarded-*`, поддерживается не везде.

### deep Если не получилось
- **`1.2.3.4` не сохраняется после доверия** — адрес клиента не попал в `trustedIPs`: посмотри его в первом выводе (`x-forwarded-for` без подделки) и добавь его подсеть.
- **В `x-forwarded-for` только адрес Docker-шлюза** — на Mac с Docker Desktop все запросы приходят «из виртуальной машины»; это нормально для локального стенда.
- **Traefik не стартует после правки** — проверь отступы YAML и перезапусти (`docker compose logs traefik`).

### quiz
- Почему `X-Forwarded-For` от недоверенного источника Traefik заменяет, а от доверенного — сохраняет?
- Как proxy protocol отличается от заголовка `X-Forwarded-For`?
- Какой адрес в цепочке считать настоящим клиентом, если перед Traefik один балансировщик?

### links
- https://doc.traefik.io/traefik/reference/install-configuration/entrypoints/#forwarded-headers | forwarded headers | Traefik: forwardedHeaders
- https://www.haproxy.org/download/1.8/doc/proxy-protocol.txt | спецификация proxy protocol | HAProxy: PROXY protocol

## 9.5 Плагины: Yaegi, локальный плагин | short: Плагины | est: ~55 мин
### intro
**Слова шага:** *плагин*, *Yaegi*, *локальный плагин*, *`experimental.localPlugins`*, *`.traefik.yml`*, *Plugin Catalog*, *риски*.

:::tip Если совсем просто
Готовых «станций» (middleware) у Traefik много, но иногда нужна своя. Плагин — это **маленькая программа на Go**, которую Traefik подгружает и ставит на конвейер как ещё одну станцию. Программа выполняется **внутри** Traefik, поэтому ей нужно доверять так же, как самому Traefik.
:::

Плагины для Traefik v3 пишутся на **Go** и исполняются встроенным интерпретатором **Yaegi** (без компиляции). Два способа подключения:

1. **Из каталога** (*Plugin Catalog*, plugins.traefik.io): указываешь имя модуля и версию в `experimental.plugins`, Traefik **скачивает** код с GitHub при запуске. Просто, но нужен интернет и доверие к автору.
2. **Локальный плагин**: код лежит в папке, смонтированной в Traefik (`/plugins-local/src/<модуль>/`), и подключается через `experimental.localPlugins`. Для разработки и для кода, который ты хочешь контролировать сама.

Напишем **свой плагин**: он добавляет к ответу заголовок с заданным именем и значением. В папке плагина нужны три файла: манифест `.traefik.yml` (описание), `go.mod` (имя модуля Go) и сам код `plugin.go`:

```bash run
mkdir -p ~/traefik-lab/edge/plugins-local/src/github.com/mira/myheader && cd ~/traefik-lab/edge/plugins-local/src/github.com/mira/myheader
cat > .traefik.yml <<'EOF'
displayName: My Header
type: middleware
import: github.com/mira/myheader
summary: Добавляет заголовок к ответу.
testData:
  name: X-Plugin
  value: hello
EOF
cat > go.mod <<'EOF'
module github.com/mira/myheader

go 1.22
EOF
cat > plugin.go <<'EOF'
// Package myheader — учебный middleware: добавляет заголовок к каждому ответу.
package myheader

import (
	"context"
	"net/http"
)

// Config — настройки плагина (поля читаются из конфигурации Traefik).
type Config struct {
	Name  string `json:"name,omitempty"`
	Value string `json:"value,omitempty"`
}

// CreateConfig — значения по умолчанию.
func CreateConfig() *Config {
	return &Config{Name: "X-Plugin", Value: "hello"}
}

type myHeader struct {
	next  http.Handler
	name  string
	value string
}

// New создаёт экземпляр middleware.
func New(ctx context.Context, next http.Handler, config *Config, name string) (http.Handler, error) {
	return &myHeader{next: next, name: config.Name, value: config.Value}, nil
}

func (m *myHeader) ServeHTTP(rw http.ResponseWriter, req *http.Request) {
	rw.Header().Set(m.name, m.value)
	m.next.ServeHTTP(rw, req)
}
EOF
find ~/traefik-lab/edge/plugins-local -type f | sed "s|$HOME/||" | sort
```

### result
```out auto
```

Теперь подключаем плагин: в **статической** конфигурации объявляем модуль (`experimental.localPlugins`), в Compose монтируем папку, а в **динамической** — используем как обычный middleware с блоком `plugin`:

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
        - "10.0.0.0/8"
        - "172.16.0.0/12"
        - "192.168.0.0/16"
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

accessLog: {}
EOF
cat > compose.s95.yaml <<'EOF'
services:
  traefik:
    volumes:
      - ./plugins-local:/plugins-local:ro
EOF
sed 's|^COMPOSE_FILE=.*|&:compose.s95.yaml|' .env > .env.new && mv .env.new .env
docker compose -f compose.s93.yaml down 2>&1 | tail -1
docker compose up -d 2>&1 | tail -1
cat > compose.s95lab.yaml <<'EOF'
name: s95lab

services:
  lab:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.s95.rule=Host(`plug.shop.localhost`)
      - traefik.http.routers.s95.entrypoints=websecure
      - traefik.http.routers.s95.tls=true
      - traefik.http.routers.s95.middlewares=hello
      - traefik.http.middlewares.hello.plugin.myheader.name=X-Hello
      - traefik.http.middlewares.hello.plugin.myheader.value=from-plugin

networks:
  proxy:
    external: true
EOF
docker compose -f compose.s95lab.yaml up -d 2>&1 | tail -1
sleep 6
echo "--- ответ с заголовком, который добавил наш плагин:"
curl -s -o /dev/null -D - https://plug.shop.localhost/ | grep -iE '^(HTTP|x-hello)'
echo "--- журнал Traefik про плагины:"
docker compose logs --no-log-prefix traefik 2>&1 | grep -iE 'plugin' | cut -c1-160 | head -3
```

```out auto
```

В ответе появился заголовок **`X-Hello: from-plugin`**, которого нет ни в `whoami`, ни в Traefik «из коробки» — его поставил наш плагин. Поля `name` и `value` в метках — это поля структуры `Config` из `plugin.go`: структура объявляет, какие настройки принимает плагин.

**Плагин из каталога** подключается так (в прогоне методички не запускался — нужен интернет и сторонний код):

```yaml
experimental:
  plugins:
    rewritebody:
      moduleName: github.com/packruler/rewrite-body
      version: v1.2.0
```

**Риски плагинов — обязательно прочитай:**

- плагин **выполняется внутри процесса Traefik** без изолированной среды: он видит все запросы и ответы, включая пароли и токены;
- плагин из каталога **скачивается при запуске** — если автор выпустит вредоносную версию, а ты не закрепишь версию, получишь её;
- Yaegi — интерпретатор, **не все пакеты Go** в нём работают, а скорость ниже, чем у встроенных middleware.

Правила: брать плагины только из источников, которым доверяешь; **закреплять версию** (`version: v1.2.0`, не «последняя»); читать код перед подключением; если нужна критичная логика (авторизация, шифрование) — лучше отдельный сервис и `forwardAuth`, а не плагин.

### why
Плагины делают Traefik расширяемым, но для большинства задач хватает встроенных middleware и `forwardAuth`. Локальный плагин — хороший способ **понять**, как устроен конвейер: любая встроенная станция устроена так же — получает запрос, что-то делает, передаёт `next`.

### deep Команды по частям
`.traefik.yml` — манифест плагина: тип (`middleware`), путь импорта и тестовые данные. `go.mod` — объявление модуля Go (имя должно совпадать с `moduleName`). В `plugin.go`: `Config` — настройки, `CreateConfig()` — их значения по умолчанию, `New(...)` — создание экземпляра, `ServeHTTP(...)` — обработка запроса (после своих действий нужно вызвать `next.ServeHTTP`, иначе запрос не пойдёт дальше). Каталог плагина в контейнере: `/plugins-local/src/github.com/mira/myheader`.

### deep Как ещё можно
- **Wasm-плагины:** в Traefik есть и поддержка WebAssembly (плагины на других языках), но она менее распространена.
- **Тестирование плагина:** обычные Go-тесты (`go test`) на `http.Handler`, до подключения к Traefik.
- **Публикация в каталог:** репозиторий на GitHub с темой `traefik-plugin` и тегами версий.

### deep Если не получилось
- **В журнале `plugin: failed to eval`** — ошибка в коде Go (Yaegi сообщает строку); проверь синтаксис и импорты.
- **`unable to find plugin`** — путь к папке не совпадает с `moduleName` (`/plugins-local/src/github.com/mira/myheader`) или не подключён `experimental.localPlugins` в `traefik.yml`.
- **Заголовка нет** — middleware не подключён к роутеру (`routers.s95.middlewares=hello`) или поля метки названы не так, как в `Config` (`name`, `value`).

### quiz
- Чем локальный плагин отличается от плагина из каталога?
- Какие три файла нужны в папке плагина и за что отвечает каждый?
- Какие риски у плагинов и как их снижают?

### links
- https://doc.traefik.io/traefik/plugins/ | плагины Traefik | Traefik: plugins
- https://github.com/traefik/plugindemo | демонстрационный плагин | GitHub: plugindemo

## 9.6 Миграция с v2 на v3 | short: Миграция v2 → v3 | est: ~50 мин
### intro
**Слова шага:** *миграция*, *`ipWhiteList` → `ipAllowList`*, *синтаксис правил v2 и v3*, *`ruleSyntax`*, *`defaultRuleSyntax`*, *`Headers` → `Header`*.

:::tip Если совсем просто
Ты наверняка встретишь конфигурацию, написанную для Traefik v2: в интернете большинство старых примеров именно такие. Часть из них в v3 **перестанет работать**. Мы узнаем, что именно, и как перевести их без боли.
:::

Основные изменения между v2 и v3, которые ломают старые конфигурации:

| v2 | v3 | Что делать |
|---|---|---|
| middleware `ipWhiteList` | **`ipAllowList`** | переименовать (метки и файлы); старое имя в v3 ещё работает, но с предупреждением `deprecated` |
| ``HostRegexp(`{sub:[a-z]+}.example.com`)`` | ``HostRegexp(`^[a-z]+\.example\.com$`)`` | обычное регулярное выражение вместо `{имя:шаблон}` |
| `Headers(…)`, `HeadersRegexp(…)` | `Header(…)`, `HeaderRegexp(…)` | единственное число |
| ``PathPrefix(`/a`, `/b`)`` не было | можно несколько значений | необязательно |
| `ipStrategy` в `ipWhiteList` | то же в `ipAllowList` | без изменений |
| `traefik.enable` и др. | без изменений | — |
| провайдер Marathon, Rancher v1 | удалены | перейти на другие провайдеры |
| `sticky.cookie` | без изменений | — |

Чтобы переехать **постепенно**, в v3 есть режим совместимости: старый синтаксис правил можно сохранить **для отдельного роутера** меткой `ruleSyntax=v2` или **для всего Traefik** настройкой `core.defaultRuleSyntax: v2` в статической конфигурации. Проверим на стенде два роутера с **одним и тем же** правилом в синтаксисе v2 (с фигурными скобками): у второго включён режим совместимости:

```bash run
cd ~/traefik-lab/edge
docker compose -f compose.s95lab.yaml down 2>&1 | tail -1
cat > compose.s96.yaml <<'EOF'
name: s96

services:
  v3:
    image: traefik/whoami
    command: ["--name", "ПРАВИЛО-V3"]
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.s96-v3.rule=HostRegexp(`{sub:[a-z0-9]+}.shop.localhost`) && PathPrefix(`/v3`)
      - traefik.http.routers.s96-v3.entrypoints=websecure
      - traefik.http.routers.s96-v3.tls=true
      - traefik.http.services.s96-v3.loadbalancer.server.port=80
  v2:
    image: traefik/whoami
    command: ["--name", "ПРАВИЛО-V2"]
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.s96-v2.rule=HostRegexp(`{sub:[a-z0-9]+}.shop.localhost`) && PathPrefix(`/v2`)
      - traefik.http.routers.s96-v2.ruleSyntax=v2
      - traefik.http.routers.s96-v2.entrypoints=websecure
      - traefik.http.routers.s96-v2.tls=true
      - traefik.http.services.s96-v2.loadbalancer.server.port=80
  hdr:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.s96-hdr.rule=Host(`hdr.shop.localhost`) && Headers(`X-Debug`, `1`)
      - traefik.http.routers.s96-hdr.entrypoints=websecure
      - traefik.http.routers.s96-hdr.tls=true
      - traefik.http.services.s96-hdr.loadbalancer.server.port=80
  old-wl:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.s96-wl.rule=Host(`v2.shop.localhost`) && PathPrefix(`/wl`)
      - traefik.http.routers.s96-wl.entrypoints=websecure
      - traefik.http.routers.s96-wl.tls=true
      - traefik.http.routers.s96-wl.middlewares=s96-old-wl
      - traefik.http.middlewares.s96-old-wl.ipwhitelist.sourcerange=10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
      - traefik.http.services.s96-wl.loadbalancer.server.port=80

networks:
  proxy:
    external: true
EOF
docker compose -f compose.s96.yaml up -d 2>&1 | tail -1
sleep 6
tapi() { curl -s -u mira:coffee-secret "https://traefik.shop.localhost/api/$1"; }
echo "--- роутеры глазами Traefik (статус и ошибка):"
tapi http/routers | jq -r '.[] | select(.name | startswith("s96-")) | [.name, .status, ((.error // []) | join(" ") | sub("^.*: unsupported"; "unsupported"))] | @tsv' | sort
echo "--- запросы:"
curl -s -o /dev/null -w 'правило v2-синтаксиса БЕЗ ruleSyntax -> HTTP %{http_code}\n' https://v2.shop.localhost/v3/
curl -s -o /dev/null -w 'старый ipWhiteList (пока работает)    -> HTTP %{http_code}\n' https://v2.shop.localhost/wl/
curl -s https://v2.shop.localhost/v2/ | grep -m1 '^Name' | sed 's/^/правило v2-синтаксиса С ruleSyntax=v2 -> /'
echo "--- что написал Traefik про ipwhitelist:"
docker compose logs --no-log-prefix traefik 2>&1 | grep -iE 'ipwhitelist' | cut -c1-170 | tail -1
```

### result
```out auto
```

- **`s96-hdr`** — правило `Headers(…)` (синтаксис v2): роутер получил статус **`disabled`** и ошибку `unsupported function: Headers`: в v3 правило называется `Header`. Это **громкая** поломка: она видна в дашборде и журнале.
- **`s96-v3`** — правило `HostRegexp({sub:[a-z0-9]+}.shop.localhost)` в синтаксисе v2, но **без** режима совместимости: статус `enabled` (Traefik не видит ошибки: фигурные скобки он считает частью обычного регулярного выражения), но **правило ничему не соответствует**, и запрос получает `404`. Это **тихая** поломка — самая коварная при миграции.
- **`s96-v2`** — то же правило с меткой `ruleSyntax=v2`: **работает** (`Name: ПРАВИЛО-V2`).
- **`ipwhitelist`** — старое имя middleware в v3 пока работает (запрос получил `200`), но в журнале — предупреждение: `Middleware … of type IPWhiteList is deprecated, please use IPAllowList instead`. Лечение — **переименовать в `ipallowlist`** до того, как имя удалят.

**План миграции без боли:**

1. Включи `core.defaultRuleSyntax: v2` в статической конфигурации (или `ruleSyntax=v2` на роутерах) — всё продолжит работать, как раньше.
2. Переведи правила на синтаксис v3 по одному (`Headers` → `Header`, `HostRegexp` с `{…}` → обычная регулярка) и проверь каждое в дашборде.
3. Замени `ipWhiteList` на `ipAllowList` (сейчас это предупреждение, потом будет ошибка), убери удалённые провайдеры.
4. Выключи режим совместимости.

Ещё одно напоминание про v3: **по умолчанию** Traefik v3 стал строже к закодированным символам в пути (мы видели предупреждение в журнале с первого запуска) — если твой бэкенд зависит от `%2F` и подобного, настройки `encodedCharacters` в входе нужно проверить по документации миграции.

### why
Миграция по принципу «режим совместимости, потом по шагам» безопаснее, чем «поправить всё сразу»: у тебя в каждый момент рабочий стенд. А знание таблицы замен экономит время при чтении чужих конфигураций: в блогах и ответах на форумах легко найти пример для v2 и не заметить, что он устарел.

### deep Команды по частям
`ruleSyntax=v2` на роутере или `core.defaultRuleSyntax: v2` в `traefik.yml` — выбор синтаксиса правил (`v3` по умолчанию). `jq … ((.error // []) | join(" ") | .[0:70])` — склеить список ошибок роутера в строку и взять первые 70 символов. Роутер с ошибкой остаётся в списке (статус `disabled`) — поэтому проверяй дашборд после каждого изменения.

### deep Как ещё можно
- **Официальная инструкция:** в документации Traefik есть страница «Migrate from v2 to v3» со всеми изменениями.
- **Параллельный запуск:** на время миграции можно держать v2 и v3 рядом на разных портах и переводить сервисы по одному.
- **Валидация конфигурации:** тестовый запуск `traefik --configFile=…` в контейнере показывает ошибки статической конфигурации до боевого запуска.

### deep Если не получилось
- **`s96-v3` отвечает `200`** — включён `defaultRuleSyntax: v2` в `traefik.yml` или твоя версия Traefik читает скобки как шаблон: проверь статическую конфигурацию.
- **Для всех трёх `404`** — не запущены роутеры: проверь `docker compose -f compose.s96.yaml ps` и что имена `*.shop.localhost` разрешаются.
- **Журнал не содержит предупреждения про `ipwhitelist`** — оно пишется один раз при создании middleware: пересоздай стенд (`docker compose -f compose.s96.yaml up -d --force-recreate`) и повтори поиск.

### quiz
- Как называется в v3 middleware, который раньше был `ipWhiteList`?
- Что изменилось в `HostRegexp` и как включить старый синтаксис для одного роутера?
- Из каких шагов состоит безопасная миграция?

### links
- https://doc.traefik.io/traefik/migrate/v2-to-v3/ | миграция v2 → v3 | Traefik: migrate v2 → v3
- https://doc.traefik.io/traefik/migrate/v3/ | изменения внутри v3 | Traefik: v3 migration guide

## 9.7 🔨 Подделка X-Forwarded-For | short: 🔨 Подделка X-Forwarded-For | est: ~55 мин
### intro
**Слова шага:** *подделка заголовка*, *`trustedIPs`*, *`ipStrategy.depth`*, *обход ограничения по IP*, *доверять только своим*.

:::tip Если совсем просто
Охрана пускает «только из офиса» и смотрит на записку «пришёл из офиса». Но записку может написать **любой посетитель**, если охрана верит запискам от всех подряд. Воспроизведём такой обход — и закроем его.
:::

Сценарий: админка `admin.shop.localhost` разрешена **только** адресам из «офисной» сети `203.0.113.0/24`. Оператор настроил `ipAllowList` с `ipStrategy.depth=1`: «перед Traefik один балансировщик; он **дописывает** адрес клиента в конец `X-Forwarded-For`; значит, настоящий клиент — **последний** адрес в заголовке». Но **вход при этом доверяет `X-Forwarded-For` от всей частной сети** (как мы настроили в шаге 9.4 — и наш «клиент» как раз из частной сети). Атакующий просто присылает нужный заголовок:

```bash run
cd ~/traefik-lab/edge
docker compose -f compose.s96.yaml down 2>&1 | tail -1
cat > compose.s97.yaml <<'EOF'
name: s97

services:
  admin:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.s97.rule=Host(`admin.shop.localhost`)
      - traefik.http.routers.s97.entrypoints=websecure
      - traefik.http.routers.s97.tls=true
      - traefik.http.routers.s97.middlewares=s97-office
      - traefik.http.middlewares.s97-office.ipallowlist.sourcerange=203.0.113.0/24
      - traefik.http.middlewares.s97-office.ipallowlist.ipstrategy.depth=1

networks:
  proxy:
    external: true
EOF
docker compose -f compose.s97.yaml up -d 2>&1 | tail -1
sleep 5
echo "--- обычный запрос (адрес не из офиса):"
curl -s -o /dev/null -w 'HTTP %{http_code}\n' https://admin.shop.localhost/
echo "--- атакующий присылает X-Forwarded-For: 203.0.113.7 (вход доверяет частной сети):"
curl -s -H 'X-Forwarded-For: 203.0.113.7' -o /dev/null -w 'HTTP %{http_code}\n' https://admin.shop.localhost/
```

### result
```out auto
```

Обычный запрос получил `403`, а запрос с поддельным заголовком — **`200`**: админка открыта. Разберём почему. Traefik доверяет заголовку от нашего клиента (его адрес в `trustedIPs`) и **оставляет** присланное `X-Forwarded-For: 203.0.113.7` как есть. Оператор взял **последний** адрес заголовка — а это то, что написал сам атакующий: честный балансировщик, дописывающий настоящий адрес, тут не участвовал.

**Починка** — сузить доверие до **настоящего** балансировщика. Если вход не доверяет источнику, заголовок от него **заменяется** настоящим адресом источника (он не из `203.0.113.0/24`), и доступ закрыт. Объявим доверенным только один «адрес балансировщика» (`10.99.99.99/32` — адрес, которого у нашего клиента нет):

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
        - "10.99.99.99/32"      # только настоящий балансировщик
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

accessLog: {}
EOF
docker compose restart traefik 2>&1 | tail -1
sleep 5
echo "--- та же подделка после сужения trustedIPs:"
curl -s -H 'X-Forwarded-For: 203.0.113.7' -o /dev/null -w 'HTTP %{http_code}\n' https://admin.shop.localhost/
docker compose -f compose.s97.yaml down 2>&1 | tail -1
```

```out auto
```

Теперь подделка не работает (`403`). Три правила, которые стоит запомнить из этого шага:

1. **`trustedIPs` — только адреса твоих прокси**, а не «всю частную сеть» и тем более не `0.0.0.0/0` (`forwardedHeaders.insecure: true`).
2. **`depth` должен совпадать с реальным числом доверенных прокси перед Traefik**; при неверном `depth` (и широком `trustedIPs`) ты берёшь адрес, который мог написать клиент.
3. **Лучшая защита от подделки IP — не использовать IP как единственный фактор**: для админок добавляй пароль, mTLS или `forwardAuth` (шаги 4.6, 7.6, 5.4).

### why
Это одна из самых частых реальных уязвимостей: «ограничение по IP» обходится одним заголовком. Причина всегда одна: доверие шире, чем реальная цепочка прокси. Проверка делается просто — отправь запрос с поддельным заголовком **со своего компьютера**: если он что-то изменил, доверие слишком широкое.

### deep Команды по частям
`ipallowlist.ipstrategy.depth=1` — брать последний (самый правый) адрес из `X-Forwarded-For`, как его получил Traefik. `forwardedHeaders.trustedIPs: ["10.99.99.99/32"]` — доверять заголовкам только от одного адреса (`/32` — ровно один адрес). `curl -H 'X-Forwarded-For: …'` — отправить свой заголовок.

### deep Как ещё можно
- **Не использовать `depth` вовсе:** если Traefik стоит прямо в интернете (нет прокси перед ним), оставь стратегию по умолчанию — Traefik берёт адрес соединения, подделать который нельзя.
- **`excludedIPs`:** перечислить адреса «своих» прокси, которые нужно пропустить при поиске клиента в цепочке (альтернатива `depth`).
- **Проверка в тестах:** добавь в проверки релиза (шаг 10.5) запрос с поддельным `X-Forwarded-For`, который обязан получить отказ.

### deep Если не получилось
- **Подделка не прошла даже в первом опыте (`403`)** — адрес клиента не входит в `trustedIPs` (в шаге 9.4 мы добавили частные сети; если у тебя другая подсеть Docker, добавь её).
- **После починки всё равно `200`** — Traefik не перезапущен (`trustedIPs` — статическая настройка): `docker compose restart traefik`.
- **`500` вместо `403`** — ошибка в метках middleware: проверь имена в дашборде (`s97-office@docker`).

### quiz
- Почему подделка `X-Forwarded-For` сработала в первом опыте?
- Как связаны `trustedIPs` и `ipStrategy.depth` и что должно совпадать с реальностью?
- Какие меры, кроме IP-ограничения, защищают админку?

### links
- https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/ipallowlist/ | ipAllowList | Traefik: ipAllowList
- https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Forwarded-For#security_and_privacy_concerns | безопасность X-Forwarded-For | MDN: X-Forwarded-For
