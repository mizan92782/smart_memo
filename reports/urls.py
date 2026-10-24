from rest_framework.routers import DefaultRouter
from reports.views.report_view import ReportViewSet

router = DefaultRouter()
router.register(r'', ReportViewSet, basename='report')

urlpatterns = router.urls
