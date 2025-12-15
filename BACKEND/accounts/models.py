"""
Modelos para la aplicación de cuentas de usuario.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Modelo de usuario personalizado que extiende AbstractUser.
    
    Incluye un campo adicional 'role' para diferenciar tipos de usuarios:
    - admin: Administradores del sistema
    - service: Usuarios de servicio/API
    - external: Usuarios externos (doctores, pacientes, etc.)
    """
    
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('service', 'Service User'),
        ('external', 'External User'),
    )
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='external',
        verbose_name='Rol del usuario',
        help_text='Tipo de usuario en el sistema'
    )
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
