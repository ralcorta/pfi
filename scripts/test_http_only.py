#!/usr/bin/env python3
"""
Script para probar que solo el servidor HTTP esté funcionando
y que el puerto UDP 4789 no esté escuchando
"""
import socket
import requests
import time
import sys
from urllib.parse import urljoin

def test_http_server(base_url="http://localhost:8080"):
    """Prueba que el servidor HTTP esté funcionando"""
    try:
        # Probar endpoint de health
        health_url = urljoin(base_url, "/health")
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            print("✅ Servidor HTTP funcionando correctamente")
            print(f"   Health check: {response.status_code}")
            return True
        else:
            print(f"❌ Servidor HTTP respondió con código: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error conectando al servidor HTTP: {e}")
        return False

def test_udp_port_not_listening(host="localhost", port=4789):
    """Prueba que el puerto UDP 4789 NO esté escuchando"""
    try:
        # Intentar conectar al puerto UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        
        # Enviar un paquete de prueba
        test_data = b"test"
        sock.sendto(test_data, (host, port))
        
        # Si llegamos aquí, el puerto está escuchando (malo)
        sock.close()
        print(f"❌ Puerto UDP {port} está escuchando (no debería)")
        return False
        
    except socket.timeout:
        # Timeout es bueno - significa que no hay respuesta
        print(f"✅ Puerto UDP {port} no está escuchando (correcto)")
        return True
    except ConnectionRefusedError:
        # Connection refused es bueno - puerto no está abierto
        print(f"✅ Puerto UDP {port} no está escuchando (correcto)")
        return True
    except Exception as e:
        print(f"✅ Puerto UDP {port} no está escuchando: {e}")
        return True
    finally:
        try:
            sock.close()
        except:
            pass

def test_demo_endpoints(base_url="http://localhost:8080"):
    """Prueba los endpoints de demo"""
    try:
        # Probar endpoint de demo status
        status_url = urljoin(base_url, "/demo/status")
        response = requests.get(status_url, timeout=5)
        
        if response.status_code == 200:
            print("✅ Endpoint /demo/status funcionando")
            data = response.json()
            print(f"   Demo activo: {data.get('demo_active', 'N/A')}")
        else:
            print(f"❌ Endpoint /demo/status falló: {response.status_code}")
            
        # Probar endpoint de información de PCAP precargado
        preloaded_info_url = urljoin(base_url, "/demo/preloaded-info")
        response = requests.get(preloaded_info_url, timeout=5)
        
        if response.status_code == 200:
            print("✅ Endpoint /demo/preloaded-info funcionando")
            data = response.json()
            print(f"   PCAP precargado: {data.get('preloaded_file', 'N/A')}")
        else:
            print(f"❌ Endpoint /demo/preloaded-info falló: {response.status_code}")
            
        # Probar endpoint de demo start-fast
        start_fast_url = urljoin(base_url, "/demo/start-fast")
        response = requests.get(start_fast_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Endpoint /demo/start-fast funcionando")
            data = response.json()
            print(f"   Mensaje: {data.get('message', 'N/A')}")
        else:
            print(f"❌ Endpoint /demo/start-fast falló: {response.status_code}")
            
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error probando endpoints de demo: {e}")
        return False

def main():
    """Función principal de prueba"""
    print("🧪 Probando configuración HTTP-only del sensor...")
    print("=" * 60)
    
    # Obtener URL base de argumentos o usar default
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    print(f"🌐 URL base: {base_url}")
    print()
    
    # Ejecutar pruebas
    tests_passed = 0
    total_tests = 3
    
    print("1. Probando servidor HTTP...")
    if test_http_server(base_url):
        tests_passed += 1
    print()
    
    print("2. Probando que puerto UDP 4789 NO esté escuchando...")
    if test_udp_port_not_listening():
        tests_passed += 1
    print()
    
    print("3. Probando endpoints de demo...")
    if test_demo_endpoints(base_url):
        tests_passed += 1
    print()
    
    # Resumen
    print("=" * 60)
    print(f"📊 Resultados: {tests_passed}/{total_tests} pruebas pasaron")
    
    if tests_passed == total_tests:
        print("🎉 ¡Todas las pruebas pasaron! El servidor está configurado correctamente para HTTP-only.")
        return 0
    else:
        print("⚠️  Algunas pruebas fallaron. Revisar la configuración.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
