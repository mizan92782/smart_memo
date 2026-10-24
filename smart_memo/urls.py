import os
import shutil
import re
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.core.cache import cache


def get_system_metrics():
    """Collect server system performance metrics."""
    cpu_count = os.cpu_count() or 1
    load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
    total, used, free = shutil.disk_usage("/")
    mem_total_gb = None
    mem_used_gb = None
    mem_used_pct = None
    cpu_usage_pct = None

    try:
        import psutil
        vm = psutil.virtual_memory()
        mem_total_gb = round(vm.total / (1024 ** 3), 2)
        mem_used_gb = round((vm.total - vm.available) / (1024 ** 3), 2)
        mem_used_pct = round(vm.percent, 1)
        cpu_usage_pct = round(psutil.cpu_percent(interval=0.1), 1)
    except Exception:
        try:
            with open('/proc/meminfo') as f:
                info = f.read()

            def parse_val(key):
                for line in info.splitlines():
                    if line.startswith(key):
                        parts = line.split()
                        return int(parts[1])
                return None

            mem_total_kb = parse_val('MemTotal:')
            mem_available_kb = parse_val('MemAvailable:') or parse_val('MemFree:')
            if mem_total_kb and mem_available_kb is not None:
                mem_total_gb = round(mem_total_kb / 1024.0 / 1024.0, 2)
                mem_used_gb = round((mem_total_kb - mem_available_kb) / 1024.0 / 1024.0, 2)
                mem_used_pct = round(((mem_total_kb - mem_available_kb) / mem_total_kb) * 100, 1)
        except Exception:
            pass

        try:
            load_per_cpu = (load_avg[0] / cpu_count) if cpu_count else 0.0
            cpu_usage_pct = round(min(100.0, load_per_cpu * 100.0), 1)
        except Exception:
            cpu_usage_pct = None

    return {
        "cpu_count": cpu_count,
        "load_average": {
            "1m": round(load_avg[0], 2),
            "5m": round(load_avg[1], 2),
            "15m": round(load_avg[2], 2),
        },
        "load_1m": round(load_avg[0], 2),
        "load_5m": round(load_avg[1], 2),
        "load_15m": round(load_avg[2], 2),
        "disk_total_gb": round(total / (1024 ** 3), 2),
        "disk_used_gb": round(used / (1024 ** 3), 2),
        "disk_free_gb": round(free / (1024 ** 3), 2),
        "memory_total_gb": mem_total_gb,
        "memory_used_gb": mem_used_gb,
        "memory_used_pct": mem_used_pct,
        "cpu_usage_percent": cpu_usage_pct,
    }


def health_view(request):
    """Health check endpoint providing live system status."""
    system = get_system_metrics()
    try:
        load_1m = float(system["load_average"]["1m"])
    except Exception:
        load_1m = 0.0
    cpu_count = int(system.get("cpu_count") or 1)
    load_per_cpu = load_1m / cpu_count if cpu_count else load_1m

    try:
        used = float(system.get("disk_used_gb", 0.0))
        total = float(system.get("disk_total_gb", 1.0))
        disk_used_pct = (used / total) * 100 if total else 0.0
    except Exception:
        disk_used_pct = 0.0

    cpu_pct = system.get('cpu_usage_percent')
    mem_pct = system.get('memory_used_pct')

    level = "Normal"
    if (cpu_pct and cpu_pct > 90) or (mem_pct and mem_pct > 90) or load_per_cpu > 1.5 or disk_used_pct > 90:
        level = "Risk"
    elif (cpu_pct and cpu_pct > 70) or (mem_pct and mem_pct > 70) or load_per_cpu > 0.7 or disk_used_pct > 70:
        level = "Abnormal"

    message = "🚀 Server is up and running!"
    if level == "Abnormal":
        message = "⚠️ Server showing elevated resource usage"
    elif level == "Risk":
        message = "🔥 Server under high resource pressure — immediate attention recommended"

    context = {
        "project_name": "Smart Memo",
        "status": "ok",
        "server_health": level,
        "message": message,
        "message_plain": re.sub(r"[\U00010000-\U0010ffff]|[\u2600-\u27ff]", "", message).strip(),
        "system": system,
    }
    if request.headers.get("Accept") == "application/json" or request.GET.get("format") == "json":
        return JsonResponse(context)
    return render(request, "health.html", context)


def health_live_view(request):
    """Liveness probe: verifies the web process is running and accepting HTTP requests."""
    return JsonResponse({
        "status": "alive",
        "service": "smart-memo-backend"
    }, status=200)


def health_ready_view(request):
    """
    Readiness probe: validates database connectivity, migration status,
    and cache availability without exposing secrets or connection strings.
    Returns HTTP 200 when ready, HTTP 503 if downstream dependency fails.
    """
    checks = {}
    is_ready = True

    # 1. Database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "connected"
    except Exception as exc:
        checks["database"] = f"unhealthy: {exc.__class__.__name__}"
        is_ready = False

    # 2. Database migrations check
    try:
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            checks["migrations"] = f"pending ({len(plan)} unapplied)"
            is_ready = False
        else:
            checks["migrations"] = "up_to_date"
    except Exception as exc:
        checks["migrations"] = f"unhealthy: {exc.__class__.__name__}"
        is_ready = False

    # 3. Cache connectivity
    try:
        cache.set("_readiness_probe", "ok", timeout=5)
        val = cache.get("_readiness_probe")
        if val == "ok":
            checks["cache"] = "connected"
        else:
            checks["cache"] = "degraded: read_mismatch"
    except Exception as exc:
        checks["cache"] = f"degraded: {exc.__class__.__name__}"

    status_code = 200 if is_ready else 503
    return JsonResponse({
        "status": "ready" if is_ready else "unhealthy",
        "service": "smart-memo-backend",
        "checks": checks
    }, status=status_code)


urlpatterns = [
    path('health/', health_view, name='health-check'),
    path('health/live/', health_live_view, name='health-live'),
    path('health/ready/', health_ready_view, name='health-ready'),
    path('admin/', admin.site.urls),
    path('products/', include('products.urls')),
    path('categories/', include('categories.urls')),
    path('users/', include('users.urls')),
    path('cards/', include('cards.urls')),
    path('stores/', include('stores.urls')),
    path('inventory/', include('inventory.urls')),
    path('orders/', include('orders.urls')),
    path('purchases/', include('purchases.urls')),
    path('reports/', include('reports.urls')),
    path('notifications/', include('notifications.urls')),
]


# Swagger / ReDoc OpenAPI documentation
try:
    from drf_yasg.views import get_schema_view
    from drf_yasg import openapi
    from rest_framework import permissions

    schema_view = get_schema_view(
        openapi.Info(
            title="Smart Memo API",
            default_version='v1',
            description="API documentation for Smart Memo Backend",
        ),
        public=True,
        permission_classes=(permissions.AllowAny,),
    )

    urlpatterns += [
        path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
        path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger'),
        path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    ]
except ImportError:
    pass

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT else settings.BASE_DIR / 'static')