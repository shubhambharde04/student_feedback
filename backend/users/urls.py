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
    dashboard_analytics, hod_export_report_pdf,
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
    DepartmentViewSet, BranchViewSet, SemesterViewSet, SubjectOfferingViewSet, SubjectAssignmentViewSet,
    get_student_subjects, teacher_assignments, assign_teacher,
    get_offering_details, student_dashboard,
    close_feedback_session,

    # Teacher Management
    manage_teachers, teacher_detail,
)

# Import session-based views from separate file
from .session_views import (
    FeedbackSessionViewSet, QuestionViewSet, FeedbackFormViewSet,
    SessionOfferingViewSet,
    get_active_feedback_form, submit_feedback,
    teacher_analytics as teacher_analytics_new, 
    hod_analytics as hod_analytics_new, 
    generate_report, hod_comprehensive_report,
)

# Import session analytics
from .session_analytics import session_comparison_analytics

# Import comprehensive analytics
from .comprehensive_analytics import comprehensive_analytics, analytics_dashboard_data

# Import student import system
from .student_import import (
    upload_students, get_student_upload_template, get_session_students,
    assign_student_to_session, remove_student_from_session
)

router = DefaultRouter()
router.register(r'subjects', SubjectViewSet)
router.register(r'feedback', FeedbackViewSet)

# NEW: Register academic model viewsets
router.register(r'departments', DepartmentViewSet)
router.register(r'branches', BranchViewSet)
router.register(r'semesters', SemesterViewSet)
router.register(r'offerings', SubjectOfferingViewSet)
router.register(r'assignments', SubjectAssignmentViewSet)

# NEW: Register session-based viewsets
router.register(r'sessions', FeedbackSessionViewSet)
router.register(r'questions', QuestionViewSet)
router.register(r'feedback-forms', FeedbackFormViewSet)
router.register(r'session-offerings', SessionOfferingViewSet)

urlpatterns = [
    path('hod/pdf-report/', hod_export_report_pdf, name='hod_export_report_pdf'),
    # swallowed by the FeedbackViewSet router (feedback/<pk>/).
    path('feedback/active-form/', get_active_feedback_form, name='get_active_feedback_form'),
    path('feedback/submit/', submit_feedback, name='submit_feedback_session'),
    path('feedback/submit-legacy/', feedback_submit, name='feedback_submit'),

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
    path('hod/teacher/<int:pk>/report/', hod_teacher_report, name='hod_teacher_report'),
    path('hod/department/report/', hod_department_report, name='hod_department_report'),
    path('hod/send-report-emails/', hod_send_report_emails, name='hod_send_report_emails'),

    # Teacher
    path('teacher/analytics/', teacher_analytics, name='teacher_analytics'),
    path('teacher/dashboard/', teacher_dashboard, name='teacher_dashboard'),
    path('teacher/performance/', teacher_performance, name='teacher_performance'),
    path('teacher/performance-charts/', teacher_performance_charts, name='teacher_performance_charts'),

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
    path('subject-offerings/', SubjectOfferingViewSet.as_view({'get': 'list', 'post': 'create'}), name='subject_offerings_alias'),

    path('test/', test_endpoint, name='test'),
    path('health/', health_check, name='health'),


    # Teacher Management (HOD-only)
    path('users/teachers/', manage_teachers, name='manage_teachers'),
    path('users/teachers/<int:pk>/', teacher_detail, name='teacher_detail_api'),

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
    path('students/bulk-upload/', upload_students, name='bulk_upload_students'),
    path('students/bulk-delete/', bulk_delete_students, name='bulk_delete_students'),
    path('students/bulk-enroll-semester/', bulk_enroll_students_semester, name='bulk_enroll_students_semester'),
    
    # Session lifecycle
    path('sessions/<int:pk>/close/', close_feedback_session, name='close_feedback_session'),

    # Analytics
    path('analytics/department/', department_analytics, name='department_analytics'),
    path('analytics/branch-comparison/', branch_comparison_analytics, name='branch_comparison_analytics'),
    
    # NEW: Session-based feedback system
    # NOTE: feedback/active-form/ and feedback/submit/ moved to top of urlpatterns
    path('analytics/teacher/', teacher_analytics_new, name='teacher_analytics_new'),
    path('analytics/hod/', hod_analytics_new, name='hod_analytics_new'),
    path('analytics/session-comparison/', session_comparison_analytics, name='session_comparison_analytics'),
    path('analytics/comprehensive/', comprehensive_analytics, name='comprehensive_analytics'),
    path('analytics/dashboard/', analytics_dashboard_data, name='analytics_dashboard_data'),
    path('reports/generate/', generate_report, name='generate_report'),
    path('hod/teacher/<int:teacher_id>/comprehensive-report/', hod_comprehensive_report, name='hod_comprehensive_report'),
    
    # NEW: Student Import System
    path('students/upload/', upload_students, name='upload_students'),
    path('students/upload-template/', get_student_upload_template, name='get_student_upload_template'),
    path('students/session/<int:session_id>/', get_session_students, name='get_session_students'),
    path('students/assign/', assign_student_to_session, name='assign_student_to_session'),
    path('students/session/<int:session_id>/remove/<int:student_id>/', remove_student_from_session, name='remove_student_from_session'),
    
    # Legacy endpoints (keep for compatibility)
    path('subject-offerings/', SubjectOfferingViewSet.as_view({'get': 'list', 'post': 'create'}), name='subject_offerings_alias'),
    path('', include(router.urls)),
]

