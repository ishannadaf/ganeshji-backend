from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

class Mandal(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "ganesh_mandals"

    def __str__(self):
        return self.name


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

    mandal = models.ForeignKey(
            Mandal,
            on_delete=models.CASCADE,
            related_name="users"
        )

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
            models.Index(fields=["mandal"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.role})"


# ============================
# DONATIONS
# ============================
class Donation(models.Model):
    mandal_event = models.ForeignKey(
        "MandalEvent",
        on_delete=models.CASCADE,
        related_name="donations"
    )

    donor_name = models.CharField(max_length=200)
    amount = models.FloatField()

    whatsapp_number = models.CharField(max_length=20)
    donation_type = models.CharField(max_length=50)
    received_by = models.CharField(max_length=100)

    date = models.DateTimeField()
    remarks = models.TextField(blank=True, null=True)

    created_by_user_id = models.IntegerField()
    created_by_name = models.CharField(max_length=100)
    mandal = models.ForeignKey(
            Mandal,
            on_delete=models.CASCADE,
            related_name="donation"
        )

    client_donation_id = models.CharField(
        max_length=50,
        unique=True
    )

    is_synced = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "donations"
        ordering = ["-date"]
        
        
# ============================
# EXPENSES
# ============================
class Expense(models.Model):
    mandal_event = models.ForeignKey(
        "MandalEvent",
        on_delete=models.CASCADE,
        related_name="expenses"
    )

    category = models.CharField(max_length=100)
    amount = models.FloatField()

    payment_mode = models.CharField(max_length=50)
    paid_to = models.CharField(max_length=100)

    created_by_user_id = models.IntegerField()
    created_by_name = models.CharField(max_length=100)
    mandal = models.ForeignKey(
            Mandal,
            on_delete=models.CASCADE,
            related_name="expense"
        )

    date = models.DateTimeField()

    client_expense_id = models.CharField(
        max_length=50,
        unique=True
    )
    # event_id = models.IntegerField()
    is_synced = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "expenses"
        ordering = ["-date"]

class EventMaster(models.Model):
    event_name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.event_name

class MandalEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(EventMaster, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')  # 🚨 Prevent duplicate event creation
        
    
# ============================
# WALLET TRANSFER
# ============================
class WalletTransfer(models.Model):
    from_user_id = models.IntegerField()
    to_manager_id = models.IntegerField()

    mandal = models.ForeignKey(
            Mandal,
            on_delete=models.CASCADE,
            related_name="wallet_transfer"
        )
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
    mandal_event = models.ForeignKey(
        MandalEvent,
        on_delete=models.CASCADE,
        related_name="wallet_transfers",
        null=True
    )
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
    
    

    
    
class SubscriptionPlan(models.Model):
    PLAN_TYPES = [
        ("GOLD", "Gold"),
        ("SILVER", "Silver"),
        ("PLATINUM", "Platinum"),
    ]

    name = models.CharField(max_length=20, choices=PLAN_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(default=365)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - ₹{self.price}"


class MandalSubscription(models.Model):

    mandal = models.ForeignKey("Mandal", on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    payment_transaction_id = models.CharField(max_length=200)
    user_upi_id = models.CharField(max_length=200, null=True, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mandal.name} - {self.plan.name}"