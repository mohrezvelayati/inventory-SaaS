from rest_framework import serializers
from users.models import User


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'phone_number', 'password']
        extra_kwargs = {'password': {'write_only': True}} # This ensures that the password is not returned in the response when creating a new user.

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
    

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'phone_number']



class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)