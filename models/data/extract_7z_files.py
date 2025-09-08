#!/usr/bin/env python3
"""
Script para descomprimir archivos .7z en las carpetas de backup
"""

import os
import sys
import shutil
from pathlib import Path
import subprocess

def run_command(cmd, description):
    """Ejecuta un comando y maneja errores"""
    print(f"🔄 {description}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}: {e.stderr}")
        return False

def check_7z_installed():
    """Verifica si 7z está instalado en el sistema"""
    try:
        result = subprocess.run(['7z'], capture_output=True, text=True)
        return True
    except FileNotFoundError:
        return False

def extract_7z_with_7z(file_path, extract_to):
    """Descomprime archivo .7z usando 7z nativo"""
    cmd = f'7z x "{file_path}" -o"{extract_to}" -y'
    return run_command(cmd, f"Descomprimiendo {file_path.name}")

def extract_7z_with_python(file_path, extract_to):
    """Descomprime archivo .7z usando py7zr (fallback)"""
    try:
        import py7zr
        print(f"🔄 Descomprimiendo {file_path.name} con py7zr...")
        with py7zr.SevenZipFile(file_path, mode='r') as archive:
            archive.extractall(path=extract_to)
        print(f"✅ {file_path.name} descomprimido exitosamente")
        return True
    except ImportError:
        print("❌ py7zr no está instalado. Instálalo con: pip install py7zr")
        return False
    except Exception as e:
        print(f"❌ Error descomprimiendo {file_path.name}: {e}")
        return False

def extract_7z_files():
    """Recorre las carpetas de backup y descomprime archivos .7z"""
    
    # Obtener el directorio del proyecto
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    BACKUP_DIR = PROJECT_ROOT / "models" / "data" / "backup"
    
    print("🎯 DESCOMPRIMIENDO ARCHIVOS .7Z EN BACKUP")
    print("="*50)
    
    if not BACKUP_DIR.exists():
        print(f"❌ Directorio backup no encontrado: {BACKUP_DIR}")
        print("💡 Ejecuta primero: poetry run python models/data/download_pcap_data.py")
        return False
    
    # Buscar todos los archivos .7z
    seven_z_files = list(BACKUP_DIR.rglob("*.7z"))
    
    if not seven_z_files:
        print("ℹ️  No se encontraron archivos .7z en el directorio backup")
        return True
    
    print(f" Encontrados {len(seven_z_files)} archivos .7z")
    
    # Verificar si 7z está instalado
    has_7z = check_7z_installed()
    if has_7z:
        print("✅ 7z nativo encontrado en el sistema")
    else:
        print("⚠️  7z nativo no encontrado, intentando con py7zr")
    
    success_count = 0
    error_count = 0
    
    for seven_z_file in seven_z_files:
        print(f"\n�� Procesando: {seven_z_file.name}")
        print(f"   Ubicación: {seven_z_file}")
        
        # Directorio donde extraer (mismo directorio que el archivo .7z)
        extract_dir = seven_z_file.parent
        
        # Intentar descomprimir
        success = False
        if has_7z:
            success = extract_7z_with_7z(seven_z_file, extract_dir)
        else:
            success = extract_7z_with_python(seven_z_file, extract_dir)
        
        if success:
            success_count += 1
            # Verificar si se extrajeron archivos .pcap
            pcap_files = list(extract_dir.glob("*.pcap"))
            if pcap_files:
                print(f"   📄 Archivos .pcap extraídos: {len(pcap_files)}")
                for pcap in pcap_files:
                    print(f"      - {pcap.name}")
            
            # Preguntar si eliminar el archivo .7z original
            try:
                response = input(f"   🗑️  ¿Eliminar archivo .7z original? (y/N): ").strip().lower()
                if response in ['y', 'yes', 's', 'si']:
                    seven_z_file.unlink()
                    print(f"   ✅ Archivo .7z eliminado: {seven_z_file.name}")
                else:
                    print(f"   ℹ️  Archivo .7z conservado: {seven_z_file.name}")
            except KeyboardInterrupt:
                print(f"\n   ⏹️  Operación cancelada por el usuario")
                break
        else:
            error_count += 1
    
    print(f"\n�� Resumen de descompresión:")
    print(f"   - Archivos procesados exitosamente: {success_count}")
    print(f"   - Archivos con errores: {error_count}")
    print(f"   - Total: {len(seven_z_files)}")
    
    if success_count > 0:
        print(f"\n✅ Descompresión completada")
        print(f"💡 Ahora puedes ejecutar: make extract")
    
    return error_count == 0

def main():
    """Función principal"""
    print(" SCRIPT DE DESCOMPRESIÓN DE ARCHIVOS .7Z")
    print("="*50)
    print("�� Este script descomprimirá archivos .7z en las carpetas de backup")
    print("   y extraerá los archivos .pcap contenidos.")
    print("="*50)
    
    if extract_7z_files():
        print(f"\n�� DESCOMPRESIÓN COMPLETADA EXITOSAMENTE")
        print("="*50)
        print("�� Próximos pasos:")
        print("   1. make extract  (convertir PCAP a CSV)")
        print("   2. poetry run python models/training/detection/run_ransomware_training.py")
    else:
        print(f"\n❌ ERROR EN LA DESCOMPRESIÓN")
        print("="*50)
        print(" Revisa los errores anteriores y los permisos de archivos")
        sys.exit(1)

if __name__ == "__main__":
    main()
