#!/bin/bash

# Ransomware Detection Sensor Installation Script

set -e

echo "=========================================="
echo "Ransomware Detection Sensor Installation"
echo "=========================================="

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry is not installed. Please install Poetry first:"
    echo "   curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

echo "✅ Poetry found"

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Install dependencies
echo "📦 Installing dependencies..."
poetry install

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p examples

# Check if model exists
model_path="../../convlstm_model.keras"
if [ ! -f "$model_path" ]; then
    echo "⚠️  Warning: Model file not found at $model_path"
    echo "   Please ensure the trained model is available before running the sensor"
else
    echo "✅ Model file found: $model_path"
fi

# Make test script executable
chmod +x test_sensor.py

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "Quick start:"
echo "  cd app/sensor"
echo "  poetry run python src/main.py --mode live --interface en0"
echo ""
echo "For more examples, see: examples/usage_examples.md"
echo ""
