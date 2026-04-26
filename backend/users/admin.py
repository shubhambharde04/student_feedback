from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.shortcuts import render
from django.contrib import messages
from .models import (
    Subject, User, Branch, Semester,
    SubjectOffering, SubjectAssignment, StudentSemester,
    FeedbackSession, Question, FeedbackForm, SessionOffering,
    FeedbackResponse, Answer, SubmissionTracker, FeedbackSubmission
)

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'role', 'enrollment_no', 'department')

    def save(self, commit=True):
        user = super().save(commit=False)
        if user.role == 'student':
            user.set_password(user.username)
            user.enrollment_no = user.username
            user.is_first_login = True
        if commit:
            user.save()
        return user

class AssignSemesterForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Branch, Semester
        self.fields['branch'] = forms.ModelChoiceField(queryset=Branch.objects.all())  # type: ignore
        self.fields['semester'] = forms.ModelChoiceField(queryset=Semester.objects.all())  # type: ignore

def assign_students_to_semester(modeladmin, request, queryset):
    """Admin action to bulk assign students to a branch and semester."""
    if 'apply' in request.POST:
        form = AssignSemesterForm(request.POST)
        if form.is_valid():
            branch = form.cleaned_data['branch']
            semester = form.cleaned_data['semester']
            count = 0
            for student in queryset:
                if student.role == 'student':
                    # Update/Create the StudentSemester mapping
                    from .models import StudentSemester
                    StudentSemester.objects.update_or_create(  # type: ignore
                        student=student,
                        defaults={'branch': branch, 'semester': semester}
                    )
                    count += 1
            
            messages.success(request, f"{count} students assigned to {branch.code} Semester {semester.number} successfully!")
            return None
    else:
        # Pre-fill with the selected IDs
        form = AssignSemesterForm(initial={
            '_selected_action': request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
        })

    return render(request, 'admin/assign_semester.html', {
        'students': queryset,
        'form': form,
        'opts': User._meta if hasattr(User, '_meta') else None,  # type: ignore
    })

assign_students_to_semester.short_description = "Assign selected students to branch & semester"  # type: ignore

class CustomUserAdmin(UserAdmin):
    model = User
    add_form = CustomUserCreationForm
    list_display = ('username', 'email', 'role', 'department', 'get_branch')
    list_filter = UserAdmin.list_filter + ('role', 'department')
    actions = [assign_students_to_semester]

    def get_branch(self, obj):
        if hasattr(obj, 'student_semesters') and obj.student_semesters.exists():
            active_semester = obj.student_semesters.filter(is_active=True).first()
            if active_semester:
                return active_semester.branch.code
        return "-"
    get_branch.short_description = 'Branch'  # type: ignore
    
    fieldsets = UserAdmin.fieldsets + (  # type: ignore
        ('Role Information', {'fields': ('role', 'enrollment_no', 'department', 'is_first_login')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'enrollment_no', 'department'),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.role != 'student':
            if hasattr(form, 'base_fields') and 'department' in form.base_fields:  # type: ignore
                form.base_fields['department'].required = False  # type: ignore
        return form

admin.site.register(User, CustomUserAdmin)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'credits')
    search_fields = ('name', 'code')
    ordering = ('code',)

@admin.register(SubjectOffering)
class SubjectOfferingAdmin(admin.ModelAdmin):
    list_display = ('subject', 'branch', 'semester', 'is_active')
    list_filter = ('branch', 'semester', 'is_active')
    search_fields = ('subject__name', 'subject__code')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('subject', 'branch', 'semester')

@admin.register(SubjectAssignment)
class SubjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ('offering', 'teacher', 'semester', 'branch', 'assigned_date', 'is_active')
    list_filter = ('is_active', 'assigned_date', 'offering__semester', 'offering__branch')
    search_fields = (
        'offering__subject__name',
        'offering__subject__code',
        'teacher__username',
        'teacher__first_name',
        'teacher__last_name',
    )
    ordering = ('-assigned_date',)
    
    def semester(self, obj):
        return obj.offering.semester
    semester.admin_order_field = 'offering__semester'  # type: ignore
    semester.short_description = 'Semester'  # type: ignore
    
    def branch(self, obj):
        return obj.offering.branch
    branch.admin_order_field = 'offering__branch'  # type: ignore
    branch.short_description = 'Branch'  # type: ignore
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'offering__subject', 'offering__branch', 'offering__semester', 'teacher'
        )

@admin.register(StudentSemester)
class StudentSemesterAdmin(admin.ModelAdmin):
    list_display = ('student', 'branch', 'semester')
    list_filter = ('branch', 'semester')
    search_fields = ('student__username',)

admin.site.register(Branch)
admin.site.register(Semester)

# Session-Based Feedback Models
@admin.register(FeedbackSession)
class FeedbackSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'year', 'is_active', 'start_date', 'end_date')
    list_filter = ('is_active', 'type', 'year')
    search_fields = ('name',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text_truncated', 'question_type', 'category', 'is_active', 'order')
    list_filter = ('question_type', 'category', 'is_active')
    search_fields = ('text',)
    
    def text_truncated(self, obj):
        return obj.text[:100]
    text_truncated.short_description = 'Question Text'

@admin.register(FeedbackForm)
class FeedbackFormAdmin(admin.ModelAdmin):
    list_display = ('name', 'session')
    list_filter = ('session',)

@admin.register(SessionOffering)
class SessionOfferingAdmin(admin.ModelAdmin):
    list_display = ('base_offering', 'session', 'teacher', 'is_active')
    list_filter = ('session', 'is_active')

@admin.register(SubmissionTracker)
class SubmissionTrackerAdmin(admin.ModelAdmin):
    list_display = ('student', 'offering', 'session', 'created_at')
    list_filter = ('session', 'created_at')
    search_fields = ('student__username', 'student__enrollment_no')

@admin.register(FeedbackResponse)
class FeedbackResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'teacher', 'session', 'submitted_at')
    list_filter = ('session', 'submitted_at')
    search_fields = ('teacher__username', 'overall_remark')

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'rating', 'response_parent')
    list_filter = ('question__category', 'question__question_type')



@admin.register(FeedbackSubmission)
class FeedbackSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'offering', 'session', 'submitted_at', 'is_completed')
    list_filter = ('session', 'is_completed', 'submitted_at')
    search_fields = ('student__username', 'student__enrollment_no')

