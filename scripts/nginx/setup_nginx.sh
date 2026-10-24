#!/bin/bash
# scripts/nginx/setup_nginx.sh
# Set up Nginx site configuration for IKON Backend
# Usage: sudo ./scripts/nginx/setup_nginx.sh <domain>
# Example: sudo ./scripts/nginx/setup_nginx.sh api.yoursite.com
# ─────────────────────────────────────────────────────────

set -e

DOMAIN=${1:-"localhost"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF_SOURCE="$SCRIPT_DIR/app.conf"
CONF_NAME="ikon_backend"
SITES_AVAILABLE="/etc/nginx/sites-available/$CONF_NAME"
SITES_ENABLED="/etc/nginx/sites-enabled/$CONF_NAME"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  IKON Backend — Nginx Setup"
echo "  Domain: $DOMAIN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Substitute domain placeholder ─────────────────────────────────────
echo "📝 Generating Nginx config for domain: $DOMAIN"
sed "s/\${SERVER_NAME}/$DOMAIN/g" "$CONF_SOURCE" > /tmp/ikon_nginx.conf

# ── 2. Copy to sites-available ────────────────────────────────────────────
echo "📂 Copying config to $SITES_AVAILABLE"
sudo cp /tmp/ikon_nginx.conf "$SITES_AVAILABLE"

# ── 3. Enable site (symlink to sites-enabled) ─────────────────────────────
if [ -L "$SITES_ENABLED" ]; then
    echo "🔗 Symlink already exists: $SITES_ENABLED"
else
    echo "🔗 Enabling site: $SITES_ENABLED"
    sudo ln -s "$SITES_AVAILABLE" "$SITES_ENABLED"
fi

# ── 4. Remove default site if it exists ──────────────────────────────────
if [ -L "/etc/nginx/sites-enabled/default" ]; then
    echo "🗑️  Removing default Nginx site"
    sudo rm -f /etc/nginx/sites-enabled/default
fi

# ── 5. Test Nginx configuration ───────────────────────────────────────────
echo "🔍 Testing Nginx configuration..."
sudo nginx -t

# ── 6. Reload Nginx ──────────────────────────────────────────────────────
echo "♻️  Reloading Nginx..."
sudo systemctl reload nginx

echo ""
echo "✅ Nginx setup complete!"
echo "   Config: $SITES_AVAILABLE"
echo "   Domain: https://$DOMAIN"
echo ""
echo "Next steps:"
echo "  1. Install SSL: sudo certbot --nginx -d $DOMAIN"
echo "  2. Verify: curl -I https://$DOMAIN/health/"
