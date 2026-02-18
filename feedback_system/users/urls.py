from rest_framework.routers import DefaultRouter
from .views import SubjectViewSet, FeedbackViewSet

router = DefaultRouter()
router.register(r'subjects', SubjectViewSet)
router.register(r'feedbacks', FeedbackViewSet)

urlpatterns = router.urls
