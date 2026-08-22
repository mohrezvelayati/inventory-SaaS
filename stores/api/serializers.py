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
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
    )
    username = serializers.CharField(source='user.username', read_only=True)
    user_full_name = serializers.CharField(
        source='user.full_name',
        read_only=True,
    )
    invite_username = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = StoreMembership
        fields = [
            'id',
            'store',
            'user',
            'username',
            'user_full_name',
            'invite_username',
            'role',
            'created_at',
            'updated_at',
        ]

        read_only_fields = ['store', 'created_at', 'updated_at']

    def validate_user(self, user):
        if user.memberships.exists():
            raise serializers.ValidationError(
                'This user already belongs to a store'
            )

        return user

    def validate(self, attrs):
        user = attrs.get('user')
        invite_username = attrs.pop('invite_username', '').strip()

        if user is not None and invite_username:
            raise serializers.ValidationError({
                'invite_username': 'Provide user or invite_username, not both.'
            })

        if user is None:
            if not invite_username:
                raise serializers.ValidationError({
                    'invite_username': 'This field is required.'
                })
            try:
                user = User.objects.get(username=invite_username)
            except User.DoesNotExist as error:
                raise serializers.ValidationError({
                    'invite_username': 'No user exists with this username.'
                }) from error
            self.validate_user(user)
            attrs['user'] = user

        return attrs


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
