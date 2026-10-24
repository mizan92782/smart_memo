#!/bin/bash
# scripts/seeds/run_seeds.sh
# Run all database seed files with DB flush
# WARNING: This will DELETE ALL DATA and re-seed from scratch!
# Usage: ./scripts/seeds/run_seeds.sh [--no-flush]
# ─────────────────────────────────────────────────────────

set -e

FLUSH=${1:-"--flush"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  IKON Backend — Database Seed Runner"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$PROJECT_ROOT"

# ── Safety Warning ────────────────────────────────────────────────────────
if [ "$FLUSH" = "--flush" ]; then
    echo ""
    echo "⚠️  WARNING: This will FLUSH the database (delete ALL data) then re-seed!"
    echo "   Continue? [y/N]"
    read -r confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "❌ Aborted."
        exit 0
    fi

    echo ""
    echo "🗑️  Flushing database..."
    python manage.py flush --no-input
    echo "✅ Database flushed"
fi

# ── Run Migrations First ──────────────────────────────────────────────────
echo ""
echo "📦 Running migrations..."
python manage.py migrate --no-input
echo "✅ Migrations complete"

# ── Run Seed Root ─────────────────────────────────────────────────────────
echo ""
echo "🌱 Running seed files..."
python scripts/seeds/seed_root.py

echo ""
echo "✅ All seeds completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
