from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, UserProfileView, FarmViewSet, CropViewSet, 
    InventoryViewSet, ExpenseViewSet, RevenueViewSet, 
    WorkerViewSet, AttendanceViewSet, TaskAssignmentViewSet, 
    NotificationViewSet, WeatherView, MarketPriceView, 
    DashboardStatsView, ExportReportView
)

router = DefaultRouter()
router.register(r'farms', FarmViewSet, basename='farm')
router.register(r'crops', CropViewSet, basename='crop')
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'revenues', RevenueViewSet, basename='revenue')
router.register(r'workers', WorkerViewSet, basename='worker')
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'tasks', TaskAssignmentViewSet, basename='task')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/profile/', UserProfileView.as_view(), name='profile'),
    path('weather/', WeatherView.as_view(), name='weather'),
    path('market/', MarketPriceView.as_view(), name='market'),
    path('dashboard/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('reports/export/', ExportReportView.as_view(), name='export-report'),
    path('', include(router.urls)),
]
