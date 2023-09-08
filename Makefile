run_app:
	[ -e .env ] || cp .env_template .env # if the .env file does not exist, create it from .env template
	streamlit run llama2_chatbot.py --server.enableCORS false --server.enableXsrfProtection false -- --noauth

clear_log:
	rm -f ./log/interaction_log.log
	$(info Log file deleted. Restart app to create a new empty log file - otherwise log output will not be recorded.)

tpch:
	mkdir -p ./db_files/tpch
	rm -f ./db_files/tpch/*.duckdb
	python db_utils/make_tpch.py 0.1

lfu:
	mkdir -p ./db_files/lfu
	rm -f ./db_files/lfu/*.*
	pip install kaggle
	cd ./db_files/lfu; kaggle datasets download -d yuriykatser/industrial-data-from-the-ladlefurnace-unit
	cd ./db_files/lfu; unzip industrial-data-from-the-ladlefurnace-unit.zip
	cd ./db_files/lfu; rm -f industrial-data-from-the-ladlefurnace-unit.zip
	cd ./db_files/lfu; python ../../db_utils/make_lfu.py

wca:
	mkdir -p ./db_files/wca
	rm -f ./db_files/wca/*.*
	cd ./db_files/wca; wget https://www.worldcubeassociation.org/export/results/WCA_export250_20230907T121444Z.sql.zip
	cd ./db_files/wca; unzip WCA_export*.zip
	cd ./db_files/wca; rm -f WCA_export*.zip
	pip install sqlglot
	cd ./db_files/wca; python ../../db_utils/make_wca.py
	cd ./db_files/wca; ls | grep -xv "wca.duckdb" | xargs rm