from django.urls import path

from . import views

urlpatterns = [
    path("", views.inspection_list, name="inspection-list"),
    path("<int:session_id>/", views.inspection_detail, name="inspection-detail"),
    path("approvals/", views.approval_queue, name="approval-queue"),
    path("approvals/<int:session_id>/", views.approval_detail, name="approval-detail"),
]
