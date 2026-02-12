/**
 * Matrix Rain Animation
 *
 * Affiche une animation de "pluie" de caractères style Matrix
 * en arrière-plan du splash screen.
 */

(function() {
    const canvas = document.getElementById('matrix-canvas');
    const ctx = canvas.getContext('2d');

    // Configuration
    const config = {
        fontSize: 14,
        chars: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*',
        speed: 50, // ms entre les frames
        dropSpeed: 1, // vitesse de chute
    };

    // Resize canvas to window
    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }

    // Initialize
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Colonnes de caractères
    const columns = Math.floor(canvas.width / config.fontSize);
    const drops = Array(columns).fill(0);

    /**
     * Dessine une frame de l'animation
     */
    function draw() {
        // Fond semi-transparent pour effet de trail
        ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Style de texte
        ctx.fillStyle = '#00ff00';
        ctx.font = `${config.fontSize}px monospace`;

        // Pour chaque colonne
        for (let i = 0; i < drops.length; i++) {
            // Caractère aléatoire
            const char = config.chars[Math.floor(Math.random() * config.chars.length)];

            // Position
            const x = i * config.fontSize;
            const y = drops[i] * config.fontSize;

            // Dessiner le caractère
            ctx.fillText(char, x, y);

            // Reset la goutte si elle atteint le bas ou aléatoirement
            if (y > canvas.height && Math.random() > 0.975) {
                drops[i] = 0;
            }

            // Descendre la goutte
            drops[i] += config.dropSpeed;
        }
    }

    // Animation loop
    setInterval(draw, config.speed);
})();
