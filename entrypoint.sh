#!/bin/sh

if [ "$REGISTRY_URL" = "http://localhost:5000" ]
then
  registry serve /etc/docker/registry/config.yml &
  REGPID=$!
  python /main.py
  kill $REGPID
  registry garbage-collect /etc/docker/registry/config.yml
else
  python /main.py
fi
