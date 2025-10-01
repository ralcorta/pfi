"""Utilidades de logging"""
import logging
import sys
import os
from pathlib import Path

def setup_logger(config: dict):
    """Configura el logger con configuración personalizada"""
    # Configuración por defecto
    level = config.get('level', 'INFO')
    format_str = config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = config.get('file')
    
    # Crear logger
    logger = logging.getLogger('ransomware_sensor')
    logger.setLevel(getattr(logging, level.upper()))
    
    # Limpiar handlers existentes
    logger.handlers.clear()
    
    # Handler para stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(getattr(logging, level.upper()))
    
    # Formatter
    formatter = logging.Formatter(format_str)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)
    
    # Handler para archivo si se especifica
    if log_file:
        # Crear directorio de logs si no existe
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Evitar propagación a logger root
    logger.propagate = False
    
    return logger