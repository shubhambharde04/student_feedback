from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import Feedback, Subject, User, FeedbackWindow, Branch, Semester

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'enrollment_no', 'branch', 'semester')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make passwords optional so admin doesn't have to type them for students
        self.fields['username'].help_text = "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        if 'role' in self.fields:
            self.fields['role'].help_text = "Select 'student' to auto-set the password to the username."

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        
        # If neither password was provided but role is student, that's fine
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if user.role == 'student':
            user.set_password(user.username)
            user.enrollment_no = user.username
            user.is_first_login = True
        if commit:
            user.save()
        return user

class CustomUserAdmin(UserAdmin):
    model = User
    add_form = CustomUserCreationForm
    
    fieldsets = UserAdmin.fieldsets + (
        ('Role Information', {'fields': ('role', 'enrollment_no', 'branch', 'semester', 'is_first_login')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'enrollment_no', 'branch', 'semester'),
        }),
    )


class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'teacher', 'semester')
    filter_horizontal = ('branches', 'students')


admin.site.register(User, CustomUserAdmin)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Feedback)
admin.site.register(FeedbackWindow)
admin.site.register(Branch)
admin.site.register(Semester)
