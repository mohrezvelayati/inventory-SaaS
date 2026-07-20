from customers.models import Customer



def create_customer(*, store, full_name, phone_number):

    customer, created = Customer.objects.get_or_create(
        store=store,
        phone_number=phone_number,
        defaults={
            'full_name': full_name
        }
    )


    return customer