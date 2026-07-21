from django.db import models


from stores.models import Store
from catalog.models import Product
from customers.models import Customer
from users.models import User



class WantedProduct(models.Model):

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='wanted_products')
    
    # Product that was in Our Store 
    product = models.ForeignKey(Product,
                                on_delete=models.SET_NULL,
                                null=True,
                                blank=True,
                                related_name='wanted_products'
                                )

    # Product that is not in our store
    product_name = models.CharField(max_length=255)

    brand = models.CharField(max_length=255, blank=True)

    size = models.CharField(max_length=20)

    wanted_count = models.PositiveBigIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    
    class Meta:
        unique_together = (
            'store',
            'product_name',
            'size',
        )
        verbose_name_plural = 'Wanted'


    def __str__(self):
        return f"{self.product_name} - {self.size}"
    



class WantedCustomerRequest(models.Model):
    wanted_product = models.ForeignKey(WantedProduct, on_delete=models.CASCADE, related_name='customer_requests')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer} - {self.wanted_product}"