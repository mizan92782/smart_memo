"""
scripts/seeds/seed_root.py — Root Seed Runner

This file orchestrates the execution of all individual seed files in order.
Add new seeds to the SEED_MODULES list below.

Usage:
    python scripts/seeds/seed_root.py
    # Or via bash:
    ./scripts/seeds/run_seeds.sh

Seed Convention:
    - Each seed module must define a `run()` function.
    - Seeds run in the order listed in SEED_MODULES.
    - Seeds should be idempotent (safe to run multiple times).

Adding a new seed:
    1. Create scripts/seeds/seed_<app_name>.py
    2. Define: def run(): ...
    3. Add it to SEED_MODULES below.
"""
import os
import sys
import django
import traceback

# ── Bootstrap Django ──────────────────────────────────────────────────────────
# Add project root to path so manage.py can be found
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_memo.settings')
django.setup()

# ── Seed Modules (in execution order) ────────────────────────────────────────
# Format: importable dotted path to module containing run()
SEED_MODULES = [
    # Add seed modules here as you create them:
    # 'scripts.seeds.seed_users',
    # 'scripts.seeds.seed_categories',
    # 'scripts.seeds.seed_products',
    # 'scripts.seeds.seed_configuration',
]


# ─────────────────────────────────────────────────────────────────────────────

def run_seeds():
    """Execute all seed modules in order."""
    if not SEED_MODULES:
        print("ℹ️  No seed modules registered in SEED_MODULES. Add seeds to run.")
        return

    print(f"🌱 Running {len(SEED_MODULES)} seed module(s)...")
    print("")

    success_count = 0
    failure_count = 0

    for module_path in SEED_MODULES:
        try:
            print(f"  ▶ {module_path} ...", end=" ")
            module = __import__(module_path, fromlist=['run'])
            module.run()
            print("✅ Done")
            success_count += 1
        except Exception:
            print("❌ Failed")
            print(f"\n  Error in {module_path}:")
            traceback.print_exc()
            failure_count += 1
            print("")

    print("")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Seeds complete: {success_count} succeeded, {failure_count} failed")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if failure_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    run_seeds()
