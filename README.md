# Traefik Lab — reverse proxy, service discovery, TLS

![Traefik](https://raw.githubusercontent.com/meeymirita/works-lab/main/images/traefik.png)

**Статус: 🟡 переписана 18.10.2026 в большую лабу (11 сессий, 69 шагов, ~43 ч): методичка собрана ассистентом из Markdown-исходников, все блоки с запуском выполнены в изолированном Docker, схемы и «Ожидаемые результаты» настоящие. Владелец не проходила и не вычитывала; не запускалось: реальный Let’s Encrypt, токены DNS-провайдеров, proxy protocol с внешним балансировщиком, плагины из каталога.**
**Сложность: низкая–средняя** (инфраструктурная, не про код; Docker объясняется в шаге 1.4 ровно в нужном объёме).

## О чём

Reverse proxy, который сам находит контейнеры: маршруты по меткам, middlewares, балансировка и выкатка без простоя, TLS (mkcert, ACME), TCP/UDP, наблюдаемость. Сквозной проект CoffeeShop — от трёх открытых портов до одного входа с HTTPS, защитой и метриками.

## Стек

Traefik v3.7 + Docker Compose + Node.js API + nginx + PostgreSQL 18 + Adminer; mkcert; Pebble (тестовый ACME-сервер); k6; Prometheus, Grafana, Jaeger.

## Формат

Методичка [`traefik.html`](traefik.html) ([открыть на сайте](https://anitech.meeymirita.ru/works/traefik.html)) собрана из исходников `src/*.md` командой `python3 tools/build-manual.py traefik --run` (блоки ` ```bash run ` выполняются в Docker-в-Docker `traefik-dind`, образ-«терминал» — `Dockerfile`; результаты — `src/outputs.json`; схемы — `src/schemes.py` → `src/schemes/*.html`). Два режима прохождения: «с нуля» (все файлы создаются в шаге 1.5) и «продолжение» Docker-лабы.

## Что внутри (11 сессий)

1. Азбука: прокси, HTTP, TLS; стенд CoffeeShop; имена `*.localhost`
2. Установка и первый маршрут: статика и динамика, `traefik.yml`, `docker.sock`, `whoami`, дашборд, 🔨 «404 / 502 / 504»
3. Docker provider и правила маршрутизации: события Docker, правила, приоритеты, сети и порты, CoffeeShop за Traefik
4. Middlewares: порядок, пути, redirect, headers и CORS, compress и basicAuth, chain и файл, защита админки, 🔨 `$` в хэше
5. Надёжность и защита: rateLimit, inFlightReq, ipAllowList, retry, circuitBreaker, forwardAuth, k6, 🔨 двойной заказ
6. Балансировка и выкатка: копии, healthcheck, sticky, canary, mirroring, blue/green, 🔨 «все больны»
7. TLS, часть 1: рукопожатие, mkcert, `websecure`, редирект, TLS options, mTLS, 🔨 `certificate verify failed`
8. TLS, часть 2: ACME на Pebble (HTTP-01, TLS-ALPN-01, DNS-01, wildcard), секреты, HTTP/3, переезд на сервер, 🔨 `acme.json` и сорванный заказ
9. TCP/UDP, файловый провайдер, IP клиента: PostgreSQL и DNS через Traefik, плагин на Go, миграция v2 → v3, 🔨 подделка `X-Forwarded-For`
10. Наблюдаемость и итоговый проект: журнал JSON, Prometheus и Grafana, трассировка, дерево вопросов, итоговый стек (`starter/`: `up.sh`, `smoke.sh`), 🔨 Production Hell
11. Итоговое ТЗ без ответа: партнёрский API с mTLS, лимитами и выкаткой по метрикам

Модель: `EntryPoint → Router → Middleware → Service`.

## Лицензия и авторство

Код — MIT, тексты — CC BY 4.0, обложки и иллюстрации не покрыты (см. [LICENSE](LICENSE)). Кто что сделал: [NOTICE](NOTICE).

---

Часть сборного репозитория лабораторных работ — [anitech-performance](https://github.com/meeymirita/anitech-performance).

## План

План лабы — [`traefik_lab_plan.md`](traefik_lab_plan.md) (реализован 18.10.2026; отличия описаны в начале файла).
