(function () {
    var overlay = document.querySelector('[data-login-success-overlay]');
    if (!overlay) {
        return;
    }

    var redirectDelay = parseInt(overlay.getAttribute('data-redirect-delay'), 10);
    if (!Number.isFinite(redirectDelay) || redirectDelay < 0) {
        redirectDelay = 1800;
    }

    requestAnimationFrame(function () {
        overlay.classList.add('login-success-overlay--visible');
    });


    setTimeout(function () {
        overlay.classList.add('login-success-overlay--fade');
    }, redirectDelay);

    overlay.addEventListener('transitionend', function (event) {
        if (event.propertyName === 'opacity' && overlay.classList.contains('login-success-overlay--fade')) {
            overlay.remove();
        }
    });
})();
