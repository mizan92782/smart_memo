"""
users/serializers/user_ser.py — DRF Serializers for User
"""
from rest_framework import serializers
from users.models.user_mod import User
from users.models.profile_mod import Profile


from shared.enums.enums import UserRoleEnum


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['full_name', 'phone_number', 'address', 'avatar']


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'role', 'is_active', 'created_at', 'profile']


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(required=False, default="")
    role = serializers.ChoiceField(choices=UserRoleEnum.choices, required=False, default=UserRoleEnum.CUSTOMER)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, min_length=8, required=True)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['full_name', 'phone_number', 'address', 'avatar']
        extra_kwargs = {
            'full_name': {'required': False},
            'phone_number': {'required': False},
            'address': {'required': False},
            'avatar': {'required': False, 'allow_null': True},
        }

