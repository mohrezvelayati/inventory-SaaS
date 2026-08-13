from rest_framework import serializers

from customers.models import Customer
from stores.services import MembershipResolutionError, get_current_membership



class CustomerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer
        fields = [
            'id',
            'full_name',
            'phone_number',
            'created_at',
            'updated_at',
        ]

        read_only_fields = [
            'id',
            'created_at',
            'updated_at'
        ]


    def validate_phone_number(self, phone_number):
        """
        Validate that the phone number is unique across all customers.
        """
        request = self.context.get('request')

        if request is None or not request.user.is_authenticated:
            return phone_number

        try:
            membership = get_current_membership(request.user)
        except MembershipResolutionError:
            raise serializers.ValidationError("Store not found.")

        customers = Customer.objects.filter(store=membership.store, phone_number=phone_number)

        if self.instance is not None:
            customers = customers.exclude(id=self.instance.id)

        if customers.exists():
            raise serializers.ValidationError("A customer with this phone number already exists in this store.")

        return phone_number