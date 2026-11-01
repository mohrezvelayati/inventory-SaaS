from django.db import models

from stores.models import Store



class Category(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('store', 'name')
        verbose_name_plural = 'Categories'




class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    category = models.ManyToManyField(Category, related_name='products', blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    



class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=50, null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=0)
    sale_price = models.DecimalField(max_digits=12, decimal_places=0)
    current_stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'size'],
                condition=models.Q(size__isnull=False),
                name='unique_product_variant_size',
            ),
            models.UniqueConstraint(
                fields=['product'],
                condition=models.Q(size__isnull=True),
                name='unique_sizeless_variant_per_product',
            ),
        ]

    @property
    def without_size(self):
        return self.size is None

    
    def __str__(self):
        size_label = self.size if self.size is not None else 'No size'
        return f"{self.product.name} - {size_label}"
