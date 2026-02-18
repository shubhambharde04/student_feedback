from rest_framework import viewsets
from .models import Subject, Feedback
from .serializers import SubjectSerializer, FeedbackSerializer
from rest_framework.permissions import IsAuthenticated


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]


class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # HOD sees everything
        if user.role == 'hod':
            return Feedback.objects.all()

        # Teacher sees feedback of their subjects
        if user.role == 'teacher':
            return Feedback.objects.filter(subject__teacher=user)

        # Student sees only their feedback
        if user.role == 'student':
            return Feedback.objects.filter(student=user)

        return Feedback.objects.none()
