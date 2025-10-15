#!/bin/sh

if [ "$REGISTRY_URL" = "http://localhost:5000" ]
then
  case "$LOG_LEVEL" in
    DEBUG|TRACE) out=stderr ;;
    *) out=null ;;
  esac
  registry serve /etc/docker/registry/config.yml >/dev/$out 2>&1 &
  REGPID=$!
  python /main.py
  kill $REGPID
  registry garbage-collect /etc/docker/registry/config.yml >/dev/$out 2>&1
else
  python /main.py
fi
