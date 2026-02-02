document.addEventListener('DOMContentLoaded', function () {
    const slides = document.querySelectorAll('.slide-item');
    const nextBtn = document.querySelector('.slider-nav.next');
    const prevBtn = document.querySelector('.slider-nav.prev');
    let currentSlide = 0;

    function showSlide(index) {
        // Hide all slides
        slides.forEach(slide => {
            slide.classList.remove('active');
        });

        // Calculate valid index
        if (index >= slides.length) {
            currentSlide = 0;
        } else if (index < 0) {
            currentSlide = slides.length - 1;
        } else {
            currentSlide = index;
        }

        // Show current slide
        slides[currentSlide].classList.add('active');
    }

    // Event Listeners
    nextBtn.addEventListener('click', () => {
        showSlide(currentSlide + 1);
    });

    prevBtn.addEventListener('click', () => {
        showSlide(currentSlide - 1);
    });

    // Optional: Auto-advance every 5 seconds
    setInterval(() => {
        showSlide(currentSlide + 1);
    }, 5000);
});
