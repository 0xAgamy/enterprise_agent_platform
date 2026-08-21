# 🏢 Enterprise Agent Platform

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![LangGraph](https://img.shields.io/badge/Powered%20by-LangGraph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-teal.svg)](https://fastapi.tiangolo.com/)

A production-oriented, multi-agent commerce platform leveraging **LangGraph**.

---

## Getting Started
**Prerequisites**
- Python 3.13+
- uv (Fast Python package installer and resolver)
- Docker & Docker Compose

### 1. Clone the Repository
```bash
git clone https://github.com/0xAgamy/enterprise_agent_platform.git
cd enterprise_agent_platform
```


### 2. Configure Environment Variables
Copy the example environment files and fill in your credentials (e.g., LLM API keys, database URLs):
```bash
cp .env.example .env
cp .env.postgres.example .env.postgres
```
Edit `.env` and `.env.postgres` with your preferred text editor.

### 3. Install Dependencies & Start Services
The included `Makefile` provides a streamlined setup process that syncs Python dependencies and spins up the required Docker containers (PostgreSQL and Qdrant):
```bash
make run-docker-compose
```

### 4. Access the Application
- FastAPI Docs: `http://localhost:8000/docs` (or the port specified in your .env)
- Streamlit Frontend: `http://localhost:8501` (or the port specified in your setup)
