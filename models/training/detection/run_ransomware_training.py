#!/usr/bin/env python3
"""
Pipeline completo para entrenar un modelo de detección de ransomware
Mejorado con features específicas y arquitectura híbrida CNN+LSTM
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_script(script_name, description):
    """Ejecuta un script y maneja errores"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"📄 Ejecutando: {script_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, text=True, check=True)
        
        elapsed_time = time.time() - start_time
        print(f"✅ {description} completado en {elapsed_time:.2f} segundos")
        
        if result.stdout:
            print("\n📋 Salida del script:")
            print(result.stdout)
            
        return True
        
    except subprocess.CalledProcessError as e:
        elapsed_time = time.time() - start_time
        print(f"❌ Error en {description} después de {elapsed_time:.2f} segundos")
        print(f"📋 Error: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def check_dependencies():
    """Verifica que las dependencias estén instaladas"""
    print("🔍 Verificando dependencias...")
    
    required_packages = [
        'numpy', 'pandas', 'tensorflow', 'scikit-learn', 
        'matplotlib', 'seaborn', 'scipy', 'joblib'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Faltan dependencias: {', '.join(missing_packages)}")
        print("💡 Instala con: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ Todas las dependencias están instaladas")
    return True

def check_data_files():
    """Verifica que los archivos de datos existan"""
    print("\n🔍 Verificando archivos de datos...")
    
    required_files = [
        '../../data/traffic_dataset_full.csv'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ Faltan archivos de datos: {', '.join(missing_files)}")
        print("💡 Ejecuta primero el script de conversión PCAP a CSV")
        return False
    
    print("✅ Todos los archivos de datos están disponibles")
    return True

def main():
    """Función principal del pipeline"""
    print("🎯 PIPELINE DE ENTRENAMIENTO - DETECTOR DE RANSOMWARE")
    print("="*60)
    print("📋 Este pipeline entrenará un modelo híbrido CNN+LSTM")
    print("   con features específicas para detección de ransomware")
    print("="*60)
    
    # Verificar dependencias
    if not check_dependencies():
        sys.exit(1)
    
    # Verificar archivos de datos
    if not check_data_files():
        sys.exit(1)
    
    # Pipeline de scripts
    scripts = [
        ("1_preprocesar_datos.py", "Preprocesamiento de datos y extracción de features de ransomware"),
        ("2_dividir_datos_train_test.py", "División de datos en train/test con normalización"),
        ("3_entrenar_modelo.py", "Entrenamiento del modelo híbrido CNN+LSTM"),
        ("4_evaluar_modelo.py", "Evaluación del modelo con métricas específicas"),
        ("5_visualizar_resultados.py", "Visualización de resultados y análisis")
    ]
    
    # Ejecutar cada script
    for script_name, description in scripts:
        if not run_script(script_name, description):
            print(f"\n❌ Pipeline detenido en: {description}")
            print("💡 Revisa los errores y ejecuta manualmente el script fallido")
            sys.exit(1)
    
    # Resumen final
    print(f"\n{'='*60}")
    print("🎉 PIPELINE COMPLETADO EXITOSAMENTE")
    print(f"{'='*60}")
    print("📁 Archivos generados:")
    print("  - convlstm_model_ransomware_final.keras (modelo entrenado)")
    print("  - evaluation_results.json (métricas detalladas)")
    print("  - evaluation_visualization.png (gráficos de evaluación)")
    print("  - training_history.npy (historial de entrenamiento)")
    print("\n🎯 El modelo está listo para detectar ransomware!")
    print("💡 Usa el modelo con el script run_model.py para inferencia")

if __name__ == "__main__":
    main()
