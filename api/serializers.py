from rest_framework import serializers
from django.contrib.auth import authenticate
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
# USER REGISTRATION
# ============================
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "mobile",
            "password",
            "role",
            "mandal_name",
        )

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


# ============================
# DONATION
# ============================
class DonationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donation
        fields = "__all__"


# ============================
# EXPENSE
# ============================
class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = "__all__"


# ============================
# WALLET TRANSFER
# ============================
class WalletTransferSerializer(serializers.ModelSerializer):
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
        

# 🔐 USER REGISTRATION
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "mandal_name",
            "name",
            "mobile",
            "password",
            "role",
        )

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user