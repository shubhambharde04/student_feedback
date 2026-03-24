from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Branch(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Semester(models.Model):
    number = models.IntegerField(unique=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} ({self.number})"


class User(AbstractUser):

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('hod', 'HOD'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    is_first_login = models.BooleanField(default=True)
    
    # Student specific fields
    enrollment_no = models.CharField(max_length=50, unique=True, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    semester = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)

    branches = models.ManyToManyField(
        Branch,
        related_name="subjects",
        blank=True
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subjects"
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teacher'},
        related_name="subjects"
    )
    students = models.ManyToManyField(
        User,
        related_name="enrolled_subjects",
        limit_choices_to={'role': 'student'},
        blank=True
    )

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.name} ({self.code})"


class Feedback(models.Model):

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        related_name="feedbacks"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="feedbacks"
    )

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
    overall_rating = models.FloatField(default=0)

    comment = models.TextField()

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

    class Meta:
        unique_together = ('subject', 'student')
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
        self.overall_rating = round(sum(ratings) / len(ratings), 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.subject.name} - {self.overall_rating}"


class FeedbackWindow(models.Model):

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Feedback Window {self.start_date} - {self.end_date}"
