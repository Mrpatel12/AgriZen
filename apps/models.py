import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.db.models import Sum, F, ExpressionWrapper, DecimalField

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

# --- AUTH & USER PROFILE ---

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = (
        ('FARMER', 'Farmer'),
        ('MANAGER', 'Farm Manager'),
        ('ADMIN', 'Admin'),
    )
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='FARMER')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.email} ({self.role})"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    farm_name = models.CharField(max_length=150, blank=True)
    farm_location = models.CharField(max_length=200, blank=True)
    farm_size = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def __str__(self):
        return f"Profile of {self.user.email}"

# --- FARMS & CROPS ---

class Farm(BaseModel):
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=200)
    size = models.DecimalField(max_digits=10, decimal_places=2)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='farms')
    managers = models.ManyToManyField(User, related_name='managed_farms', blank=True)

    def __str__(self):
        return self.name

class Crop(BaseModel):
    STATUS_CHOICES = (
        ('PLANTED', 'Planted'),
        ('GROWING', 'Growing'),
        ('HARVESTED', 'Harvested'),
        ('CANCELLED', 'Cancelled'),
    )
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='crops')
    name = models.CharField(max_length=100)
    variety = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANTED')
    planting_date = models.DateField(default=timezone.now)
    harvest_date = models.DateField(null=True, blank=True)
    yield_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    yield_unit = models.CharField(max_length=20, default='kg')

    def __str__(self):
        return f"{self.name} ({self.variety}) - {self.farm.name}"

# --- INVENTORY ---

class Inventory(BaseModel):
    CATEGORY_CHOICES = (
        ('SEEDS', 'Seeds'),
        ('FERTILIZERS', 'Fertilizers'),
        ('PESTICIDES', 'Pesticides'),
        ('EQUIPMENT', 'Equipment'),
    )
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='inventories')
    item_name = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=20, default='kg')
    low_stock_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=10.0)

    def __str__(self):
        return f"{self.item_name} ({self.category}) - {self.farm.name}"

# --- FINANCES (EXPENSES & REVENUES) ---

class Expense(BaseModel):
    CATEGORY_CHOICES = (
        ('LABOR', 'Labor'),
        ('SEED', 'Seed'),
        ('FERTILIZER', 'Fertilizer'),
        ('EQUIPMENT', 'Equipment'),
        ('MISC', 'Miscellaneous'),
    )
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='expenses')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.category} expense: {self.amount} - {self.farm.name}"

class Revenue(BaseModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='revenues')
    crop = models.ForeignKey(Crop, on_delete=models.SET_NULL, null=True, blank=True, related_name='revenues')
    buyer_name = models.CharField(max_length=150, blank=True)
    quantity_sold = models.DecimalField(max_digits=12, decimal_places=2)
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True)
    date = models.DateField(default=timezone.now)

    def save(self, *args, **kwargs):
        self.total_amount = self.quantity_sold * self.price_per_unit
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Sale to {self.buyer_name or 'Unknown'}: {self.total_amount} - {self.farm.name}"

# --- WORKERS ---

class Worker(BaseModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='workers')
    name = models.CharField(max_length=150)
    role = models.CharField(max_length=100)
    wage_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Wage rate per day")
    contact_info = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.name} ({self.role}) - {self.farm.name}"

class Attendance(models.Model):
    STATUS_CHOICES = (
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LEAVE', 'Leave'),
    )
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PRESENT')

    class Meta:
        unique_together = ('worker', 'date')

    def __str__(self):
        return f"{self.worker.name} on {self.date}: {self.status}"

class TaskAssignment(BaseModel):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    )
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='tasks')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='tasks')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    due_date = models.DateField()

    def __str__(self):
        return f"Task for {self.worker.name}: {self.description[:30]}"

# --- NOTIFICATIONS & WEATHER/MARKET MOCKS ---

class Notification(models.Model):
    TYPE_CHOICES = (
        ('LOW_STOCK', 'Low Stock Alert'),
        ('HARVEST', 'Harvest Reminder'),
        ('WEATHER', 'Weather Warning'),
        ('MARKET', 'Market Price Alert'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.type}] for {self.user.email}: {self.message[:30]}"

class OTPVerification(models.Model):
    email = models.EmailField(unique=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=5)

    def __str__(self):
        return f"OTP for {self.email}: {self.otp_code}"

