"""
Ouverture intelligente du navigateur, compatible WSL.
"""

import os
import platform
import subprocess
import webbrowser
from pathlib import Path


def is_wsl() -> bool:
    """Détecte si on est dans WSL (Windows Subsystem for Linux)."""
    try:
        # Méthode 1 : Vérifier /proc/version
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower() or 'wsl' in f.read().lower()
    except (FileNotFoundError, PermissionError):
        pass

    # Méthode 2 : Vérifier WSL_DISTRO_NAME
    return 'WSL' in os.environ.get('WSL_DISTRO_NAME', '')


def open_browser_wsl(url: str) -> bool:
    """
    Ouvre le navigateur Windows depuis WSL.

    Args:
        url: URL à ouvrir

    Returns:
        True si succès, False sinon
    """
    # Essayer différentes méthodes dans l'ordre de préférence
    methods = [
        # Méthode 1 : wslview (si installé)
        lambda: subprocess.run(
            ['wslview', url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        ),

        # Méthode 2 : cmd.exe /c start
        lambda: subprocess.run(
            ['cmd.exe', '/c', 'start', url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        ),

        # Méthode 3 : powershell.exe start
        lambda: subprocess.run(
            ['powershell.exe', '-c', 'start', url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        ),

        # Méthode 4 : explorer.exe (fallback)
        lambda: subprocess.run(
            ['explorer.exe', url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        ),
    ]

    for method in methods:
        try:
            method()
            return True
        except (FileNotFoundError, subprocess.CalledProcessError, PermissionError):
            continue

    return False


def open_browser(url: str, verbose: bool = False) -> bool:
    """
    Ouvre l'URL dans le navigateur par défaut, avec support WSL.

    Args:
        url: URL à ouvrir
        verbose: Afficher les messages de debug

    Returns:
        True si le navigateur s'est ouvert, False sinon
    """
    if verbose:
        print(f"[DEBUG] Tentative d'ouverture : {url}")

    # Détection WSL
    if is_wsl():
        if verbose:
            print("[DEBUG] WSL détecté, utilisation de cmd.exe")
        success = open_browser_wsl(url)
        if success:
            if verbose:
                print("[DEBUG] ✓ Navigateur Windows ouvert depuis WSL")
            return True
        else:
            if verbose:
                print("[DEBUG] ✗ Échec d'ouverture du navigateur WSL")
            return False

    # Mode standard (Linux/macOS/Windows natif)
    try:
        if verbose:
            print(f"[DEBUG] Plateforme : {platform.system()}")

        result = webbrowser.open(url)

        if result:
            if verbose:
                print("[DEBUG] ✓ webbrowser.open() réussi")
            return True
        else:
            if verbose:
                print("[DEBUG] ✗ webbrowser.open() a retourné False")
            return False

    except Exception as e:
        if verbose:
            print(f"[DEBUG] ✗ Exception : {e}")
        return False


def get_browser_command() -> str:
    """Retourne la commande qui sera utilisée pour ouvrir le navigateur."""
    if is_wsl():
        # Tester quelle méthode WSL est disponible
        methods = [
            ('wslview', 'wslview (recommandé)'),
            ('cmd.exe', 'cmd.exe /c start'),
            ('powershell.exe', 'powershell.exe -c start'),
            ('explorer.exe', 'explorer.exe (fallback)'),
        ]

        for cmd, desc in methods:
            try:
                subprocess.run(
                    [cmd, '--version'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=1
                )
                return desc
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        return "Aucune méthode WSL disponible"
    else:
        return f"webbrowser ({platform.system()})"
