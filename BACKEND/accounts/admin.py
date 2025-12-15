"""
Configuración del Django Admin para la aplicación de cuentas.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Configuración del admin para el modelo User personalizado.
    """
    
    # Campos a mostrar en la lista
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'role',
        'is_active',
        'is_staff',
        'date_joined'
    )
    
    # Filtros laterales
    list_filter = (
        'role',
        'is_staff',
        'is_active',
        'is_superuser',
        'date_joined'
    )
    
    # Campos de búsqueda
    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name'
    )
    
    # Ordenamiento por defecto
    ordering = ('-date_joined',)
    
    # Configuración de fieldsets para el formulario de edición
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('role',)
        }),
    )
    
    # Configuración de fieldsets para el formulario de creación
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('role',)
        }),
    )
