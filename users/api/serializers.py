from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from stores.models import Permission, StoreMembership
from stores.services import NoMembershipError, get_current_membership
from users.models import User


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'phone_number', 'password']
        extra_kwargs = {'password': {'write_only': True}} # This ensures that the password is not returned in the response when creating a new user.

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class CurrentStoreSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)


class CurrentMembershipSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    role = serializers.CharField(read_only=True)
    store = CurrentStoreSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()

    @extend_schema_field(
        serializers.ListField(
            child=serializers.CharField()
        )
    )
    def get_permissions(self, membership):
        if membership.role == StoreMembership.RoleChoices.MANAGER:
            return list(
                Permission.objects
                .order_by('code')
                .values_list('code', flat=True)
            )

        return list(
            membership.permissions
            .order_by('permission__code')
            .values_list('permission__code', flat=True)
        )


class UserSerializer(serializers.ModelSerializer):
    membership = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'full_name',
            'phone_number',
            'membership',
        ]
        read_only_fields = ['id', 'membership']

    @extend_schema_field(
        CurrentMembershipSerializer(allow_null=True)
    )
    def get_membership(self, user):
        try:
            membership = get_current_membership(user)
        except NoMembershipError:
            return None

        return CurrentMembershipSerializer(membership).data



class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
