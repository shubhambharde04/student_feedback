from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SubjectViewSet, FeedbackViewSet,
    login_view, logout_view, user_profile,
    student_subjects,
    teacher_analytics, teacher_dashboard, teacher_performance,
    teacher_performance_charts,
    hod_report, hod_dashboard_overview, hod_teachers, hod_teacher_detail,
    hod_send_report, hod_send_custom_email, hod_analytics, hod_statistics,
    feedback_statistics, feedback_analysis, teacher_ranking,
    dashboard_analytics, export_report,
    feedback_window_manager, feedback_window_detail,
    current_feedback_window,
    health_check, test_endpoint,
)

router = DefaultRouter()
router.register(r'subjects', SubjectViewSet)
router.register(r'feedback', FeedbackViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('test/', test_endpoint, name='test'),
    path('health/', health_check, name='health'),

    # Auth
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/profile/', user_profile, name='profile'),

    # Student
    path('student-subjects/', student_subjects, name='student_subjects'),

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

    # Feedback window management
    path('hod/feedback-windows/', feedback_window_manager, name='feedback_window_manager'),
    path('hod/feedback-windows/<int:pk>/', feedback_window_detail, name='feedback_window_detail'),
    path('feedback-window/current/', current_feedback_window, name='current_feedback_window'),
]
