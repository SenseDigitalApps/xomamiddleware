"""
Script de verificación del setup local.

Ejecutar después de:
- Instalar dependencias
- Aplicar migraciones
- Iniciar el servidor

Uso:
    python scripts/verify_setup.py
"""

import sys
import os

# Agregar el directorio padre al path para importar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verify_setup():
    """Verifica el setup del proyecto."""
    
    print("=" * 60)
    print("🔍 VERIFICACIÓN DEL SETUP LOCAL - MEET MIDDLEWARE")
    print("=" * 60)
    print()
    
    errors = []
    warnings = []
    success = []
    
    # 1. Verificar Django
    print("📦 Verificando Django...")
    try:
        import django
        print(f"   ✅ Django instalado: v{django.get_version()}")
        success.append("Django")
    except ImportError:
        print("   ❌ Django no está instalado")
        errors.append("Django no instalado")
    
    # 2. Verificar Django REST Framework
    print("📦 Verificando Django REST Framework...")
    try:
        import rest_framework
        print(f"   ✅ DRF instalado")
        success.append("DRF")
    except ImportError:
        print("   ❌ Django REST Framework no está instalado")
        errors.append("DRF no instalado")
    
    # 3. Verificar drf-spectacular
    print("📦 Verificando drf-spectacular...")
    try:
        import drf_spectacular
        print(f"   ✅ drf-spectacular instalado")
        success.append("drf-spectacular")
    except ImportError:
        print("   ❌ drf-spectacular no está instalado")
        errors.append("drf-spectacular no instalado")
    
    # 4. Verificar Google APIs
    print("📦 Verificando Google API Client...")
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        print(f"   ✅ Google API Client instalado")
        success.append("Google API Client")
    except ImportError:
        print("   ❌ Google API Client no está instalado")
        errors.append("Google API Client no instalado")
    
    # 5. Verificar Celery y Redis
    print("📦 Verificando Celery...")
    try:
        import celery
        print(f"   ✅ Celery instalado")
        success.append("Celery")
    except ImportError:
        print("   ⚠️  Celery no está instalado (opcional)")
        warnings.append("Celery no instalado")
    
    print("📦 Verificando Redis...")
    try:
        import redis
        print(f"   ✅ Redis client instalado")
        success.append("Redis")
    except ImportError:
        print("   ⚠️  Redis no está instalado (opcional)")
        warnings.append("Redis no instalado")
    
    # 6. Verificar psycopg2
    print("📦 Verificando psycopg2 (PostgreSQL driver)...")
    try:
        import psycopg2
        print(f"   ✅ psycopg2 instalado")
        success.append("psycopg2")
    except ImportError:
        print("   ⚠️  psycopg2 no está instalado (se usará SQLite)")
        warnings.append("psycopg2 no instalado - usando SQLite")
    
    print()
    print("=" * 60)
    
    # 7. Verificar configuración de Django
    print("⚙️  Verificando configuración de Django...")
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
        import django
        django.setup()
        
        from django.conf import settings
        print(f"   ✅ Settings cargados correctamente")
        print(f"   - DEBUG: {settings.DEBUG}")
        print(f"   - ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
        print(f"   - DATABASE ENGINE: {settings.DATABASES['default']['ENGINE']}")
        success.append("Django Settings")
    except Exception as e:
        print(f"   ❌ Error al cargar settings: {e}")
        errors.append(f"Settings error: {e}")
    
    # 8. Verificar apps instaladas
    print("📱 Verificando apps del proyecto...")
    try:
        from django.apps import apps
        project_apps = ['accounts', 'meetings', 'integrations', 'core']
        for app_name in project_apps:
            try:
                apps.get_app_config(app_name)
                print(f"   ✅ App '{app_name}' registrada")
                success.append(f"App {app_name}")
            except:
                print(f"   ❌ App '{app_name}' no registrada")
                errors.append(f"App {app_name} no registrada")
    except Exception as e:
        print(f"   ❌ Error verificando apps: {e}")
        errors.append(f"Apps error: {e}")
    
    # 9. Verificar modelos
    print("📊 Verificando modelos...")
    try:
        from accounts.models import User
        from meetings.models import Meeting, Participant, MeetingRecording
        print(f"   ✅ Modelo User importado")
        print(f"   ✅ Modelo Meeting importado")
        print(f"   ✅ Modelo Participant importado")
        print(f"   ✅ Modelo MeetingRecording importado")
        success.append("Modelos")
    except Exception as e:
        print(f"   ❌ Error al importar modelos: {e}")
        errors.append(f"Modelos error: {e}")
    
    # 10. Verificar serializers
    print("📝 Verificando serializers...")
    try:
        from meetings.serializers import MeetingCreateSerializer, MeetingSerializer
        from accounts.serializers import UserSerializer
        print(f"   ✅ Serializers importados correctamente")
        success.append("Serializers")
    except Exception as e:
        print(f"   ❌ Error al importar serializers: {e}")
        errors.append(f"Serializers error: {e}")
    
    # 11. Verificar views
    print("🌐 Verificando views...")
    try:
        from meetings.views import MeetingViewSet
        from accounts.views import UserViewSet
        from core.views import health_check
        print(f"   ✅ ViewSets importados correctamente")
        success.append("ViewSets")
    except Exception as e:
        print(f"   ❌ Error al importar views: {e}")
        errors.append(f"ViewSets error: {e}")
    
    # 12. Verificar URLs
    print("🗺️  Verificando URLs...")
    try:
        from django.urls import get_resolver
        resolver = get_resolver()
        print(f"   ✅ URLs configuradas correctamente")
        success.append("URLs")
    except Exception as e:
        print(f"   ❌ Error al cargar URLs: {e}")
        errors.append(f"URLs error: {e}")
    
    print()
    print("=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    print(f"✅ Exitosos: {len(success)}")
    print(f"⚠️  Warnings: {len(warnings)}")
    print(f"❌ Errores: {len(errors)}")
    print()
    
    if warnings:
        print("⚠️  ADVERTENCIAS:")
        for warning in warnings:
            print(f"   - {warning}")
        print()
    
    if errors:
        print("❌ ERRORES:")
        for error in errors:
            print(f"   - {error}")
        print()
        print("🔧 Solución: Ejecutar 'pip install -r requirements.txt'")
        return False
    else:
        print("✅ ¡TODO OK! El proyecto está configurado correctamente.")
        print()
        print("🚀 Próximos pasos:")
        print("   1. python manage.py makemigrations")
        print("   2. python manage.py migrate")
        print("   3. python manage.py createsuperuser")
        print("   4. python manage.py runserver")
        print()
        return True

if __name__ == '__main__':
    try:
        verify_setup()
    except KeyboardInterrupt:
        print("\n\n⚠️  Verificación interrumpida")
        sys.exit(1)

