run-docker-compose:
	uv sync
	docker compose up --build 
run-api:
	uvicorn apps.api.app:app --reload
run-ui:
	cd apps/frontend/ && streamlit run app.py
	