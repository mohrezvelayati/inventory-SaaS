from rest_framework import serializers

from customers.models import Customer




class CustomerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer
        fields = [
            'id',
            'full_name',
            'phone_number',
            'created_at'
        ]

        read_only_fields = ['id', 'created_at']