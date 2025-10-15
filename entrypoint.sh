#!/bin/sh

if [ "$REGISTRY_URL" = "http://localhost:5000" ]
then
  # Sending registry stuff to stderr for docker log filteringability
  registry serve /etc/docker/registry/config.yml >/dev/stderr &
  REGPID=$!
  python /main.py
  kill $REGPID
  registry garbage-collect /etc/docker/registry/config.yml >/dev/stderr
else
  python /main.py
fi
