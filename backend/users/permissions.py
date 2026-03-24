"""
Custom role-based permissions for the Student Feedback System.
"""
from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    """Allow access only to users with the 'student' role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'student'
        )


class IsTeacher(BasePermission):
    """Allow access only to users with the 'teacher' role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'teacher'
        )


class IsHOD(BasePermission):
    """Allow access only to users with the 'hod' role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'hod'
        )


class IsAdminOrHOD(BasePermission):
    """Allow access to users with 'admin' or 'hod' role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ('admin', 'hod')
        )

