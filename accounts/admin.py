from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class Admin(BaseUserAdmin):
    """
    Custom admin for our User model.
    We extend Django's default UserAdmin so we keep all the
    nice password handling and permission UI.
    """

    # Columns shown in the user list
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "employee_id",
        "is_active",
        "is_staff",
    )

    list_filter = ("role", "is_staff", "is_active")

    search_fields = ("username", "email", "first_name", "last_name", "employee_id")

    ordering = ("username",)

    # How the edit form is organized
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "employee_id")}),
        ("Role & Permissions", {
            "fields": (
                "role",
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # Fields shown when creating a new user
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "email",
                "role",
                "employee_id",
                "password1",
                "password2",
                "is_staff",
                "is_active",
            ),
        }),
    )