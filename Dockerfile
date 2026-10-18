# Образ-«терминал» для сборки методички: docker CLI + compose + bash/curl/jq + инструменты лабы.
# Демон — отдельный (docker:dind), см. tools/build-manual.py и traefik/src/run.json
FROM docker:cli
RUN apk add --no-cache bash curl jq git openssl apache2-utils postgresql18-client bind-tools ca-certificates \
 && A=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/') \
 && curl -fsSL "https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-$A" -o /usr/local/bin/mkcert && chmod +x /usr/local/bin/mkcert \
 && curl -fsSL "https://github.com/grafana/k6/releases/download/v2.3.0/k6-v2.3.0-linux-$A.tar.gz" | tar -xz -C /tmp && mv /tmp/k6-*/k6 /usr/local/bin/k6
WORKDIR /work
CMD ["bash"]
