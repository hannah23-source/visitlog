
from django.contrib import admin
from .models import Visitor


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = (
        'first_name',
        'last_name',
        'contact_number',
        'purpose',
        'time_in',
    )
    search_fields = (
        'first_name',
        'last_name',
        'contact_number',
    )
    list_filter = ('time_in',)

