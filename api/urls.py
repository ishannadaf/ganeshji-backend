from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView
from . import views

urlpatterns = [
    # 🔐 AUTH
    path("login/", views.login),
    path("token/", TokenObtainPairView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),

    # 💰 DONATIONS
    path("donations/create/", views.create_donation),
    path("donations/", views.get_donations),
    path("donations/delete/<str:client_id>/", views.delete_donation),

    # 💸 EXPENSES
    path("expenses/create/", views.create_expense),
    path("expenses/", views.get_expenses),
    path("expenses/delete/<str:client_id>/", views.delete_expense),

    # 💼 WALLET
    path("wallet/create/", views.create_wallet_request),
    path("wallet/", views.get_wallet_requests),
    path("wallet/approve/", views.approve_wallet_request),
    path("wallet/reject/", views.reject_wallet_request),

    # 🔔 NOTIFICATIONS
    path("notifications/", views.get_notifications),
    
    # 🧑‍🤝‍🧑 USERS / SIGNUP
    # path("register/", views.register),
    
    path("user/update-profile/", views.update_profile),
    path("user/change-password/", views.change_password),
    path("user/update/", views.update_user),
    path("user/list/", views.list_users),
    
    path("user/add/", views.add_user),
    path("ping/", views.ping),
    path("signup/", views.signup),
    
    
    path("sync/user/", views.sync_user, name="sync_user"),
    path("sync/donations/", views.sync_donations, name="sync_donations"),
    path("sync/expenses/", views.sync_expenses, name="sync_expenses"),
    
    
    path("collections/summary/", views.collection_summary),
    path("collections/user/<int:user_id>/", views.donations_by_user),

]