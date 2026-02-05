from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


# ============================
# CUSTOM USER MANAGER
# ============================
class UserManager(BaseUserManager):
    def create_user(self, mobile, password=None, **extra_fields):
        if not mobile:
            raise ValueError("Mobile number is required")

        user = self.model(mobile=mobile, **extra_fields)
        user.set_password(password)  # 🔐 HASHED PASSWORD
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(mobile, password, **extra_fields)


# ============================
# CUSTOM USER MODEL
# ============================
class User(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True)

    mandal_name = models.CharField(max_length=100)

    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15, unique=True)

    role = models.CharField(
        max_length=20,
        choices=(
            ("Manager", "Manager"),
            ("User", "User"),
        ),
    )

    # 🔐 Subscription
    is_paid = models.BooleanField(default=False)
    is_demo_user = models.BooleanField(default=True)

    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)

    # 📊 Counters
    donation_count = models.IntegerField(default=0)
    expense_count = models.IntegerField(default=0)
    entry_count = models.IntegerField(default=0)

    # 💰 Wallet
    wallet_balance = models.FloatField(default=0)
    total_collected = models.FloatField(default=0)
    total_transferred = models.FloatField(default=0)
    manager_balance = models.FloatField(default=0)

    # Django auth flags
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "mobile"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "ganesh_users"
        indexes = [
            models.Index(fields=["mobile"]),
            models.Index(fields=["mandal_name"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.role})"


# ============================
# DONATIONS
# ============================
class Donation(models.Model):
    donor_name = models.CharField(max_length=200)
    amount = models.FloatField()

    whatsapp_number = models.CharField(max_length=20)
    donation_type = models.CharField(max_length=50)
    received_by = models.CharField(max_length=100)

    date = models.DateTimeField()
    remarks = models.TextField(blank=True, null=True)

    created_by_user_id = models.IntegerField()
    created_by_name = models.CharField(max_length=100)
    mandal_name = models.CharField(max_length=100)
    
    client_donation_id = models.CharField(
    max_length=50,
    unique=True
)
    is_synced = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    class Meta:
        db_table = "donations"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.donor_name} - ₹{self.amount}"


# ============================
# EXPENSES
# ============================
class Expense(models.Model):
    category = models.CharField(max_length=100)
    amount = models.FloatField()

    payment_mode = models.CharField(max_length=50)
    paid_to = models.CharField(max_length=100)

    created_by_user_id = models.IntegerField()
    created_by_name = models.CharField(max_length=100)
    mandal_name = models.CharField(max_length=100)

    date = models.DateTimeField()
    
    client_expense_id = models.CharField(
    max_length=50,
    unique=True
)
    is_synced = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    class Meta:
        db_table = "expenses"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.category} - ₹{self.amount}"


# ============================
# WALLET TRANSFER
# ============================
class WalletTransfer(models.Model):
    from_user_id = models.IntegerField()
    to_manager_id = models.IntegerField()

    mandal_name = models.CharField(max_length=100)
    amount = models.FloatField()

    status = models.CharField(
        max_length=20,
        choices=(
            ("Pending", "Pending"),
            ("Approved", "Approved"),
            ("Rejected", "Rejected"),
        ),
        default="Pending",
    )

    requested_at = models.DateTimeField()
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "wallet_transfers"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"₹{self.amount} | {self.status}"


# ============================
# APP NOTIFICATIONS
# ============================
class AppNotification(models.Model):
    to_user_id = models.IntegerField()

    title = models.CharField(max_length=200)
    message = models.TextField()

    type = models.CharField(max_length=50)
    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField()

    class Meta:
        db_table = "app_notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title