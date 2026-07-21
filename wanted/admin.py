from django.contrib import admin

from wanted.models import WantedProduct, WantedCustomerRequest


@admin.register(WantedProduct)
class WantedProductAdmin(admin.ModelAdmin):

    list_display = [
        "product_name",
        "size",
        "store",
        "wanted_count",
    ]


    readonly_fields = ["wanted_count"]



admin.site.register(WantedCustomerRequest)