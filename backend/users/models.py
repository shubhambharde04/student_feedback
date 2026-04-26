from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid


class Department(models.Model):
    """Academic Departments"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        ordering = ['name']


class Branch(models.Model):
    """Academic branches (IT, CSE, ECE, etc.)"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='branches', null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    class Meta:
        ordering = ['name']


class Semester(models.Model):
    """Academic semesters (1-6)"""
    id = models.AutoField(primary_key=True)
    number = models.IntegerField(unique=True, validators=[MinValueValidator(1), MaxValueValidator(6)])
    name = models.CharField(max_length=50)

    @property
    def year(self):
        """Derive year from semester: 1st/2nd sem -> year 1, 3rd/4th -> year 2, etc."""
        return (self.number + 1) // 2  # type: ignore

    @property
    def year_name(self):
        """Map semester number to year name (1st, 2nd, 3rd Year)"""
        if self.number in [1, 2]:
            return "1st Year"
        elif self.number in [3, 4]:
            return "2nd Year"
        elif self.number in [5, 6]:
            return "3rd Year"
        return "Unknown Year"

    def __str__(self) -> str:
        return f"{self.name} ({self.number})"

    class Meta:
        ordering = ['number']


class Subject(models.Model):
    """Core subject information - NO branch/semester here"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    credits = models.IntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(10)])  # type: ignore

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    class Meta:
        ordering = ['code']


class SubjectOffering(models.Model):
    """
    CRITICAL: This is the CORE of the academic model
    Represents when/where a subject is offered
    Links: Subject + Branch + Semester
    """
    id = models.AutoField(primary_key=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='offerings')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='offerings')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='offerings')
    
    # Additional offering-specific fields
    is_active = models.BooleanField(default=True)  # type: ignore
    max_students = models.IntegerField(default=60, validators=[MinValueValidator(1)])  # type: ignore

    class Meta:
        # CRITICAL: Prevent duplicate offerings
        unique_together = ('subject', 'branch', 'semester')
        ordering = ['branch', 'semester', 'subject']
    
    def __str__(self) -> str:  # type: ignore
        return f"{self.subject.code} | {self.branch.name} | Sem {self.semester.number}"  # type: ignore 



class SubjectAssignment(models.Model):
    """
    One teacher per SubjectOffering
    Same teacher can teach multiple offerings
    """

    id = models.AutoField(primary_key=True)

    # 🔥 CRITICAL CHANGE
    offering = models.OneToOneField(
        SubjectOffering,
        on_delete=models.CASCADE,
        related_name='assignment'
    )

    teacher = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='assignments',
        limit_choices_to={'role__in': ['teacher', 'hod']}
    )

    assigned_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # type: ignore

    class Meta:
        ordering = ['-assigned_date']

    def clean(self):
        # 1. Enforce One teacher per SubjectOffering (OneToOne check)
        # This is already partially handled by OneToOneField, but explicit clean is better for Admin
        if SubjectAssignment.objects.filter(offering=self.offering).exclude(pk=self.pk).exists():  # type: ignore
            raise ValidationError("This offering already has a teacher assigned.")

        # 2. 🔥 NEW: Enforce One subject per teacher per semester
        # A teacher can teach the same subject in multiple branches, but cannot teach a DIFFERENT subject in the same semester.
        other_assignments = SubjectAssignment.objects.filter(  # type: ignore
            teacher=self.teacher,
            offering__semester=self.offering.semester,  # type: ignore
            is_active=True
        ).exclude(pk=self.pk)

        for assignment in other_assignments:
            if assignment.offering.subject != self.offering.subject:  # type: ignore
                raise ValidationError(
                    f"Teacher {self.teacher.username} is already teaching '{assignment.offering.subject.name}' in this semester. "  # type: ignore
                    f"A teacher can only teach one subject per semester."
                )

    def save(self, *args, **kwargs):
        self.full_clean()  # 🔥 enforce validation
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # type: ignore
        return f"{self.teacher.get_full_name()} - {self.offering}"  # type: ignore




class User(AbstractUser):
    """Extended user model with role-based fields"""

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('hod', 'HOD'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)  # type: ignore
    is_first_login = models.BooleanField(default=True)  # type: ignore
    
    # Student specific fields
    enrollment_no = models.CharField(max_length=50, unique=True, null=True, blank=True)
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    designation = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., Lecturer, Senior Lecturer, Professor")

    class Meta(AbstractUser.Meta):  # type: ignore
        constraints = [
            models.UniqueConstraint(
                fields=['department'], 
                condition=models.Q(role='hod'), 
                name='unique_hod_per_department'
            )
        ]

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"

    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_teacher(self):
        return self.role == 'teacher'

    @property
    def is_hod(self):
        return self.role == 'hod'

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def student_profile(self):
        """Bridge property to provide student's active academic profile (replaces legacy StudentProfile model)"""
        if self.role != 'student':
            return None
        # Try to get the profile for the currently active session
        from .models import FeedbackSession
        active_session = FeedbackSession.objects.filter(is_active=True).first()
        if active_session:
            profile = self.student_semesters.filter(session=active_session).first()
            if profile:
                return profile
        # Fallback to any active semester record
        return self.student_semesters.filter(is_active=True).first()


# Legacy Feedback and FeedbackWindow models have been removed.
# The system now uses the session-based FeedbackResponse and FeedbackSubmission models below.


# ============================================================
# NEW SESSION-BASED ARCHITECTURE MODELS
# ============================================================

class FeedbackSession(models.Model):
    """
    Core session model - represents academic feedback periods
    e.g., "ODD 2024", "EVEN 2024"
    """
    SESSION_TYPES = (
        ('ODD', 'Odd Semester'),
        ('EVEN', 'Even Semester'),
    )
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, help_text="e.g., 'ODD 2024'")
    type = models.CharField(max_length=4, choices=SESSION_TYPES)
    year = models.IntegerField(help_text="Academic year")
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False, help_text="Once locked, no modifications allowed")
    is_closed = models.BooleanField(default=False, help_text="Once closed, no feedback submissions allowed")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-year', '-type']
        unique_together = ('type', 'year')
    
    def __str__(self):
        return f"{self.name} ({self.year})"
    
    def clean(self):
        if self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date")
    
    @property
    def is_current(self):
        """Check if this session is currently active based on dates"""
        from django.utils import timezone
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date and self.is_active and not self.is_closed
    
    @property
    def can_submit_feedback(self):
        """Check if feedback can be submitted for this session"""
        from django.utils import timezone
        today = timezone.now().date()
        return (
            self.is_active and 
            not self.is_locked and 
            not self.is_closed and
            self.start_date <= today <= self.end_date
        )
    
    def close_session(self):
        """Close the session - end feedback period"""
        self.is_active = False
        self.is_closed = True
        self.save(update_fields=['is_active', 'is_closed'])
    
    def start_session(self):
        """Start the session - begin feedback period"""
        if not self.is_closed:
            self.is_active = True
            self.save(update_fields=['is_active'])


class StudentSemester(models.Model):
    """
    Links students to their current branch and semester
    This model tracks student's academic progression across sessions
    """
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_semesters')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    session = models.ForeignKey(FeedbackSession, on_delete=models.CASCADE, related_name='student_sessions', null=True, blank=True)
    class_name = models.CharField(max_length=50, help_text="Class/Section name", default="A")
    roll_number = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('student', 'session')
        indexes = [
            models.Index(fields=['session', 'branch', 'semester']),
            models.Index(fields=['student', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.branch.name} Sem {self.semester.number} ({self.session.name})"
    
    def clean(self):
        # Validate that student has student role
        if self.student.role != 'student':
            raise ValidationError("Only students can be assigned to semesters")




class Question(models.Model):
    """
    Dynamic questions that can be created/updated by HOD
    """
    QUESTION_TYPES = (
        ('RATING', 'Rating (1-5)'),
        ('TEXT', 'Text Feedback'),
        ('MULTIPLE_CHOICE', 'Multiple Choice'),
    )
    
    QUESTION_CATEGORIES = (
        ('TEACHING', 'Teaching Quality'),
        ('PUNCTUALITY', 'Punctuality'),
        ('CLARITY', 'Clarity of Explanation'),
        ('INTERACTION', 'Student Interaction'),
        ('BEHAVIOR', 'Teacher Behavior'),
        ('GENERAL', 'General Feedback'),
    )
    
    id = models.AutoField(primary_key=True)
    text = models.TextField(help_text="Question text")
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='RATING')
    category = models.CharField(max_length=20, choices=QUESTION_CATEGORIES, blank=True)
    weight = models.FloatField(default=1.0, help_text="Weight for analytics calculation")
    is_active = models.BooleanField(default=True)
    is_required = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For multiple choice questions
    choices = models.JSONField(default=dict, blank=True, help_text="JSON object for multiple choice options")
    
    class Meta:
        ordering = ['order', 'category', 'text']
    
    def __str__(self):
        return f"{self.text[:50]}... ({self.question_type})"


class FeedbackForm(models.Model):
    """
    Dynamic feedback forms created per session
    """
    id = models.AutoField(primary_key=True)
    session = models.ForeignKey(FeedbackSession, on_delete=models.CASCADE, related_name='forms')
    name = models.CharField(max_length=200, help_text="Form name for identification")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-session__year', 'name']
        unique_together = ('session', 'name')
    
    def __str__(self):
        return f"{self.name} - {self.session.name}"
    
    @property
    def question_count(self):
        return self.questions.count()
    
    @property
    def required_question_count(self):
        return self.questions.filter(is_required=True).count()


class FormQuestionMapping(models.Model):
    """
    Many-to-many mapping between forms and questions
    Allows dynamic question assignment to forms
    """
    id = models.AutoField(primary_key=True)
    form = models.ForeignKey(FeedbackForm, on_delete=models.CASCADE, related_name='questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='form_mappings')
    order = models.IntegerField(default=0, help_text="Display order in this specific form")
    is_required = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ('form', 'question')
    
    def __str__(self):
        return f"{self.form.name} - {self.question.text[:30]}..."


class SessionOffering(models.Model):
    """
    Enhanced SubjectOffering linked to specific sessions
    This replaces the basic SubjectOffering for session-based tracking
    """
    id = models.AutoField(primary_key=True)
    session = models.ForeignKey(FeedbackSession, on_delete=models.CASCADE, related_name='offerings')
    base_offering = models.ForeignKey(SubjectOffering, on_delete=models.CASCADE, related_name='session_offerings')
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='session_offerings', limit_choices_to={'role__in': ['teacher', 'hod']})
    
    # Session-specific data
    max_students = models.IntegerField(default=60)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-session__year', 'base_offering']
        unique_together = ('session', 'base_offering')
    
    def __str__(self):
        return f"{self.base_offering} - {self.session.name}"


class FeedbackSubmission(models.Model):
    """
    LEGACY/COMPATIBILITY model for feedback submissions.
    Ensures no data loss while transitioning to anonymous FeedbackResponse.
    """
    id = models.AutoField(primary_key=True)
    session = models.ForeignKey('FeedbackSession', on_delete=models.CASCADE, related_name='submissions')
    form = models.ForeignKey('FeedbackForm', on_delete=models.CASCADE)
    offering = models.ForeignKey('SessionOffering', on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey('User', on_delete=models.CASCADE, related_name='submissions')
    
    # Anonymity tracking
    anonymous_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Status
    is_completed = models.BooleanField(default=False)
    completion_percentage = models.FloatField(default=0.0)
    
    # Metadata
    submitted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # Overall Feedback
    overall_remark = models.TextField(blank=True, null=True)
    sentiment_score = models.FloatField(default=0.0)
    sentiment_label = models.CharField(max_length=20, default='neutral')

    class Meta:
        unique_together = ('student', 'offering')

    def __str__(self):
        return f"Submission {self.id} by {self.student.username}"


class FeedbackResponse(models.Model):
    """
    ANONYMOUS container for a feedback submission.
    This model stores metadata and overall remarks but NO Student FK.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(FeedbackSession, on_delete=models.CASCADE, related_name='responses')
    form = models.ForeignKey(FeedbackForm, on_delete=models.CASCADE)
    offering = models.ForeignKey(SessionOffering, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedback_responses', limit_choices_to={'role__in': ['teacher', 'hod']})
    
    # Aggregated/Overall data
    overall_remark = models.TextField(blank=True, null=True)
    sentiment_score = models.FloatField(default=0.0)
    sentiment_label = models.CharField(max_length=20, default='neutral')
    
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response {self.id} for {self.teacher}"


class Answer(models.Model):
    """
    Individual answers linked to an anonymous FeedbackResponse.
    Supports rating, text, and choice types dynamically.
    """
    id = models.AutoField(primary_key=True)
    response_parent = models.ForeignKey(FeedbackResponse, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    
    rating = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    text_response = models.TextField(blank=True)
    choice_response = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Answer to {self.question.id} in {self.response_parent.id}"


class SubmissionTracker(models.Model):
    """
    SECURE TRACKER: Links Student to a Response for duplicate prevention.
    Stored separately to maintain practical anonymity in reports.
    """
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    session = models.ForeignKey(FeedbackSession, on_delete=models.CASCADE)
    offering = models.ForeignKey(SessionOffering, on_delete=models.CASCADE)
    response_set = models.OneToOneField(FeedbackResponse, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('student', 'offering') # Enforcement: One submission per student per subject
        indexes = [
            models.Index(fields=['student', 'session']),
        ]

    def __str__(self):
        return f"{self.student.username} submitted for {self.offering}"
