from rest_framework import serializers

from users.models import User
from stores.models import Store, StoreMembership


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