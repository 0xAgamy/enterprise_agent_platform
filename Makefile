run-docker-compose:
	uv sync
	docker compose up --build 
run-api:
	uvicorn apps.api.app:app --reload
run-ui:
	cd frontend/ && streamlit run app.py
	