#!/usr/bin/env python
"""
Demo du splash screen WebSocket avec événements simulés.

Usage:
    uv run python demo_splash.py

Puis ouvrir http://localhost:8079 dans votre navigateur.
"""

import asyncio
from src.launcher.splash.server import SplashServer
from src.launcher.splash.events import EventType


async def demo_splash():
    """Démo interactive du splash screen."""

    print("\n" + "=" * 60)
    print("🎬 DÉMO SPLASH SCREEN WEBSOCKET")
    print("=" * 60)

    # Démarrer le serveur
    print("\n1️⃣  Démarrage du serveur splash...")
    server = SplashServer(port=8079)
    await server.start()

    splash_url = "http://localhost:8079"
    print(f"✓ Serveur actif sur {splash_url}")
    print(f"\n📍 Ouvrez cette URL dans votre navigateur : {splash_url}")
    print("   (Vous avez 5 secondes pour ouvrir le navigateur)\n")

    await asyncio.sleep(5)

    # Simuler le pipeline ETL
    print("2️⃣  Simulation du pipeline ETL...\n")

    phases = [
        ("Configuration & Validation", [
            "✓ .env file found",
            "✓ Kaggle credentials valid",
            "✓ Directory permissions OK",
        ]),
        ("Pre-flight Health Check", [
            "✓ Directory structure OK",
            "✓ Python dependencies installed",
            "✓ All CSV files present (9/9)",
        ]),
        ("Downloading CSV Files", [
            "Downloading olist_orders.csv...",
            "✓ Downloaded olist_orders.csv (42.5 MB)",
            "Downloading olist_customers.csv...",
            "✓ Downloaded olist_customers.csv (12.1 MB)",
        ]),
        ("ETL Pipeline", [
            "Starting ETL pipeline...",
            "✓ Extracting data from CSV files",
            "✓ Transforming data (cleaning, parsing)",
            "✓ Loading into SQLite database",
            "✓ Database created (54.0 MB)",
        ]),
        ("Post-ETL Validation", [
            "✓ Database schema valid (6 tables)",
            "✓ Row count check passed",
            "✓ Data integrity validated",
        ]),
        ("Launching Dashboard", [
            "Starting dashboard server...",
            "✓ Dashboard process started (PID: 12345)",
            "✓ Dashboard is ready at http://localhost:8080",
        ]),
    ]

    for i, (phase_title, logs) in enumerate(phases, 1):
        # Broadcast phase start
        print(f"   PHASE {i}: {phase_title}")
        await server.broadcast_event(
            EventType.PHASE_START,
            {"phase_num": i, "title": phase_title}
        )

        await asyncio.sleep(1)

        # Broadcast logs
        for log_message in logs:
            # Déterminer le level
            if log_message.startswith("✓"):
                level = "SUCCESS"
            elif log_message.startswith("⚠"):
                level = "WARNING"
            elif log_message.startswith("✗"):
                level = "ERROR"
            else:
                level = "INFO"

            print(f"      {log_message}")
            await server.broadcast_event(
                EventType.LOG,
                {"level": level, "message": log_message}
            )

            await asyncio.sleep(0.3)

        # Broadcast phase complete
        duration_ms = len(logs) * 300 + 1000
        await server.broadcast_event(
            EventType.PHASE_COMPLETE,
            {"phase_num": i, "duration_ms": duration_ms}
        )

        print(f"      ✓ Phase {i} completed in {duration_ms/1000:.2f}s\n")
        await asyncio.sleep(0.5)

    # Dashboard ready
    print("3️⃣  Dashboard prêt - Broadcast de l'événement redirect...\n")
    await server.broadcast_event(
        EventType.DASHBOARD_READY,
        {"url": "http://localhost:8080", "redirect_delay_ms": 5000}
    )

    print("✓ Success box affichée dans le navigateur")
    print("  Auto-redirect dans 5 secondes...\n")

    await asyncio.sleep(7)

    # Shutdown
    print("4️⃣  Arrêt du serveur...\n")
    await server.shutdown()

    print("=" * 60)
    print("✅ DÉMO TERMINÉE")
    print("=" * 60)
    print("\nLe splash screen devrait avoir affiché :")
    print("  - 6 phases avec progression 0% → 100%")
    print("  - ~20 messages de logs en temps réel")
    print("  - Success box verte avec redirect")
    print("\nTout s'est bien passé ? Le splash fonctionne ! 🎉\n")


if __name__ == "__main__":
    try:
        asyncio.run(demo_splash())
    except KeyboardInterrupt:
        print("\n\n⚠ Démo interrompue par l'utilisateur")
