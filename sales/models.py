from django.db import models
from stores.models import Store, StoreMembership
# import customer
from catalog.models import ProductVariant


class Sale(models.Model):

    class Channel(models.TextChoices):
        STORE = 'store', 'حضوری'
        INSTAGRAM = 'instagram', 'اینستاگرام'
        WEBSITE = 'website', 'وبسایت'
        REFERRAL = 'referral', 'معرفی توسط دوست'
        OTHER = 'other', 'سایر'

    class PaymentChoices(models.TextChoices):
        CASH = "cash", "نقد"
        CARD = "card", "کارت پوز"
        ONLINE = "online", "آنلاین(کارت به کارت)"


    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='sales')
    seller = models.ForeignKey(StoreMembership, on_delete=models.PROTECT)
    # customer = models.ForeignKey(Customer,on_delete=models.SET_NULL,null=True,blank=True,related_name="sales")
    chanel = models.CharField(max_length=20, choices=Channel.choices)
    payment_method = models.CharField(max_length=20, choices=PaymentChoices.choices)
    total_amount = models.DecimalField(max_digits=12, decimal_places=0)
    created_at = models.DateTimeField(auto_now_add=True)





class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT,related_name="sale_items")
    quantity = models.PositiveBigIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12,decimal_places=0)
    discount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    finl_price = models.DecimalField(max_digits=12, decimal_places=0)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.variant} - {self.quantity}"