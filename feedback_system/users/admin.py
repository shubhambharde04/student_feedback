from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Feedback, Subject, User

class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = UserAdmin.fieldsets + (
        ('Role Information', {'fields': ('role',)}),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Subject)
admin.site.register(Feedback)
