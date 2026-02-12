/**
 * Splash Screen WebSocket Client
 *
 * Connecte au launcher backend et affiche les phases/logs en temps réel.
 */

class SplashClient {
    constructor() {
        this.ws = null;
        this.totalPhases = 8;  // Max possible (peut être mis à jour)
        this.currentPhase = 0;
        this.logCount = 0;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;

        // Éléments DOM
        this.elements = {
            phaseNum: document.querySelector('.phase-num'),
            phaseTitle: document.querySelector('.phase-title'),
            progressBar: document.getElementById('progress-bar'),
            progressPercent: document.getElementById('progress-percent'),
            progressPhase: document.getElementById('progress-phase'),
            logOutput: document.getElementById('log-output'),
            logsCount: document.getElementById('logs-count'),
            successBox: document.getElementById('success-box'),
            errorBox: document.getElementById('error-box'),
            errorMessage: document.getElementById('error-message'),
            dashboardUrl: document.getElementById('dashboard-url'),
        };

        this.connect();
        this.setupRetryButton();
    }

    /**
     * Connecte au serveur WebSocket
     */
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleEvent(data);
            } catch (error) {
                console.error('Failed to parse message:', error);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.handleDisconnect();
        };
    }

    /**
     * Gère la déconnexion et tentatives de reconnexion
     */
    handleDisconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
            console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
            setTimeout(() => this.connect(), delay);
        } else {
            this.showError('Connection lost. Please refresh the page.');
        }
    }

    /**
     * Gère un événement reçu du serveur
     */
    handleEvent(event) {
        const { type, data } = event;

        switch (type) {
            case 'connected':
                console.log('Connected:', data.message);
                break;

            case 'config':
                // Configuration du nombre de phases
                if (data.total_phases) {
                    this.totalPhases = data.total_phases;
                    console.log(`Total phases configured: ${this.totalPhases}`);
                }
                break;

            case 'phase_start':
                this.updatePhase(data);
                break;

            case 'phase_complete':
                this.completePhase(data);
                break;

            case 'log':
                this.addLog(data);
                break;

            case 'dashboard_ready':
                this.showSuccess(data);
                break;

            case 'error':
                this.showError(data.message, data.fatal);
                break;

            default:
                console.warn('Unknown event type:', type);
        }
    }

    /**
     * Met à jour l'affichage de la phase courante
     */
    updatePhase(data) {
        this.currentPhase = data.phase_num;

        this.elements.phaseNum.textContent = `PHASE ${data.phase_num}`;
        this.elements.phaseTitle.textContent = data.title;

        this.updateProgress();

        // Animation
        this.elements.phaseNum.style.animation = 'none';
        setTimeout(() => {
            this.elements.phaseNum.style.animation = 'pulse 2s ease-in-out infinite';
        }, 10);
    }

    /**
     * Marque une phase comme complétée
     */
    completePhase(data) {
        const durationSec = (data.duration_ms / 1000).toFixed(2);
        this.addLog({
            level: 'SUCCESS',
            message: `✓ Phase ${data.phase_num} completed in ${durationSec}s`,
        });
    }

    /**
     * Met à jour la barre de progression
     */
    updateProgress() {
        const percent = Math.round((this.currentPhase / this.totalPhases) * 100);

        this.elements.progressBar.style.width = `${percent}%`;
        this.elements.progressPercent.textContent = `${percent}%`;
        this.elements.progressPhase.textContent = `Phase ${this.currentPhase}/${this.totalPhases}`;
    }

    /**
     * Ajoute une entrée de log
     */
    addLog(data) {
        const { level = 'INFO', message } = data;

        const entry = document.createElement('div');
        entry.className = `log-entry ${level}`;
        entry.textContent = message;

        this.elements.logOutput.appendChild(entry);

        // Auto-scroll vers le bas
        this.elements.logOutput.scrollTop = this.elements.logOutput.scrollHeight;

        // Mettre à jour le compteur
        this.logCount++;
        this.elements.logsCount.textContent = `${this.logCount} messages`;

        // Limiter le nombre de logs (garder les 100 derniers)
        const maxLogs = 100;
        while (this.elements.logOutput.children.length > maxLogs) {
            this.elements.logOutput.removeChild(this.elements.logOutput.firstChild);
        }
    }

    /**
     * Affiche l'état de succès et redirige vers le dashboard
     */
    showSuccess(data) {
        const { url, redirect_delay_ms = 3000 } = data;

        // Afficher la success box
        this.elements.successBox.classList.remove('hidden');
        this.elements.dashboardUrl.textContent = url;

        // Mettre la barre de progression à 100%
        this.currentPhase = this.totalPhases;
        this.updateProgress();

        // Configurer les boutons d'action
        const baseUrl = url.replace(/\/presentation\/?$/, '');
        const btnPresentation = document.getElementById('btn-presentation');
        const btnModule = document.getElementById('btn-module');
        if (btnPresentation) {
            btnPresentation.href = `${baseUrl}/presentation`;
        }
        if (btnModule) {
            btnModule.href = `${baseUrl}/presentation/module_1_fundamentals/0`;
        }

        // Rediriger après le délai
        setTimeout(() => {
            window.location.href = url;
        }, redirect_delay_ms);
    }

    /**
     * Affiche un message d'erreur
     */
    showError(message, fatal = false) {
        this.elements.errorBox.classList.remove('hidden');
        this.elements.errorMessage.textContent = message;

        // Ajouter aussi dans les logs
        this.addLog({
            level: 'ERROR',
            message: `✗ ERROR: ${message}`,
        });

        // Si erreur fatale, arrêter l'animation de phase
        if (fatal) {
            const phaseDisplay = document.querySelector('.phase-display');
            phaseDisplay.style.animation = 'none';
        }
    }

    /**
     * Configure le bouton de retry
     */
    setupRetryButton() {
        const retryBtn = document.getElementById('retry-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                window.location.reload();
            });
        }
    }
}

// Initialiser le client au chargement de la page
window.addEventListener('DOMContentLoaded', () => {
    new SplashClient();
});
