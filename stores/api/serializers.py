from rest_framework import serializers

from users.models import User
from stores.models import Store, StoreMembership, Permission, MembershipPermission



class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['id', 'name', 'created_at', 'updated_at']

    def validate(self, attrs):
        user = self.context['request'].user

        if user.memberships.exists():
            raise serializers.ValidationError(
                'You already belong to a store'
            )

        return attrs



class MembershipSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = StoreMembership
        fields = ['id', 'store', 'user', 'role', 'created_at', 'updated_at']

        read_only_fields = ['store', 'created_at', 'updated_at']

    def validate_user(self, user):
        if user.memberships.exists():
            raise serializers.ValidationError(
                'This user already belongs to a store'
            )

        return user


class MembershipRoleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreMembership
        fields = ['role']


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'code', 'name']
        read_only_fields = ['id', 'code', 'name']


class MembershipPermissionSerializer(serializers.ModelSerializer):
    permission_code = serializers.CharField(
        source='permission.code',
        read_only=True,
    )
    permission_name = serializers.CharField(
        source="permission.name",
        read_only=True,
    )
    class Meta:
        model = MembershipPermission
        fields = [
            'id',
            'permission',
            'permission_code',
            'permission_name',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'permission_code',
            'permission_name',
            'created_at',
        ]
