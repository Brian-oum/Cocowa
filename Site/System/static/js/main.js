document.addEventListener("DOMContentLoaded", function () {

    let currentSlide = 0;

    const slides = document.querySelectorAll('.home-slide');
    const dots = document.querySelectorAll('.dot');

    if (!slides.length) return; // safety check

    function showSlide(index) {
        slides.forEach(s => s.classList.remove('active'));
        dots.forEach(d => d.classList.remove('active'));

        slides[index].classList.add('active');

        if (dots[index]) {
            dots[index].classList.add('active');
        }
    }

    function nextSlide() {
        currentSlide = (currentSlide + 1) % slides.length;
        showSlide(currentSlide);
    }

    setInterval(nextSlide, 5000);

    dots.forEach((dot, i) => {
        dot.addEventListener("click", () => {
            currentSlide = i;
            showSlide(i);
        });
    });

});

function toggleMenu() {
    const nav = document.querySelector(".nav-links");

    if (nav) {
        nav.classList.toggle("active");
    }
}

document.addEventListener("click", function (e) {
    const nav = document.querySelector(".nav-links");
    const hamburger = document.querySelector(".hamburger");

    if (!nav || !hamburger) return;

    const clickedInsideMenu = nav.contains(e.target);
    const clickedHamburger = hamburger.contains(e.target);

    if (!clickedInsideMenu && !clickedHamburger) {
        nav.classList.remove("active");
    }
});

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
        drawWave(canvas.height * 0.8, 55, 0.005, 400);
    }

    window.addEventListener('load', drawWavyBackground);
    window.addEventListener('resize', drawWavyBackground);

(function () {
  // 1. Scroll-reveal observer
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const delay = el.dataset.revealDelay || 0;
          setTimeout(() => el.classList.add('revealed'), Number(delay));
          revealObserver.unobserve(el);
        }
      });
    },
    { threshold: 0.12 }
  );

  document.querySelectorAll('[data-reveal], [data-stagger]').forEach((el) =>
    revealObserver.observe(el)
  );

  // 2. Sticky-nav compact class
  const nav = document.querySelector('.main-nav');
  if (nav) {
    window.addEventListener('scroll', () => {
      nav.classList.toggle('scrolled', window.scrollY > 60);
    }, { passive: true });
  }
})();