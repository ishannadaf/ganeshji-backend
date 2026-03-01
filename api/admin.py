from django.contrib import admin
from .models import Donation, Expense, User, WalletTransfer, AppNotification

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "donor_name",
        "amount",
        "donation_type",
        "mandal",
        "date",
    )
    search_fields = ("donor_name", "mandal")
    list_filter = ("donation_type", "mandal")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "category",
        "amount",
        "payment_mode",
        "mandal",
        "date",
    )
    search_fields = ("category", "paid_to", "mandal")
    list_filter = ("payment_mode", "mandal", "category")
    
    

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "mobile",
        "role",
        "mandal",
        "is_paid",
        "wallet_balance",
    )
    search_fields = ("name", "mobile", "mandal")
    list_filter = ("role", "is_paid", "mandal")



@admin.register(WalletTransfer)
class WalletTransferAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "amount",
        "status",
        "mandal",
        "from_user_id",
        "to_manager_id",
        "requested_at",
    )
    list_filter = ("status", "mandal")
    search_fields = ("mandal",)
    
    
@admin.register(AppNotification)
class AppNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "type",
        "to_user_id",
        "is_read",
        "created_at",
    )
    list_filter = ("type", "is_read")
    search_fields = ("title", "message")
    
