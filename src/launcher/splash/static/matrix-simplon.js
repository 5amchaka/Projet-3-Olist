// Simplon Rain — Pluie de caractères aux couleurs de la DA Simplon
// Rouge primaire #E2001A, accents plus clairs, fond sombre bleuté
(function() {
    const canvas = document.getElementById('matrix-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const config = {
        fontSize: 14,
        chars: 'SIMPLON0123456789abcdefghijklmnopqrstuvwxyz{}[]<>=/+*',
        brandLetters: new Set(['S', 'I', 'M', 'P', 'L', 'O', 'N']),
        speed: 45,
        dropSpeed: 1,
        // Couleurs fidèles à la DA
        brandColor: '#E2001A',      // Rouge Simplon primaire
        brandGlow: '#FF3348',       // Rouge clair pour le glow
        dimColor: '#4A0A12',        // Rouge très sombre pour les caractères normaux
        trailColor: '#1A0508',      // Trace subtile
    };

    let columns, drops, chars, stayTime;

    function initArrays() {
        columns = Math.floor(canvas.width / config.fontSize);
        drops = new Array(columns);
        chars = new Array(columns);
        stayTime = new Array(columns);
        for (let i = 0; i < columns; i++) {
            drops[i] = Math.random() * -50;  // Démarrage décalé
            chars[i] = '';
            stayTime[i] = 0;
        }
    }

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        initArrays();
    }

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    function draw() {
        // Fond semi-transparent pour l'effet de traînée
        ctx.fillStyle = 'rgba(15, 15, 20, 0.06)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.font = `${config.fontSize}px 'Source Sans 3', 'Consolas', monospace`;

        for (let i = 0; i < columns; i++) {
            const charPool = config.chars;
            const char = chars[i] || charPool[Math.floor(Math.random() * charPool.length)];
            const x = i * config.fontSize;
            const y = drops[i] * config.fontSize;

            // Skip si hors écran (au-dessus)
            if (y < 0) {
                drops[i] += config.dropSpeed;
                chars[i] = charPool[Math.floor(Math.random() * charPool.length)];
                continue;
            }

            ctx.shadowBlur = 0;
            ctx.shadowColor = 'transparent';

            if (config.brandLetters.has(char.toUpperCase())) {
                // Lettres SIMPLON : rouge vif + glow
                ctx.fillStyle = config.brandColor;
                ctx.shadowColor = config.brandGlow;
                ctx.shadowBlur = 12;

                // Rester plus longtemps visible
                if (stayTime[i] < 15) {
                    stayTime[i]++;
                    ctx.fillText(char.toUpperCase(), x, y);
                    ctx.shadowBlur = 0;
                    continue;
                }
            } else {
                // Caractères normaux : rouge très atténué
                ctx.fillStyle = config.dimColor;
            }

            ctx.fillText(char, x, y);
            ctx.shadowBlur = 0;

            // Reset ou descente
            if (y > canvas.height && Math.random() > 0.975) {
                drops[i] = 0;
                chars[i] = charPool[Math.floor(Math.random() * charPool.length)];
                stayTime[i] = 0;
            } else {
                drops[i] += config.dropSpeed;
                chars[i] = charPool[Math.floor(Math.random() * charPool.length)];
            }
        }
    }

    setInterval(draw, config.speed);
})();
