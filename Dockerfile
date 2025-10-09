FROM registry:2 AS registry-stage

FROM python:3.11-slim-bullseye

RUN pip install requests datetime 

COPY --from=registry-stage /bin/registry /bin/registry

RUN mkdir -p /var/lib/registry /etc/docker/registry

RUN echo 'version: 0.1\n\
storage:\n\
  filesystem:\n\
    rootdirectory: /var/lib/registry\n\
  delete:\n\
    enabled: true\n\
http:\n\
  addr: :5000\n\
  headers:\n\
    X-Content-Type-Options: [nosniff]' > /etc/docker/registry/config.yml

ENV REGISTRY_URL=http://localhost:5000

COPY main.py .

COPY entrypoint.sh .

ENTRYPOINT entrypoint.sh

