from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # Core Auth & Profile
    login_view, logout_view, user_profile, change_password,
    
    # Dashboard & Performance (Legacy/Core)
    teacher_analytics, teacher_dashboard, teacher_performance,
    teacher_performance_charts,
    
    # HOD Operations
    hod_dashboard_overview, hod_teachers, hod_teacher_detail,
    hod_send_report, hod_send_custom_email, hod_analytics, hod_statistics,
    feedback_analysis, teacher_ranking, dashboard_analytics,
    hod_export_report_pdf, hod_report, hod_send_report_emails,
    
    # Academic Model Views
    DepartmentViewSet, BranchViewSet, SemesterViewSet, SubjectOfferingViewSet, 
    SubjectAssignmentViewSet, SubjectViewSet,
    get_student_subjects, teacher_assignments, assign_teacher,
    get_offering_details, student_dashboard,
    
    # Enrollment & Students
    enroll_student, bulk_enroll, list_enrollments, delete_enrollment, 
    enrollment_form_data, bulk_upload_students, bulk_delete_students, 
    bulk_enroll_students_semester,
    
    # Teacher Management
    manage_teachers, teacher_detail,
    
    # Analytics
    department_analytics, branch_comparison_analytics,
    
    # Utilities
    health_check, test_endpoint, close_feedback_session,
    student_subjects_v2,
)

# Session-based views
from .session_views import (
    FeedbackSessionViewSet, QuestionViewSet, FeedbackFormViewSet,
    SessionOfferingViewSet, get_active_feedback_form, submit_feedback,
    teacher_analytics as teacher_analytics_new, 
    hod_analytics as hod_analytics_new, 
    generate_report, hod_comprehensive_report,
    hod_department_comprehensive_report,
)

# Specialized Analytics
from .session_analytics import session_comparison_analytics
from .comprehensive_analytics import comprehensive_analytics, analytics_dashboard_data

# Student Import
from .student_import import (
    upload_students, get_student_upload_template, get_session_students,
    assign_student_to_session, remove_student_from_session
)

# Router Configuration
router = DefaultRouter()
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'branches', BranchViewSet, basename='branch')
router.register(r'semesters', SemesterViewSet, basename='semester')
router.register(r'offerings', SubjectOfferingViewSet, basename='offering')
router.register(r'assignments', SubjectAssignmentViewSet, basename='assignment')
router.register(r'sessions', FeedbackSessionViewSet, basename='session')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'feedback-forms', FeedbackFormViewSet, basename='feedback-form')
router.register(r'session-offerings', SessionOfferingViewSet, basename='session-offering')

urlpatterns = [
    # 1. Critical Session Feedback (Must be BEFORE generic routes)
    path('feedback/active-form/', get_active_feedback_form, name='get_active_feedback_form'),
    path('feedback/submit/', submit_feedback, name='submit_feedback_session'),
    
    # 2. Authentication
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/profile/', user_profile, name='profile'),
    path('auth/change-password/', change_password, name='change_password'),

    # 3. HOD Dashboard & Analytics
    path('hod/dashboard/', hod_dashboard_overview, name='hod_dashboard'),
    path('hod/dashboard-analytics/', dashboard_analytics, name='dashboard_analytics'),
    path('hod/teachers/', hod_teachers, name='hod_teachers'),
    path('hod/teacher/<int:pk>/', hod_teacher_detail, name='hod_teacher_detail'),
    path('hod/analytics/', hod_analytics, name='hod_analytics'),
    path('hod/statistics/', hod_statistics, name='hod_statistics'),
    path('hod/analysis/', feedback_analysis, name='feedback_analysis'),
    path('hod/teacher-ranking/', teacher_ranking, name='teacher_ranking'),
    path('hod/send-email/', hod_send_custom_email, name='hod_send_custom_email'),
    path('hod/send-report/', hod_send_report, name='hod_send_report'),
    path('hod/send-report-emails/', hod_send_report_emails, name='hod_send_report_emails'),
    path('hod/pdf-report/', hod_export_report_pdf, name='hod_export_report_pdf'),
    
    # 4. HOD Reports (Consolidated)
    path('hod/report/', hod_report, name='hod_report'),
    path('hod/teacher/<int:teacher_id>/report/', hod_comprehensive_report, name='hod_teacher_report'),
    path('hod/department/report/', hod_department_comprehensive_report, name='hod_department_report'),
    path('reports/generate/', generate_report, name='generate_report'),

    # 5. Teacher APIs
    path('teacher/dashboard/', teacher_dashboard, name='teacher_dashboard'),
    path('teacher/performance/', teacher_performance, name='teacher_performance'),
    path('teacher/performance-charts/', teacher_performance_charts, name='teacher_performance_charts'),
    path('teacher/analytics/', teacher_analytics, name='teacher_analytics'),
    path('teacher/assignments/', teacher_assignments, name='teacher_assignments'),

    # 6. Student APIs
    path('student/dashboard/', student_dashboard, name='student_dashboard'),
    path('student/subjects/', get_student_subjects, name='student_subjects'),
    
    # 7. Academic Management
    path('assign-teacher/', assign_teacher, name='assign_teacher'),
    path('offering/<int:pk>/', get_offering_details, name='get_offering_details'),
    path('sessions/<int:pk>/close/', close_feedback_session, name='close_feedback_session'),

    # 8. User & Enrollment Management
    path('users/teachers/', manage_teachers, name='manage_teachers'),
    path('users/teachers/<int:pk>/', teacher_detail, name='teacher_detail_api'),
    path('enrollments/', list_enrollments, name='list_enrollments'),
    path('enrollments/form-data/', enrollment_form_data, name='enrollment_form_data'),
    path('enrollments/enroll/', enroll_student, name='enroll_student'),
    path('enrollments/bulk-enroll/', bulk_enroll, name='bulk_enroll'),
    path('enrollments/<str:pk>/', delete_enrollment, name='delete_enrollment'),

    # 9. Bulk Student Operations (Consolidated)
    path('students/upload/', upload_students, name='upload_students'),
    path('students/upload-template/', get_student_upload_template, name='get_student_upload_template'),
    path('students/bulk-delete/', bulk_delete_students, name='bulk_delete_students'),
    path('students/bulk-enroll-semester/', bulk_enroll_students_semester, name='bulk_enroll_students_semester'),
    path('students/session/<int:session_id>/', get_session_students, name='get_session_students'),
    path('students/assign/', assign_student_to_session, name='assign_student_to_session'),
    path('students/session/<int:session_id>/remove/<int:student_id>/', remove_student_from_session, name='remove_student_from_session'),

    # 10. Specialized Analytics
    path('analytics/teacher/', teacher_analytics_new, name='teacher_analytics_new'),
    path('analytics/hod/', hod_analytics_new, name='hod_analytics_new'),
    path('analytics/department/', department_analytics, name='department_analytics'),
    path('analytics/branch-comparison/', branch_comparison_analytics, name='branch_comparison_analytics'),
    path('analytics/session-comparison/', session_comparison_analytics, name='session_comparison_analytics'),
    path('analytics/comprehensive/', comprehensive_analytics, name='comprehensive_analytics'),
    path('analytics/dashboard/', analytics_dashboard_data, name='analytics_dashboard_data'),

    # 11. Legacy & System
    path('student-subjects/', student_subjects_v2, name='student_subjects_legacy'),
    path('test/', test_endpoint, name='test'),
    path('health/', health_check, name='health'),
    
    # 12. Router URLs
    path('', include(router.urls)),
]
