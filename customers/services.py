from django.core.exceptions import ValidationError

from customers.models import Customer



def create_customer(*, store, full_name, phone_number, gender=None, age=None):

    if gender is not None and gender not in Customer.GenderChoices.values:
        raise ValidationError('gender must be one of: ' + ', '.join(Customer.GenderChoices.values))

    # Look up only by (store, phone_number): gender/age are extra data applied
    # on creation, not identity keys. Passing them in the lookup would fail to
    # match an existing customer (e.g. one whose gender is already set) and
    # would create a duplicate that violates store+phone uniqueness.
    customer, created = Customer.objects.get_or_create(
        store=store,
        phone_number=phone_number,
        defaults={
            'full_name': full_name,
            'gender': gender,
            'age': age,
        }
    )

    return customer