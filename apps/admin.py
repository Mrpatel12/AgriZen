from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Profile, Farm, Crop, Inventory, Expense, Revenue, 
    Worker, Attendance, TaskAssignment, Notification
)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Roles', {'fields': ('role',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Roles', {'fields': ('role',)}),
    )
    search_fields = ('email',)
    ordering = ('email',)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'farm_name', 'farm_location')
    search_fields = ('user__email', 'farm_name')

@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'size', 'owner', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'location', 'owner__email')

@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ('name', 'variety', 'status', 'planting_date', 'harvest_date', 'farm')
    list_filter = ('status', 'planting_date', 'farm')
    search_fields = ('name', 'variety', 'farm__name')

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'category', 'quantity', 'unit', 'low_stock_threshold', 'farm')
    list_filter = ('category', 'farm')
    search_fields = ('item_name', 'farm__name')

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount', 'date', 'farm')
    list_filter = ('category', 'date', 'farm')
    search_fields = ('description', 'farm__name')

@admin.register(Revenue)
class RevenueAdmin(admin.ModelAdmin):
    list_display = ('buyer_name', 'crop', 'quantity_sold', 'price_per_unit', 'total_amount', 'date', 'farm')
    list_filter = ('date', 'farm')
    search_fields = ('buyer_name', 'crop__name', 'farm__name')

@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'wage_rate', 'farm')
    list_filter = ('role', 'farm')
    search_fields = ('name', 'role', 'farm__name')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('worker', 'date', 'status')
    list_filter = ('status', 'date')
    search_fields = ('worker__name',)

@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ('worker', 'farm', 'description', 'status', 'due_date')
    list_filter = ('status', 'due_date', 'farm')
    search_fields = ('description', 'worker__name')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'message', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('message', 'user__email')
