"""
users/views/user_view.py — Views for User App
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from users.models.user_mod import User
from users.models.profile_mod import Profile
from users.serializers.user_ser import (
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    ProfileUpdateSerializer,
    ProfileSerializer,
)
from users.services.user_service import UserService
from users.repositories.user_repository import UserRepository
from shared.responses.responses import custome_success_response, custome_error_response


from shared.throtling import LoginAnonThrottle, LoginUserThrottle, SignupAnonThrottle


class UserViewSet(viewsets.GenericViewSet):
    """ViewSet for User authentication and profile operations."""
    queryset = UserRepository.list_users()
    serializer_class = UserSerializer

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], throttle_classes=[SignupAnonThrottle])
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

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], throttle_classes=[LoginAnonThrottle, LoginUserThrottle])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user, token = UserService.login_user(email=email, password=password, request=request)
        return custome_success_response(
            message="Login successful.",
            data={
                "token": token,
                "user": UserSerializer(user).data,
            },
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        UserService.logout_user(request.user, request=request)
        return custome_success_response(
            message="Logout successful.",
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], throttle_classes=[LoginUserThrottle], url_path='change-password')
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        _, new_token = UserService.change_password(request.user, old_password, new_password)
        return custome_success_response(
            message="Password changed successfully.",
            data={"token": new_token},
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        return custome_success_response(
            message="Profile retrieved.",
            data=UserSerializer(request.user).data,
            data_title="user"
        )

    @action(detail=False, methods=['get', 'patch'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        if request.method == 'GET':
            profile, _ = Profile.objects.get_or_create(user=request.user)
            return custome_success_response(
                message="Profile retrieved.",
                data=ProfileSerializer(profile).data,
                data_title="profile"
            )

        serializer = ProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = UserService.update_profile(request.user, **serializer.validated_data)
        return custome_success_response(
            message="Profile updated successfully.",
            data=ProfileSerializer(profile).data,
            data_title="profile"
        )

