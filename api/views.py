from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
import logging
from django.db.models import Sum
from .serializers import EventMasterSerializer, MandalEventSerializer
from .models import EventMaster, Mandal, MandalEvent, MandalSubscription, SubscriptionPlan, Mandal
from rest_framework.permissions import AllowAny
import razorpay
from django.conf import settings
from rest_framework.response import Response
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
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
    print(request.data)
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
        "user_id": user.id,
        "mandal_id": user.mandal.id,
        "role": user.role,
    },
    status=status.HTTP_200_OK
)

def calculate_user_wallet(user_id, mandal_event):
    donations = Donation.objects.filter(
        mandal_event=mandal_event,
        created_by_user_id=user_id,
        is_deleted=False
    ).aggregate(total=Sum("amount"))["total"] or 0

    expenses = Expense.objects.filter(
        mandal_event=mandal_event,
        created_by_user_id=user_id,
        is_deleted=False
    ).aggregate(total=Sum("amount"))["total"] or 0

    sent = WalletTransfer.objects.filter(
        from_user_id=user_id,
        status="Approved"
    ).aggregate(total=Sum("amount"))["total"] or 0

    return donations - expenses - sent

def calculate_manager_wallet(manager_id, mandal_event):
    base_wallet = calculate_user_wallet(manager_id, mandal_event)

    received = WalletTransfer.objects.filter(
        to_manager_id=manager_id,
        status="Approved"
    ).aggregate(total=Sum("amount"))["total"] or 0

    return base_wallet + received


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sync_wallet(request):
    event_id = request.GET.get("event_id")

    if not event_id:
        return Response({"error": "event_id required"}, status=400)

    try:
        mandal_event = MandalEvent.objects.get(
            id=event_id,
            user=request.user
        )
    except MandalEvent.DoesNotExist:
        return Response({"error": "Invalid event"}, status=403)

    user = request.user

    if user.role == "Manager":
        wallet = calculate_manager_wallet(user.id, mandal_event)
    else:
        wallet = calculate_user_wallet(user.id, mandal_event)

    return Response({
        "wallet_balance": wallet
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    event_id = request.GET.get("event_id")

    if not event_id:
        return Response({"error": "event_id required"}, status=400)

    try:
        mandal_event = MandalEvent.objects.get(
            id=event_id,
            user=request.user
        )
    except MandalEvent.DoesNotExist:
        return Response({"error": "Invalid event"}, status=403)

    total_collection = Donation.objects.filter(
        mandal_event=mandal_event,
        is_deleted=False
    ).aggregate(total=Sum("amount"))["total"] or 0

    total_expense = Expense.objects.filter(
        mandal_event=mandal_event,
        is_deleted=False
    ).aggregate(total=Sum("amount"))["total"] or 0

    return Response({
        "total_collection": total_collection,
        "total_expense": total_expense,
        "net_balance": total_collection - total_expense
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    data = request.data

    if User.objects.filter(mobile=data.get("mobile")).exists():
        return Response(
            {"error": "Mobile already registered"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 🔥 Create or get Mandal
    mandal, created = Mandal.objects.get_or_create(
        name=data["mandal_name"]
    )

    user = User.objects.create_user(
        mobile=data["mobile"],
        password=data["password"],
        name=data["name"],
        mandal=mandal,
        role=data.get("role") or "Manager"
    )

    refresh = RefreshToken.for_user(user)

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user_id": user.id,
        "mandal_id": mandal.id,
        "role": user.role,
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
    mandal_event_id = request.data.get("mandal_event")
    print("Received donation creation request for event_id:", request.data)
    if not mandal_event_id:
        return Response({"error": "mandal_event is required"}, status=400)

    try:
        mandal_event = MandalEvent.objects.get(
            id=mandal_event_id,
            user=request.user  # ensures event belongs to this manager
        )
    except MandalEvent.DoesNotExist:
        return Response({"error": "Invalid event"}, status=403)

    serializer = DonationSerializer(
        data=request.data,
        context={"request": request}
    )

    if serializer.is_valid():
        serializer.save(
        mandal_event=mandal_event,
        mandal=request.user.mandal   # 🔥 ADD THIS
        )
        return Response(serializer.data, status=201)

    return Response(serializer.errors, status=400)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_donations(request):
    event_id = request.GET.get("event_id")

    if not event_id:
        return Response({"error": "event_id required"}, status=400)

    try:
        mandal_event = MandalEvent.objects.get(
            id=event_id,
            user=request.user
        )
    except MandalEvent.DoesNotExist:
        return Response({"error": "Invalid event"}, status=403)

    if request.user.role == "Manager":
        qs = Donation.objects.filter(
            mandal_event=mandal_event,
            is_deleted=False
        )
    else:
        qs = Donation.objects.filter(
            mandal_event=mandal_event,
            created_by_user_id=request.user.id,
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
    mandal_event_id = request.data.get("mandal_event")

    if not mandal_event_id:
        return Response({"error": "mandal_event is required"}, status=400)

    try:
        mandal_event = MandalEvent.objects.get(
            id=mandal_event_id,
            user=request.user  # ensures event belongs to this manager
        )
    except MandalEvent.DoesNotExist:
        return Response({"error": "Invalid event"}, status=403)

    serializer = ExpenseSerializer(
        data=request.data,
        context={"request": request}
    )

    if serializer.is_valid():
        serializer.save(
        mandal_event=mandal_event,
        mandal=request.user.mandal   # 🔥 ADD THIS
        )
        return Response(serializer.data, status=201)

    return Response(serializer.errors, status=400)

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
        mobile=request.user.mobile
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

    required = ["name", "mobile", "password"]
    for field in required:
        if not data.get(field):
            return Response(
                {"error": f"{field} is required"},
                status=400
            )

    # 🔥 Use relational mandal instead of string
    if User.objects.filter(
        mobile=data["mobile"],
        mandal=manager.mandal
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
        mandal=manager.mandal   # ✅ FIXED
    )

    return Response(
        {
            "message": "User added successfully",
            "user": {
                "id": user.id,
                "name": user.name,
                "mobile": user.mobile,
                "role": user.role,
                "mandal_id": manager.mandal.id,
                "mandal_name": manager.mandal.name,
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
    event_id = request.GET.get("event_id")

    if not event_id:
        return Response({"error": "event_id required"}, status=400)

    try:
        mandal_event = MandalEvent.objects.get(
            id=event_id,
            user=request.user
        )
    except MandalEvent.DoesNotExist:
        return Response({"error": "Invalid event"}, status=403)

    donations = Donation.objects.filter(
        mandal_event=mandal_event,
        is_deleted=False
    )

    serializer = DonationSerializer(donations, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sync_expenses(request):
    event_id = request.GET.get("event_id")

    if not event_id:
        return Response({"error": "event_id required"}, status=400)

    try:
        mandal_event = MandalEvent.objects.get(
            id=event_id,
            user=request.user
        )
    except MandalEvent.DoesNotExist:
        return Response({"error": "Invalid event"}, status=403)

    expenses = Expense.objects.filter(
        mandal_event=mandal_event,
        is_deleted=False
    )

    serializer = ExpenseSerializer(expenses, many=True)
    return Response(serializer.data)


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
    print("Updating user_id:", user_id, "with data:", data)
    if not user_id:
        return Response(
            {"error": "user_id is required"},
            status=400
        )

    try:
        # 🔥 FIX: use relational mandal instead of mandal_name
        user = User.objects.get(
            id=user_id,
            mandal=manager.mandal
        )
    except User.DoesNotExist:
        return Response(
            {"error": "User not found"},
            status=404
        )

    # Optional: prevent manager from editing another manager
    if user.role == "Manager" and user.id != manager.id:
        return Response(
            {"error": "Cannot modify another manager"},
            status=403
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_events(request):
    events = EventMaster.objects.all()
    serializer = EventMasterSerializer(events, many=True)
    print(serializer.data)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_mandal_event(request):
    if request.user.role != "Manager":
        return Response({"error": "Only manager can create event"}, status=403)

    event_id = request.data.get('event_id')

    if not event_id:
        return Response({"error": "event_id required"}, status=400)

    if MandalEvent.objects.filter(user=request.user, event_id=event_id).exists():
        return Response({"error": "Event already created"}, status=400)

    MandalEvent.objects.create(
        user=request.user,
        event_id=event_id
    )

    return Response({"message": "Event created successfully"})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_events(request):
    events = MandalEvent.objects.filter(user=request.user)
    serializer = MandalEventSerializer(events, many=True)
    return Response(serializer.data)


client = razorpay.Client(auth=(settings.RAZORPAY_KEY, settings.RAZORPAY_SECRET))

@csrf_exempt
@api_view(['POST'])
def create_subscription_order(request):

    amount = 99900

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return Response({
        "order_id": order["id"],
        "amount": amount
    })
    
    
@csrf_exempt
@api_view(['POST'])
def verify_and_activate_subscription(request):

    order_id = request.data.get("order_id")
    payment_id = request.data.get("payment_id")
    signature = request.data.get("signature")
    mandal_id = request.data.get("mandal_id")
    user_upi_id = request.data.get("upi_id")

    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        })
    except:
        return Response({"error": "Payment verification failed"}, status=400)

    mandal = Mandal.objects.get(id=mandal_id)
    plan = SubscriptionPlan.objects.get(name="GOLD")

    # deactivate old subscription
    MandalSubscription.objects.filter(
        mandal=mandal,
        is_active=True
    ).update(is_active=False)

    start = timezone.now()
    end = start + timedelta(days=365)

    MandalSubscription.objects.create(
        mandal=mandal,
        plan=plan,
        start_date=start,
        end_date=end,
        payment_transaction_id=payment_id,
        user_upi_id=user_upi_id,
        is_active=True
    )

    return Response({"message": "Subscription Activated"})


@api_view(['GET'])
def get_subscription_status(request, mandal_id):

    # mandal_id = request.GET.get("mandal_id")
    print(mandal_id)
    try:
        sub = MandalSubscription.objects.filter(
            mandal_id=mandal_id,
            is_active=True
        ).latest("created_at")

        if not sub:
            return Response({
            "is_active": False
            })
        elif sub.end_date < timezone.now():
            sub.is_active = False
            sub.save()
        return Response({
            "is_active": sub.is_active,
            "plan": sub.plan.name,
            "start_date": sub.start_date,
            "end_date": sub.end_date
        })
    except:
        return Response({
            "is_active": False
        })
        
        
@api_view(['POST'])
def validate_session(request):

    user_id = request.data.get("user_id")

    try:
        user = User.objects.get(id=user_id)

        return Response({
            "valid": True,
            "role": user.role,
            "mandal_id": user.mandal_id
        })

    except User.DoesNotExist:
        return Response({
            "valid": False
        })