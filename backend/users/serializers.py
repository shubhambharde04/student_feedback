from django.utils import timezone
from rest_framework import serializers
from .models import (
    User, Subject, SubjectOffering, SubjectAssignment, 
    Branch, Semester, Department,
    # New models
    FeedbackSession, Question, FeedbackForm, FormQuestionMapping,
    SessionOffering, FeedbackResponse, Answer, SubmissionTracker, 
    StudentSemester
)


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for academic departments"""
    class Meta:
        model = Department
        fields = ['id', 'name']


class TeacherSerializer(serializers.ModelSerializer):
    """Serializer for Teachers (using User model)"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email', 'department', 'designation', 'is_active']


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
            'enrollment_no', 'department', 'department_name', 'designation',
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


class TeacherCreateSerializer(serializers.Serializer):
    """Serializer for creating teacher users from the frontend"""
    first_name = serializers.CharField(max_length=100, required=True)
    last_name = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=6)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False, allow_null=True
    )
    designation = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')

    def validate_email(self, value):
        """Reject duplicate email addresses"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        """Create a new teacher user with auto-generated username and hashed password"""
        email = validated_data['email']
        password = validated_data.pop('password')

        # Auto-generate username from email prefix
        base_username = email.split('@')[0].lower().replace(' ', '_')
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        user = User(
            username=username,
            email=email,
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role='teacher',
            department=validated_data.get('department'),
            designation=validated_data.get('designation', ''),
            is_first_login=True,
        )
        user.set_password(password)  # Hash the password
        user.save()
        return user


class TeacherListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing teachers"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    full_name = serializers.SerializerMethodField()
    subject_count = serializers.SerializerMethodField()

    assigned_departments = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'department', 'department_name', 'designation', 'is_active',
            'subject_count', 'assigned_departments', 'date_joined'
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_subject_count(self, obj):
        return obj.assignments.filter(is_active=True).count() if hasattr(obj, 'assignments') else 0

    def get_assigned_departments(self, obj):
        if not hasattr(obj, 'assignments'):
            return []
        # Get all distinct department IDs where this teacher is assigned a subject
        dept_ids = obj.assignments.filter(is_active=True).values_list('offering__branch__department_id', flat=True).distinct()
        return list(filter(None, dept_ids))


class StudentSemesterSerializer(serializers.ModelSerializer):
    """Serializer for a student's assigned branch and semester"""
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    branch_code = serializers.CharField(source='branch.code', read_only=True)
    semester_name = serializers.CharField(source='semester.name', read_only=True)
    semester_number = serializers.IntegerField(source='semester.number', read_only=True)

    class Meta:
        model = StudentSemester
        fields = [
            'id', 'student', 'branch', 'semester',
            'branch_name', 'branch_code', 'semester_name', 'semester_number'
        ]



# Legacy FeedbackSerializer and FeedbackWindowSerializer have been removed.
# The system now uses FeedbackResponseSerializer and FeedbackSubmissionSerializer below.


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


# ============================================================
# NEW SESSION-BASED ARCHITECTURE SERIALIZERS
# ============================================================

class FeedbackSessionSerializer(serializers.ModelSerializer):
    """Serializer for feedback sessions"""
    is_current = serializers.BooleanField(read_only=True)
    can_submit_feedback = serializers.BooleanField(read_only=True)
    offering_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FeedbackSession
        fields = [
            'id', 'name', 'type', 'year', 'start_date', 'end_date',
            'is_active', 'is_locked', 'is_closed', 'is_current', 'can_submit_feedback',
            'description', 'offering_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_offering_count(self, obj):
        return obj.offerings.count()


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for dynamic questions"""
    form_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = [
            'id', 'text', 'question_type', 'category', 'weight',
            'is_active', 'is_required', 'order', 'choices',
            'form_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_form_count(self, obj):
        return obj.form_mappings.count()


class QuestionListSerializer(serializers.ModelSerializer):
    """Lightweight question serializer for lists"""
    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'category', 'weight', 'is_required', 'order']


class FeedbackFormSerializer(serializers.ModelSerializer):
    """Serializer for feedback forms"""
    session_name = serializers.CharField(source='session.name', read_only=True)
    question_count = serializers.IntegerField(read_only=True)
    required_question_count = serializers.IntegerField(read_only=True)
    questions = serializers.SerializerMethodField()
    
    class Meta:
        model = FeedbackForm
        fields = [
            'id', 'session', 'session_name', 'name', 'description',
            'is_active', 'question_count', 'required_question_count',
            'questions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_questions(self, obj):
        """Get questions with their order for this form"""
        mappings = obj.questions.select_related('question').order_by('order')
        return [
            {
                'id': mapping.question.id,
                'text': mapping.question.text,
                'question_type': mapping.question.question_type,
                'category': mapping.question.category,
                'weight': mapping.question.weight,
                'is_required': mapping.is_required,
                'order': mapping.order
            }
            for mapping in mappings
        ]


class FormQuestionMappingSerializer(serializers.ModelSerializer):
    """Serializer for form-question mappings"""
    question_text = serializers.CharField(source='question.text', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)
    
    class Meta:
        model = FormQuestionMapping
        fields = ['id', 'form', 'question', 'question_text', 'question_type', 'order', 'is_required']


class SessionOfferingSerializer(serializers.ModelSerializer):
    """Serializer for session-specific offerings"""
    subject_name = serializers.CharField(source='base_offering.subject.name', read_only=True)
    subject_code = serializers.CharField(source='base_offering.subject.code', read_only=True)
    branch_name = serializers.CharField(source='base_offering.branch.name', read_only=True)
    branch_code = serializers.CharField(source='base_offering.branch.code', read_only=True)
    semester_name = serializers.CharField(source='base_offering.semester.name', read_only=True)
    semester_number = serializers.IntegerField(source='base_offering.semester.number', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    teacher_username = serializers.CharField(source='teacher.username', read_only=True)
    session_name = serializers.CharField(source='session.name', read_only=True)
    
    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name() or obj.teacher.username
        return None
    
    class Meta:
        model = SessionOffering
        fields = [
            'id', 'session', 'session_name', 'base_offering', 'teacher',
            'teacher_name', 'teacher_username', 'subject_name', 'subject_code',
            'branch_name', 'branch_code', 'semester_name', 'semester_number',
            'max_students', 'is_active', 'created_at'
        ]
        read_only_fields = ['created_at']


class AnswerSerializer(serializers.ModelSerializer):
    """Serializer for individual answers"""
    question_text = serializers.CharField(source='question.text', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)

    class Meta:
        model = Answer
        fields = ['id', 'question', 'question_text', 'question_type', 'rating', 'text_response', 'choice_response']


class FeedbackResponseSerializer(serializers.ModelSerializer):
    """Serializer for anonymous feedback responses"""
    answers = AnswerSerializer(many=True, read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    session_name = serializers.CharField(source='session.name', read_only=True)
    
    class Meta:
        model = FeedbackResponse
        fields = ['id', 'session', 'session_name', 'form', 'offering', 'teacher', 'teacher_name', 'overall_remark', 'sentiment_score', 'sentiment_label', 'submitted_at', 'answers']


class SubmissionTrackerSerializer(serializers.ModelSerializer):
    """Serializer for submission tracking"""
    class Meta:
        model = SubmissionTracker
        fields = ['id', 'student', 'session', 'offering', 'response_set']


class AnalyticsSerializer(serializers.Serializer):
    """Serializer for feedback analytics summary"""
    session_id = serializers.IntegerField()
    session_name = serializers.CharField()
    overall_avg = serializers.FloatField()
    total_submissions = serializers.IntegerField()


class SessionComparisonSerializer(serializers.Serializer):
    """Serializer for comparing two sessions"""
    session_1_avg = serializers.FloatField()
    session_2_avg = serializers.FloatField()
    trend = serializers.FloatField() 
    improvement_percentage = serializers.FloatField()
    trend_analysis = serializers.CharField()
