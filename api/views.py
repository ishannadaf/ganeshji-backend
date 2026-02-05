from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
import logging
logger = logging.getLogger(__name__)

from .models import (
    User,
    Donation,
    Expense,
    WalletTransfer,
    AppNotification
)

from .serializers import (
    UserSerializer,
    DonationSerializer,
    ExpenseSerializer,
    WalletTransferSerializer,
    AppNotificationSerializer,
    RegisterSerializer
)


# ============================
# AUTH / LOGIN
# ============================
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(["POST"])
def login(request):
    logger.warning("LOGIN ATTEMPT: %s", request.data)
    mobile = request.data.get("mobile")
    password = request.data.get("password")

    if not mobile or not password:
        return Response(
            {"error": "Mobile and password required"},
            status=400
        )

    user = authenticate(request, mobile=mobile, password=password)

    if user is None:
        return Response(
            {"error": "Invalid credentials"},
            status=401
        )

    refresh = RefreshToken.for_user(user)

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "name": user.name,
            "mobile": user.mobile,
            "role": user.role,
            "mandal_name": user.mandal_name,
            "is_paid": user.is_paid,
        }
    })
    
    
@api_view(["POST"])
def signup(request):
    logger.warning("SIGNUP DATA RAW: %s", request.body)
    logger.warning("SIGNUP DATA PARSED: %s", request.data)
    data = request.data
    logger.warning("SIGNUP ATTEMPT: %s", request.data)
    if User.objects.filter(mobile=data.get("mobile")).exists():
        return Response(
            {"error": "Mobile already registered"},
            status=400
        )

    user = User.objects.create_user(
        mobile=data["mobile"],
        password=data["password"],
        name=data["name"],
        mandal_name=data["mandal_name"],
        role=data.get("role", "Manager")
    )

    refresh = RefreshToken.for_user(user)

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "name": user.name,
            "mobile": user.mobile,
            "role": user.role,
            "mandal_name": user.mandal_name,
        }
    })

@api_view(["GET"])
def ping(request):
    print("🔥 PING HIT FROM PHONE")
    return Response({"ok": True})

# ============================
# DONATIONS
# ============================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_donation(request):   
    data = request.data.copy()
    logger.warning("DONATION HIT: %s", request.data)
    data["created_by_user_id"] = request.user.id
    data["created_by_name"] = request.user.name
    data["mandal_name"] = request.user.mandal_name

    donation, created = Donation.objects.get_or_create(
        client_donation_id=data.get("client_donation_id"),
        defaults=data
    )

    return Response(
        DonationSerializer(donation).data,
        status=201 if created else 200
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_donations(request):
    mandal = request.GET.get("mandal")
    role = request.GET.get("role")
    user_id = request.GET.get("user_id")

    if role == "Manager":
        qs = Donation.objects.filter(
            mandal_name=mandal,
            is_deleted=False
        )
    else:
        qs = Donation.objects.filter(
            created_by_user_id=user_id,
            is_deleted=False
        )

    return Response(DonationSerializer(qs, many=True).data)


# ============================
# EXPENSES
# ============================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_expense(request):
    data = request.data.copy()

    data["created_by_user_id"] = request.user.id
    data["created_by_name"] = request.user.name
    data["mandal_name"] = request.user.mandal_name

    expense, created = Expense.objects.get_or_create(
        client_expense_id=data.get("client_expense_id"),
        defaults=data
    )

    return Response(
        ExpenseSerializer(expense).data,
        status=201 if created else 200
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_donation(request, client_donation_id):
    try:
        donation = Donation.objects.get(
            client_donation_id=client_donation_id
        )
        donation.is_deleted = True
        donation.save()

        return Response(status=204)
    except Donation.DoesNotExist:
        return Response(status=404)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_expenses(request):
    mandal = request.GET.get("mandal")
    role = request.GET.get("role")
    user_id = request.GET.get("user_id")

    if role == "Manager":
        qs = Expense.objects.filter(
            mandal_name=mandal,
            is_deleted=False
        )
    else:
        qs = Expense.objects.filter(
            created_by_user_id=user_id,
            is_deleted=False
        )

    return Response(ExpenseSerializer(qs, many=True).data)

# ============================
# WALLET TRANSFERS
# ============================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_wallet_request(request):
    data = request.data.copy()
    data["from_user_id"] = request.user.id
    data["mandal_name"] = request.user.mandal_name

    serializer = WalletTransferSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_wallet_requests(request):
    user = request.user

    if user.role != "Manager":
        return Response(
            {"error": "Only managers can view requests"},
            status=403
        )

    qs = WalletTransfer.objects.filter(
        mandal_name=user.mandal_name
    )
    return Response(WalletTransferSerializer(qs, many=True).data)


# ============================
# NOTIFICATIONS
# ============================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    qs = AppNotification.objects.filter(
        to_user_id=request.user.id
    )
    return Response(AppNotificationSerializer(qs, many=True).data)


@api_view(["POST"])
def register(request):
    logger.warning("SIGNUP DATA RAW: %s", request.body)
    logger.warning("SIGNUP DATA PARSED: %s", request.data)
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "User registered successfully"},
            status=status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user

    mandal_name = request.data.get("mandal_name")

    if not mandal_name:
        return Response(
            {"error": "mandal_name is required"},
            status=400
        )

    # Only manager can update mandal
    if user.role != "Manager":
        return Response(
            {"error": "Permission denied"},
            status=403
        )

    user.mandal_name = mandal_name
    user.save()

    return Response({"message": "Profile updated"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user

    target_user_id = request.data.get("user_id")
    old_password = request.data.get("old_password")
    new_password = request.data.get("new_password")

    # Determine target user
    if target_user_id:
        if user.role != "Manager":
            return Response(
                {"error": "Permission denied"},
                status=403
            )
        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=404
            )
    else:
        target_user = user

        if not old_password:
            return Response(
                {"error": "Old password required"},
                status=400
            )

        if not target_user.check_password(old_password):
            return Response(
                {"error": "Old password incorrect"},
                status=400
            )

    # Set new password (hashed)
    target_user.set_password(new_password)
    target_user.save()

    return Response({"message": "Password updated"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_wallet_request(request):
    data = request.data.copy()

    transfer, created = WalletTransfer.objects.get_or_create(
        client_wallet_transfer_id=data.get("client_wallet_transfer_id"),
        defaults=data
    )

    return Response(
        WalletTransferSerializer(transfer).data,
        status=201 if created else 200
    )
    
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approve_wallet_request(request):
    transfer_id = request.data.get("client_wallet_transfer_id")

    try:
        transfer = WalletTransfer.objects.get(
            client_wallet_transfer_id=transfer_id
        )

        transfer.status = "Approved"
        transfer.approved_at = timezone.now()
        transfer.save()

        return Response({"message": "Approved"})
    except WalletTransfer.DoesNotExist:
        return Response(status=404)
    
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reject_wallet_request(request):
    transfer_id = request.data.get("client_wallet_transfer_id")

    try:
        transfer = WalletTransfer.objects.get(
            client_wallet_transfer_id=transfer_id
        )

        transfer.status = "Rejected"
        transfer.approved_at = timezone.now()
        transfer.save()

        return Response({"message": "Rejected"})
    except WalletTransfer.DoesNotExist:
        return Response(status=404)
    
    
from django.contrib.auth.hashers import make_password

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_user(request):
    manager = request.user

    if manager.role != "Manager":
        return Response(
            {"error": "Permission denied"},
            status=403
        )

    mobile = request.data.get("mobile")

    if User.objects.filter(mobile=mobile).exists():
        return Response(
            {"error": "User already exists"},
            status=409
        )

    user = User.objects.create(
        name=request.data.get("name"),
        mobile=mobile,
        mandal_name=manager.mandal_name,
        role="User",
        password=make_password(request.data.get("password"))
    )

    return Response(
        UserSerializer(user).data,
        status=201
    )