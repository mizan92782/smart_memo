#!/bin/bash
# scripts/nginx/restart_nginx.sh
# Restart Nginx service
# Usage: sudo ./scripts/nginx/restart_nginx.sh [reload|restart|stop|status]

set -e
ACTION=${1:-reload}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Nginx Control — Action: $ACTION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

case $ACTION in
    reload)
        echo "🔍 Testing config first..."
        sudo nginx -t
        echo "♻️  Reloading Nginx (graceful, zero-downtime)..."
        sudo systemctl reload nginx
        echo "✅ Nginx reloaded"
        ;;
    restart)
        echo "🔍 Testing config first..."
        sudo nginx -t
        echo "🔄 Restarting Nginx..."
        sudo systemctl restart nginx
        echo "✅ Nginx restarted"
        ;;
    stop)
        echo "⛔ Stopping Nginx..."
        sudo systemctl stop nginx
        echo "✅ Nginx stopped"
        ;;
    status)
        sudo systemctl status nginx
        ;;
    *)
        echo "Usage: $0 [reload|restart|stop|status]"
        exit 1
        ;;
esac
