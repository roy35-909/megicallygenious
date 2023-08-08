from django.urls import path
from . import views

urlpatterns = [
    path('', views.Index, name="index"),
    path('success-page/', views.Success, name="success")
]
