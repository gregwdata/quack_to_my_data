run_app:
	[ -e .env ] || cp .env_template .env # if the .env file does not exist, create it from .env template
	streamlit run llama2_chatbot.py --server.enableCORS false --server.enableXsrfProtection false -- --noauth

tpch:
	mkdir -p ./db_files/tpch
	rm -f ./db_files/tpch/*.duckdb
	python db_utils/make_tpch.py 0.1