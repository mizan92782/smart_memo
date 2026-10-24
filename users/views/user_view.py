"""
users/views/user_view.py — Views for User App
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from users.models.user_mod import User
from users.serializers.user_ser import UserSerializer, RegisterSerializer, LoginSerializer
from users.services.user_service import UserService
from users.repositories.user_repository import UserRepository
from shared.responses.responses import custome_success_response, custome_error_response


class UserViewSet(viewsets.GenericViewSet):
    """ViewSet for User authentication and profile operations."""
    queryset = UserRepository.list_users()
    serializer_class = UserSerializer

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        full_name = serializer.validated_data.get('full_name', '')
        role = serializer.validated_data.get('role')

        if UserRepository.exists_by_email(email):
            return custome_error_response("A user with this email already exists.", status_code=status.HTTP_400_BAD_REQUEST)

        user, profile = UserService.register_user(email=email, password=password, full_name=full_name, role=role)
        return custome_success_response(
            message="User registered successfully.",
            data=UserSerializer(user).data,
            data_title="user",
            status_code=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        return custome_success_response(
            message="Profile retrieved.",
            data=UserSerializer(request.user).data,
            data_title="user"
        )
