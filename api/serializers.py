from rest_framework import serializers
from .models import (
    User,
    Donation,
    Expense,
    WalletTransfer,
    AppNotification
)

# ============================
# USER (SAFE RESPONSE)
# ============================
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = (
            "password",
            "is_superuser",
            "is_staff",
            "groups",
            "user_permissions",
        )


# ============================
# USER REGISTRATION (SINGLE)
# ============================
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = (
            "mandal_name",
            "name",
            "mobile",
            "password",
            "role",
        )

    def validate_mobile(self, value):
        if User.objects.filter(mobile=value).exists():
            raise serializers.ValidationError("Mobile already registered")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")

        user = User.objects.create_user(
            mobile=validated_data["mobile"],
            password=password,
            name=validated_data["name"],
            mandal_name=validated_data["mandal_name"],
            role=validated_data.get("role", "Manager"),
        )
        return user



# ============================
# DONATION (MAPPED)
# ============================
class DonationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donation
        fields = "__all__"




# ============================
# EXPENSE (MAPPED)
# ============================
class ExpenseSerializer(serializers.ModelSerializer):
    # # ===== Incoming from MAUI (PascalCase) =====
    # Amount = serializers.DecimalField(
    #     source="amount", max_digits=10, decimal_places=2
    # )
    # Category = serializers.CharField(source="category")
    # PaymentMode = serializers.CharField(source="payment_mode")
    # PaidTo = serializers.CharField(source="paid_to")
    # Date = serializers.DateTimeField(source="date")
    # ClientExpenseId = serializers.CharField(
    #     source="client_expense_id"
    # )
    # IsSynced = serializers.BooleanField(
    #     source="is_synced", required=False
    # )

    # # ===== Snake_case model fields (NOT required from request) =====
    # amount = serializers.DecimalField(
    #     max_digits=10, decimal_places=2, required=False
    # )
    # category = serializers.CharField(required=False)
    # payment_mode = serializers.CharField(required=False)
    # paid_to = serializers.CharField(required=False)
    # date = serializers.DateTimeField(required=False)
    # client_expense_id = serializers.CharField(required=False)

    # # ===== Server-controlled fields =====
    # created_by_user_id = serializers.IntegerField(read_only=True)
    # created_by_name = serializers.CharField(read_only=True)
    # mandal_name = serializers.CharField(read_only=True)

    class Meta:
        model = Expense
        fields = "__all__"


# ============================
# WALLET TRANSFER (MAPPED)
# ============================
class WalletTransferSerializer(serializers.ModelSerializer):
    Amount = serializers.DecimalField(
        source="amount", max_digits=10, decimal_places=2
    )
    ClientWalletTransferId = serializers.CharField(
        source="client_wallet_transfer_id"
    )

    class Meta:
        model = WalletTransfer
        fields = "__all__"


# ============================
# APP NOTIFICATIONS
# ============================
class AppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppNotification
        fields = "__all__"
