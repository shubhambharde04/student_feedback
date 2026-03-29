from django.utils import timezone
from rest_framework import serializers
from .models import (
    User, Subject, SubjectOffering, SubjectAssignment, 
    Feedback, FeedbackWindow, Branch, Semester, Department
)


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for academic departments"""
    class Meta:
        model = Department
        fields = ['id', 'name']


class BranchSerializer(serializers.ModelSerializer):
    """Serializer for academic branches"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = Branch
        fields = ['id', 'name', 'code', 'department', 'department_name']


class SemesterSerializer(serializers.ModelSerializer):
    """Serializer for academic semesters"""
    class Meta:
        model = Semester
        fields = ['id', 'number', 'name']


class SubjectSerializer(serializers.ModelSerializer):
    """Core subject information - NO branch/semester here"""
    class Meta:
        model = Subject
        fields = ['id', 'name', 'code', 'description', 'credits']


class SubjectOfferingSerializer(serializers.ModelSerializer):
    """CRITICAL: Subject + Branch + Semester combination"""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    subject_credits = serializers.IntegerField(source='subject.credits', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    branch_code = serializers.CharField(source='branch.code', read_only=True)
    semester_name = serializers.CharField(source='semester.name', read_only=True)
    semester_number = serializers.IntegerField(source='semester.number', read_only=True)
    
    # Teacher information (from assignment)
    teacher = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    teacher_id = serializers.SerializerMethodField()

    class Meta:
        model = SubjectOffering
        fields = [
            'id', 'subject', 'branch', 'semester', 'is_active', 'max_students',
            'subject_name', 'subject_code', 'subject_credits',
            'branch_name', 'branch_code',
            'semester_name', 'semester_number',
            'teacher', 'teacher_name', 'teacher_id'
        ]

    def get_teacher(self, obj):
        """Get teacher from active assignment"""
        # Using hasattr to safely check OneToOne relation
        assignment = getattr(obj, 'assignment', None)
        if assignment and assignment.is_active and assignment.teacher:
            return {
                'id': assignment.teacher.id,
                'username': assignment.teacher.username,
                'full_name': assignment.teacher.get_full_name() or assignment.teacher.username
            }
        return None

    def get_teacher_name(self, obj):
        """Get teacher name from active assignment"""
        teacher_info = self.get_teacher(obj)
        return teacher_info['full_name'] if teacher_info else None

    def get_teacher_id(self, obj):
        """Get teacher ID from active assignment"""
        teacher_info = self.get_teacher(obj)
        return teacher_info['id'] if teacher_info else None


class SubjectAssignmentSerializer(serializers.ModelSerializer):
    """Teacher assignment to subject offering"""
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    teacher_username = serializers.CharField(source='teacher.username', read_only=True)
    offering_details = SubjectOfferingSerializer(source='offering', read_only=True)

    class Meta:
        model = SubjectAssignment
        fields = [
            'id', 'offering', 'teacher', 'assigned_date', 'is_active',
            'teacher_name', 'teacher_username', 'offering_details'
        ]


class UserSerializer(serializers.ModelSerializer):
    """Base user serializer"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    student_branch = serializers.SerializerMethodField()
    student_semester = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'first_name', 'last_name',
            'enrollment_no', 'department', 'department_name',
            'student_branch', 'student_semester', 'is_first_login'
        ]

    def get_student_branch(self, obj):
        if obj.role == 'student' and hasattr(obj, 'student_profile'):
            return {'id': obj.student_profile.branch.id, 'name': obj.student_profile.branch.name, 'code': obj.student_profile.branch.code}
        return None

    def get_student_semester(self, obj):
        if obj.role == 'student' and hasattr(obj, 'student_profile'):
            return {'id': obj.student_profile.semester.id, 'name': obj.student_profile.semester.name, 'number': obj.student_profile.semester.number}
        return None


class FeedbackSerializer(serializers.ModelSerializer):
    """
    Robust student feedback serializer with strict validation logic.
    - Auto-assigns student from request.user
    - Validates feedback window
    - Validates student branch/semester
    - Validates teacher assignment existence
    - Prevents duplicate feedback
    """
    student_name = serializers.SerializerMethodField()
    subject_name = serializers.CharField(source='offering.subject.name', read_only=True)
    subject_code = serializers.CharField(source='offering.subject.code', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Feedback
        fields = [
            'id', 'offering', 'student',
            'punctuality_rating', 'teaching_rating', 'clarity_rating',
            'interaction_rating', 'behavior_rating', 'overall_rating',
            'comment', 'sentiment', 'created_at',
            'student_name', 'subject_name', 'subject_code', 'teacher_name'
        ]
        read_only_fields = ['student', 'overall_rating', 'sentiment', 'created_at']

    def get_student_name(self, obj):
        request = self.context.get("request")
        if request and request.user.role in ["hod", "admin", "teacher"]:
            return obj.student.get_full_name() or obj.student.username
        return "Anonymous"

    def get_teacher_name(self, obj):
        # Using a more robust lookup for the OneToOne relationship
        if not obj.offering:
            return "Unassigned"
            
        # Try both 'assignment' (specified related_name) and 'subjectassignment' (default)
        assignment = getattr(obj.offering, 'assignment', None)
        if not assignment:
            # Fallback to default name if related_name is somehow missing
            assignment = getattr(obj.offering, 'subjectassignment', None)
            
        if assignment and assignment.teacher:
            return assignment.teacher.get_full_name() or assignment.teacher.username
        return "Unassigned"


    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user if request else None
        if not user:
            raise serializers.ValidationError("Authentication required.")
        offering = attrs.get('offering')

        if user.role != 'student':
            raise serializers.ValidationError("Only students can submit feedback.")

        # 1. Validate Feedback Window
        from django.utils import timezone
        window = FeedbackWindow.objects.filter(is_active=True).first()  # type: ignore
        now = timezone.now()
        if not window:
            raise serializers.ValidationError("No active feedback window found.")
        if not (window.start_date <= now <= window.end_date):
            raise serializers.ValidationError("Feedback window is currently closed.")

        # 2. Validate Student Branch & Semester
        if not hasattr(user, 'student_profile') or offering.branch != user.student_profile.branch or offering.semester != user.student_profile.semester:
            raise serializers.ValidationError(
                "You can only submit feedback for subjects in your enrolled branch and semester."
            )

        # 3. Ensure Teacher Exists (OneToOne assignment)
        if not hasattr(offering, 'assignment'):
            raise serializers.ValidationError("Feedback cannot be submitted as no teacher is assigned to this subject.")

        # 4. Prevent Duplicate Feedback
        if Feedback.objects.filter(student=user, offering=offering).exists():  # type: ignore
            raise serializers.ValidationError("You have already submitted feedback for this subject.")

        # Assign student to attrs for save
        attrs['student'] = user
        return attrs



class FeedbackWindowSerializer(serializers.ModelSerializer):
    """Control when feedback is allowed"""
    class Meta:
        model = FeedbackWindow
        fields = ['id', 'start_date', 'end_date', 'is_active', 'description']


class LoginSerializer(serializers.Serializer):
    """User login serializer"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Password change serializer"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class SubjectOfferingCreateSerializer(serializers.ModelSerializer):
    """For HOD/Admin to create new subject offerings"""
    class Meta:
        model = SubjectOffering
        fields = ['subject', 'branch', 'semester', 'is_active', 'max_students']
    
    def validate(self, attrs):
        """Prevent duplicate offerings"""
        subject = attrs.get('subject')
        branch = attrs.get('branch')
        semester = attrs.get('semester')
        
        # Check if offering already exists
        if SubjectOffering.objects.filter(  # type: ignore
            subject=subject,
            branch=branch,
            semester=semester
        ).exists():
            raise serializers.ValidationError(
                "This subject is already offered in this branch and semester."
            )
        return attrs


class TeacherAssignmentSerializer(serializers.ModelSerializer):
    """For HOD/Admin to assign teachers to offerings"""
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    offering_details = SubjectOfferingSerializer(source='offering', read_only=True)

    class Meta:
        model = SubjectAssignment
        fields = ['id', 'offering', 'teacher', 'assigned_date', 'is_active', 'teacher_name', 'offering_details']
    
    def validate(self, attrs):
        """Prevent duplicate teacher assignments"""
        offering = attrs.get('offering')
        teacher = attrs.get('teacher')
        
        # Base query for duplicate checks
        assignments = SubjectAssignment.objects.all()  # type: ignore
        if self.instance:
            assignments = assignments.exclude(pk=self.instance.pk)
            
        # 1. Check if this teacher is already assigned to this offering
        if assignments.filter(
            offering=offering,
            teacher=teacher,
            is_active=True
        ).exists():
            raise serializers.ValidationError(
                "This teacher is already assigned to this subject offering."
            )
        
        # 2. Check if offering already has an active teacher
        if assignments.filter(
            offering=offering,
            is_active=True
        ).exists():
            raise serializers.ValidationError(
                "This subject offering already has an assigned teacher."
            )
        return attrs

