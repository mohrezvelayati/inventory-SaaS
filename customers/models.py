from django.db import models


from stores.models import Store



class Customer(models.Model):

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='customers')
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=11)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        unique_together = ('store', 'phone_number')


    def __str__(self):
        return self.full_name