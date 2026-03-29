from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # Existing
    SubjectViewSet, FeedbackViewSet, feedback_submit,
    login_view, logout_view, user_profile, change_password,
    student_subjects_v2,
    teacher_analytics, teacher_dashboard, teacher_performance,
    teacher_performance_charts,
    hod_report, hod_dashboard_overview, hod_teachers, hod_teacher_detail,
    hod_send_report, hod_send_custom_email, hod_analytics, hod_statistics,
    feedback_statistics, feedback_analysis, teacher_ranking,
    dashboard_analytics, export_report,
    feedback_window_manager, feedback_window_detail,
    current_feedback_window,
    health_check, test_endpoint,
    hod_teacher_report, hod_department_report, hod_send_report_emails,
    enroll_student, bulk_enroll, list_enrollments,
    delete_enrollment, enrollment_form_data,
    bulk_upload_students, bulk_delete_students, bulk_enroll_students_semester,
    
    # Department Analytics
    department_analytics,
    branch_comparison_analytics,
    
    # NEW ACADEMIC MODEL
    BranchViewSet, SemesterViewSet, SubjectOfferingViewSet, SubjectAssignmentViewSet,
    get_student_subjects, teacher_assignments, assign_teacher,
    get_offering_details, student_dashboard,
)

router = DefaultRouter()
router.register(r'subjects', SubjectViewSet)
router.register(r'feedback', FeedbackViewSet)

# NEW: Register academic model viewsets
router.register(r'branches', BranchViewSet)
router.register(r'semesters', SemesterViewSet)
router.register(r'offerings', SubjectOfferingViewSet)
router.register(r'assignments', SubjectAssignmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('test/', test_endpoint, name='test'),
    path('feedback/submit/', feedback_submit, name='feedback_submit'),
    path('health/', health_check, name='health'),

    # Auth
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/profile/', user_profile, name='profile'),
    path('auth/change-password/', change_password, name='change_password'),

    # Student - CORE ACADEMIC MODEL
    path('student/subjects/', get_student_subjects, name='student_subjects'),
    path('student/dashboard/', student_dashboard, name='student_dashboard'),

    # Teacher - CORE ACADEMIC MODEL
    path('teacher/assignments/', teacher_assignments, name='teacher_assignments'),

    # HOD/Admin - CORE ACADEMIC MODEL
    path('assign-teacher/', assign_teacher, name='assign_teacher'),
    path('offering/<int:pk>/', get_offering_details, name='get_offering_details'),

    # Legacy endpoints (keep for compatibility)
    path('student-subjects/', student_subjects_v2, name='student_subjects_legacy'),

    # Teacher
    path('teacher/analytics/', teacher_analytics, name='teacher_analytics'),
    path('teacher/dashboard/', teacher_dashboard, name='teacher_dashboard'),
    path('teacher/performance/', teacher_performance, name='teacher_performance'),
    path('teacher/performance-charts/', teacher_performance_charts, name='teacher_performance_charts'),

    # HOD
    path('hod/dashboard/', hod_dashboard_overview, name='hod_dashboard'),
    path('hod/dashboard-analytics/', dashboard_analytics, name='dashboard_analytics'),
    path('hod/teachers/', hod_teachers, name='hod_teachers'),
    path('hod/teacher/<int:pk>/', hod_teacher_detail, name='hod_teacher_detail'),
    path('hod/send-report/', hod_send_report, name='hod_send_report'),
    path('hod/send-email/', hod_send_custom_email, name='hod_send_custom_email'),
    path('hod/analytics/', hod_analytics, name='hod_analytics'),
    path('hod/statistics/', hod_statistics, name='hod_statistics'),
    path('hod/report/', hod_report, name='hod_report'),
    path('hod/analysis/', feedback_analysis, name='feedback_analysis'),
    path('hod/teacher-ranking/', teacher_ranking, name='teacher_ranking'),
    path('hod/export-report/', export_report, name='export_report'),
    path('hod/teacher/<int:pk>/report/', hod_teacher_report, name='hod_teacher_report'),
    path('hod/department/report/', hod_department_report, name='hod_department_report'),
    path('hod/send-report-emails/', hod_send_report_emails, name='hod_send_report_emails'),

    # Feedback window management
    path('hod/feedback-windows/', feedback_window_manager, name='feedback_window_manager'),
    path('hod/feedback-windows/<int:pk>/', feedback_window_detail, name='feedback_window_detail'),
    path('feedback-window/current/', current_feedback_window, name='current_feedback_window'),

    # Enrollment management
    path('enrollments/', list_enrollments, name='list_enrollments'),
    path('enrollments/form-data/', enrollment_form_data, name='enrollment_form_data'),
    path('enrollments/enroll/', enroll_student, name='enroll_student'),
    path('enrollments/bulk-enroll/', bulk_enroll, name='bulk_enroll'),
    path('enrollments/<str:pk>/', delete_enrollment, name='delete_enrollment'),
    
    # Bulk Operations
    path('students/bulk-upload/', bulk_upload_students, name='bulk_upload_students'),
    path('students/bulk-delete/', bulk_delete_students, name='bulk_delete_students'),
    path('students/bulk-enroll-semester/', bulk_enroll_students_semester, name='bulk_enroll_students_semester'),
    
    # Analytics
    path('analytics/department/', department_analytics, name='department_analytics'),
    path('analytics/branch-comparison/', branch_comparison_analytics, name='branch_comparison_analytics'),
]

