#!/usr/bin/env bash
cd "$(dirname "$0")"

case "${1:-}" in
  start)
    pm2 start ecosystem.config.js
    ;;
  stop)
    pm2 stop teaching-docs-server
    ;;
  restart)
    pm2 restart teaching-docs-server
    ;;
  status)
    pm2 status teaching-docs-server
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac
