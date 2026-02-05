from django.db import models

class Donation(models.Model):
    id = models.AutoField(primary_key=True)

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

    class Meta:
        db_table = "donations"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.donor_name} - ₹{self.amount}"


class Expense(models.Model):
    id = models.AutoField(primary_key=True)

    category = models.CharField(max_length=100)
    amount = models.FloatField()

    payment_mode = models.CharField(max_length=50)
    paid_to = models.CharField(max_length=100)

    # 🔐 OWNERSHIP
    created_by_user_id = models.IntegerField()
    created_by_name = models.CharField(max_length=100)

    # 🔑 MANDAL LINK
    mandal_name = models.CharField(max_length=100)

    date = models.DateTimeField()

    class Meta:
        db_table = "expenses"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.category} - ₹{self.amount}"
    
    
class User(models.Model):
    id = models.AutoField(primary_key=True)

    mandal_name = models.CharField(max_length=100)

    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15, unique=True)
    password = models.CharField(max_length=100)

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

    payment_id = models.CharField(
        max_length=100, null=True, blank=True
    )

    expiry_date = models.DateTimeField(null=True, blank=True)

    # 📊 Counters
    donation_count = models.IntegerField(default=0)
    expense_count = models.IntegerField(default=0)
    entry_count = models.IntegerField(default=0)

    # 💰 WALLET SYSTEM
    wallet_balance = models.FloatField(default=0)
    total_collected = models.FloatField(default=0)
    total_transferred = models.FloatField(default=0)
    manager_balance = models.FloatField(default=0)

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["mobile"]),
            models.Index(fields=["mandal_name"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.role})"
    
    
class WalletTransfer(models.Model):
    id = models.AutoField(primary_key=True)

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
        indexes = [
            models.Index(fields=["mandal_name"]),
            models.Index(fields=["status"]),
            models.Index(fields=["from_user_id"]),
            models.Index(fields=["to_manager_id"]),
        ]

    def __str__(self):
        return f"₹{self.amount} | {self.status}"
    

class AppNotification(models.Model):
    id = models.AutoField(primary_key=True)

    to_user_id = models.IntegerField()

    title = models.CharField(max_length=200)
    message = models.TextField()

    type = models.CharField(max_length=50)   # e.g. Wallet
    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField()

    class Meta:
        db_table = "app_notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["to_user_id"]),
            models.Index(fields=["type"]),
            models.Index(fields=["is_read"]),
        ]

    def __str__(self):
        return f"{self.title} ({'Read' if self.is_read else 'Unread'})"    
