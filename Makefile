# Activate environment (use this command directly in terminal)
env:
	@echo "To activate the environment, run: source .venv/bin/activate"
	@echo "Or use: poetry shell"

# Poetry setup and management
install:
	poetry install

install-dev:
	poetry install --with dev

shell:
	poetry shell

update:
	poetry update

# Data processing
run-extract:
	poetry run python data/pcap_to_csv_full.py $(ARGS)

run-preprocess:
	poetry run python training/detection/1_preprocesar_datos.py

run-split-train-test-data:
	poetry run python training/detection/2_dividir_datos_train_test.py

run-training:
	poetry run python training/detection/3_entrenar_modelo.py

run-evaluate:
	poetry run python training/detection/4_evaluar_modelo.py

# Adversarial training
run-adversarial-obfuscate:
	poetry run python training/ofuscacion/1_ofuscar_datos.py

run-adversarial-retrain:
	poetry run python training/ofuscacion/2_reentrenar_modelo.py

run-adversarial-evaluate:
	poetry run python training/ofuscacion/3_evaluar_modelo_adversarial.py

# Main application
run-detection:
	poetry run python app/network-traffic-detection/src/main.py

run-model:
	poetry run python run_model.py

# Complete workflows
run-all-detection:
	make run-preprocess
	make run-split-train-test-data
	make run-training
	make run-evaluate

run-all-adversarial:
	make run-adversarial-obfuscate
	make run-adversarial-retrain
	make run-adversarial-evaluate

# Development tools
format:
	poetry run black .

lint:
	poetry run flake8 .

type-check:
	poetry run mypy .

test:
	poetry run pytest

# Legacy compatibility
run: shell