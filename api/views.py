from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

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
    AppNotificationSerializer
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes

@api_view(["POST"])
def login(request):
    mobile = request.data.get("mobile")
    password = request.data.get("password")

    try:
        user = User.objects.get(mobile=mobile, password=password)
        return Response(UserSerializer(user).data)
    except User.DoesNotExist:
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_donation(request):
    serializer = DonationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_donations(request):
    mandal = request.GET.get("mandal")
    role = request.GET.get("role")
    user_id = request.GET.get("user_id")

    if role == "Manager":
        qs = Donation.objects.filter(mandal_name=mandal)
    else:
        qs = Donation.objects.filter(created_by_user_id=user_id)

    return Response(DonationSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_expense(request):
    serializer = ExpenseSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_expenses(request):
    mandal = request.GET.get("mandal")
    role = request.GET.get("role")
    user_id = request.GET.get("user_id")

    if role == "Manager":
        qs = Expense.objects.filter(mandal_name=mandal)
    else:
        qs = Expense.objects.filter(created_by_user_id=user_id)

    return Response(ExpenseSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_wallet_request(request):
    serializer = WalletTransferSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_wallet_requests(request):
    mandal = request.GET.get("mandal")
    status_param = request.GET.get("status", "Pending")

    qs = WalletTransfer.objects.filter(
        mandal_name=mandal,
        status=status_param
    )
    return Response(WalletTransferSerializer(qs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    user_id = request.GET.get("user_id")
    qs = AppNotification.objects.filter(to_user_id=user_id)
    return Response(AppNotificationSerializer(qs, many=True).data)
