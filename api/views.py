from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
import logging
from django.db.models import Sum

from django.db import transaction


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
    mobile = request.data.get("mobile")
    password = request.data.get("password")

    if not mobile or not password:
        return Response(
            {"error": "Mobile and password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 🔐 Authenticate using USERNAME_FIELD
    user = authenticate(request, username=mobile, password=password)

    if user is None:
        return Response(
            {"error": "Invalid mobile or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {"error": "User account is disabled"},
            status=status.HTTP_403_FORBIDDEN
        )

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "name": user.name,
                "mobile": user.mobile,
                "role": user.role,
                "mandal_name": user.mandal_name,
                "is_paid": user.is_paid,
            },
        },
        status=status.HTTP_200_OK
    )

def calculate_user_wallet(user_id):
    donations = Donation.objects.filter(
        created_by_user_id=user_id,
        is_deleted=False
    ).aggregate(total=Sum("amount"))["total"] or 0

    expenses = Expense.objects.filter(
        created_by_user_id=user_id,
        is_deleted=False
    ).aggregate(total=Sum("amount"))["total"] or 0

    sent = WalletTransfer.objects.filter(
        from_user_id=user_id,
        status="Approved"
    ).aggregate(total=Sum("amount"))["total"] or 0

    return donations - expenses - sent

def calculate_manager_wallet(manager_id):
    base_wallet = calculate_user_wallet(manager_id)

    received = WalletTransfer.objects.filter(
        to_manager_id=manager_id,
        status="Approved"
    ).aggregate(total=Sum("amount"))["total"] or 0

    return base_wallet + received


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sync_wallet(request):
    user = request.user

    if user.role == "Manager":
        wallet = calculate_manager_wallet(user.id)
    else:
        wallet = calculate_user_wallet(user.id)

    return Response({
        "wallet_balance": wallet
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    mandal = request.user.mandal_name

    total_collection = Donation.objects.filter(
        mandal_name=mandal,
        is_deleted=False
    ).aggregate(total=Sum("amount"))["total"] or 0

    total_expense = Expense.objects.filter(
        mandal_name=mandal,
        is_deleted=False
    ).aggregate(total=Sum("amount"))["total"] or 0

    return Response({
        "total_collection": total_collection,
        "total_expense": total_expense,
        "net_balance": total_collection - total_expense
    })


@api_view(["POST"])
def signup(request):
    logger.warning("SIGNUP HIT: %s", request.data)
    data = request.data

    if User.objects.filter(mobile=data.get("mobile")).exists():
        return Response(
            {"error": "Mobile already registered"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.create_user(
        mobile=data["mobile"],
        password=data["password"],
        name=data["name"],
        mandal_name=data["mandal_name"],
        role=data.get("role") or "Manager"
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
    }, status=status.HTTP_201_CREATED)


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
    logger.warning("DONATION HIT: %s", request.data)

    serializer = DonationSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(
                created_by_user_id=request.user.id,
                created_by_name=request.user.name,
                mandal_name=request.user.mandal_name
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    logger.error("DONATION ERROR: %s", serializer.errors)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def collection_summary(request):
    user = request.user

    if user.role != "Manager":
        return Response(
            {"detail": "Access denied"},
            status=status.HTTP_403_FORBIDDEN
        )

    mandal = user.mandal_name

    donations = (
        Donation.objects
        .filter(mandal_name=mandal, is_deleted=False)
        .values("created_by_user_id", "created_by_name")
        .annotate(total=Sum("amount"))
        .order_by("created_by_name")
    )

    return Response(donations)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def donations_by_user(request, user_id):
    user = request.user

    if user.role != "Manager":
        return Response(
            {"detail": "Access denied"},
            status=status.HTTP_403_FORBIDDEN
        )

    qs = Donation.objects.filter(
        created_by_user_id=user_id,
        mandal_name=user.mandal_name,
        is_deleted=False
    ).order_by("-date")

    return Response(DonationSerializer(qs, many=True).data)


# ============================
# EXPENSES
# ============================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_expense(request):
    logger.warning("EXPENSE HIT: %s", request.data)

    serializer = ExpenseSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(
            created_by_user_id=request.user.id,
            created_by_name=request.user.name,
            mandal_name=request.user.mandal_name
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    logger.error("EXPENSE ERROR: %s", serializer.errors)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_donation(request, client_id):
    user = request.user

    try:
        donation = Donation.objects.get(
            client_donation_id=client_id,
            is_deleted=False
        )
    except Donation.DoesNotExist:
        return Response(
            {"error": "Donation not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # 🔒 PERMISSION CHECK
    if user.role != "Manager" and donation.created_by_user_id != user.id:
        return Response(
            {"error": "Permission denied"},
            status=status.HTTP_403_FORBIDDEN
        )

    # ❌ SOFT DELETE
    donation.is_deleted = True
    donation.save(update_fields=["is_deleted"])

    return Response(
        {"message": "Donation deleted successfully"},
        status=status.HTTP_200_OK
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_expense(request, client_id):
    user = request.user

    try:
        expense = Expense.objects.get(
            client_expense_id=client_id,
            is_deleted=False
        )
    except Expense.DoesNotExist:
        return Response(
            {"error": "Expense not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # 🔒 PERMISSION CHECK
    if user.role != "Manager" and expense.created_by_user_id != user.id:
        return Response(
            {"error": "Permission denied"},
            status=status.HTTP_403_FORBIDDEN
        )

    # ❌ SOFT DELETE
    expense.is_deleted = True
    expense.save(update_fields=["is_deleted"])

    return Response(
        {"message": "Expense deleted successfully"},
        status=status.HTTP_200_OK
    )


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
    user = request.user

    amount = request.data.get("amount")
    client_id = request.data.get("client_wallet_transfer_id")

    if not amount or not client_id:
        return Response(
            {"error": "Amount and client id required"},
            status=400
        )

    WalletTransfer.objects.create(
        client_wallet_transfer_id=client_id,
        from_user_id=user.id,
        mandal_name=user.mandal_name,
        amount=amount,
        status="Pending",
        requested_at=timezone.now()
    )

    return Response(
        {"message": "Wallet request created"},
        status=201
    )




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
        mandal_name=user.mandal_name,
        status="Pending"
    ).order_by("requested_at")

    return Response(
        WalletTransferSerializer(qs, many=True).data
    )



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
    logger.warning("REGISTER HIT: %s", request.data)
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
    data = request.data

    target_user_id = data.get("user_id")
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not target_user_id or not new_password:
        return Response(
            {"error": "Invalid request"},
            status=400
        )

    try:
        target_user = User.objects.get(id=target_user_id)
    except User.DoesNotExist:
        return Response(
            {"error": "User not found"},
            status=404
        )

    # 🔐 Self password change → verify old password
    if user.id == target_user.id:
        if not old_password or not target_user.check_password(old_password):
            return Response(
                {"error": "Current password incorrect"},
                status=403
            )

    # 🔒 Manager can change sub-user password without old password
    elif user.role != "Manager":
        return Response(
            {"error": "Permission denied"},
            status=403
        )

    target_user.set_password(new_password)
    target_user.save()

    return Response(
        {"message": "Password changed successfully"},
        status=200
    )

    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approve_wallet_request(request):
    manager = request.user

    if manager.role != "Manager":
        return Response({"error": "Only manager can approve"}, status=403)

    transfer_id = request.data.get("client_wallet_transfer_id")

    try:
        transfer = WalletTransfer.objects.get(
            client_wallet_transfer_id=transfer_id,
            status="Pending"
        )
    except WalletTransfer.DoesNotExist:
        return Response({"error": "Transfer not found"}, status=404)

    user = User.objects.get(id=transfer.from_user_id)

    # 🔴 CRITICAL WALLET LOGIC
    user.wallet_balance -= transfer.amount
    manager.wallet_balance += transfer.amount

    user.total_transferred += transfer.amount

    user.save()
    manager.save()

    transfer.status = "Approved"
    transfer.approved_at = timezone.now()
    transfer.save()

    return Response({"message": "Approved"})


    
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reject_wallet_request(request):
    manager = request.user

    if manager.role != "Manager":
        return Response({"error": "Only manager can reject"}, status=403)

    transfer_id = request.data.get("client_wallet_transfer_id")

    try:
        transfer = WalletTransfer.objects.get(
            client_wallet_transfer_id=transfer_id,
            status="Pending"
        )
    except WalletTransfer.DoesNotExist:
        return Response({"error": "Transfer not found"}, status=404)

    transfer.status = "Rejected"
    transfer.approved_at = timezone.now()
    transfer.save()

    return Response({"message": "Rejected"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_users(request):
    users = User.objects.filter(
        mandal_name=request.user.mandal_name
    )

    return Response(
        UserSerializer(users, many=True).data
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_user(request):
    manager = request.user

    if manager.role != "Manager":
        return Response(
            {"error": "Only managers can add users"},
            status=403
        )

    data = request.data

    required = ["name", "mobile", "password", "mandal_name"]
    for field in required:
        if not data.get(field):
            return Response(
                {"error": f"{field} is required"},
                status=400
            )

    if User.objects.filter(
        mobile=data["mobile"],
        mandal_name=manager.mandal_name
    ).exists():
        return Response(
            {"error": "User already exists"},
            status=409
        )

    user = User.objects.create_user(
        mobile=data["mobile"],
        password=data["password"],
        name=data["name"],
        role="User",
        mandal_name=manager.mandal_name
    )

    return Response(
        {
            "message": "User added successfully",
            "user": {
                "id": user.id,
                "name": user.name,
                "mobile": user.mobile,
                "role": user.role
            }
        },
        status=201
    )

    
# api/views.py
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sync_user(request):
    user = request.user

    if not user or not user.is_active:
        return Response(
            {"error": "User not active"},
            status=status.HTTP_403_FORBIDDEN
        )

    return Response(
        {
            "id": user.id,
            "name": user.name,
            "mobile": user.mobile,
            "role": user.role,
            "mandal_name": user.mandal_name,

            # 🔐 Subscription
            "is_paid": user.is_paid,
            "is_demo_user": user.is_demo_user,

            # 💰 Wallet
            "wallet_balance": user.wallet_balance,
            "total_collected": user.total_collected,
            "total_transferred": user.total_transferred,
            "manager_balance": user.manager_balance,

            # 📊 Counters
            "donation_count": user.donation_count,
            "expense_count": user.expense_count,
            "entry_count": user.entry_count,
        },
        status=status.HTTP_200_OK
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sync_donations(request):
    user = request.user

    if not user or not user.is_active:
        return Response(
            {"error": "User not active"},
            status=status.HTTP_403_FORBIDDEN
        )

    donations = Donation.objects.filter(
        mandal_name=user.mandal_name,
        is_deleted=False
    ).order_by("-date")

    serializer = DonationSerializer(donations, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sync_expenses(request):
    user = request.user

    if not user or not user.is_active:
        return Response(
            {"error": "User not active"},
            status=status.HTTP_403_FORBIDDEN
        )

    expenses = Expense.objects.filter(
        mandal_name=user.mandal_name,
        is_deleted=False
    ).order_by("-date")

    serializer = ExpenseSerializer(expenses, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_user(request):
    manager = request.user

    if manager.role != "Manager":
        return Response(
            {"error": "Only managers can update users"},
            status=403
        )

    data = request.data
    user_id = data.get("user_id")

    if not user_id:
        return Response(
            {"error": "user_id is required"},
            status=400
        )

    try:
        user = User.objects.get(id=user_id, mandal_name=manager.mandal_name)
    except User.DoesNotExist:
        return Response(
            {"error": "User not found"},
            status=404
        )

    if data.get("name"):
        user.name = data["name"]

    if data.get("password"):
        user.set_password(data["password"])

    user.save()

    return Response(
        {"message": "User updated successfully"},
        status=200
    )
