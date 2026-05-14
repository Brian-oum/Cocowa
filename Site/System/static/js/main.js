
    let currentSlide = 0;
    const slides = document.querySelectorAll('.slide');
    const dots = document.querySelectorAll('.dot');

    function showSlide(index) {
        slides.forEach(s => s.classList.remove('active'));
        dots.forEach(d => d.classList.remove('active'));
        
        slides[index].classList.add('active');
        dots[index].classList.add('active');
    }

    function nextSlide() {
        currentSlide = (currentSlide + 1) % slides.length;
        showSlide(currentSlide);
    }

    // Change slide every 5 seconds
    setInterval(nextSlide, 5000);

function drawWavyBackground() {
        const canvas = document.getElementById('waveCanvas');
        const ctx = canvas.getContext('2d');
        
        // Match canvas size to the section size
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Increased visibility: Using a darker teal with 0.2 opacity instead of 0.08
        ctx.strokeStyle = 'rgba(0, 104, 55, 0.2)'; 
        ctx.lineWidth = 3; // Thicker lines for better visibility

        function drawWave(yOffset, amplitude, frequency, shift) {
            ctx.beginPath();
            ctx.moveTo(0, canvas.height / 2);

            for (let x = 0; x < canvas.width; x++) {
                // Added a 'shift' to move the waves horizontally so they don't overlap perfectly
                const y = Math.sin((x + shift) * frequency) * amplitude + yOffset;
                ctx.lineTo(x, y);
            }
            ctx.stroke();
        }

        // Draw 5 overlapping waves with varying heights to mimic the screenshot bubbles
        drawWave(canvas.height * 0.3, 50, 0.004, 0);
        drawWave(canvas.height * 0.4, 80, 0.002, 100);
        drawWave(canvas.height * 0.5, 40, 0.006, 200);
        drawWave(canvas.height * 0.6, 70, 0.003, 300);
        drawWave(canvas.height * 0.8, 55, 0.005, 400);
    }

    window.addEventListener('load', drawWavyBackground);
    window.addEventListener('resize', drawWavyBackground);