"""
Serializers para la aplicación de cuentas de usuario.

Incluye serializers para:
- Lectura de información de usuarios
- Creación de usuarios con manejo seguro de passwords
"""

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer básico para el modelo User.
    
    Usado para lectura de información de usuarios.
    No incluye datos sensibles como password.
    """
    
    role_display = serializers.CharField(
        source='get_role_display',
        read_only=True
    )
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'role_display',
            'is_active',
            'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']
    
    def get_full_name(self, obj):
        """Retorna el nombre completo del usuario."""
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        return obj.username


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para creación de usuarios.
    
    Incluye validación de password y hash seguro.
    """
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='Contraseña del usuario (mínimo 8 caracteres)'
    )
    
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='Confirmación de contraseña'
    )
    
    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'password_confirm',
            'first_name',
            'last_name',
            'role'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }
    
    def validate_password(self, value):
        """Valida la contraseña usando los validadores de Django."""
        validate_password(value)
        return value
    
    def validate(self, data):
        """Valida que las contraseñas coincidan."""
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': 'Las contraseñas no coinciden.'
            })
        return data
    
    def create(self, validated_data):
        """
        Crea un usuario con password hasheado correctamente.
        """
        # Remover password_confirm ya que no es parte del modelo
        validated_data.pop('password_confirm', None)
        
        # Extraer password
        password = validated_data.pop('password')
        
        # Crear usuario sin password
        user = User.objects.create(**validated_data)
        
        # Establecer password (esto lo hashea automáticamente)
        user.set_password(password)
        user.save()
        
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para actualización de usuarios.
    
    No incluye password (se actualiza por separado).
    """
    
    class Meta:
        model = User
        fields = [
            'email',
            'first_name',
            'last_name',
            'role',
            'is_active'
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer para cambio de contraseña.
    """
    
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate_new_password(self, value):
        """Valida la nueva contraseña."""
        validate_password(value)
        return value
    
    def validate(self, data):
        """Valida que las contraseñas nuevas coincidan."""
        if data.get('new_password') != data.get('new_password_confirm'):
            raise serializers.ValidationError({
                'new_password_confirm': 'Las contraseñas no coinciden.'
            })
        return data
