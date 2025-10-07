#!/usr/bin/env python3
"""
Script para probar la funcionalidad de precarga de PCAP
"""
import time
import requests
import sys
from urllib.parse import urljoin

def test_preload_functionality(base_url="http://localhost:8080"):
    """Prueba la funcionalidad de precarga de PCAP"""
    print("🧪 Probando funcionalidad de precarga de PCAP...")
    print("=" * 60)
    
    try:
        # 1. Verificar información del PCAP precargado
        print("1. Verificando información del PCAP precargado...")
        preloaded_info_url = urljoin(base_url, "/demo/preloaded-info")
        response = requests.get(preloaded_info_url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ PCAP precargado: {data.get('preloaded_file', 'N/A')}")
            print(f"   Nota: {data.get('note', 'N/A')}")
        else:
            print(f"❌ Error obteniendo info de PCAP precargado: {response.status_code}")
            return False
        
        # 2. Probar demo rápido (debería usar PCAP precargado)
        print("\n2. Probando demo rápido (PCAP precargado)...")
        start_time = time.time()
        
        start_fast_url = urljoin(base_url, "/demo/start-fast")
        response = requests.get(start_fast_url, timeout=15)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Demo rápido iniciado en {response_time:.2f} segundos")
            print(f"   Mensaje: {data.get('message', 'N/A')}")
            
            # Verificar que fue rápido (menos de 5 segundos)
            if response_time < 5:
                print("🚀 ¡Excelente! Demo iniciado rápidamente (PCAP precargado)")
            else:
                print("⚠️  Demo tardó más de lo esperado, puede que no esté usando PCAP precargado")
        else:
            print(f"❌ Error iniciando demo rápido: {response.status_code}")
            return False
        
        # 3. Verificar estado del demo
        print("\n3. Verificando estado del demo...")
        time.sleep(2)  # Esperar un poco para que el demo se procese
        
        status_url = urljoin(base_url, "/demo/status")
        response = requests.get(status_url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Estado del demo: {data.get('demo_active', 'N/A')}")
            if data.get('demo_active'):
                print("🎭 Demo está activo y procesando paquetes")
            else:
                print("⏸️  Demo no está activo")
        else:
            print(f"❌ Error obteniendo estado del demo: {response.status_code}")
        
        # 4. Detener demo
        print("\n4. Deteniendo demo...")
        stop_url = urljoin(base_url, "/demo/stop")
        response = requests.post(stop_url, timeout=5)
        
        if response.status_code == 200:
            print("✅ Demo detenido correctamente")
        else:
            print(f"❌ Error deteniendo demo: {response.status_code}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def main():
    """Función principal"""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    
    print(f"🌐 URL base: {base_url}")
    print("💡 Asegúrate de que el servidor esté ejecutándose")
    print()
    
    if test_preload_functionality(base_url):
        print("\n" + "=" * 60)
        print("🎉 ¡Todas las pruebas de precarga pasaron!")
        print("✅ El PCAP se está precargando correctamente")
        print("🚀 Las demos deberían iniciar mucho más rápido")
        return 0
    else:
        print("\n" + "=" * 60)
        print("⚠️  Algunas pruebas fallaron")
        print("🔍 Revisar la configuración del servidor")
        return 1

if __name__ == "__main__":
    sys.exit(main())
