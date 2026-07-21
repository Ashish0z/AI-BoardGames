# AI-BoardGames

A minimal framework for local AI-powered board games, starting with Monopoly.

## What is included
- Python backend framework with reusable abstractions for multiple board games.
- Initial Monopoly implementation built on top of shared game engine abstractions.
- In-memory game state store and move validation flow.
- Ollama-backed AI move selection service (adaptive to player skill level).
- Ollama-backed coaching chat endpoint.
- Basic web UI with game state panel and chat window.

## Project structure
- `/backend/app/core`: abstract game models, base class, state store.
- `/backend/app/games/monopoly`: Monopoly game implementation.
- `/backend/app/ai`: local Ollama integration and AI services.
- `/backend/app/main.py`: FastAPI application and API routes.
- `/frontend/index.html`: basic browser UI.
- `/tests`: focused backend tests.

## Run locally
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start Ollama locally (default expected at `http://localhost:11434`) and ensure a model (default `llama3.1`) is available.
3. Start the backend:
   ```bash
   uvicorn backend.app.main:app --reload
   ```
4. Open the UI:
   - `http://127.0.0.1:8000/ui`

## Notes
- This is a basic framework intentionally designed for extension to additional games (for example, Catan) by adding new classes that extend `BoardGame`.
