from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # 🔐 AUTH
    path("login/", views.login),
    path("token/refresh/", TokenRefreshView.as_view()),

    # 💰 DONATIONS
    path("donations/create/", views.create_donation),
    path("donations/", views.get_donations),

    # 💸 EXPENSES
    path("expenses/create/", views.create_expense),
    path("expenses/", views.get_expenses),

    # 💼 WALLET
    path("wallet/create/", views.create_wallet_request),
    path("wallet/", views.get_wallet_requests),

    # 🔔 NOTIFICATIONS
    path("notifications/", views.get_notifications),
    
    # 🧑‍🤝‍🧑 USERS / SIGNUP
    path("register/", views.register),
    
    path("user/update-profile/", views.update_profile),
    
    path("user/change-password/", views.change_password),
    
    path("wallet/approve/", views.approve_wallet_request),
    path("wallet/reject/", views.reject_wallet_request),
    
    path("user/add/", views.add_user),
]