from django.contrib.auth import get_user_model
from rest_framework import generics, permissions

from apps.analytics.models import AuditLog
from core.tracing import trace_step

from .serializers import UserRegistrationSerializer, UserProfileSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        trace_step("RegisterView.perform_create()", "logic")
        user = serializer.save()
        trace_step(f"DB: User #{user.id} created (username={user.username})", "db")
        AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            entity_type="user",
            entity_id=user.id,
            user_id=user.id,
            changes={
                "username": user.username,
                "event": "user.registered",
            },
        )
        trace_step("DB: AuditLog entry created (user.registered)", "db")


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
