from django.contrib import admin
from .models import Donation, Expense, User, WalletTransfer, AppNotification

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "donor_name",
        "amount",
        "donation_type",
        "mandal_name",
        "date",
    )
    search_fields = ("donor_name", "mandal_name")
    list_filter = ("donation_type", "mandal_name")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "category",
        "amount",
        "payment_mode",
        "mandal_name",
        "date",
    )
    search_fields = ("category", "paid_to", "mandal_name")
    list_filter = ("payment_mode", "mandal_name", "category")
    
    

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "mobile",
        "role",
        "mandal_name",
        "is_paid",
        "wallet_balance",
    )
    search_fields = ("name", "mobile", "mandal_name")
    list_filter = ("role", "is_paid", "mandal_name")



@admin.register(WalletTransfer)
class WalletTransferAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "amount",
        "status",
        "mandal_name",
        "from_user_id",
        "to_manager_id",
        "requested_at",
    )
    list_filter = ("status", "mandal_name")
    search_fields = ("mandal_name",)
    
    
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
    
