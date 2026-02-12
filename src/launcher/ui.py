"""Interface utilisateur CLI avec animation Matrix et gestion des couleurs."""

import random
import time
from contextlib import contextmanager
from typing import Literal

from colorama import Fore, Style, init

# Initialiser colorama pour le support cross-platform
init(autoreset=True)

# Palette de couleurs
COLORS = {
    "banner": Fore.GREEN + Style.BRIGHT,
    "phase": Fore.CYAN + Style.BRIGHT,
    "success": Fore.GREEN,
    "warning": Fore.YELLOW,
    "error": Fore.RED + Style.BRIGHT,
    "info": Fore.WHITE,
    "skip": Fore.MAGENTA,
}

# Symboles
SYMBOLS = {
    "success": "✓",
    "error": "✗",
    "warning": "⚠",
    "info": "ℹ",
    "skip": "⊘",
}


class UIManager:
    """Gestionnaire d'interface utilisateur pour le launcher."""

    def __init__(self, verbose: bool = False, quiet: bool = False):
        self.verbose = verbose
        self.quiet = quiet
        self._phase_counter = 0

    def show_matrix_intro(self) -> None:
        """Afficher l'animation Matrix avant le banner."""
        if self.quiet:
            return

        # Caractères Matrix
        chars = "01█▓▒░"

        # Animation : 20 lignes de caractères aléatoires
        for _ in range(20):
            line = "".join(random.choice(chars) for _ in range(80))
            print(f"{COLORS['banner']}{line}")
            time.sleep(0.02)  # 400ms total

        print()  # Ligne vide avant le banner

    def show_banner(self) -> None:
        """Afficher le banner ASCII OLIST."""
        if self.quiet:
            return

        banner = f"""
{COLORS['banner']}╔═══════════════════════════════════════════════════════════╗
{COLORS['banner']}║              OLIST Dashboard Launcher v1.0                ║
{COLORS['banner']}╚═══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(banner)

    def show_separator(self) -> None:
        """Afficher un séparateur de section."""
        if not self.quiet:
            print("─" * 60)

    @contextmanager
    def phase_context(self, title: str):
        """Context manager pour une phase avec header et timing."""
        self._phase_counter += 1
        phase_num = self._phase_counter

        if not self.quiet:
            self.show_separator()
            print(f"{COLORS['phase']}PHASE {phase_num}: {title}{Style.RESET_ALL}")
            self.show_separator()

        start = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start
            if not self.quiet:
                self.success(f"Phase completed in {elapsed:.2f}s")
                print()

    def success(self, message: str) -> None:
        """Afficher un message de succès."""
        if not self.quiet:
            print(f"{COLORS['success']}{SYMBOLS['success']} {message}{Style.RESET_ALL}")

    def error(self, message: str) -> None:
        """Afficher un message d'erreur."""
        print(f"{COLORS['error']}{SYMBOLS['error']} {message}{Style.RESET_ALL}")

    def warning(self, message: str) -> None:
        """Afficher un message d'avertissement."""
        if not self.quiet:
            print(f"{COLORS['warning']}{SYMBOLS['warning']} {message}{Style.RESET_ALL}")

    def info(self, message: str) -> None:
        """Afficher un message d'information."""
        if self.verbose or not self.quiet:
            print(f"{COLORS['info']}{SYMBOLS['info']} {message}{Style.RESET_ALL}")

    def skip(self, message: str) -> None:
        """Afficher un message de skip."""
        if not self.quiet:
            print(f"\n{COLORS['skip']}{SYMBOLS['skip']} Skipping: {message}{Style.RESET_ALL}\n")

    def display_live_log(self, level: str, message: str) -> None:
        """Afficher un log en temps réel depuis le bridge."""
        if self.quiet and level.upper() not in ["ERROR", "CRITICAL"]:
            return

        level_colors = {
            "DEBUG": Fore.CYAN,
            "INFO": Fore.WHITE,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Fore.RED + Style.BRIGHT,
        }

        color = level_colors.get(level.upper(), Fore.WHITE)
        print(f"  {color}[{level}] {message}{Style.RESET_ALL}")

    def show_success_box(self, url: str) -> None:
        """Afficher la box de succès finale avec l'URL du dashboard."""
        if self.quiet:
            print(f"Dashboard: {url}")
            return

        # Box parfaitement alignée (largeur intérieure: 59 caractères)
        width = 59
        title = "DASHBOARD READY"
        access_label = f"Access: {url}"
        stop_msg = "Press Ctrl+C to stop"

        # Centrer le titre
        title_padding = (width - len(title)) // 2
        title_line = f"║{' ' * title_padding}{title}{' ' * (width - len(title) - title_padding)}║"

        # Ligne vide
        empty_line = f"║{' ' * width}║"

        # Ligne d'accès (alignée à gauche avec 2 espaces de marge)
        access_line = f"║  {access_label}{' ' * (width - len(access_label) - 2)}║"

        # Ligne stop (alignée à gauche avec 2 espaces de marge)
        stop_line = f"║  {stop_msg}{' ' * (width - len(stop_msg) - 2)}║"

        box = f"""
{COLORS['success']}╔{'═' * width}╗
{title_line}
{empty_line}
{access_line}
{stop_line}
╚{'═' * width}╝{Style.RESET_ALL}
"""
        print(box)
