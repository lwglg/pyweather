ARG NODE_VERSION=24
FROM node:${NODE_VERSION}-alpine

ARG NEWMAN_VERSION=6.2.1
LABEL org.opencontainers.image.title="gntech/pyweather-newman" \
      org.opencontainers.image.description="Executor (Newman) da collection Postman do pyweather"

RUN npm install --global --no-fund --no-audit "newman@${NEWMAN_VERSION}" \
 && npm cache clean --force

WORKDIR /postman
COPY infra/docker/newman/run.sh /usr/local/bin/run-smoke
RUN chmod +x /usr/local/bin/run-smoke

# A collection e os environments são montados em /postman (veja docker-compose.smoke.yml),
# de modo que são exatamente os mesmos arquivos usados no Postman.
USER node
ENTRYPOINT ["run-smoke"]
