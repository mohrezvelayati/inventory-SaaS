from django.contrib import admin

from .models import Store, StoreInvitation, StoreMembership



admin.site.register(Store)
admin.site.register(StoreMembership)
admin.site.register(StoreInvitation)
