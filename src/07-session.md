# Сессия 7 · TLS, часть 1: локальные сертификаты
dur: ~4 ч

## 7.1 Как работает TLS: рукопожатие, сертификат, цепочка доверия | short: Как работает TLS | est: ~45 мин
### intro
**Слова шага:** *TLS*, *HTTPS*, *сертификат*, *открытый и закрытый ключ*, *удостоверяющий центр (CA)*, *цепочка доверия*, *SNI*, *рукопожатие*.

:::tip Если совсем просто
Ты приходишь в банк. Как понять, что это настоящий банк, а не декорация? Сотрудник показывает **лицензию**, выданную **Центробанком**, которому ты доверяешь. Лицензия — это сертификат, Центробанк — удостоверяющий центр. Потом вы договариваетесь о **секретном языке** на время разговора (шифровании). HTTPS — это обычный HTTP, который ведут на таком секретном языке.
:::

```svg
@tls-handshake
```

**TLS** (*Transport Layer Security*) — протокол, который шифрует соединение и проверяет, что ты говоришь с тем, с кем думаешь. **HTTPS** — это HTTP поверх TLS. Что нужно знать:

- **Ключевая пара.** Сервер владеет двумя связанными ключами: **закрытым** (никому не показывает) и **открытым** (раздаёт всем). То, что зашифровано открытым, расшифровывается только закрытым.
- **Сертификат** — файл-«паспорт», в котором написано: «этот открытый ключ принадлежит сайту `shop.localhost`, действителен с … по …», и стоит **подпись** того, кто его выдал.
- **Удостоверяющий центр (CA)** — организация, чьей подписи доверяют. Список доверенных CA встроен в твою систему и браузер.
- **Цепочка доверия:** сертификат сайта подписан промежуточным CA, тот — корневым; корневой уже есть в твоей системе. Если цепочка доходит до знакомого корня, сертификату верят.
- **SNI** (*Server Name Indication*) — клиент в начале рукопожатия сообщает, **какое имя** он ищет (`shop.localhost`), чтобы сервер с сотней сайтов выбрал нужный сертификат. Поэтому Traefik может держать много сертификатов на одном порту 443.

**Рукопожатие** (упрощённо, TLS 1.3): клиент здоровается и называет имя (SNI) → сервер присылает сертификат → клиент проверяет подпись и цепочку → стороны вырабатывают общий **сеансовый ключ** → дальше всё шифруется им (он быстрый). Посмотрим цепочку настоящего сайта и поймём, чьей подписью заверен его сертификат:

```bash run
echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null | openssl x509 -noout -subject -issuer -dates
```

### result
```out auto
```

Четыре строки: **`subject`** — для кого выдан сертификат, **`issuer`** — кто его выдал (удостоверяющий центр), **`notBefore` / `notAfter`** — срок действия. Срок короткий: современные сертификаты живут от нескольких месяцев до года, чтобы утечка ключа была недолгой бедой. Браузер в этот момент проверяет: имя совпадает с `subject` (или с альтернативными именами), срок не истёк, подпись цепочки ведёт к знакомому корню.

### why
Почти все «таинственные» ошибки TLS — это нарушение одной из трёх проверок: **имя** (сертификат выдан для другого имени), **срок** (истёк), **доверие** (цепочка ведёт к неизвестному CA). Зная это, ты читаешь сообщение `certificate verify failed` как список подозреваемых, а не как загадку (шаг 7.7).

### deep Команды по частям
`openssl s_client -connect example.com:443 -servername example.com` — открыть TLS-соединение и вывести сведения (`-servername` — SNI). `echo |` — подать пустой ввод, чтобы соединение закрылось само. `2>/dev/null` — скрыть служебные сообщения. `openssl x509 -noout -subject -issuer -dates` — прочитать присланный сертификат и показать только перечисленные поля.

### deep Как ещё можно
- **В браузере:** значок замка → «Сертификат» → вкладка с цепочкой (на Mac — просмотр в связке ключей).
- **`curl -v`:** показывает версию TLS, шифр и данные сертификата (шаг 1.1).
- **Онлайн-проверка:** сервис SSL Labs проверяет настройку TLS публичного сайта.

### deep Если не получилось
- **Ничего не напечаталось** — нет доступа в интернет или порт 443 закрыт; проверь `curl -I https://example.com`.
- **`openssl: command not found`** — на Mac есть `openssl` (или `LibreSSL`); если нет, поставь через `brew install openssl`.

### quiz
- Для чего нужны закрытый и открытый ключи и кто кому их показывает?
- Какие три проверки делает клиент с сертификатом сайта?
- Зачем клиент в начале рукопожатия сообщает имя (SNI)?

### links
- https://developer.mozilla.org/ru/docs/Web/Security/Transport_Layer_Security | TLS | MDN: TLS
- https://letsencrypt.org/ru/docs/ | Let’s Encrypt: документация | Let’s Encrypt: документация

## 7.2 mkcert: свой локальный CA | short: mkcert | est: ~45 мин
### intro
**Слова шага:** *mkcert*, *локальный CA*, *корневой сертификат*, *`CAROOT`*, *SAN*, *wildcard-сертификат*, *связка ключей*.

:::tip Если совсем просто
Настоящие сертификаты выдаёт «Центробанк». Для учёбы мы **открываем свой банк на кухне**: объявляем себя центром выдачи паспортов, говорим своему компьютеру «этому банку доверяй» — и дальше выдаём себе паспорта на любое имя. Так работает `mkcert`: наша «личная лицензия» действует только на нашем компьютере.
:::

```svg
@cert-chain
```

**mkcert** — маленькая утилита, которая:

1. создаёт **локальный CA** (корневой сертификат + ключ) и вносит корневой сертификат в системное хранилище доверия (на Mac — в связку ключей) и браузеры (`mkcert -install`);
2. по запросу выпускает **сертификаты для любых имён** (`mkcert shop.localhost`), подписанные этим CA.

Браузеры и `curl` доверяют таким сертификатам без предупреждений — на **твоём** компьютере. На чужом они недействительны, и это правильно: **корневой ключ mkcert никому не передавай** (кто его получит, сможет подделывать сертификаты для твоего компьютера). Установка на Mac: `brew install mkcert` (а для Firefox ещё `brew install nss`). Затем создаём CA и сертификат для наших имён:

```bash run
mkdir -p ~/traefik-lab/edge/certs && cd ~/traefik-lab/edge/certs
mkcert -install 2>&1 | grep -v '^$' | head -3
echo "--- где лежит корневой CA:"
ls "$(mkcert -CAROOT)"
echo "--- выпускаем сертификат на наши имена:"
mkcert -cert-file shop.pem -key-file shop-key.pem shop.localhost '*.shop.localhost' whoami.localhost localhost 2>&1 | grep -E 'Created|expires' | sed -E 's/^The certificate at "([^"]+)".*/сертификат: \1/'
ls
echo "--- что внутри:"
openssl x509 -in shop.pem -noout -issuer -dates -ext subjectAltName | sed 's/^ *//'
```

### result
```out auto
```

`mkcert -install` создал локальный CA и добавил его в хранилище доверия (на Mac появится запрос пароля администратора — это нормально). В папке `rootCA.pem` — корневой сертификат (публичный), `rootCA-key.pem` — его **секретный ключ**. Выпущенный сертификат `shop.pem` и ключ `shop-key.pem` лежат в `~/traefik-lab/edge/certs`.

Внутри сертификата: **`issuer`** — наш локальный CA (`mkcert …`), **срок** — около двух лет и трёх месяцев (так устроен `mkcert`), а в **`Subject Alternative Name`** (SAN, «альтернативные имена») — все наши имена: `shop.localhost`, **`*.shop.localhost`** (любое имя вида `что-то.shop.localhost`), `whoami.localhost`, `localhost`. Современные браузеры смотрят именно SAN, а не поле `subject`. Звёздочка — **wildcard**: она покрывает **один уровень** поддомена, поэтому `a.b.shop.localhost` не подойдёт.

### why
Теперь у нас есть свой «маленький Let’s Encrypt» для разработки. Он нужен потому, что **HTTPS нельзя «отложить на потом»**: у многих браузерных возможностей (камера, `Service Worker`, часть cookie) есть требование безопасного контекста, а ошибки TLS проще ловить на локальной машине, чем на сервере.

### deep Команды по частям
`mkcert -install` — создать CA (если ещё нет) и установить его как доверенный. `mkcert -CAROOT` — путь к папке с корневым CA. `mkcert -cert-file shop.pem -key-file shop-key.pem имя1 имя2 …` — выпустить сертификат на перечисленные имена и записать в выбранные файлы. `openssl x509 -in … -noout -issuer -dates -ext subjectAltName` — показать издателя, срок и список имён.

### deep Как ещё можно
- **`openssl` вручную:** тот же результат — `openssl req` и `openssl x509`, но длиннее (в шаге 7.6 мы так сделаем CA для клиентов).
- **Хранить CA в другом месте:** переменная `CAROOT=/путь mkcert …`.
- **Убрать за собой:** `mkcert -uninstall` удаляет доверие к локальному CA; папку `CAROOT` можно удалить вместе с ключом.

### deep Если не получилось
- **`mkcert: command not found`** — установи: `brew install mkcert`.
- **В браузере всё равно предупреждение** — браузер не подхватил корень: перезапусти его; в Firefox нужен `nss` (`brew install nss`, затем снова `mkcert -install`).
- **Пароль администратора не принимает** — `mkcert -install` меняет системные настройки доверия; выполни от пользователя с правами администратора.

### quiz
- Что делает `mkcert -install` и почему корневой ключ нельзя никому отдавать?
- Что такое SAN и зачем он браузеру?
- Что покрывает wildcard `*.shop.localhost`, а что нет?

### links
- https://github.com/FiloSottile/mkcert | mkcert | GitHub: mkcert
- https://doc.traefik.io/traefik/https/tls/ | TLS в Traefik | Traefik: TLS

## 7.3 Подключаем сертификат: websecure, tls=true | short: Подключаем сертификат | est: ~50 мин
### intro
**Слова шага:** *entryPoint `websecure`*, *`tls=true`*, *`tls.certificates`*, *`certFile` / `keyFile`*, *терминирование TLS*, *порт 443*.

:::tip Если совсем просто
Мы уже настроили «охранника у входа» (Traefik). Теперь ему нужна **вторая дверь для шифрованных посетителей** (порт 443) и **паспорт для этой двери** (наш сертификат). И каждому маршруту надо сказать: «для тебя — шифрованная дверь».
:::

Что нужно добавить, по порядку:

1. **Вход `websecure`** на `:443` — в `traefik.yml` (статическая конфигурация).
2. **Папка с сертификатами** в Traefik и **файл `tls.yml`** в `dynamic/` — со списком «сертификат + ключ».
3. **Метки роутеров**: `entrypoints=websecure` и `tls=true` (без `tls=true` роутер на входе 443 отвечал бы открытым текстом).
4. **Порт 443** в `ports` у Traefik.

Traefik **терминирует** TLS: расшифровывает запрос на входе, а внутри сети Docker к сервисам идёт обычным HTTP — сервисам ничего менять не нужно. Правим файлы Traefik и перезапускаем его (`traefik.yml` — статика, после правки нужен перезапуск):

```bash run
cd ~/traefik-lab/edge
cat > traefik/traefik.yml <<'EOF'
entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

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
cat > traefik/dynamic/tls.yml <<'EOF'
tls:
  certificates:
    - certFile: /certs/shop.pem
      keyFile: /certs/shop-key.pem
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
cd ~/traefik-lab/coffeeshop
cat > compose.s7.yaml <<'EOF'
services:
  web:
    labels:
      - traefik.http.routers.coffee-web.entrypoints=websecure
      - traefik.http.routers.coffee-web.tls=true
  api:
    labels:
      - traefik.http.routers.coffee-api.entrypoints=websecure
      - traefik.http.routers.coffee-api.tls=true
      - traefik.http.routers.coffee-api-post.entrypoints=websecure
      - traefik.http.routers.coffee-api-post.tls=true
  adminer:
    labels:
      - traefik.http.routers.coffee-adminer.entrypoints=websecure
      - traefik.http.routers.coffee-adminer.tls=true
EOF
sed 's|^COMPOSE_FILE=.*|&:compose.s7.yaml|' .env > .env.new && mv .env.new .env
docker compose up -d 2>&1 | tail -3
sleep 6
echo "--- HTTPS на сайт (без -k: системе доверяем благодаря mkcert -install):"
curl -s -o /dev/null -w 'https://shop.localhost/          -> HTTP %{http_code}\n' https://shop.localhost/
curl -s -o /dev/null -w 'https://shop.localhost/api/menu  -> HTTP %{http_code}\n' https://shop.localhost/api/menu
echo "--- параметры TLS-соединения:"
curl -sv https://shop.localhost/ -o /dev/null 2>&1 | grep -E 'SSL connection using|subject:|issuer:|using HTTP/'
echo "--- а по HTTP (порт 80)?"
curl -s -o /dev/null -w 'http://shop.localhost/           -> HTTP %{http_code}\n' http://shop.localhost/
```

### result
```out auto
```

HTTPS работает **без предупреждений**: `curl` сам проверил цепочку (`issuer` — наш локальный CA, доверенный в системе). Открой в браузере **https://shop.localhost** — рядом с адресом замок, меню загружается, заказ делается. Строка `SSL connection using TLSv1.3 / …` показывает версию протокола и шифр (`X25519MLKEM768` в её составе — гибридный обмен ключами, устойчивый к будущим квантовым компьютерам; он есть в новых версиях `curl`/OpenSSL и у тебя может выглядеть иначе).

А вот по HTTP (порт 80) — **`404`**: на входе `web` больше нет ни одного роутера (мы перевели их все на `websecure`). Пользователь, набравший `http://…`, получит ошибку. Исправим это в следующем шаге редиректом.

### why
Все наши сервисы получили HTTPS **без единого изменения в самих приложениях**: сайт и API по-прежнему слушают порт 80/3000 по обычному HTTP внутри сети. Это главное практическое преимущество «терминирования» TLS на прокси: сертификатами занимается одно место.

### deep Команды по частям
`certificates: - certFile: … keyFile: …` — список пар «сертификат + ключ»; Traefik выбирает нужную по SNI. Папку `certs` монтируем в Traefik только на чтение. `routers.<имя>.tls=true` — роутер обслуживает TLS-соединения. `curl -sv … 2>&1 | grep -E '…'` — показать только строки про параметры TLS и версию HTTP.

### deep Как ещё можно
- **Без файла `tls.yml`:** сертификаты можно выдавать автоматически (Let’s Encrypt — следующая сессия) — тогда ручной список не нужен.
- **Сертификат по умолчанию:** если ни один сертификат не подходит под запрошенное имя, Traefik отдаёт встроенный самоподписанный `TRAEFIK DEFAULT CERT` (браузер покажет предупреждение). Свой сертификат по умолчанию задаётся `tls.stores.default.defaultCertificate`.
- **HTTP/2:** на 443 Traefik автоматически говорит по HTTP/2 (`HTTP/2 200` в выводе `curl -v`).

### deep Если не получилось
- **Предупреждение о сертификате в браузере** — не установлен локальный CA (`mkcert -install`) или сертификат выпущен не на это имя: имя должно быть в SAN (шаг 7.2).
- **`curl: (60) SSL certificate problem`** — `curl` не доверяет CA: это бывает у `curl` из Homebrew, у которого свой список CA; запусти с `--cacert "$(mkcert -CAROOT)/rootCA.pem"`.
- **`TRAEFIK DEFAULT CERT`** в сведениях о соединении — Traefik не загрузил твой сертификат: проверь пути в `tls.yml` (внутри контейнера это `/certs/…`) и журнал `docker compose logs traefik`.
- **Порт 443 занят** — другой проект использует его; смени левую цифру (`"8443:443"`) и добавь `:8443` в адреса.

### quiz
- Какие четыре изменения нужны, чтобы сервис заработал по HTTPS?
- Что значит «Traefik терминирует TLS» и что получает сервис?
- Что отдаёт Traefik, если ни один сертификат не подошёл под имя?

### links
- https://doc.traefik.io/traefik/https/tls/#user-defined | свои сертификаты | Traefik: user-defined certificates
- https://doc.traefik.io/traefik/routing/routers/#tls | TLS у роутера | Traefik: router TLS

## 7.4 Редирект HTTP → HTTPS на уровне входа | short: Редирект на HTTPS | est: ~35 мин
### intro
**Слова шага:** *редирект на уровне entryPoint*, *`301`*, *`HSTS`*, *`redirections.entryPoint`*, *`-L` у curl*.

:::tip Если совсем просто
Кто-то стучится в обычную дверь, а нужная — шифрованная. Вместо «такой двери нет» (404) мы ставим у обычной двери указатель: «вход — вон там». Один указатель на всё здание, а не на каждый кабинет.
:::

В шаге 4.3 мы делали редирект через `redirectScheme` на каждом роутере. Но проще и надёжнее — **один раз на уровне входа**: любой запрос, пришедший на порт 80, получает `301` на тот же адрес по `https`. Это статическая настройка `entryPoints.web.http.redirections`:

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
sleep 4
echo "--- http -> https:"
curl -s -o /dev/null -D - http://shop.localhost/api/menu | grep -iE '^(HTTP|location)'
echo "--- с -L curl сам идёт по адресу из Location:"
curl -sL -o /dev/null -w 'конечный адрес: %{url_effective}  HTTP %{http_code}\n' http://shop.localhost/api/menu
echo "--- а Adminer и дашборд (с паролем):"
curl -sL --location-trusted -o /dev/null -w '%{url_effective} -> HTTP %{http_code}\n' -u mira:coffee-secret http://adminer.shop.localhost/
```

### result
```out auto
```

Каждый запрос на HTTP получает **`301 Moved Permanently`** с `Location: https://…` и тем же путём. С флагом `-L` `curl` сам переходит на новый адрес и получает `200`. Браузер делает это автоматически.

Редирект на входе обходит все роутеры: даже если у нового сервиса забыли указать редирект, он всё равно не будет доступен по HTTP — вход на 80 принадлежит только редиректу. Поэтому **роутерам теперь достаточно `entrypoints=websecure`**; роутеров на `web` больше нет — это то, как делают в рабочих стендах.

**HSTS** (заголовок `Strict-Transport-Security`) — следующий уровень: он просит браузер **запомнить**, что с этим сайтом нужно всегда ходить по HTTPS, даже если пользователь набрал `http://`. Включается в middleware `headers` полями `stsSeconds` и `stsIncludeSubdomains`; действует только в ответах по HTTPS. Начинай с маленького срока (`stsSeconds=300`), потому что если потом понадобится вернуть HTTP, браузеры будут отказываться заходить.

### why
HTTP на порту 80 после этой настройки существует ровно для одной цели — перенаправить. Настроено один раз и работает для всех будущих сервисов — это пример того, как конфигурация «на входе» (static) экономит работу в конфигурации сервисов (dynamic).

### deep Команды по частям
`redirections.entryPoint.to: websecure` — на какой вход перенаправить; `scheme: https` — какой протокол поставить в адрес; `permanent: true` — `301` вместо временного `302`. `curl -sL … -w '%{url_effective}'` — `-L` идти по редиректам, `%{url_effective}` — адрес, на котором `curl` закончил. `--location-trusted` — отправлять логин и пароль и после редиректа (по умолчанию `curl` не передаёт их дальше, если сменились схема или порт).

### deep Как ещё можно
- **Старый способ (`redirectScheme`):** подходит, если нужно перенаправлять не всё, а только некоторые роутеры (шаг 4.3).
- **Редирект не со всех путей:** вход `web` оставляют без редиректа и ставят только отдельные роутеры с `redirectScheme` — например, чтобы не трогать путь проверки Let’s Encrypt `/.well-known/acme-challenge/` (Traefik сам обработает его до редиректа, шаг 8.2).
- **Нестандартный порт:** `to: websecure` берёт порт из входа `websecure`; при `8443:443` адрес в `Location` получит `:8443`.

### deep Если не получилось
- **`Connection refused` на порту 80** — Traefik не перезапущен после правки или порт 80 не опубликован (проверь `ports`).
- **Редирект есть, а на HTTPS `404`** — у роутера нет `entrypoints=websecure` и `tls=true`: см. шаг 7.3.
- **Цикл редиректов** — перед Traefik стоит ещё прокси, который отдаёт ему запросы по HTTP; тогда редирект должен делаться на внешнем прокси (шаг 9.4).

### quiz
- Чем редирект на уровне входа лучше `redirectScheme` на каждом роутере?
- Что делает флаг `-L` у `curl` и зачем он тут?
- Для чего нужен HSTS и почему его включают осторожно?

### links
- https://doc.traefik.io/traefik/routing/entrypoints/#redirection | редирект на входе | Traefik: entryPoint redirection
- https://developer.mozilla.org/ru/docs/Web/HTTP/Headers/Strict-Transport-Security | HSTS | MDN: HSTS

## 7.5 TLS options: версия, шифры, SNI | short: TLS options | est: ~45 мин
### intro
**Слова шага:** *TLS options*, *`minVersion`*, *`cipherSuites`*, *`sniStrict`*, *`curl --tlsv1.2 --tls-max 1.2`*, *именованные опции*.

:::tip Если совсем просто
Дверь можно сделать «для любого желающего» (старые замки тоже подходят), а можно потребовать только современные замки. Чем строже — тем безопаснее, но самые старые клиенты не войдут. Эти правила называются **TLS options**.
:::

**TLS options** — набор требований к соединению. Описываются в динамической конфигурации (файл) и подключаются к роутеру меткой `tls.options=имя@file`. Важная особенность: **параметры TLS выбираются на этапе рукопожатия, когда клиент ещё не прислал путь запроса — известно только имя (SNI)**. Поэтому опции привязаны к **имени**, а не к роутеру целиком: если на одно и то же имя смотрят два роутера с разными опциями (например, отличающиеся только путём), Traefik не сможет выбрать и применит `default`. Основные поля:

| Поле | Что делает |
|---|---|
| `minVersion` | минимальная версия протокола (`VersionTLS12`, `VersionTLS13`) |
| `cipherSuites` | допустимые наборы шифров (для TLS 1.2; в 1.3 набор фиксирован) |
| `sniStrict` | отвергать соединения с **неизвестным именем** (без запасного сертификата) |
| `clientAuth` | требовать клиентский сертификат (mTLS — шаг 7.6) |

Опции с именем `default` применяются ко **всем** роутерам, остальные — по меткам. Сделаем опцию `modern` — только TLS 1.3 — и сравним, как её видит клиент, который «умеет» только 1.2. Для этого понадобятся два **разных имени**: `new.shop.localhost` (с опцией `modern`) и `old.shop.localhost` (с опциями по умолчанию):

```bash run
cd ~/traefik-lab/edge
cat > traefik/dynamic/tls-options.yml <<'EOF'
tls:
  options:
    modern:
      minVersion: VersionTLS13
    strict-sni:
      minVersion: VersionTLS12
      sniStrict: true
EOF
cat > compose.s75.yaml <<'EOF'
name: s75

services:
  lab:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.s75-modern.rule=Host(`new.shop.localhost`)
      - traefik.http.routers.s75-modern.entrypoints=websecure
      - traefik.http.routers.s75-modern.tls=true
      - traefik.http.routers.s75-modern.tls.options=modern@file
      - traefik.http.routers.s75-old.rule=Host(`old.shop.localhost`)
      - traefik.http.routers.s75-old.entrypoints=websecure
      - traefik.http.routers.s75-old.tls=true
      - traefik.http.services.s75.loadbalancer.server.port=80
      - traefik.http.routers.s75-modern.service=s75
      - traefik.http.routers.s75-old.service=s75

networks:
  proxy:
    external: true
EOF
docker compose -f compose.s75.yaml up -d 2>&1 | tail -1
sleep 4
t() { printf '%-34s -> ' "$1"; shift; curl -s -o /dev/null -w 'HTTP %{http_code}\n' "$@" 2>&1 || true; }
echo "--- версия протокола, которую выбирает curl:"
curl -sv https://new.shop.localhost/ -o /dev/null 2>&1 | grep -m1 'SSL connection using'
echo "--- клиент «только TLS 1.2» против роутера с minVersion=1.3 и против обычного:"
t "new (TLS 1.3 only), клиент 1.2" --tlsv1.2 --tls-max 1.2 https://new.shop.localhost/
t "old (по умолчанию), клиент 1.2" --tlsv1.2 --tls-max 1.2 https://old.shop.localhost/
t "new, обычный клиент"            https://new.shop.localhost/
```

### result
```out auto
```

Современный `curl` договаривается о **TLS 1.3**. Клиент, ограниченный версией 1.2 (`--tls-max 1.2`), к роутеру с `minVersion: VersionTLS13` **не может подключиться** (`HTTP 000` — рукопожатие не состоялось), а к обычному роутеру подключается (`200`). Именно так «выключают» старые протоколы: TLS 1.0 и 1.1 уже небезопасны, а TLS 1.2 пока допустим.

**Что про `sniStrict`.** Если клиент просит имя, под которое у Traefik нет сертификата, по умолчанию он отдаёт «запасной» самоподписанный сертификат (`TRAEFIK DEFAULT CERT`). С `sniStrict: true` такое соединение **обрывается**: клиент вообще не получит ответа. Проверим на имени `other.localhost`, которого нет в нашем сертификате (подключение без проверки подлинности — `-k`, чтобы увидеть разницу в поведении):

```bash run
cd ~/traefik-lab/edge
echo "--- без sniStrict (опция default), имя без сертификата:"
curl -sk -o /dev/null -w 'HTTP %{http_code}  (отдан запасной сертификат)\n' https://other.localhost/
cat > traefik/dynamic/tls-options.yml <<'EOF'
tls:
  options:
    modern:
      minVersion: VersionTLS13
    default:
      minVersion: VersionTLS12
      sniStrict: true
EOF
sleep 3
echo "--- с sniStrict (default):"
curl -sk -o /dev/null -w 'HTTP %{http_code}\n' https://other.localhost/ || true
curl -s -o /dev/null -w 'своё имя shop.localhost: HTTP %{http_code}\n' https://shop.localhost/
```

```out auto
```

Без `sniStrict` Traefik отвечает даже на «чужое» имя (запасным сертификатом, и `404`, потому что роутера нет), с `sniStrict` — `HTTP 000`: рукопожатие обрывается, клиент ничего не получил. Свои имена продолжают работать. Опция `default` применяется ко **всем** роутерам, которые не выбрали другую; так что одна запись теперь подняла минимум до TLS 1.2 на всём стенде и включила строгий SNI.

### why
TLS options — «политика безопасности» входа в одном месте. Здесь важно не «зажать всё максимально», а понимать цену: слишком строгие настройки ломают старых клиентов (устаревшие приложения, встроенные устройства). Стандартная разумная настройка — `minVersion: VersionTLS12` (или 1.3, если клиенты современные) и оставить шифры по умолчанию: набор Traefik и Go уже безопасен.

### deep Команды по частям
`routers.<имя>.tls.options=modern@file` — подключить именованную опцию из файла (суффикс `@file` обязателен). `--tlsv1.2 --tls-max 1.2` — разрешить `curl` только TLS 1.2. `curl -k` — не проверять сертификат (**только для опытов**). `|| true` в конце — чтобы ошибка `curl` не останавливала остальные команды блока.

### deep Как ещё можно
- **`cipherSuites`:** список допустимых шифров TLS 1.2 (например, `TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256`); для TLS 1.3 набор фиксирован и не настраивается.
- **`curvePreferences`**, **`alpnProtocols`** — тонкая настройка кривых и протоколов (HTTP/2).
- **Проверка «снаружи»:** `nmap --script ssl-enum-ciphers -p 443 host` или онлайн-сервис SSL Labs.

### deep Если не получилось
- **Клиент 1.2 всё равно подключился к `modern`** — опция не подключена или на то же имя смотрит второй роутер без опции (тогда применяется `default`): проверь метку `tls.options=modern@file`, имя в `tls-options.yml` и что имена роутеров разные.
- **Все запросы стали `000`** — опция `default` с `sniStrict` отвергла имя, которого нет в сертификате (например, ты обратилась по IP): используй имена из SAN.
- **Файл не подхвачен** — подожди несколько секунд (Docker Desktop на Mac) или перезапусти Traefik.

### quiz
- Что делает `minVersion: VersionTLS13` и какие клиенты она отсекает?
- Что отдаёт Traefik на неизвестное имя без `sniStrict` и с ним?
- Чем именованная опция отличается от `default`?

### links
- https://doc.traefik.io/traefik/https/tls/#tls-options | TLS options | Traefik: TLS options
- https://wiki.mozilla.org/Security/Server_Side_TLS | рекомендации Mozilla по TLS | Mozilla: Server Side TLS

## 7.6 mTLS: клиентский сертификат | short: mTLS | est: ~55 мин
### intro
**Слова шага:** *mTLS (взаимный TLS)*, *клиентский сертификат*, *`clientAuth`*, *`RequireAndVerifyClientCert`*, *свой CA для клиентов*, *`curl --cert`*.

:::tip Если совсем просто
Обычный TLS — сервер показывает паспорт клиенту: «я настоящий банк». В **mTLS** паспорт показывают **обе стороны**: клиент тоже предъявляет сертификат, и сервер пускает только тех, у кого он есть. Ключ-карта вместо пароля.
:::

```svg
@mtls
```

При mTLS Traefik **требует у клиента сертификат** и проверяет, что тот подписан доверенным **CA клиентов**. Без сертификата рукопожатие не состоится — пароль даже не спросят. Так защищают внутренние API, админки, связь между сервисами. Нам понадобится **свой CA для клиентов** (отдельный от серверного!) и клиентский сертификат, подписанный им. Сделаем их с помощью `openssl`:

```bash run
cd ~/traefik-lab/edge/certs
openssl req -x509 -newkey rsa:2048 -nodes -days 365 -keyout clients-ca-key.pem -out clients-ca.pem -subj "/CN=Coffee Clients CA" 2>/dev/null
openssl req -newkey rsa:2048 -nodes -keyout client-key.pem -out client.csr -subj "/CN=mira" 2>/dev/null
openssl x509 -req -in client.csr -CA clients-ca.pem -CAkey clients-ca-key.pem -CAcreateserial -days 365 -out client.pem 2>/dev/null
rm -f client.csr clients-ca.srl
ls
echo "--- кто подписал клиентский сертификат и для кого он:"
openssl x509 -in client.pem -noout -subject -issuer | sed 's/^ *//'
```

### result
```out auto
```

Создано пять файлов: `clients-ca.pem` и `clients-ca-key.pem` — наш CA клиентов (ключ CA храним в секрете), `client.pem` и `client-key.pem` — сертификат и ключ клиента `mira`. Теперь опишем опцию TLS, которая **требует** такой сертификат, и защитим ею отдельный адрес `mtls.shop.localhost`:

```bash run
cd ~/traefik-lab/edge
docker compose -f compose.s75.yaml down 2>&1 | tail -1
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
EOF
cat > compose.s76.yaml <<'EOF'
name: s76

services:
  lab:
    image: traefik/whoami
    networks: [proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.s76.rule=Host(`mtls.shop.localhost`)
      - traefik.http.routers.s76.entrypoints=websecure
      - traefik.http.routers.s76.tls=true
      - traefik.http.routers.s76.tls.options=mtls@file

networks:
  proxy:
    external: true
EOF
docker compose -f compose.s76.yaml up -d 2>&1 | tail -1
sleep 4
echo "--- без клиентского сертификата:"
curl -s -o /dev/null -w 'HTTP %{http_code}\n' https://mtls.shop.localhost/ || true
echo "--- с клиентским сертификатом:"
curl -s --cert certs/client.pem --key certs/client-key.pem https://mtls.shop.localhost/ | grep -E '^(Hostname|GET|Host)'
echo "--- сайт без mTLS открывается как раньше:"
curl -s -o /dev/null -w 'https://shop.localhost/ -> HTTP %{http_code}\n' https://shop.localhost/
```

```out auto
```

Без сертификата — **`HTTP 000`**: Traefik оборвал рукопожатие, пустое место вместо ответа. С сертификатом — ответ `whoami`. Остальные сайты по-прежнему работают без клиентских сертификатов — требование действует **только на роутерах с этой опцией**.

**Что значит `clientAuthType`:**

| Значение | Поведение |
|---|---|
| `NoClientCert` | сертификат не запрашивается (по умолчанию) |
| `RequestClientCert` | запрашивается, но можно не присылать |
| `RequireAnyClientCert` | нужен, но не проверяется |
| `VerifyClientCertIfGiven` | если прислан — проверить |
| `RequireAndVerifyClientCert` | **нужен и должен быть подписан нашим CA** |

В работе почти всегда берут `RequireAndVerifyClientCert`.

### why
mTLS — самый сильный способ закрыть доступ: сертификат не подобрать перебором и не «подсмотреть» как пароль. Ценой является управление сертификатами (выдача, срок, отзыв). Поэтому его применяют там, где клиентов немного и они «свои»: админки, межсервисные вызовы, B2B-API.

### deep Команды по частям
`openssl req -x509 -newkey rsa:2048 -nodes -days 365 -keyout … -out … -subj "/CN=…"` — создать самоподписанный CA (`-x509`), с новым ключом без пароля (`-nodes`). `openssl req -newkey … -out client.csr` — запрос на сертификат (CSR) клиента. `openssl x509 -req -in … -CA … -CAkey … -out …` — подписать запрос нашим CA. `curl --cert … --key …` — предъявить клиентский сертификат и ключ.

### deep Как ещё можно
- **Один и тот же CA и для сервера, и для клиентов** — работает, но смешивать не рекомендуется: тогда любой клиентский сертификат можно использовать как серверный.
- **Отзыв сертификатов:** в Traefik нет списка отзыва; отзывают, меняя CA или сокращая срок жизни клиентских сертификатов.
- **Передача данных о сертификате в приложение:** middleware `passTLSClientCert` кладёт сертификат клиента в заголовок `X-Forwarded-Tls-Client-Cert-Info`.

### deep Если не получилось
- **С сертификатом всё равно `000`** — клиентский сертификат подписан не тем CA, который указан в `caFiles` (путь внутри контейнера — `/certs/clients-ca.pem`), или Traefik не перечитал файл опций.
- **`curl: (58) unable to set private key file`** — ключ не соответствует сертификату: пересоздай пару.
- **Браузер не показывает окно выбора сертификата** — сертификат нужно загрузить в связку ключей (формат `.p12`: `openssl pkcs12 -export -inkey client-key.pem -in client.pem -out client.p12`).

### quiz
- Чем mTLS отличается от обычного TLS и от `basicAuth`?
- Зачем отдельный CA для клиентов и что значит `RequireAndVerifyClientCert`?
- Что видит клиент без сертификата и почему не запрашивается пароль?

### links
- https://doc.traefik.io/traefik/https/tls/#client-authentication-mtls | mTLS | Traefik: client authentication
- https://www.cloudflare.com/learning/access-management/what-is-mutual-tls/ | что такое mTLS | Cloudflare: mTLS

## 7.7 🔨 certificate verify failed / unknown authority | short: 🔨 certificate verify failed | est: ~50 мин
### intro
**Слова шага:** *`certificate verify failed`*, *`unknown authority`*, *три причины: имя, срок, доверие*, *`--cacert`*, *`-k` (только для опытов)*.

:::tip Если совсем просто
Охранник проверил паспорт и отказал. Причин три: фото не твоё (**имя не то**), паспорт просрочен (**срок**), выдан неизвестной организацией (**не доверяем CA**). Сообщение об ошибке подсказывает, какая именно. Научимся читать.
:::

Ошибка TLS — самая частая у новичков. Воспроизведём две причины из трёх. Первая — **клиент не доверяет CA, который выдал сертификат**. Заставим `curl` проверять сертификат по «чужому» CA (нашему клиентскому из шага 7.6, а не по mkcert):

```bash run
cd ~/traefik-lab/edge
echo "--- 1) клиент не знает нужный CA:"
mkdir -p /tmp/empty-ca
curl -sS -o /dev/null --cacert certs/clients-ca.pem --capath /tmp/empty-ca https://shop.localhost/ ; echo "код выхода curl: $?"
echo "--- 2) имя, для которого у Traefik нет сертификата (отдаётся запасной TRAEFIK DEFAULT CERT):"
curl -sS -o /dev/null https://other.localhost/ 2>&1 | head -2
echo "--- убеждаемся, что дело в доверии, а не в соединении (-k отключает проверку: ТОЛЬКО для диагностики):"
curl -sk -o /dev/null -w 'с -k: HTTP %{http_code}\n' https://other.localhost/
```

### result
```out auto
```

Обе ошибки — **код `60`** (проблема сертификата), но причины разные:

1. **`unable to get local issuer certificate`** — `curl` не нашёл в своём списке доверенных CA того, кто подписал сертификат сайта (мы подсунули ему не тот файл `--cacert`). **Лечение:** добавить нужный CA в доверенные (`mkcert -install`, или `--cacert` с правильным файлом, или системное хранилище).
2. **`no alternative certificate subject name matches target hostname`** (для `other.localhost`) — Traefik отдал **запасной самоподписанный** сертификат (`TRAEFIK DEFAULT CERT`), потому что для этого имени своего нет, а в запасном этого имени нет. Это ошибка «имя не совпало» (в других версиях `curl` и в браузерах она выглядит как `self-signed certificate` или `NET::ERR_CERT_COMMON_NAME_INVALID`). **Лечение:** выпустить сертификат на это имя (добавить в SAN) и подключить его.

Флаг `-k` убирает проверку — ответ приходит (`404`: роутера для имени нет), но так делают **только для диагностики**: он отключает всю защиту. Если с `-k` работает, а без — проблема в доверии или имени, а не в сети.

**Третья причина — срок.** Сертификат истёк: ошибка `certificate has expired`. Проверка: `openssl x509 -in cert.pem -noout -dates`. Лечение — перевыпустить (в Let’s Encrypt это делается автоматически, шаг 8.2). В прогоне методички мы не воспроизводили эту ошибку (нужен сертификат с датой в прошлом), но диагностика та же.

**Памятка «что смотреть при `certificate verify failed`»:**

| Сообщение | Причина | Что делать |
|---|---|---|
| `unable to get local issuer certificate` / `unknown authority` | клиент не доверяет CA | установить CA (`mkcert -install`), `--cacert` |
| `self-signed certificate` | сервер отдал самоподписанный | свой сертификат на это имя; проверь SAN и `tls.certificates` |
| `certificate has expired` | срок вышел | перевыпустить; автоматическое обновление |
| `hostname mismatch` / `no alternative certificate subject name matches` | имя в адресе не в SAN | перевыпустить с нужным именем |

### why
Вместо «TLS не работает» теперь у тебя три вопроса: **имя**, **срок**, **доверие**. На них отвечает одна команда: `curl -v` покажет, **какой** сертификат пришёл и что в нём не так. Именно в такой последовательности и стоит искать причину.

### deep Команды по частям
`curl -sS` — тихий режим, но ошибка всё же печатается (`-S`). `--cacert файл` — доверенные CA из этого файла; `--capath папка` — доверенные CA из папки (по умолчанию системная); мы подставили **пустую**, чтобы `curl` не нашёл CA от `mkcert` в системе. `curl -k` — не проверять (опасно, только для отладки). `$?` — код выхода: `60` — проблема сертификата, `35` — не состоялось рукопожатие, `58` — ошибка клиентского ключа.

### deep Как ещё можно
- **Подробный разбор:** `openssl s_client -connect shop.localhost:443 -servername shop.localhost -showcerts` — показывает всю цепочку сертификатов, которую прислал сервер.
- **Проверить сам файл:** `openssl verify -CAfile rootCA.pem shop.pem` — подходит ли сертификат к CA.
- **Браузер:** на странице предупреждения «Подробнее» показывает причину тем же кодом (`NET::ERR_CERT_AUTHORITY_INVALID`, `…_COMMON_NAME_INVALID`, `…_DATE_INVALID`).

### deep Если не получилось
- **Первый пункт вернул `200`, а не ошибку** — твой `curl` использует системное хранилище независимо от `--cacert` (так ведёт себя `curl` с Secure Transport на Mac): ошибку можно увидеть в окне инкогнито браузера или у `curl` из Homebrew.
- **Для `other.localhost` вышло `Could not resolve host`** — твоя система не знает `*.localhost`: добавь `127.0.0.1 other.localhost` в `/etc/hosts`.
- **Нет файла `certs/clients-ca.pem`** — выполни шаг 7.6.

### quiz
- Какие три причины чаще всего стоят за `certificate verify failed`?
- Что показывает `curl -k` и почему им нельзя «лечить» проблему?
- Какой сертификат отдаёт Traefik, если для имени нет своего, и как это выглядит для клиента?

### links
- https://curl.se/docs/sslcerts.html | сертификаты в curl | curl: SSL certificates
- https://doc.traefik.io/traefik/https/tls/#default-certificate | сертификат по умолчанию | Traefik: default certificate
