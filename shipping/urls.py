from django.urls import path

from . import views

urlpatterns = [
    path("gate-passes/", views.gate_pass_list, name="gate-pass-list"),
]
