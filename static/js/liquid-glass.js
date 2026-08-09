/* Liquid Glass interactions — login card tilt, sheen, staggered entrance, submit state.
   CSS provides the baseline animation; Motion One (if reachable) upgrades the entrance.
   Everything degrades gracefully when the CDN is blocked. */
(function () {
    'use strict';

    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches ||
        (document.body && document.body.classList.contains('pref-reduce-motion'));
    var coarsePointer = window.matchMedia('(pointer: coarse)').matches;

    /* ---- Staggered entrance (CSS-driven, no dependency) ---- */
    function normalizeDelaySeconds(raw, index) {
        var delay = parseFloat(raw);
        if (!Number.isFinite(delay)) {
            return index * 0.06;
        }
        // Login uses fractional seconds (0.12). Management/Reports use ms (40, 80…).
        if (delay > 5) {
            delay = delay / 1000;
        }
        return Math.max(0, delay);
    }

    function primeEntrance() {
        // Reduce Motion (OS setting or the app's pref-reduce-motion class):
        // skip the stagger entirely — elements render visible with no animation.
        if (reduceMotion) {
            document.body.classList.add('lg-enter-ready');
            return;
        }
        var items = document.querySelectorAll('.lg-enter');
        for (var i = 0; i < items.length; i += 1) {
            var delay = normalizeDelaySeconds(items[i].getAttribute('data-lg-delay'), i);
            items[i].style.setProperty('--lg-delay', delay + 's');
        }
        requestAnimationFrame(function () {
            document.body.classList.add('lg-enter-ready');
        });
    }

    /* ---- Pointer tilt + sheen tracking ---- */
    function bindCardMotion(card) {
        if (reduceMotion || coarsePointer) {
            return;
        }

        var frame = null;
        var maxTilt = 4;

        function apply(event) {
            frame = null;
            var rect = card.getBoundingClientRect();
            var px = (event.clientX - rect.left) / rect.width;
            var py = (event.clientY - rect.top) / rect.height;
            card.style.setProperty('--lg-tilt-y', ((px - 0.5) * maxTilt * 2).toFixed(2) + 'deg');
            card.style.setProperty('--lg-tilt-x', ((0.5 - py) * maxTilt * 2).toFixed(2) + 'deg');
            card.style.setProperty('--lg-sheen-x', (px * 100).toFixed(1) + '%');
            card.style.setProperty('--lg-sheen-y', (py * 100).toFixed(1) + '%');
        }

        card.addEventListener('pointermove', function (event) {
            if (event.pointerType !== 'mouse') {
                return;
            }
            card.classList.add('login-card--tilt');
            if (frame === null) {
                frame = requestAnimationFrame(function () {
                    apply(event);
                });
            }
        });

        card.addEventListener('pointerleave', function () {
            if (frame !== null) {
                cancelAnimationFrame(frame);
                frame = null;
            }
            card.classList.remove('login-card--tilt');
            card.style.removeProperty('--lg-tilt-x');
            card.style.removeProperty('--lg-tilt-y');
        });
    }

    /* ---- Error shake ---- */
    function bindErrorShake(card) {
        if (reduceMotion) {
            return;
        }
        if (!card.querySelector('.alert, .invalid-feedback')) {
            return;
        }
        requestAnimationFrame(function () {
            card.classList.add('login-card--shake');
            card.addEventListener('animationend', function handler(event) {
                if (event.animationName === 'lg-shake') {
                    card.classList.remove('login-card--shake');
                    card.removeEventListener('animationend', handler);
                }
            });
        });
    }

    /* ---- Submit spinner ---- */
    function bindSubmitState(form) {
        var button = form.querySelector('.login-card__submit');
        if (!button) {
            return;
        }
        form.addEventListener('submit', function () {
            if (form.checkValidity && !form.checkValidity()) {
                return;
            }
            button.setAttribute('data-loading', 'true');
            button.setAttribute('aria-busy', 'true');
        });
    }

    /* ---- Success overlay progress bar synced to the redirect delay ---- */
    function syncSuccessProgress() {
        var overlay = document.querySelector('[data-login-success-overlay]');
        if (!overlay) {
            return;
        }
        var delay = parseInt(overlay.getAttribute('data-redirect-delay'), 10);
        if (Number.isFinite(delay) && delay > 0) {
            overlay.style.setProperty('--lg-progress-duration', delay + 'ms');
        }
    }

    function init() {
        primeEntrance();
        syncSuccessProgress();

        var card = document.querySelector('.page-login .login-card');
        if (card) {
            bindCardMotion(card);
            bindErrorShake(card);
        }

        var form = document.querySelector('.login-form');
        if (form) {
            bindSubmitState(form);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}());
