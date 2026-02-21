from rest_framework import serializers
from .models import (
    User,
    Donation,
    Expense,
    WalletTransfer,
    AppNotification
)
from .models import EventMaster, MandalEvent
# ============================
# USER (SAFE RESPONSE)
# ============================
class UserSerializer(serializers.ModelSerializer):
    mandal_name = serializers.CharField(source="mandal.name", read_only=True)
    mandal_id = serializers.IntegerField(source="mandal.id", read_only=True)
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "mobile",
            "role",
            "mandal_id",
            "mandal_name",
            "wallet_balance",
        ]
        # exclude = (
        #     "password",
        #     "is_superuser",
        #     "is_staff",
        #     "groups",
        #     "user_permissions",
        # )


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
        exclude = (
            "mandal",
            "created_by_user_id",
            "created_by_name",
            "is_synced",
            "is_deleted",
        )

    # def validate_mandal_event(self, value):
    #     request = self.context.get("request")
    #     user = request.user

    #     # Ensure event belongs to same mandal
    #     if value.user.mandal_id != user.mandal_id:
    #         raise serializers.ValidationError(
    #             "Invalid event for this mandal"
    #         )

    #     return value

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user

        validated_data["created_by_user_id"] = user.id
        validated_data["created_by_name"] = user.name
        # validated_data["mandal_name"] = user.mandal.name

        return super().create(validated_data)

# ============================
# EXPENSE (MAPPED)
# ============================
class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        exclude = (
            "mandal",
            "created_by_user_id",
            "created_by_name",
            "is_synced",
            "is_deleted",
        )

    # def validate_mandal_event(self, value):
    #     request = self.context.get("request")
    #     user = request.user

    #     if value.user.mandal_name != user.mandal_name:
    #         raise serializers.ValidationError(
    #             "Invalid event for this mandal"
    #         )

    #     return value

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user

        validated_data["created_by_user_id"] = user.id
        validated_data["created_by_name"] = user.name
        # validated_data["mandal_name"] = user.mandal_name

        return super().create(validated_data)


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


class EventMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventMaster
        fields = ['id', 'event_name']


class MandalEventSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(
        source="event.event_name",
        read_only=True
    )

    class Meta:
        model = MandalEvent
        fields = ["id", "event", "event_name", "created_at"]
        read_only_fields = ["created_at"]