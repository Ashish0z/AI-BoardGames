# AI-BoardGames

A framework for local AI-powered board games, starting with Monopoly.

## What is included
- Python backend framework with reusable abstractions for multiple board games.
- Expanded Monopoly implementation with a richer ruleset flow: tile types, buy/skip, rent, tax, chance/community cards, jail, and trade offers.
- In-memory game state store and move validation flow.
- Ollama-backed AI move selection service (adaptive to player skill level).
- Ollama-backed coaching chat endpoint.
- React/Vite web UI with sidebar settings, game selector buttons, Monopoly board rendering with token animations, and right-side strategy chat.

## Project structure
- `/backend/app/core`: abstract game models, base class, state store.
- `/backend/app/games/monopoly`: Monopoly game implementation.
- `/backend/app/ai`: local Ollama integration and AI services.
- `/backend/app/main.py`: FastAPI application and API routes.
- `/frontend`: React/Vite frontend application.
- `/tests`: focused backend tests.

## Run locally
1. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```
3. Start Ollama locally (default expected at `http://localhost:11434`) and ensure a model (default `llama3.1`) is available.
4. Start the backend:
   ```bash
   uvicorn backend.app.main:app --reload
   ```
5. Start the frontend dev server (in another terminal):
   ```bash
   cd frontend
   npm run dev
   ```
6. Open the UI:
   - `http://127.0.0.1:5173`
   - Or build frontend and serve via backend `/ui` route:
     ```bash
     cd frontend
     npm run build
     ```
     then open `http://127.0.0.1:8000/ui`

## Notes
- The backend game abstraction remains extensible for additional games (for example, Catan) by adding new classes that extend `BoardGame`.
