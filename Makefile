setup:
	python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

start-env:
	source venv/bin/activate

run-extract:
	python data/pcap_to_csv.py $(ARGS)

run-preprocess:
	python training/v2/1_preprocesar_datos.py

run-split-train-test-data:
	python training/v2/2_dividir_datos_train_test.py

run-training:
	python training/v2/3_entrenar_modelo.py

run-evaluate:
	python training/v2/4_evaluar_modelo.py

run-all:
	make run-preprocess
	make run-split-train-test-data
	make run-training
	make run-evaluate