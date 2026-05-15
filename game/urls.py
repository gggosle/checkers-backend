from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GameViewSet, TaskStatusView

router = DefaultRouter()
router.register(r'games', GameViewSet, basename='game')

urlpatterns = [
    path('', include(router.urls)),
    path('task-status/<str:task_id>/', TaskStatusView.as_view(), name='task-status'),
]
