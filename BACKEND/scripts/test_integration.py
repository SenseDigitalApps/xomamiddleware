#!/usr/bin/env python3
"""
Script de testing de integración para el stack Docker.

Prueba:
- Conectividad entre servicios
- CRUD completo de reuniones
- Validaciones de serializers
- Manejo de errores
- Endpoints de usuarios
- Endpoints de participantes y grabaciones

Uso:
    python scripts/test_integration.py
"""

import requests
import time
import sys
from datetime import datetime, timedelta

# Configuración
BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 10

# Colores para output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

# Contadores
tests_passed = 0
tests_failed = 0
tests_total = 0


def print_test(name, passed, details=""):
    """Imprime resultado de un test."""
    global tests_passed, tests_failed, tests_total
    
    tests_total += 1
    
    if passed:
        tests_passed += 1
        print(f"[{tests_total}] {name}... {Colors.GREEN}✅ PASS{Colors.NC}")
    else:
        tests_failed += 1
        print(f"[{tests_total}] {name}... {Colors.RED}❌ FAIL{Colors.NC}")
    
    if details:
        print(f"    {details}")


def test_health_check():
    """Test: Health check endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health/", timeout=TIMEOUT)
        data = response.json()
        
        passed = (
            response.status_code == 200 and
            data.get('status') == 'ok' and
            data.get('api') == 'running' and
            data.get('database') == 'connected'
        )
        
        print_test("Health check endpoint", passed)
        return passed
    except Exception as e:
        print_test("Health check endpoint", False, str(e))
        return False


def test_api_root():
    """Test: API Root endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
        data = response.json()
        
        passed = (
            response.status_code == 200 and
            'endpoints' in data
        )
        
        print_test("API Root endpoint", passed)
        return passed
    except Exception as e:
        print_test("API Root endpoint", False, str(e))
        return False


def test_swagger_ui():
    """Test: Swagger UI disponible"""
    try:
        response = requests.get(f"{BASE_URL}/docs/", timeout=TIMEOUT)
        passed = response.status_code == 200 and 'swagger' in response.text.lower()
        
        print_test("Swagger UI", passed)
        return passed
    except Exception as e:
        print_test("Swagger UI", False, str(e))
        return False


def test_openapi_schema():
    """Test: OpenAPI Schema"""
    try:
        response = requests.get(f"{BASE_URL}/schema/", timeout=TIMEOUT)
        data = response.json()
        
        passed = (
            response.status_code == 200 and
            'openapi' in data and
            'paths' in data
        )
        
        print_test("OpenAPI Schema", passed)
        return passed
    except Exception as e:
        print_test("OpenAPI Schema", False, str(e))
        return False


def test_list_meetings():
    """Test: Listar reuniones"""
    try:
        response = requests.get(f"{BASE_URL}/meetings/", timeout=TIMEOUT)
        
        passed = (
            response.status_code == 200 and
            isinstance(response.json(), list)
        )
        
        print_test("Listar reuniones", passed)
        return passed
    except Exception as e:
        print_test("Listar reuniones", False, str(e))
        return False


def test_create_meeting():
    """Test: Crear reunión"""
    try:
        now = datetime.now()
        start = (now + timedelta(hours=1)).isoformat() + 'Z'
        end = (now + timedelta(hours=2)).isoformat() + 'Z'
        
        data = {
            "organizer_email": "doctor@test.com",
            "invited_emails": ["paciente@test.com"],
            "scheduled_start": start,
            "scheduled_end": end,
            "external_reference": "integration_test_001"
        }
        
        response = requests.post(
            f"{BASE_URL}/meetings/",
            json=data,
            timeout=TIMEOUT
        )
        
        result = response.json()
        
        passed = (
            response.status_code == 201 and
            'id' in result and
            'meet_link' in result and
            result.get('status') == 'CREATED'
        )
        
        if passed:
            meeting_id = result['id']
            print_test("Crear reunión", True, f"ID: {meeting_id}, Link: {result.get('meet_link')}")
            return meeting_id
        else:
            print_test("Crear reunión", False, f"Status: {response.status_code}")
            return None
            
    except Exception as e:
        print_test("Crear reunión", False, str(e))
        return None


def test_get_meeting(meeting_id):
    """Test: Obtener detalle de reunión"""
    try:
        response = requests.get(
            f"{BASE_URL}/meetings/{meeting_id}/",
            timeout=TIMEOUT
        )
        
        result = response.json()
        
        passed = (
            response.status_code == 200 and
            result.get('id') == meeting_id and
            'organizer' in result and
            'participants' in result
        )
        
        print_test(f"Obtener reunión {meeting_id}", passed)
        return passed
    except Exception as e:
        print_test(f"Obtener reunión {meeting_id}", False, str(e))
        return False


def test_update_meeting(meeting_id):
    """Test: Actualizar reunión"""
    try:
        data = {"status": "SCHEDULED"}
        
        response = requests.patch(
            f"{BASE_URL}/meetings/{meeting_id}/",
            json=data,
            timeout=TIMEOUT
        )
        
        result = response.json()
        
        passed = (
            response.status_code == 200 and
            result.get('status') == 'SCHEDULED'
        )
        
        print_test(f"Actualizar reunión {meeting_id}", passed)
        return passed
    except Exception as e:
        print_test(f"Actualizar reunión {meeting_id}", False, str(e))
        return False


def test_cancel_meeting(meeting_id):
    """Test: Cancelar reunión"""
    try:
        response = requests.delete(
            f"{BASE_URL}/meetings/{meeting_id}/",
            timeout=TIMEOUT
        )
        
        result = response.json()
        
        passed = (
            response.status_code == 200 and
            'message' in result
        )
        
        print_test(f"Cancelar reunión {meeting_id}", passed)
        return passed
    except Exception as e:
        print_test(f"Cancelar reunión {meeting_id}", False, str(e))
        return False


def test_validation_errors():
    """Test: Validación de errores"""
    try:
        # Intentar crear reunión sin emails invitados
        data = {
            "organizer_email": "test@example.com",
            "invited_emails": []  # Vacío (debe fallar)
        }
        
        response = requests.post(
            f"{BASE_URL}/meetings/",
            json=data,
            timeout=TIMEOUT
        )
        
        # Debe retornar 400 Bad Request
        passed = response.status_code == 400
        
        print_test("Validación de errores", passed, "Campo requerido validado correctamente")
        return passed
    except Exception as e:
        print_test("Validación de errores", False, str(e))
        return False


def test_list_users():
    """Test: Listar usuarios"""
    try:
        response = requests.get(f"{BASE_URL}/users/", timeout=TIMEOUT)
        
        passed = (
            response.status_code == 200 and
            isinstance(response.json(), list)
        )
        
        print_test("Listar usuarios", passed)
        return passed
    except Exception as e:
        print_test("Listar usuarios", False, str(e))
        return False


def test_list_participants():
    """Test: Listar participantes"""
    try:
        response = requests.get(f"{BASE_URL}/participants/", timeout=TIMEOUT)
        
        passed = (
            response.status_code == 200 and
            isinstance(response.json(), list)
        )
        
        print_test("Listar participantes", passed)
        return passed
    except Exception as e:
        print_test("Listar participantes", False, str(e))
        return False


def test_list_recordings():
    """Test: Listar grabaciones"""
    try:
        response = requests.get(f"{BASE_URL}/recordings/", timeout=TIMEOUT)
        
        passed = (
            response.status_code == 200 and
            isinstance(response.json(), list)
        )
        
        print_test("Listar grabaciones", passed)
        return passed
    except Exception as e:
        print_test("Listar grabaciones", False, str(e))
        return False


def main():
    """Función principal de testing."""
    
    print(f"{Colors.BLUE}🔍 Esperando que el stack esté listo...{Colors.NC}")
    print("")
    
    # Esperar a que el servidor esté listo
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/health/", timeout=2)
            if response.status_code == 200:
                print(f"{Colors.GREEN}✅ Servidor listo{Colors.NC}")
                print("")
                break
        except:
            if attempt < max_attempts - 1:
                print(f"   Esperando... ({attempt + 1}/{max_attempts})")
                time.sleep(2)
            else:
                print(f"{Colors.RED}❌ Servidor no está disponible{Colors.NC}")
                sys.exit(1)
    
    # ===== EJECUTAR TESTS =====
    
    print(f"{Colors.BLUE}🧪 Ejecutando tests de integración...{Colors.NC}")
    print("")
    
    # Tests básicos
    test_health_check()
    test_api_root()
    test_swagger_ui()
    test_openapi_schema()
    
    print("")
    
    # Tests de endpoints
    test_list_meetings()
    test_list_users()
    test_list_participants()
    test_list_recordings()
    
    print("")
    
    # Test CRUD completo
    meeting_id = test_create_meeting()
    
    if meeting_id:
        test_get_meeting(meeting_id)
        test_update_meeting(meeting_id)
        test_cancel_meeting(meeting_id)
    
    print("")
    
    # Test de validaciones
    test_validation_errors()
    
    print("")
    
    # ===== RESUMEN FINAL =====
    print("=" * 50)
    print("📊 RESUMEN FINAL")
    print("=" * 50)
    print("")
    print(f"Total:  {tests_total}")
    print(f"{Colors.GREEN}Passed: {tests_passed}{Colors.NC}")
    print(f"{Colors.RED}Failed: {tests_failed}{Colors.NC}")
    print(f"Success Rate: {(tests_passed/tests_total*100):.1f}%")
    print("")
    
    if tests_failed == 0:
        print(f"{Colors.GREEN}✅ ¡TODOS LOS TESTS PASARON!{Colors.NC}")
        print("")
        print("🎉 El stack Docker está completamente funcional")
        print("")
        sys.exit(0)
    else:
        print(f"{Colors.YELLOW}⚠️  {tests_failed} test(s) fallaron{Colors.NC}")
        print("")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Tests interrumpidos{Colors.NC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{Colors.RED}❌ Error inesperado: {e}{Colors.NC}")
        sys.exit(1)

