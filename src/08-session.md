# Сессия 8 · TLS, часть 2: Let’s Encrypt
dur: ~4 ч

## 8.1 ACME простыми словами; лимиты Let’s Encrypt | short: ACME и Let’s Encrypt | est: ~45 мин
### intro
**Слова шага:** *ACME*, *Let’s Encrypt*, *аккаунт*, *заказ (order)*, *вызов (challenge)*, *финализация*, *staging*, *лимиты*.

:::tip Если совсем просто
Раньше за сертификатом ходили в «паспортный стол» с бумагами и платили. **Let’s Encrypt** — бесплатный автоматический паспортный стол. Приходишь не лично, а программой: «хочу сертификат для `shop.example.com`». Стол отвечает: «докажи, что сайт твой — положи вот эту записку на сайт». Ты кладёшь, стол проверяет и выдаёт сертификат. Всё это без человека — по протоколу **ACME**.
:::

```svg
@acme-flow
```

**ACME** (*Automatic Certificate Management Environment*) — протокол, по которому программа (у нас Traefik) сама получает и обновляет сертификаты у удостоверяющего центра. **Let’s Encrypt** — бесплатный публичный центр, который отвечает по ACME. Порядок:

1. **Аккаунт.** Traefik регистрируется (почта нужна для напоминаний) и получает ключ аккаунта.
2. **Заказ.** «Хочу сертификат на `shop.example.com`».
3. **Вызов (challenge).** Центр придумывает задание, которое может выполнить только настоящий владелец имени: положить файл на сайт (**HTTP-01**), выставить особый сертификат на 443 (**TLS-ALPN-01**) или создать TXT-запись в DNS (**DNS-01**).
4. **Проверка.** Центр сам заходит и проверяет.
5. **Финализация.** Traefik присылает запрос на сертификат — получает готовый и подключает к сайту. Через ~60 дней он **сам обновит** сертификат (срок жизни — 90 дней).

Всё это Traefik делает сам; нам нужно написать несколько строк настройки. Для опытов у Let’s Encrypt есть **staging** («учебный» стенд): он работает по тем же правилам, но выдаёт сертификаты, которым браузеры **не доверяют**, и у него гораздо мягче лимиты. Посмотрим на «входную дверь» настоящего staging-сервера — каталог адресов ACME:

```bash run
curl -s https://acme-staging-v02.api.letsencrypt.org/directory | jq 'del(.meta)'
```

### result
```out auto
```

Каталог — это список адресов, по которым умеет отвечать ACME-сервер (запись со случайным именем в начале — не ошибка: Let’s Encrypt нарочно добавляет случайные ключи, чтобы клиенты не привыкали к жёстко записанному списку): `newNonce`, `newAccount` (регистрация), `newOrder` (заказ), `revokeCert` (отзыв) и другие. Traefik знает этот протокол и обращается к ним сам. Адрес каталога (`…/directory`) — единственное, что нужно указать в настройках (`caServer`).

**Лимиты Let’s Encrypt (боевого сервера):** их нужно знать заранее, потому что их легко исчерпать ошибками.

| Лимит | Значение (может меняться — сверяйся с документацией) |
|---|---|
| сертификатов на один зарегистрированный домен | 50 в неделю |
| точно такой же набор имён | 5 в неделю |
| неудачных проверок для одного имени | 5 в час |
| заказов на аккаунт | 300 в 3 часа |

Поэтому правило: **всё отлаживай на staging** (`caServer: https://acme-staging-v02.api.letsencrypt.org/directory`) и только потом переключай на боевой.

**Что у нас в лабе вместо настоящего Let’s Encrypt.** У нас нет реального домена и публичного адреса, поэтому проверку нельзя выполнить «по-настоящему»: настоящему серверу некуда прийти. Вместо staging мы поднимем **Pebble** — тестовый ACME-сервер от самого Let’s Encrypt: он понимает тот же протокол и проходит все три вида проверки, только работает у нас на компьютере и выдаёт «учебные» сертификаты. Для Traefik разницы нет: меняется лишь `caServer`. Всё, что мы пройдём в шагах 8.2–8.3, **честно выполнено** — но **с Pebble, а не с реальным Let’s Encrypt**.

### why
ACME — причина, по которой «сертификаты» перестали быть заботой людей: нет ручной выдачи, нет забытых сроков. Но чтобы не получить бан по лимитам и понимать журнал при ошибках, нужно знать, как идёт заказ и какие проверки бывают.

### deep Команды по частям
`curl -s https://acme-staging-v02.api.letsencrypt.org/directory` — получить каталог (JSON); `jq 'del(.meta)'` — убрать вложенный блок `meta` (описание условий и сайт центра), чтобы вывод был короче.

### deep Как ещё можно
- **Другие ACME-центры:** ZeroSSL, Google Trust Services, Buypass; в Traefik меняется только `caServer` (и, для некоторых, нужны ключи привязки аккаунта `eab`).
- **`certbot`** — «классический» клиент ACME: тоже получает сертификат, но обновление и перезагрузку сервера нужно настраивать отдельно.
- **Caddy** делает то же самое автоматически, без настроек (если ты проходила Caddy-лабу).

### deep Если не получилось
- **`curl` не получает ответ** — нет интернета или блокируется доступ к Let’s Encrypt; тогда шаг можно пропустить: следующие шаги работают без интернета (Pebble локально).
- **В выводе есть `meta`** — ты не добавила `jq 'del(.meta)'`, это нормально, просто длиннее.

### quiz
- Назови шаги ACME от аккаунта до готового сертификата.
- Чем отличаются проверки HTTP-01, TLS-ALPN-01 и DNS-01?
- Зачем нужен staging и что такое Pebble?

### links
- https://letsencrypt.org/how-it-works/ | как работает Let’s Encrypt | Let’s Encrypt: how it works
- https://letsencrypt.org/docs/rate-limits/ | лимиты | Let’s Encrypt: rate limits

## 8.2 certificatesResolvers и HTTP-01 | short: Resolver и HTTP-01 | est: ~60 мин
### intro
**Слова шага:** *`certificatesResolvers`*, *`httpChallenge`*, *`acme.json`*, *Pebble*, *`caServer`*, *`certResolver`*, *`constraints`*.

:::tip Если совсем просто
Мы ставим в доме **автомат по выдаче паспортов**: говорим, где «паспортный стол» (`caServer`), как с ним доказывать (`httpChallenge`) и где хранить выданные паспорта (`acme.json`). А на каждой двери (роутере) пишем: «паспорт для меня выдавай этот автомат» (`tls.certresolver=le`).
:::

**Резолвер сертификатов** (`certificatesResolvers`) — раздел статической конфигурации Traefik, в котором описано **как получать сертификаты**. В нём: почта, `storage` (файл, где лежит всё полученное — ключ аккаунта и сертификаты), `caServer` (адрес ACME) и **способ проверки** (`httpChallenge`, `tlsChallenge` или `dnsChallenge`). Роутер, которому нужен сертификат, ссылается на резолвер меткой **`tls.certresolver=имя`**; увидев имя в правиле `Host()`, Traefik сам закажет сертификат.

**HTTP-01** — самая простая проверка: центр заходит на `http://имя/.well-known/acme-challenge/<токен>` (порт **80**), а Traefik отвечает нужным значением. Поэтому имя должно указывать на твой сервер и порт 80 должен быть доступен из интернета.

Чтобы это проверить у себя, нам нужен свой ACME-сервер, который «заходит» на наши имена: Pebble и маленький помощник к нему (**challtestsrv**, «DNS-шпаргалка»: на любой вопрос «где живёт имя?» отвечает адресом нашего Traefik). Построим **отдельный учебный стенд** `acme` с собственным Traefik — чтобы не трогать основной стенд `edge`. Структура:

```text
~/traefik-lab/acme/
├── compose.yaml       # Pebble + challtestsrv + свой Traefik + whoami
├── traefik.yml        # статическая конфигурация (resolver)
├── pebble/
│   ├── pebble-config.json
│   └── pebble.minica.pem   # корень, которому доверяет Traefik при разговоре с Pebble
└── letsencrypt/       # сюда Traefik положит acme.json
```

```bash run
mkdir -p ~/traefik-lab/acme/pebble ~/traefik-lab/acme/letsencrypt ~/traefik-lab/acme/hooks && cd ~/traefik-lab/acme
docker create --name pebble-src ghcr.io/letsencrypt/pebble:latest > /dev/null
docker cp pebble-src:/test/certs/pebble.minica.pem pebble/pebble.minica.pem
docker rm pebble-src > /dev/null
cat > pebble/pebble-config.json <<'EOF'
{
  "pebble": {
    "listenAddress": "0.0.0.0:14000",
    "managementListenAddress": "0.0.0.0:15000",
    "certificate": "test/certs/localhost/cert.pem",
    "privateKey": "test/certs/localhost/key.pem",
    "httpPort": 80,
    "tlsPort": 443,
    "ocspResponderURL": "",
    "externalAccountBindingRequired": false,
    "retryAfter": { "authz": 1, "order": 1 },
    "keyAlgorithm": "ecdsa",
    "profiles": { "default": { "description": "default", "validityPeriod": 7776000 } }
  }
}
EOF
cat > traefik.yml <<'EOF'
entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

providers:
  docker:
    exposedByDefault: true                 # включаем всё, но только то, что прошло constraints
    network: acme
    constraints: "Label(`acme-lab`, `true`)"

certificatesResolvers:
  le:
    acme:
      email: admin@example.test
      storage: /letsencrypt/acme.json
      caServer: https://pebble:14000/dir   # у настоящего staging: https://acme-staging-v02.api.letsencrypt.org/directory
      httpChallenge:
        entryPoint: web

log:
  level: INFO
  noColor: true
EOF
cat > compose.yaml <<'EOF'
name: acme

services:
  pebble:
    image: ghcr.io/letsencrypt/pebble:latest
    command: ["-config", "/pebble/pebble-config.json", "-dnsserver", "challtestsrv:8053"]
    environment:
      PEBBLE_VA_NOSLEEP: "1"
    volumes:
      - ./pebble:/pebble:ro
    ports:
      - "15000:15000"
    networks: [acme]

  challtestsrv:
    image: ghcr.io/letsencrypt/pebble-challtestsrv:latest
    command: ["-defaultIPv4", "10.30.50.3", "-defaultIPv6", "", "-http01", "", "-https01", "", "-tlsalpn01", ""]
    ports:
      - "8055:8055"
    networks:
      acme:
        ipv4_address: 10.30.50.4

  traefik:
    image: traefik:v3.7
    environment:
      LEGO_CA_CERTIFICATES: /pebble.minica.pem
    ports:
      - "8443:443"
    volumes:
      - ./traefik.yml:/etc/traefik/traefik.yml:ro
      - ./pebble/pebble.minica.pem:/pebble.minica.pem:ro
      - ./letsencrypt:/letsencrypt
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      acme:
        ipv4_address: 10.30.50.3

  shop:
    image: traefik/whoami
    networks: [acme]
    labels:
      - acme-lab=true
      - traefik.http.routers.shop.rule=Host(`shop.example.test`)
      - traefik.http.routers.shop.entrypoints=websecure
      - traefik.http.routers.shop.tls.certresolver=le

networks:
  acme:
    name: acme
    ipam:
      config:
        - subnet: 10.30.50.0/24
          ip_range: 10.30.50.128/25
EOF
docker compose up -d 2>&1 | tail -4
sleep 20
echo "--- какие сертификаты получил Traefik (файл acme.json):"
jq -r '.le.Certificates[] | [.domain.main, (.domain.sans // [] | join(","))] | @tsv' letsencrypt/acme.json
ls -l letsencrypt/acme.json | awk '{print $1, $NF}'
```

### result
```out auto
```

Traefik **сам** зарегистрировался у Pebble, заказал сертификат на `shop.example.test`, прошёл проверку HTTP-01 и сохранил результат в `acme.json`. Мы ничего не выпускали руками. Обрати внимание на права файла: **`-rw-------`** (600, читает только владелец) — в файле лежит закрытый ключ, и Traefik требует такие права (если они шире — отказывается работать, шаг 8.7).

Проверим сертификат «снаружи», как это сделал бы клиент. Корень Pebble у каждого запуска свой — возьмём его у самого Pebble и попросим `curl` проверять сертификат по нему:

```bash run
cd ~/traefik-lab/acme
curl -s --cacert pebble/pebble.minica.pem https://localhost:15000/roots/0 -o pebble/pebble-root.pem
echo "--- запрос по HTTPS с проверкой сертификата (порт 8443 — так мы вывели 443 наружу):"
curl -sv --cacert pebble/pebble-root.pem https://shop.example.test:8443/ -o /dev/null 2>&1 | grep -E 'SSL connection using|subject:|issuer:|expire date|using HTTP/'
```

```out auto
```

Соединение прошло **с настоящей проверкой**: `issuer` — тестовый центр Pebble (цепочка ведёт к корню, который мы дали `curl`), срок — 90 дней. Поле `subject` пустое — у современных сертификатов имя хранится не в нём, а в списке **альтернативных имён (SAN)**, и проверяется оно именно там. Браузер отнёсся бы к этому сертификату как к чужому (корень Pebble ему не знаком) — точно так же, как к сертификату staging.

Три слова, которые встретились в настройке:

- **`constraints`** — «фильтр контейнеров»: этот Traefik учитывает только те, у которых есть метка `acme-lab=true`. Так второй Traefik на той же Docker-машине не трогает чужие контейнеры (и их не трогает основной `edge`: у наших нет `traefik.enable`). Выражение пишется на таком же языке правил, как `Host()`.
- **`exposedByDefault: true`** здесь безопасен именно благодаря `constraints`.
- **`entryPoint: web`** в `httpChallenge` — через какой вход приходит проверка (должен быть порт 80).

Для **настоящего** staging в `caServer` стоит адрес Let’s Encrypt, нужен публичный домен, указывающий на сервер, и открытый порт 80; Pebble и `challtestsrv` исчезают из файла.

### why
Вся автоматика — три вещи: **резолвер** (как получать), **метка на роутере** (для какого имени) и **файл хранения** (где держать). Дальше Traefik сам заказывает, подключает и обновляет сертификаты. Важно хранить `acme.json` на томе, который переживает пересоздание контейнера: иначе при каждом перезапуске будет новый заказ, и лимиты Let’s Encrypt закончатся.

### deep Команды по частям
`docker create --name pebble-src … && docker cp pebble-src:/test/certs/pebble.minica.pem …` — достать из образа Pebble файл корневого сертификата без запуска контейнера (`docker create` создаёт контейнер, но не запускает его). `LEGO_CA_CERTIFICATES` — переменная библиотеки `lego` (на ней построен ACME-клиент Traefik): «доверяй этому CA при разговоре с ACME-сервером». `ipv4_address: 10.30.50.3` — фиксированный адрес Traefik, чтобы `challtestsrv` отвечал им на DNS-запросы. `jq -r '.le.Certificates[] | …'` — список сертификатов в `acme.json` (ключ `le` — имя резолвера). `curl --cacert файл` — проверять сертификат только по этому корню.

### deep Как ещё можно
- **`tlsChallenge` и `dnsChallenge`** — другие способы проверки (шаг 8.3).
- **Хранилище в Consul/etcd** или общий том — для кластеров из нескольких Traefik (у файла `acme.json` на каждом экземпляре будет свой аккаунт).
- **Использовать резолвер по умолчанию:** `entryPoints.websecure.http.tls.certResolver: le` — тогда метку `tls.certresolver` на каждом роутере писать не нужно.

### deep Если не получилось
- **В `acme.json` пусто** — Traefik не успел или проверка не прошла: смотри `docker compose logs traefik` (ищи слова `acme`, `error`) и `docker compose logs pebble`.
- **`certificate signed by unknown authority` в журнале Traefik при разговоре с Pebble** — не подключён `LEGO_CA_CERTIFICATE`/файл `pebble.minica.pem`: проверь `environment` и монтирование.
- **`Bind … port is already allocated` на 8443/15000/8055** — порт занят: смени левую цифру в `ports`.

### quiz
- Что описывает раздел `certificatesResolvers` и какой меткой роутер выбирает резолвер?
- Зачем Traefik файл `acme.json`, почему он должен храниться на томе и почему у него права `600`?
- Что делает `constraints` и когда он необходим?

### links
- https://doc.traefik.io/traefik/reference/install-configuration/tls/certificate-resolvers/acme/ | ACME в Traefik | Traefik: ACME
- https://github.com/letsencrypt/pebble | Pebble | GitHub: Pebble

## 8.3 TLS-ALPN-01, DNS-01 и wildcard | short: TLS-ALPN-01, DNS-01, wildcard | est: ~60 мин
### intro
**Слова шага:** *TLS-ALPN-01*, *DNS-01*, *TXT-запись*, *wildcard-сертификат*, *`tls.domains`*, *провайдер `exec`*, *`propagation`*.

:::tip Если совсем просто
Доказать, что имя твоё, можно тремя способами. **HTTP-01**: «положи записку на сайт» (нужен открытый порт 80). **TLS-ALPN-01**: «покажи особый сертификат на порту 443» (порт 80 не нужен). **DNS-01**: «запиши записку в адресную книгу домена» (вообще не нужен доступ извне к серверу — и только он умеет выдавать сертификат на **все поддомены сразу**).
:::

| Проверка | Что нужно | Когда выбирать |
|---|---|---|
| HTTP-01 | открытый порт 80 | обычный публичный сайт |
| TLS-ALPN-01 | открытый порт 443, порт 80 закрыт | когда 80 недоступен |
| DNS-01 | доступ к DNS-записям домена (по API провайдера) | сервер за закрытым периметром, **wildcard** (`*.example.com`), внутренние сервисы |

**Wildcard-сертификат** `*.example.test` покрывает любой поддомен первого уровня и выдаётся **только** по DNS-01 (этого требуют правила ACME). В Traefik он заказывается через **`tls.domains`**: «главное имя `example.test` + дополнительные `*.example.test`».

DNS-01 требует, чтобы программа могла **создавать TXT-записи** в DNS домена. Для настоящих провайдеров (Cloudflare, Route 53, Gandi и ещё больше сотни) в Traefik есть готовые встроенные адаптеры: достаточно указать `provider: cloudflare` и положить токен в переменную окружения (шаг 8.4). У нас нет настоящего DNS, поэтому используем **универсальный адаптер `exec`**: Traefik вызывает наш небольшой скрипт, а тот отправляет TXT-запись в `challtestsrv` (наш «учебный DNS»). Скрипт получает три аргумента: действие (`present` — создать, `cleanup` — убрать), имя записи и значение. Добавляем в стенд два новых резолвера и три сайта:

```bash run
cd ~/traefik-lab/acme
cat > hooks/dns-hook.sh <<'EOF'
#!/bin/sh
# Адаптер DNS-01 для Traefik (провайдер exec): present|cleanup <имя TXT-записи> <значение>
action=$1; host=$2; value=$3
case "$action" in
  present) wget -qO- --header 'Content-Type: application/json' --post-data "{\"host\":\"$host\",\"value\":\"$value\"}" http://challtestsrv:8055/set-txt ;;
  cleanup) wget -qO- --header 'Content-Type: application/json' --post-data "{\"host\":\"$host\"}" http://challtestsrv:8055/clear-txt ;;
esac
EOF
chmod +x hooks/dns-hook.sh
cat > traefik.yml <<'EOF'
entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

providers:
  docker:
    exposedByDefault: true
    network: acme
    constraints: "Label(`acme-lab`, `true`)"

certificatesResolvers:
  le:                               # HTTP-01
    acme:
      email: admin@example.test
      storage: /letsencrypt/acme.json
      caServer: https://pebble:14000/dir
      httpChallenge:
        entryPoint: web
  lealpn:                           # TLS-ALPN-01
    acme:
      email: admin@example.test
      storage: /letsencrypt/acme-alpn.json
      caServer: https://pebble:14000/dir
      tlsChallenge: {}
  ledns:                            # DNS-01 через наш адаптер
    acme:
      email: admin@example.test
      storage: /letsencrypt/acme-dns.json
      caServer: https://pebble:14000/dir
      dnsChallenge:
        provider: exec
        resolvers:
          - 10.30.50.4:8053         # учебный DNS (у настоящего DNS-провайдера этого поля нет)
        propagation:
          disableChecks: true       # в учебном DNS записи появляются мгновенно

log:
  level: INFO
  noColor: true
EOF
cat > compose.yaml <<'EOF'
name: acme

services:
  pebble:
    image: ghcr.io/letsencrypt/pebble:latest
    command: ["-config", "/pebble/pebble-config.json", "-dnsserver", "challtestsrv:8053"]
    environment:
      PEBBLE_VA_NOSLEEP: "1"
    volumes:
      - ./pebble:/pebble:ro
    ports:
      - "15000:15000"
    networks: [acme]

  challtestsrv:
    image: ghcr.io/letsencrypt/pebble-challtestsrv:latest
    command: ["-defaultIPv4", "10.30.50.3", "-defaultIPv6", "", "-http01", "", "-https01", "", "-tlsalpn01", ""]
    ports:
      - "8055:8055"
    networks:
      acme:
        ipv4_address: 10.30.50.4

  traefik:
    image: traefik:v3.7
    environment:
      LEGO_CA_CERTIFICATES: /pebble.minica.pem
      EXEC_PATH: /hooks/dns-hook.sh
    ports:
      - "8443:443"
    volumes:
      - ./traefik.yml:/etc/traefik/traefik.yml:ro
      - ./pebble/pebble.minica.pem:/pebble.minica.pem:ro
      - ./hooks:/hooks:ro
      - ./letsencrypt:/letsencrypt
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      acme:
        ipv4_address: 10.30.50.3

  shop:
    image: traefik/whoami
    networks: [acme]
    labels:
      - acme-lab=true
      - traefik.http.routers.shop.rule=Host(`shop.example.test`)
      - traefik.http.routers.shop.entrypoints=websecure
      - traefik.http.routers.shop.tls.certresolver=le

  alpn:
    image: traefik/whoami
    networks: [acme]
    labels:
      - acme-lab=true
      - traefik.http.routers.alpn.rule=Host(`alpn.example.test`)
      - traefik.http.routers.alpn.entrypoints=websecure
      - traefik.http.routers.alpn.tls.certresolver=lealpn

  wild:
    image: traefik/whoami
    networks: [acme]
    labels:
      - acme-lab=true
      - traefik.http.routers.wild.rule=Host(`wild.example.test`)
      - traefik.http.routers.wild.entrypoints=websecure
      - traefik.http.routers.wild.tls.certresolver=ledns
      - traefik.http.routers.wild.tls.domains[0].main=example.test
      - traefik.http.routers.wild.tls.domains[0].sans=*.example.test

networks:
  acme:
    name: acme
    ipam:
      config:
        - subnet: 10.30.50.0/24
          ip_range: 10.30.50.128/25
EOF
docker compose up -d 2>&1 | tail -3
echo "--- ждём, пока Traefik получит все три сертификата (до 90 секунд):"
for i in $(seq 1 30); do
  n=0
  for f in acme acme-alpn acme-dns; do c=$(jq -r '[.[].Certificates[]?] | length' letsencrypt/$f.json 2>/dev/null || echo 0); n=$((n + c)); done
  [ "$n" -ge 3 ] && break
  sleep 3
done
sleep 5
echo "--- сертификаты по резолверам:"
for f in acme acme-alpn acme-dns; do printf '%-10s ' $f; jq -r '.[].Certificates[]? | [.domain.main, (.domain.sans // [] | join(","))] | @tsv' letsencrypt/$f.json | tr '\n' ' '; echo; done
echo "--- запросы по HTTPS (проверка по корню Pebble):"
for h in shop alpn wild foo; do
  curl -s --cacert pebble/pebble-root.pem -o /dev/null -w "$h.example.test -> HTTP %{http_code}\n" https://$h.example.test:8443/
done
```

### result
```out auto
```

Три резолвера — три способа:

- **`shop`** (HTTP-01) — сертификат на `shop.example.test`.
- **`alpn`** (TLS-ALPN-01) — сертификат на `alpn.example.test`: проверка шла **по порту 443**, порт 80 не использовался.
- **`wild`** (DNS-01) — **один** сертификат на `example.test` и `*.example.test`. Скрипт `dns-hook.sh` создал TXT-запись, Pebble её увидел и всё выдал.

Проверка в конце: `shop`, `alpn` и `wild` отвечают `200`, а имя **`foo.example.test`**, для которого у нас нет ни роутера, ни отдельного сертификата, получает **`404`, но с валидным TLS** — его закрыл wildcard `*.example.test` (поэтому `curl` не ругнулся на сертификат). Именно за это wildcard и любят: любой новый поддомен сразу получает рабочий HTTPS, не заказывая сертификат отдельно.

### why
Выбор типа проверки определяется **вашим окружением**: порт 80 открыт — HTTP-01; нет — TLS-ALPN-01; сервер внутри сети или нужны wildcard — DNS-01. Wildcard к тому же сокращает число заказов (лимиты!): один сертификат вместо двадцати. И ещё одно следствие, которое пригодится в шаге 8.7: если у Traefik уже есть сертификат, **покрывающий имя** (в том числе wildcard из другого резолвера), он **не станет заказывать новый**.

### deep Команды по частям
`provider: exec` + `EXEC_PATH` — Traefik запускает скрипт с аргументами `present|cleanup`, имя и значение. `wget --post-data` — отправить JSON (в образе Traefik есть `wget` из BusyBox). `tls.domains[0].main` и `.sans` — заказать сертификат на главное имя и дополнительные (`[0]` — индекс записи в списке). `jq -r '.[].Certificates[]? …'` — перебрать все резолверы в файле (`.[]`) и их сертификаты. `propagation.disableChecks: true` — не проверять, что запись «разошлась» по DNS-серверам (в учебном DNS это мгновенно; в настоящем эту проверку **не выключают**).

### deep Как ещё можно
- **Готовые провайдеры:** `provider: cloudflare` (`CF_DNS_API_TOKEN`), `route53`, `digitalocean`, `gandi` и другие — вместо `exec`; их список и нужные переменные — в документации `lego`.
- **Задержка проверки:** `propagation.delayBeforeChecks: 30s` — подождать, пока запись распространится (для настоящих провайдеров полезно).
- **`dnsChallenge.resolvers`** — какие DNS-серверы спрашивать при проверке; у настоящих провайдеров обычно указывают публичные (`1.1.1.1:53`).

### deep Если не получилось
- **Файл `acme-dns.json` без сертификатов** — не отработал адаптер: проверь, что `hooks/dns-hook.sh` исполняемый (`chmod +x`) и пути внутри контейнера верны (`/hooks/dns-hook.sh`); смотри `docker compose logs traefik`.
- **`permission denied` при запуске адаптера** — нет права на исполнение; **а если `docker compose` создал вместо файла каталог** (файла не было на момент запуска) — удали его и создай скрипт заново до `docker compose up`.
- **`alpn` не получил сертификат** — порт 443 внутри сети должен быть доступен Pebble (мы настроили `tlsPort: 443` в `pebble-config.json`).
- **Прошло больше 30 секунд, сертификатов нет** — подожди ещё и посмотри журналы обоих сервисов (`docker compose logs pebble traefik`).

### quiz
- В каких случаях выбирают TLS-ALPN-01, а в каких DNS-01?
- Что такое wildcard-сертификат и какой единственный способ проверки его выдаёт?
- Как Traefik узнаёт, на какие имена заказывать сертификат в `tls.domains`?

### links
- https://doc.traefik.io/traefik/reference/install-configuration/tls/certificate-resolvers/acme/#dnschallenge | DNS-01 в Traefik | Traefik: DNS challenge
- https://go-acme.github.io/lego/dns/ | провайдеры DNS в lego | lego: DNS providers

## 8.4 Токены DNS-провайдера: секреты не в репозитории | short: Токены и секреты | est: ~40 мин
### intro
**Слова шага:** *токен DNS-провайдера*, *переменные окружения*, *`_FILE`*, *`.gitignore`*, *секреты*, *права `600`*.

:::tip Если совсем просто
Токен DNS-провайдера — **ключ от адресной книги твоего домена**. Кто его получит, сможет изменить, куда ведёт любое имя. Относись к нему как к паролю от банка: не пиши в файлы, которые попадут в репозиторий, и держи вне картинки (образа).
:::

С настоящим DNS-провайдером настройка выглядит так (**в прогоне методички не запускалось** — для этого нужен настоящий домен и токен; конфигурация проверена только на синтаксис):

```yaml
# traefik.yml
certificatesResolvers:
  le:
    acme:
      email: admin@example.com
      storage: /letsencrypt/acme.json
      dnsChallenge:
        provider: cloudflare          # имя провайдера из списка lego

# compose.yaml, сервис traefik
    environment:
      CF_DNS_API_TOKEN_FILE: /run/secrets/cf_token   # токен читается из файла
    secrets: [cf_token]

secrets:
  cf_token:
    file: ./secrets/cf_token.txt                     # файл вне git
```

Три способа передать токен, от худшего к лучшему:

1. **Прямо в `compose.yaml`** (`CF_DNS_API_TOKEN: abcdef…`) — **никогда**: файл попадёт в git.
2. **Из `.env`** (`CF_DNS_API_TOKEN=${CF_DNS_API_TOKEN}` + файл `.env` в `.gitignore`) — приемлемо для разработки.
3. **Из файла секрета** (`…_TOKEN_FILE` + Docker secrets) — лучше всего: токен не виден в `docker inspect` и переменных окружения процесса.

Главное — убедиться, что токен **не попадёт в репозиторий**. Для этого `.gitignore` и права `600`:

```bash run
cd ~/traefik-lab/acme
mkdir -p secrets
printf 'fake-token-for-the-lab\n' > secrets/cf_token.txt
chmod 600 secrets/cf_token.txt
printf 'secrets/\nletsencrypt/\n.env\n' > .gitignore
git init -q . 2>/dev/null
git add -A . 2>/dev/null
echo "--- что git собирается закоммитить:"
git status --short | head -10
echo "--- проверяем, что секреты и хранилище сертификатов игнорируются:"
git check-ignore -v secrets/cf_token.txt letsencrypt/acme.json
```

### result
```out auto
```

В списке на коммит нет ни `secrets/`, ни `letsencrypt/`: `git check-ignore` показывает, **какое именно правило** `.gitignore` их скрывает. Вместе с ними не попадают в репозиторий ни токен, ни `acme.json` (в нём закрытые ключи сертификатов). Если токен всё-таки попал в публичный репозиторий — **считай его скомпрометированным**: сразу отзови у провайдера и выпусти новый (удаление коммита из истории не помогает: бот находит токены за секунды).

**Права токена у провайдера:** выдавай токену **минимум прав**: «редактировать DNS-записи только для одного домена» (Cloudflare: «Zone → DNS → Edit» для одной зоны). Тогда утечка не даст управлять аккаунтом целиком.

### why
Токен DNS — самый «дорогой» секрет в этой лабе: он позволяет перенаправить домен и получить на него любой сертификат. Дисциплина здесь проста и должна войти в привычку: **секреты — только в окружении или файлах секретов, вне git, с минимальными правами**.

### deep Команды по частям
`printf '…' > файл` — записать строку в файл. `chmod 600` — читает и пишет только владелец. `git init -q .` — создать пустой репозиторий (в учебной папке, только для проверки). `git add -A .` — поставить все файлы на учёт (игнорируемые пропускаются). `git status --short` — краткий список. `git check-ignore -v путь` — показать файл и строку правила, которое игнорирует путь.

### deep Как ещё можно
- **Docker secrets в Swarm/Kubernetes:** там секреты — отдельные объекты с контролем доступа; идея `…_FILE` та же.
- **Менеджеры секретов** (Vault, 1Password CLI, SOPS): токен достаётся из хранилища в момент запуска и нигде не лежит открытым текстом.
- **`git-secrets`, `gitleaks`:** утилиты, которые проверяют коммиты на токены перед отправкой.

### deep Если не получилось
- **`git` не нашёл `.gitignore`** — файл должен лежать в корне папки, где выполняется `git init`.
- **`check-ignore` ничего не печатает** — путь не игнорируется: проверь, нет ли опечатки в правиле (`secrets/` с косой чертой в конце — это папка).
- **Нет `git`** — на Mac он ставится вместе с Xcode Command Line Tools (`xcode-select --install`).

### quiz
- Почему токен DNS-провайдера опаснее обычного пароля от сайта?
- Какие три способа передать токен Traefik и какой лучший?
- Что делать, если токен попал в публичный репозиторий?

### links
- https://docs.docker.com/compose/how-tos/use-secrets/ | секреты в Compose | Compose: secrets
- https://github.com/gitleaks/gitleaks | gitleaks | GitHub: gitleaks

## 8.5 HTTP/3 (QUIC) | short: HTTP/3 | est: ~45 мин
### intro
**Слова шага:** *HTTP/3*, *QUIC*, *UDP*, *`http3`*, *`Alt-Svc`*, *`advertisedPort`*.

:::tip Если совсем просто
HTTP/1 и HTTP/2 ездят по «дороге» TCP: надёжной, но с «шлагбаумами» — потерянный пакет задерживает всех. HTTP/3 ездит по **UDP** (протокол QUIC): потеря не блокирует соседние запросы, а соединение устанавливается быстрее. Для сайта это означает быстрее на плохой сети (мобильной).
:::

**HTTP/3** работает поверх **QUIC** — транспорта на базе **UDP**, а не TCP, и порт для него нужно открыть **отдельно** (UDP/443). Браузер не знает заранее, что сервер умеет HTTP/3, поэтому первый запрос идёт по HTTP/2, а в ответе сервер сообщает заголовком **`Alt-Svc`**: «для этого сайта есть HTTP/3 на порту 443». Дальше браузер переключается сам. В Traefik это включается на **входе** — полем `http3`, и нужно опубликовать **UDP-порт**. Вернёмся к основному стенду `edge`:

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
cat > compose.yaml <<'EOF'
name: edge

services:
  traefik:
    image: traefik:v3.7
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"        # HTTP/3 ездит по UDP
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

  whoami:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.whoami.rule=Host(`whoami.localhost`)
      - traefik.http.routers.whoami.entrypoints=websecure
      - traefik.http.routers.whoami.tls=true

networks:
  proxy:
    name: proxy
EOF
docker compose up -d 2>&1 | tail -2
sleep 5
echo "--- заголовок Alt-Svc в обычном ответе (по HTTP/2):"
curl -sI https://shop.localhost/ | grep -iE '^(HTTP|alt-svc)'
echo "--- опубликованные порты Traefik:"
docker compose ps --format '{{.Ports}}' traefik | tr ',' '\n' | sed 's/^ *//' | grep -E '443'
```

### result
```out auto
```

Ответ по HTTP/2 содержит **`Alt-Svc: h3=":443"; ma=2592000`**: «HTTP/3 доступен на порту 443, помни об этом 30 дней». И Traefik опубликовал два порта 443: `tcp` (для HTTP/1.1 и HTTP/2) и `udp` (для HTTP/3). Чтобы убедиться, что HTTP/3 **действительно работает**, нужен клиент с поддержкой QUIC. У системного `curl` её обычно нет; проверим клиентом, у которого она есть, запустив его в контейнере с общей с хозяином сетью:

```bash run
docker run --rm --network host alpine/curl-http3 curl -sk --http3-only --resolve shop.localhost:443:127.0.0.1 -o /dev/null -w 'HTTP/3: версия %{http_version}, код %{http_code}\n' https://shop.localhost/
```

```out auto
```

Версия `3` в выводе — запрос действительно прошёл по HTTP/3 (UDP/443). Флаг `-k` здесь нужен только потому, что корень mkcert неизвестен контейнеру с другим `curl`. Для настоящего сайта HTTP/3 включается тем же полем, а проверить его можно в браузере: инструменты разработчика → вкладка Network → колонка Protocol покажет `h3`.

### why
HTTP/3 — «бесплатное» улучшение для пользователей на плохой сети, и в Traefik оно включается двумя строками: `http3: {}` и порт `443/udp`. Но у него есть цена: **UDP чаще режут межсетевые экраны**, а у некоторых хостингов он по умолчанию закрыт — поэтому браузеры всегда умеют вернуться на HTTP/2, и сайт не ломается, если HTTP/3 недоступен.

### deep Команды по частям
`http3: {}` — включить HTTP/3 на входе (по умолчанию порт совпадает с TCP-портом входа; другой — `advertisedPort`). `"443:443/udp"` — публикация UDP-порта. `curl -I` — только заголовки. `--http3-only` — использовать только HTTP/3 (без возврата к HTTP/2). `--network host` — контейнер использует сеть хозяина (на Linux), поэтому видит опубликованные порты как `127.0.0.1`.

### deep Как ещё можно
- **Системный `curl` с HTTP/3:** собрать `curl` с поддержкой QUIC или поставить `brew install curl` (в некоторых сборках HTTP/3 включён); проверка — `curl -V | grep HTTP3`.
- **Браузеры:** Chrome и Firefox включили HTTP/3 по умолчанию; в Chrome страница `chrome://net-export` покажет подробности.
- **Файрвол:** в облаке откройте не только TCP/443, но и UDP/443.

### deep Если не получилось
- **Нет заголовка `Alt-Svc`** — `http3` не включён на входе `websecure` или Traefik не перезапущен после правки статического файла.
- **Контейнер с QUIC не достучался** — UDP/443 не опубликован или занят; на Mac Docker Desktop `--network host` ведёт себя иначе (контейнер видит сеть виртуальной машины Docker, а не твоего Mac): для проверки на Mac достаточно браузера.
- **Образ `alpine/curl-http3` недоступен** — возьми любой другой образ `curl` с HTTP/3 (для проверки нужен лишь клиент QUIC).

### quiz
- Чем HTTP/3 отличается от HTTP/2 по транспорту?
- Зачем сервер присылает заголовок `Alt-Svc` и что произойдёт, если UDP закрыт?
- Какие два изменения нужны в Traefik и Compose, чтобы включить HTTP/3?

### links
- https://doc.traefik.io/traefik/reference/install-configuration/entrypoints/#http3 | HTTP/3 у входа | Traefik: HTTP/3
- https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Connection_management_in_HTTP_1.x | эволюция HTTP | MDN: HTTP

## 8.6 Переезд на свой сервер: что менять | short: Переезд на сервер | est: ~45 мин
### intro
**Слова шага:** *боевой сервер*, *DNS-записи*, *открытые порты*, *`acme.json` на томе*, *почта для ACME*, *staging → боевой*.

:::tip Если совсем просто
Дома мы тренировались с учебными паспортами. Для настоящего сайта нужно: настоящий адрес, открытые двери в интернет, и чтобы паспортный стол смог дойти до сайта. Здесь — список того, что менять. (**Ничего на сервер из этой лабы мы не выкладываем** — это чтение и подготовка.)
:::

Чтобы настоящий Let’s Encrypt выдал сертификат, должны сойтись четыре условия:

1. **Домен, который ты контролируешь**, и **DNS-запись** (`A`/`AAAA`) для нужных имён, указывающая на IP сервера.
2. **Порты 80 и 443 (TCP)** сервера доступны из интернета (и UDP/443 — для HTTP/3). Файрвол провайдера, `ufw`/`iptables` и облачные «группы безопасности» должны их пропускать.
3. **Traefik запущен на этом сервере** с резолвером, у которого правильный `email` и `caServer`.
4. **`acme.json` лежит на постоянном томе** (чтобы не терять аккаунт и сертификаты при пересоздании контейнера).

Что меняется по сравнению с нашим стендом:

| Было (локально) | Стало (сервер) |
|---|---|
| имена `*.localhost`, mkcert | настоящие имена `shop.example.com` |
| `caServer` = Pebble | **сначала staging**, потом боевой (поле просто убирают: по умолчанию боевой) |
| порты `80:80`, `443:443` на Mac | те же, но открыты наружу |
| `admin@example.test` | настоящая почта (туда приходят предупреждения об истечении) |
| пароль в `.env` | секреты вне git (шаг 8.4) |
| `watch: true` на смонтированных файлах | то же; дополнительно — резервная копия `acme.json` |

Подготовим **боевой вариант настройки** и проверим только его синтаксис (на сервер ничего не отправляем):

```bash run
mkdir -p ~/traefik-lab/server/letsencrypt && cd ~/traefik-lab/server
cat > traefik.yml <<'EOF'
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"
    http3: {}
    http:
      tls:
        certResolver: le            # сертификаты для всех роутеров на этом входе — автоматически

providers:
  docker:
    exposedByDefault: false

certificatesResolvers:
  le:
    acme:
      email: admin@example.com      # настоящая почта
      storage: /letsencrypt/acme.json
      # сначала оставь staging, убедись, что всё работает, потом удали строку caServer
      caServer: https://acme-staging-v02.api.letsencrypt.org/directory
      httpChallenge:
        entryPoint: web

log:
  level: INFO
  noColor: true
EOF
cat > compose.yaml <<'EOF'
name: edge-server

services:
  traefik:
    image: traefik:v3.7
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./traefik.yml:/etc/traefik/traefik.yml:ro
      - ./letsencrypt:/letsencrypt          # постоянный том: acme.json переживёт пересоздание
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks: [proxy]

networks:
  proxy:
    name: proxy
EOF
touch letsencrypt/acme.json && chmod 600 letsencrypt/acme.json
docker compose config -q && echo "compose.yaml боевого варианта корректен"
ls -l letsencrypt/acme.json | awk '{print $1, $NF}'
```

### result
```out auto
```

Файл настроек собирается без ошибок (мы проверили **синтаксис**, но на сервер это не выкладывалось и настоящий Let’s Encrypt не запрашивался). Обрати внимание на три детали боевого варианта:

- **`entryPoints.websecure.http.tls.certResolver: le`** — резолвер по умолчанию для входа: роутерам достаточно `tls=true`, имя берётся из `Host()` автоматически.
- **`caServer` — staging.** Первый заказ всегда делают на staging; когда всё получилось (сертификат выдан, но браузер ему не доверяет — это нормально), строку `caServer` убирают, **удаляют `acme.json`** (там сертификаты staging) и перезапускают Traefik: он закажет настоящие.
- **Права `600` на `acme.json`** заданы заранее.

**Контрольный список перед включением боевого режима:**

1. DNS-записи созданы, `dig +short shop.example.com` возвращает IP сервера.
2. Порты 80 и 443 открыты (`curl -I http://shop.example.com` с другого компьютера отвечает).
3. На staging сертификат выдан без ошибок (журнал Traefik).
4. `acme.json` лежит на томе и входит в резервную копию.
5. Почта для напоминаний настоящая.

### why
Переезд на сервер — это не «поменять пару строк», а проверка предпосылок: имя → адрес → открытый порт → проверка → постоянное хранилище. Если какой-то пункт не выполнен, шаг 8.7 покажет, как это выглядит в журнале.

### deep Команды по частям
`docker compose config -q` — проверить файл (тихо, без вывода при успехе). `touch … && chmod 600` — создать пустой файл и сразу выдать права только владельцу. `entryPoints.websecure.http.tls.certResolver` — резолвер по умолчанию для всех роутеров входа.

### deep Как ещё можно
- **Файрвол:** на сервере с `ufw` — `ufw allow 80/tcp`, `443/tcp`, `443/udp`; в облаке — те же правила в «группе безопасности».
- **DNS-01 вместо HTTP-01**, если сервер не доступен из интернета на 80/443 (шаг 8.3).
- **Несколько серверов Traefik:** общий `acme.json` нельзя — нужен общий кластерный стор (Consul/etcd) или Traefik Enterprise.

### deep Если не получилось
- **`docker compose config` не проходит** — смотри строку с ошибкой: чаще всего неверные отступы YAML.
- **`ls` не показывает `-rw-------`** — права не выставились; повтори `chmod 600 letsencrypt/acme.json`.

### quiz
- Какие четыре условия нужны, чтобы Let’s Encrypt выдал сертификат?
- Почему первый заказ делают на staging и что делать при переходе на боевой сервер?
- Чем `certResolver` у входа удобнее метки на каждом роутере?

### links
- https://letsencrypt.org/docs/staging-environment/ | staging-окружение | Let’s Encrypt: staging
- https://doc.traefik.io/traefik/reference/install-configuration/entrypoints/#tls | TLS на входе | Traefik: entryPoint TLS

## 8.7 🔨 acme.json с неверными правами и сорванная проверка | short: 🔨 acme.json и сорванный заказ | est: ~60 мин
### intro
**Слова шага:** *`permissions … are too open`*, *`acme.json`*, *проверка не прошла*, *`Timeout during connect`*, *DNS указывает не туда*, *лимиты*.

:::tip Если совсем просто
Две самые частые беды с автоматическими сертификатами. **Первая:** файл с ключами лежит «на виду» у всех, и Traefik отказывается с ним работать. **Вторая:** паспортный стол пошёл проверять сайт, а нашёл пустое место, потому что имя указывает не на твой сервер. Мы воспроизведём обе и научимся читать журнал.
:::

**Беда 1: права на `acme.json`.** В файле закрытые ключи, поэтому Traefik проверяет, что читать его может только владелец (`600`). Сделаем файл «слишком открытым» и перезапустим Traefik в учебном стенде:

```bash run
cd ~/traefik-lab/acme
chmod 644 letsencrypt/acme.json
docker compose restart traefik 2>&1 | tail -1
sleep 5
docker compose logs --no-log-prefix traefik 2>&1 | grep -iE 'too open|permissions' | cut -c1-200 | tail -2
```

### result
```out auto
```

В журнале строка вида `permissions 644 for /letsencrypt/acme.json are too open, please use 600` — Traefik **не будет использовать** этот файл (и не сможет заказывать и обновлять сертификаты). Лечение — одна команда:

```bash run
cd ~/traefik-lab/acme
chmod 600 letsencrypt/acme.json
docker compose restart traefik 2>&1 | tail -1
sleep 5
docker compose logs --no-log-prefix --since 4s traefik 2>&1 | grep -ciE 'too open' | sed 's/^/строк «too open» в журнале после перезапуска: /'
```

```out auto
```

(Счётчик — только строки после перезапуска: их нет, сертификаты снова работают. На Mac Docker Desktop права на смонтированные файлы показываются иначе, и такой ошибки там может не быть: на сервере с Linux она встречается постоянно.)

**Беда 2: проверка не проходит.** Опыт делаем на имени из **другого** домена (`bad.broken.test`): имена из `example.test` уже покрыты wildcard-сертификатом из шага 8.3, и Traefik просто не стал бы ничего заказывать. Заставим Pebble искать сайт `bad.broken.test` по **неверному** адресу — как если бы DNS указывал не на твой сервер (`10.30.50.99` — адрес, по которому никто не отвечает):

```bash run
cd ~/traefik-lab/acme
curl -s -X POST -d '{"host":"bad.broken.test.","addresses":["10.30.50.99"]}' http://localhost:8055/add-a
cat > compose.bad.yaml <<'EOF'
services:
  bad:
    image: traefik/whoami
    networks: [acme]
    labels:
      - acme-lab=true
      - traefik.http.routers.bad.rule=Host(`bad.broken.test`)
      - traefik.http.routers.bad.entrypoints=websecure
      - traefik.http.routers.bad.tls.certresolver=le
EOF
docker compose -f compose.yaml -f compose.bad.yaml up -d 2>&1 | tail -1
echo "--- ждём ошибку заказа (до 2 минут):"
for i in $(seq 1 40); do
  docker compose logs --no-log-prefix traefik 2>&1 | grep -q 'Unable to obtain ACME certificate' && break
  sleep 3
done
echo "--- журнал Traefik про неудачный заказ:"
docker compose logs --no-log-prefix traefik 2>&1 | grep 'Unable to obtain ACME certificate' | grep -oE 'domains=\[[^]]*\]|urn:ietf:params:acme:error:[a-z]+|dial tcp [^"\\]*' | sort -u
echo "--- журнал Pebble: что он увидел:"
docker compose logs --no-log-prefix pebble 2>&1 | grep -iE 'bad.broken.test' | sed -E 's/^Pebble [0-9\/]+ [0-9:]+ //' | cut -c1-110 | tail -1
```

```out auto
```

В журнале Traefik — ошибка заказа `Unable to obtain ACME certificate for domains [bad.broken.test]`, а в её хвосте — **причина от центра**: `urn:ietf:params:acme:error:connection` и `dial tcp 10.30.50.99:80: connect: no route to host` — Pebble пошёл проверять сайт по адресу `10.30.50.99`, где никого нет. (На настоящем Let’s Encrypt то же самое выглядит как `Timeout during connect (likely firewall problem)`.) Вот причина: имя указывает не на наш Traefik.

**Алгоритм поиска причины сорванного заказа:**

1. **Что сказал центр?** Читай конец сообщения в журнале Traefik: `Timeout during connect`/`Connection refused` — до сервера не дошли; `Invalid response`/`404` — дошли, но ответил не тот; `NXDOMAIN` — имени нет в DNS.
2. **Куда указывает имя?** `dig +short имя` (в нашем учебном DNS — журнал Pebble): должен быть IP **этого** сервера.
3. **Доступен ли порт** (80 для HTTP-01, 443 для TLS-ALPN-01) **снаружи**? Файрвол, облачные группы безопасности, домашний роутер.
4. **Нет ли редиректа/правила перед проверкой?** Путь `/.well-known/acme-challenge/` должен доходить до Traefik.

Теперь **починим**: вернём имени правильный адрес (учебный DNS снова отвечает адресом Traefik) и перезапустим Traefik, чтобы он повторил заказ:

```bash run
cd ~/traefik-lab/acme
curl -s -X POST -d '{"host":"bad.broken.test."}' http://localhost:8055/clear-a
docker compose restart traefik 2>&1 | tail -1
for i in $(seq 1 20); do
  [ "$(jq -r '[.le.Certificates[] | select(.domain.main == "bad.broken.test")] | length' letsencrypt/acme.json)" = 1 ] && break
  sleep 3
done
echo "сертификатов на bad.broken.test в acme.json: $(jq -r '[.le.Certificates[] | select(.domain.main == "bad.broken.test")] | length' letsencrypt/acme.json)"
curl -s --cacert pebble/pebble-root.pem -o /dev/null -w 'bad.broken.test -> HTTP %{http_code}\n' https://bad.broken.test:8443/
```

```out auto
```

Сертификат получен и сайт отвечает по HTTPS. **Про лимиты:** с настоящим Let’s Encrypt каждая неудачная проверка засчитывается в лимит («5 неудач в час на имя»). Поэтому, увидев ошибку, **не перезапускай Traefik подряд десять раз**: найди причину, исправь, затем повторяй. А отлаживай всегда на staging.

### why
Две ошибки закрывают 90% проблем с ACME: **права на файл** и **недоступность проверки**. Обе видны в журнале Traefik одной строкой — стоит только открыть его. Привычка читать журнал «до конца строки» (причину пишет центр в её хвосте) экономит часы.

### deep Команды по частям
`curl -X POST -d '{…}' http://localhost:8055/add-a` — «учебный DNS» (`challtestsrv`) принимает команды по HTTP: `add-a` — привязать имя к адресу, `clear-a` — вернуть ответ по умолчанию. `docker compose -f compose.yaml -f compose.bad.yaml up -d` — два файла вместе. `grep -iE 'too open|permissions'` — поиск строк журнала без учёта регистра. `wc -l | tr -d ' '` — посчитать строки и убрать пробелы.

### deep Как ещё можно
- **Проверить имя до заказа:** `dig +short shop.example.com` и `curl -I http://shop.example.com/.well-known/acme-challenge/test` (должен прийти ответ Traefik, пусть даже `404`).
- **Принудительно повторить заказ:** удалить запись о сертификате из `acme.json` (или сам файл вместе с аккаунтом при переходе со staging) и перезапустить Traefik.
- **Логи ACME подробнее:** `log.level: DEBUG` покажет все шаги протокола.

### deep Если не получилось
- **Строки `too open` нет** — у тебя Mac Docker Desktop или другая файловая система: права файла внутри контейнера не поменялись; смысл шага — знать эту ошибку и её лечение.
- **Сертификат для `bad.example.test` не выдан** — подожди ещё 20–30 секунд и повтори; убедись, что `clear-a` выполнился и что `challtestsrv` отвечает на `localhost:8055`.
- **`Connection refused` на `localhost:8055`** — не опубликован порт `8055:8055` у `challtestsrv` (шаг 8.2).

### quiz
- Почему Traefik отказывается работать с `acme.json` с правами `644`?
- Какие четыре вопроса задаёшь по порядку, когда заказ сертификата сорвался?
- Почему при ошибках нельзя бесконечно перезапускать Traefik на боевом Let’s Encrypt?

### links
- https://doc.traefik.io/traefik/reference/install-configuration/tls/certificate-resolvers/acme/ | ACME в Traefik | Traefik: ACME
- https://letsencrypt.org/docs/challenge-types/ | типы проверок | Let’s Encrypt: challenge types
