import random
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

from .models import (
    Profile, Farm, Crop, Inventory, Expense, Revenue, 
    Worker, Attendance, TaskAssignment, Notification
)
from .serializers import (
    UserRegisterSerializer, UserSerializer, ProfileSerializer, 
    FarmSerializer, CropSerializer, InventorySerializer, 
    ExpenseSerializer, RevenueSerializer, WorkerSerializer, 
    AttendanceSerializer, TaskAssignmentSerializer, NotificationSerializer
)

User = get_user_model()

# --- Role Based Permissions ---
class IsFarmerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['FARMER', 'ADMIN']

class IsManagerOrFarmerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['FARMER', 'MANAGER', 'ADMIN']

# --- Auth View ---
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            Profile.objects.create(user=user)
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- Standard Viewsets with Filtering, Searching, & Sorting ---
class FarmViewSet(viewsets.ModelViewSet):
    serializer_class = FarmSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'location']
    search_fields = ['name', 'location']
    ordering_fields = ['created_at', 'size']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Farm.objects.all()
        elif user.role == 'MANAGER':
            return Farm.objects.filter(managers=user)
        return Farm.objects.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class CropViewSet(viewsets.ModelViewSet):
    serializer_class = CropSerializer
    permission_classes = [IsManagerOrFarmerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'farm']
    search_fields = ['name', 'variety']
    ordering_fields = ['planting_date', 'harvest_date']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Crop.objects.all()
        return Crop.objects.filter(Q(farm__owner=user) | Q(farm__managers=user)).distinct()

class InventoryViewSet(viewsets.ModelViewSet):
    serializer_class = InventorySerializer
    permission_classes = [IsManagerOrFarmerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'farm']
    search_fields = ['item_name']
    ordering_fields = ['quantity', 'created_at']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Inventory.objects.all()
        return Inventory.objects.filter(Q(farm__owner=user) | Q(farm__managers=user)).distinct()

    def perform_write_and_check_stock(self, serializer):
        item = serializer.save()
        if item.quantity <= item.low_stock_threshold:
            # Trigger low stock notification
            Notification.objects.create(
                user=item.farm.owner,
                type='LOW_STOCK',
                message=f"Low Stock Alert: {item.item_name} on {item.farm.name} has only {item.quantity} {item.unit} remaining (Threshold: {item.low_stock_threshold})."
            )

    def perform_create(self, serializer):
        self.perform_write_and_check_stock(serializer)

    def perform_update(self, serializer):
        self.perform_write_and_check_stock(serializer)

class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [IsFarmerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'farm']
    search_fields = ['description']
    ordering_fields = ['amount', 'date']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Expense.objects.all()
        return Expense.objects.filter(farm__owner=user)

class RevenueViewSet(viewsets.ModelViewSet):
    serializer_class = RevenueSerializer
    permission_classes = [IsFarmerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['farm', 'crop']
    search_fields = ['buyer_name']
    ordering_fields = ['total_amount', 'date']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Revenue.objects.all()
        return Revenue.objects.filter(farm__owner=user)

class WorkerViewSet(viewsets.ModelViewSet):
    serializer_class = WorkerSerializer
    permission_classes = [IsManagerOrFarmerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['farm']
    search_fields = ['name', 'role']
    ordering_fields = ['wage_rate', 'created_at']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Worker.objects.all()
        return Worker.objects.filter(Q(farm__owner=user) | Q(farm__managers=user)).distinct()

class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [IsManagerOrFarmerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['worker', 'status', 'date']
    ordering_fields = ['date']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Attendance.objects.all()
        return Attendance.objects.filter(Q(worker__farm__owner=user) | Q(worker__farm__managers=user)).distinct()

class TaskAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskAssignmentSerializer
    permission_classes = [IsManagerOrFarmerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'worker', 'farm']
    search_fields = ['description']
    ordering_fields = ['due_date', 'created_at']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return TaskAssignment.objects.all()
        return TaskAssignment.objects.filter(Q(farm__owner=user) | Q(farm__managers=user)).distinct()

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['created_at']

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

# --- Weather & Market Mocks ---
class WeatherView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # We can implement a clean cached Weather API response
        # or fall back to simulated Agri-centric meteorological forecasts
        location = request.query_params.get('location', 'Central Valley')
        weather_data = {
            'location': location,
            'temperature': random.randint(18, 35),
            'humidity': random.randint(40, 85),
            'condition': random.choice(['Sunny', 'Partly Cloudy', 'Showers', 'Humid', 'Thunderstorm']),
            'forecast': [
                {'day': 'Tomorrow', 'temp': random.randint(18, 35), 'condition': 'Sunny'},
                {'day': 'Day 2', 'temp': random.randint(18, 35), 'condition': 'Cloudy'},
                {'day': 'Day 3', 'temp': random.randint(18, 35), 'condition': 'Rainy'},
            ],
            'alert': 'High chance of evening precipitation. Recommended to adjust watering cycles.'
        }
        return Response(weather_data)

class MarketPriceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        crop_prices = [
            {'crop': 'Wheat', 'price': 220, 'trend': 'up', 'historical': [210, 215, 218, 220]},
            {'crop': 'Corn', 'price': 185, 'trend': 'down', 'historical': [192, 190, 187, 185]},
            {'crop': 'Soybeans', 'price': 340, 'trend': 'up', 'historical': [330, 335, 338, 340]},
            {'crop': 'Rice', 'price': 290, 'trend': 'stable', 'historical': [290, 291, 289, 290]},
        ]
        return Response(crop_prices)

# --- Reporting Dashboard Analytics & Export ---
class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        role = user.role

        if role == 'ADMIN':
            total_users = User.objects.count()
            total_farms = Farm.objects.count()
            total_expenses = Expense.objects.aggregate(Sum('amount'))['amount__sum'] or 0.0
            total_revenues = Revenue.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0.0
            
            return Response({
                'role': role,
                'total_users': total_users,
                'total_farms': total_farms,
                'total_expenses': float(total_expenses),
                'total_revenues': float(total_revenues),
                'total_profit': float(total_revenues - total_expenses),
            })
        
        # Farmer / Manager view
        farms = Farm.objects.filter(owner=user) if role == 'FARMER' else Farm.objects.filter(managers=user)
        farm_ids = farms.values_list('id', flat=True)

        active_crops_count = Crop.objects.filter(farm_id__in=farm_ids, status__in=['PLANTED', 'GROWING']).count()
        total_expenses = Expense.objects.filter(farm_id__in=farm_ids).aggregate(Sum('amount'))['amount__sum'] or 0.0
        total_revenues = Revenue.objects.filter(farm_id__in=farm_ids).aggregate(Sum('total_amount'))['total_amount__sum'] or 0.0

        recent_activities = []
        # Pull notifications as recent events
        notifications = Notification.objects.filter(user=user).order_by('-created_at')[:5]
        for note in notifications:
            recent_activities.append({
                'type': note.type,
                'message': note.message,
                'time': note.created_at.strftime('%Y-%m-%d %H:%M')
            })

        return Response({
            'role': role,
            'active_crops': active_crops_count,
            'total_expenses': float(total_expenses),
            'total_revenues': float(total_revenues),
            'total_profit': float(total_revenues - total_expenses),
            'recent_activities': recent_activities
        })

class ExportReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # We can serve simple, downloadable text/html or csv report summary
        user = request.user
        farms = Farm.objects.filter(owner=user)
        farm_ids = farms.values_list('id', flat=True)

        expenses = Expense.objects.filter(farm_id__in=farm_ids)
        revenues = Revenue.objects.filter(farm_id__in=farm_ids)

        report_csv = "Type,Category/Crop,Amount/Total,Date,Description/Buyer\n"
        for exp in expenses:
            report_csv += f"EXPENSE,{exp.category},{exp.amount},{exp.date},{exp.description}\n"
        for rev in revenues:
            report_csv += f"REVENUE,{rev.crop.name if rev.crop else 'Crop'},{rev.total_amount},{rev.date},{rev.buyer_name}\n"

        response = HttpResponse(report_csv, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="agrizen_financial_report.csv"'
        return response
