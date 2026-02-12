"""
Serveur FastAPI WebSocket pour le splash screen.

Diffuse les événements du launcher (phases, logs) en temps réel
vers le navigateur via WebSocket.
"""

import asyncio
import logging
from pathlib import Path
from typing import Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .events import sanitize_message, create_event, EventType


# Désactiver les logs uvicorn trop verbeux
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class SplashServer:
    """
    Serveur FastAPI qui diffuse les événements du launcher via WebSocket.
    """

    def __init__(self, port: int = 8079, host: str = "127.0.0.1", theme: str = "matrix"):
        self.port = port
        self.host = host
        self.theme = theme
        self.active_connections: Set[WebSocket] = set()
        self.server: uvicorn.Server | None = None
        self.server_task: asyncio.Task | None = None

        # Chemins des assets (AVANT _create_app)
        self.splash_dir = Path(__file__).parent
        self.templates_dir = self.splash_dir / "templates"
        self.static_dir = self.splash_dir / "static"

        # Créer l'app (utilise les chemins ci-dessus)
        self.app = self._create_app()

    def _create_app(self) -> FastAPI:
        """Crée l'application FastAPI."""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Lifespan events pour FastAPI."""
            # Startup
            yield
            # Shutdown
            await self._cleanup_connections()

        app = FastAPI(
            title="Olist Launcher Splash",
            lifespan=lifespan,
        )

        # Routes
        @app.get("/", response_class=HTMLResponse)
        async def root():
            """Serve le template HTML."""
            # html_path = self.templates_dir / "index.html"
            template_name = f"index-{self.theme}.html" if self.theme != "matrix" else "index.html"
            html_path = self.templates_dir / template_name
            if html_path.exists():
                return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
            else:
                return HTMLResponse(
                    content="<h1>Splash template not found</h1>",
                    status_code=500,
                )

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """Endpoint WebSocket pour les événements en temps réel."""
            await self._handle_websocket(websocket)

        # Monter les fichiers statiques
        if self.static_dir.exists():
            app.mount(
                "/static", StaticFiles(directory=str(self.static_dir)), name="static"
            )

        return app

    async def _handle_websocket(self, websocket: WebSocket):
        """Gère une connexion WebSocket."""
        await websocket.accept()
        self.active_connections.add(websocket)

        # Envoyer événement de connexion
        welcome = create_event(
            EventType.CONNECTED,
            {"message": "Connected to Olist Launcher"},
        )
        await websocket.send_json(welcome)

        try:
            # Keep-alive loop
            while True:
                # Attendre des messages du client (ping/pong)
                data = await websocket.receive_text()
                # On ne traite pas les messages clients pour l'instant
        except WebSocketDisconnect:
            pass
        finally:
            self.active_connections.discard(websocket)

    async def _cleanup_connections(self):
        """Ferme toutes les connexions WebSocket actives."""
        for ws in list(self.active_connections):
            try:
                await ws.close()
            except Exception:
                pass
        self.active_connections.clear()

    async def broadcast_event(
        self,
        event_type: EventType | str,
        data: dict,
    ):
        """
        Diffuse un événement à tous les clients connectés.

        Args:
            event_type: Type d'événement
            data: Données de l'événement (seront sanitizées)
        """
        # Convertir en EventType si c'est une string
        if isinstance(event_type, str):
            event_type = EventType(event_type)

        # Créer l'événement
        event = create_event(event_type, data)

        # Sanitizer avant envoi
        sanitized = sanitize_message(event)

        # Broadcaster à tous les clients
        disconnected = set()
        for ws in self.active_connections:
            try:
                await ws.send_json(sanitized)
            except Exception:
                # Connexion morte, on la marquera pour suppression
                disconnected.add(ws)

        # Nettoyer les connexions mortes
        self.active_connections -= disconnected

    async def start(self):
        """Démarre le serveur uvicorn en arrière-plan."""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",  # Réduire le bruit
            access_log=False,
        )
        self.server = uvicorn.Server(config)

        # Lancer dans une tâche asyncio
        self.server_task = asyncio.create_task(self.server.serve())

        # Attendre que le serveur soit prêt
        await asyncio.sleep(0.5)

    async def shutdown(self):
        """Arrête le serveur proprement."""
        if self.server:
            # Fermer les connexions WebSocket
            await self._cleanup_connections()

            # Arrêter le serveur
            self.server.should_exit = True

            # Attendre que la tâche se termine
            if self.server_task:
                try:
                    await asyncio.wait_for(self.server_task, timeout=3.0)
                except asyncio.TimeoutError:
                    # Force cancel si timeout
                    self.server_task.cancel()
                    try:
                        await self.server_task
                    except asyncio.CancelledError:
                        pass

    def is_running(self) -> bool:
        """Vérifie si le serveur est en cours d'exécution."""
        return self.server_task is not None and not self.server_task.done()
