#!/bin/bash
# scripts/nginx/test_nginx.sh
# Test and validate Nginx configuration
# Usage: ./scripts/nginx/test_nginx.sh

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Nginx Configuration Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test configuration syntax
echo "🔍 Running: nginx -t"
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid!"
else
    echo "❌ Nginx configuration has errors. Fix before reloading."
    exit 1
fi

# Show active sites
echo ""
echo "📋 Enabled sites:"
ls -la /etc/nginx/sites-enabled/

echo ""
echo "📋 Nginx version:"
nginx -v

echo ""
echo "📋 Nginx status:"
sudo systemctl is-active nginx
