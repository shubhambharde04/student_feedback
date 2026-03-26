from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.core.exceptions import ValidationError


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
    """Academic semesters (1-8)"""
    id = models.AutoField(primary_key=True)
    number = models.IntegerField(unique=True, validators=[MinValueValidator(1), MaxValueValidator(8)])
    name = models.CharField(max_length=50)

    @property
    def year(self):
        """Derive year from semester: 1st/2nd sem -> year 1, 3rd/4th -> year 2, etc."""
        return (self.number + 1) // 2  # type: ignore

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


class Feedback(models.Model):
    """Student feedback for specific subject offering"""
    id = models.AutoField(primary_key=True)
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        related_name="feedbacks"
    )
    
    # CRITICAL: Link to SubjectOffering, not Subject directly
    offering = models.ForeignKey(
        SubjectOffering,
        on_delete=models.CASCADE,
        related_name="feedbacks",
        default=1
    )
    
    # Teacher is inferred from offering assignment
    @property
    def teacher(self):
        """Get teacher from the offering assignment"""
        assignment = self.offering.assignment if hasattr(self.offering, 'assignment') and self.offering.assignment.is_active else None  # type: ignore
        return assignment.teacher if assignment else None  # type: ignore

    # Individual rating fields (1-5)
    punctuality_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    teaching_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    clarity_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    interaction_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    behavior_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    # Auto-calculated average of 5 ratings
    overall_rating = models.FloatField(default=0)  # type: ignore

    comment = models.TextField(blank=True, null=True)

    # Sentiment analysis result
    SENTIMENT_CHOICES = (
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    )
    sentiment = models.CharField(
        max_length=10,
        choices=SENTIMENT_CHOICES,
        default='neutral'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # CRITICAL: Prevent duplicate feedback per student per offering
        unique_together = ('offering', 'student')
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Auto-calculate overall rating
        ratings = [
            self.punctuality_rating,
            self.teaching_rating,
            self.clarity_rating,
            self.interaction_rating,
            self.behavior_rating,
        ]
        self.overall_rating = round(sum(float(r) for r in ratings) / len(ratings), 2)  # type: ignore
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # type: ignore
        return f"{self.student.username} - {self.offering} - {self.overall_rating}"  # type: ignore


class FeedbackWindow(models.Model):
    """Control when feedback is allowed"""
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)  # type: ignore
    description = models.TextField(blank=True)

class StudentSemester(models.Model):
    """Bridge model to assign students to branches and semesters"""
    student = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    
    def __str__(self) -> str:  # type: ignore
        return f"{self.student.username} - {self.branch.code} - Sem {self.semester.number}"  # type: ignore

    class Meta:
        verbose_name = "Student-Semester Assignment"
        verbose_name_plural = "Student-Semester Assignments"
