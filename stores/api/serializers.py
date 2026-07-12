from rest_framework import serializers

from users.models import User
from stores.models import Store, StoreMembership


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['id', 'name', 'created_at', 'updated_at']



class MembershipSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = StoreMembership
        fields = ['id', 'store', 'user', 'role', 'created_at', 'updated_at']