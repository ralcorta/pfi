# app/sensor/src/utils/config.py
"""Utilidades de configuración"""
import yaml
import os

def load_config(config_path: str = None):
    """Carga configuración desde archivo YAML"""
    if config_path and os.path.exists(config_path):