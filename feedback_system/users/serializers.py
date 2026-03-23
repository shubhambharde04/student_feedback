from rest_framework import serializers
from .models import User, Subject, Feedback, FeedbackWindow, Enrollment


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'first_name', 'last_name']


class SubjectSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    teacher_username = serializers.CharField(source='teacher.username', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True, default=None)
    semester_number = serializers.IntegerField(source='semester.number', read_only=True, default=None)

    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'code', 'teacher', 'teacher_name', 'teacher_username',
            'branch', 'branch_name', 'semester', 'semester_number',
        ]


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_enrollment_no = serializers.CharField(source='student.enrollment_no', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    assigned_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            'id', 'student', 'subject', 'assigned_by', 'created_at',
            'student_name', 'student_enrollment_no',
            'subject_name', 'subject_code', 'assigned_by_name',
        ]
        read_only_fields = ['assigned_by', 'created_at']

    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username

    def get_assigned_by_name(self, obj):
        if obj.assigned_by:
            return obj.assigned_by.get_full_name() or obj.assigned_by.username
        return None


class FeedbackSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    teacher_name = serializers.CharField(source='subject.teacher.get_full_name', read_only=True)

    class Meta:
        model = Feedback
        fields = [
            'id',
            'subject',
            'student',
            'punctuality_rating',
            'teaching_rating',
            'clarity_rating',
            'interaction_rating',
            'behavior_rating',
            'overall_rating',
            'comment',
            'sentiment',
            'created_at',
            'student_name',
            'subject_name',
            'subject_code',
            'teacher_name',
        ]
        read_only_fields = ['student', 'overall_rating', 'sentiment', 'created_at']

    def get_student_name(self, obj):
        request = self.context.get("request")
        if request and request.user.role == "hod":
            return obj.student.get_full_name() or obj.student.username
        return "Anonymous"

    def validate_comment(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Comment must be at least 10 characters long."
            )
        return value

    def validate(self, attrs):
        """Validate each rating is between 1 and 5."""
        rating_fields = [
            'punctuality_rating', 'teaching_rating',
            'clarity_rating', 'interaction_rating', 'behavior_rating'
        ]
        for field in rating_fields:
            val = attrs.get(field)
            if val is not None and (val < 1 or val > 5):
                raise serializers.ValidationError(
                    {field: "Rating must be between 1 and 5."}
                )
        return attrs


class FeedbackWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackWindow
        fields = ['id', 'start_date', 'end_date', 'is_active']


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

