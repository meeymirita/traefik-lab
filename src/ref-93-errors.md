# 2 · Справочник ошибок: симптом → причина → что делать | short: Справочник ошибок | kind: ref
Диагностика идёт по цепочке сверху вниз: **имя → порт → TLS → роутер → middleware → сервис**. Главный вопрос для любого кода: чей это ответ — Traefik или приложения? (шаг 10.4).

**Ответы клиенту**

| Симптом | Причина | Что делать |
|---|---|---|
| `curl: (6) Could not resolve host` | имя не находится | `/etc/hosts`, `*.localhost` (1.6) |
| `curl: (7) Failed to connect` / `Connection refused` | порт не опубликован или не запущен Traefik | `docker compose ps`, `ports` (2.3) |
| `curl: (35)`/`(56)`, `HTTP 000` на HTTPS | рукопожатие TLS не состоялось: версия, mTLS, `sniStrict` | TLS options (7.5–7.6) |
| `404 page not found` (текст Traefik) | **роутер не найден** | дашборд → роутеры; `traefik.enable`, сеть, правило, `entryPoints`, приоритет (2.7, 3.7) |
| `404` в формате приложения | приложение не знает путь | `stripPrefix`? путь у бэкенда (3.5) |
| `401 Unauthorized` | `basicAuth`/`forwardAuth` отказал | пароль, хэш (`$$` в Compose) (4.4–4.7, 5.4) |
| `403 Forbidden` | `ipAllowList` | диапазон, `trustedIPs`, `depth` (5.2, 9.7) |
| `429 Too Many Requests` | `rateLimit` / `inFlightReq` | числа лимитов, `Retry-After` (5.1) |
| `502 Bad Gateway` | сервис не ответил: порт, контейнер упал, обрыв | порт сервиса, `docker compose logs` (2.7, 3.4) |
| `503 no available server` | нет здоровых копий / разомкнут предохранитель | `serverStatus`, `/health` (6.7, 5.3) |
| `504 Gateway Timeout` | Traefik не достучался: сеть, медленный бэкенд | общая сеть, `traefik.docker.network` (2.7, 3.4) |

**TLS и сертификаты**

| Симптом | Причина | Что делать |
|---|---|---|
| `unable to get local issuer certificate` | клиент не доверяет CA | `mkcert -install`, `--cacert` (7.7) |
| `no alternative certificate subject name matches` | имя не в SAN; отдан `TRAEFIK DEFAULT CERT` | перевыпустить с нужным именем (7.7) |
| `certificate has expired` | срок вышел | перевыпустить; ACME обновляет сам (8.2) |
| `permissions 644 … are too open` | права на `acme.json` | `chmod 600` (8.7) |
| `Unable to obtain ACME certificate … Timeout during connect` | проверка не дошла до сервера | DNS указывает на сервер? порт 80/443 открыт? (8.7) |
| `Router uses a nonexistent certificate resolver` | опечатка в имени резолвера или он отключён | `certresolver=…`, журнал (8.7) |

**Конфигурация и Compose**

| Симптом | Причина | Что делать |
|---|---|---|
| `variable "…" is not set` в `docker compose config` | `$` в метке или хэше | `$$` или `.env` в одинарных кавычках (4.7) |
| роутер в дашборде `disabled`, ошибка `unsupported function` | правило v2 в v3 (`Headers`) | `Header`, `ruleSyntax=v2` (9.6) |
| роутер `enabled`, но ничего не совпадает | `HostRegexp` со скобками v2 | обычное регулярное выражение (9.6) |
| `HTTP router defined multiple times` | два контейнера с одним именем роутера | префикс проекта в именах (3.6) |
| «Could not find network … Defaulting» | контейнер не в сети `proxy` | `networks`, `traefik.docker.network` (2.7, 3.4) |
| после правки `traefik.yml` ничего не меняется | статика читается при старте | `docker compose restart traefik` (2.2) |
| `docker compose` создал **каталог** вместо файла | файла не было до запуска | создай файл до `up` (8.3) |

**Безопасность**

| Симптом | Причина | Что делать |
|---|---|---|
| админка открывается с чужого адреса | широкое `trustedIPs`, неверный `depth` | только свои прокси (9.7) |
| дашборд открыт всем | нет `admin-auth` | middleware на роутер дашборда (4.6) |
| токен в публичном репозитории | секрет в файле | отозвать токен, `…_FILE`, `.gitignore` (8.4) |
