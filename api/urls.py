from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login),

    path("donations/create/", views.create_donation),
    path("donations/", views.get_donations),

    path("expenses/create/", views.create_expense),
    path("expenses/", views.get_expenses),

    path("wallet/create/", views.create_wallet_request),
    path("wallet/", views.get_wallet_requests),

    path("notifications/", views.get_notifications),
]
