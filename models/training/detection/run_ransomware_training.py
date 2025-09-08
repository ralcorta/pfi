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
        # Obtener el directorio del script actual
        script_dir = Path(__file__).parent
        script_path = script_dir / script_name
        
        # Verificar que el script existe
        if not script_path.exists():
            print(f"❌ Script no encontrado: {script_path}")
            return False
        
        # Ejecutar el script desde su directorio SIN capturar la salida
        result = subprocess.run([sys.executable, str(script_path)], 
                              cwd=str(script_dir),  # Ejecutar desde el directorio del script
                              check=True)  # Sin capture_output para ver la salida en tiempo real
        
        elapsed_time = time.time() - start_time
        print(f"\n✅ {description} completado en {elapsed_time:.2f} segundos")
            
        return True
        
    except subprocess.CalledProcessError as e:
        elapsed_time = time.time() - start_time
        print(f"\n❌ Error en {description} después de {elapsed_time:.2f} segundos")
        print(f" Código de error: {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def check_dependencies():
    """Verifica que las dependencias estén instaladas"""
    print("�� Verificando dependencias...")
    
    # Mapeo de nombres de paquetes a sus módulos de importación
    required_packages = {
        'numpy': 'numpy',
        'pandas': 'pandas', 
        'tensorflow': 'tensorflow',
        'scikit-learn': 'sklearn',  # El módulo se llama sklearn, no scikit-learn
        'matplotlib': 'matplotlib',
        'seaborn': 'seaborn',
        'scipy': 'scipy',
        'joblib': 'joblib'
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            print(f"  ❌ {package_name}")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n❌ Faltan dependencias: {', '.join(missing_packages)}")
        print("💡 Instala con: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ Todas las dependencias están instaladas")
    return True

def check_data_files():
    """Verifica que los archivos de datos existan"""
    print("\n🔍 Verificando archivos de datos...")
    
    # Obtener el directorio del script actual
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent
    
    # Construir rutas relativas al archivo del script
    required_files = [
        project_root / "models" / "data" / "traffic_dataset_full.csv"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if file_path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}")
            missing_files.append(str(file_path))
    
    if missing_files:
        print(f"\n❌ Faltan archivos de datos: {', '.join(missing_files)}")
        print("�� Ejecuta primero el script de conversión PCAP a CSV")
        return False
    
    print("✅ Todos los archivos de datos están disponibles")
    return True

def main():
    """Función principal del pipeline"""
    print("�� PIPELINE DE ENTRENAMIENTO - DETECTOR DE RANSOMWARE")
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
            print("�� Revisa los errores y ejecuta manualmente el script fallido")
            sys.exit(1)
    
    # Resumen final
    print(f"\n{'='*60}")
    print("🎉 PIPELINE COMPLETADO EXITOSAMENTE")
    print(f"{'='*60}")
    print("�� Archivos generados:")
    print("  - convlstm_model_ransomware_final.keras (modelo entrenado)")
    print("  - evaluation_results.json (métricas detalladas)")
    print("  - evaluation_visualization.png (gráficos de evaluación)")
    print("  - training_history.npy (historial de entrenamiento)")
    print("\n🎯 El modelo está listo para detectar ransomware!")
    print("💡 Usa el modelo con el script run_model.py para inferencia")

if __name__ == "__main__":
    main()