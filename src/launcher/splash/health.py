"""
Health check pour vérifier que le dashboard est prêt.
"""

import asyncio
import aiohttp
from typing import Optional


async def wait_for_dashboard_ready(
    port: int = 8080,
    timeout: int = 30,
    interval: float = 0.5,
) -> bool:
    """
    Poll le dashboard jusqu'à ce qu'il réponde HTTP 200.

    Args:
        port: Port du dashboard (défaut: 8080)
        timeout: Timeout maximum en secondes (défaut: 30)
        interval: Intervalle entre les polls en secondes (défaut: 0.5)

    Returns:
        True si le dashboard est prêt, False si timeout
    """
    url = f"http://localhost:{port}/"
    start_time = asyncio.get_event_loop().time()

    async with aiohttp.ClientSession() as session:
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    if resp.status == 200:
                        return True
            except (aiohttp.ClientError, asyncio.TimeoutError):
                # Dashboard pas encore prêt, on réessaye
                pass

            await asyncio.sleep(interval)

    # Timeout atteint
    return False


async def check_dashboard_health(port: int = 8080) -> Optional[dict]:
    """
    Vérifie si le dashboard répond (check unique, pas de retry).

    Args:
        port: Port du dashboard

    Returns:
        Dict avec status si disponible, None sinon
    """
    url = f"http://localhost:{port}/"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                return {
                    "status": resp.status,
                    "available": resp.status == 200,
                }
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return None
