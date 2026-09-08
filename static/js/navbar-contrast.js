(function () {
    'use strict';

    const navbar = document.querySelector('.navbar[data-nav-surface]');
    if (!navbar) return;

    const body = document.body;
    const sections = Array.from(document.querySelectorAll('[data-navbar-surface]'));
    const validSurface = (value) => value === 'dark' || value === 'light';
    const resolveSectionSurface = (value) => value === 'theme' ? defaultSurface() : value;
    let observer = null;
    let rebuildFrame = 0;
    let pendingSurface = null;

    const defaultSurface = () => (
        body.classList.contains('pref-reduce-effects') || body.classList.contains('dark-mode')
            ? 'dark'
            : 'light'
    );

    const updatesSuspended = () => (
        body.classList.contains('theme-switching') || body.classList.contains('table-scroll-active')
    );

    const setSurface = (surface) => {
        const next = validSurface(surface) ? surface : defaultSurface();
        navbar.dataset.navDefaultSurface = defaultSurface();

        if (updatesSuspended()) {
            pendingSurface = next;
            return;
        }

        pendingSurface = null;
        if (navbar.dataset.navSurface !== next) navbar.dataset.navSurface = next;
    };

    const chooseSurfaceAtNavbarCenter = () => {
        if (!sections.length || updatesSuspended()) return;

        const navRect = navbar.getBoundingClientRect();
        const probeY = Math.min(window.innerHeight - 1, Math.max(0, navRect.top + navRect.height / 2));
        let selected = null;

        sections.forEach((section) => {
            const rect = section.getBoundingClientRect();
            if (rect.top > probeY || rect.bottom < probeY || rect.right <= 0 || rect.left >= window.innerWidth) return;

            const visibleWidth = Math.max(0, Math.min(rect.right, window.innerWidth) - Math.max(rect.left, 0));
            if (!selected || visibleWidth > selected.visibleWidth) {
                selected = { surface: resolveSectionSurface(section.dataset.navbarSurface), visibleWidth };
            }
        });

        setSurface(selected && validSurface(selected.surface) ? selected.surface : defaultSurface());
    };

    const rebuildObserver = () => {
        window.cancelAnimationFrame(rebuildFrame);
        rebuildFrame = window.requestAnimationFrame(() => {
            if (observer) observer.disconnect();
            if (!sections.length || !('IntersectionObserver' in window)) {
                setSurface(defaultSurface());
                return;
            }

            const navRect = navbar.getBoundingClientRect();
            const center = Math.max(0, Math.min(window.innerHeight, navRect.top + navRect.height / 2));
            const topMargin = -Math.max(0, Math.floor(center));
            const bottomMargin = -Math.max(0, Math.ceil(window.innerHeight - center - 1));

            observer = new IntersectionObserver(chooseSurfaceAtNavbarCenter, {
                root: null,
                rootMargin: `${topMargin}px 0px ${bottomMargin}px 0px`,
                threshold: 0
            });
            sections.forEach((section) => observer.observe(section));
            chooseSurfaceAtNavbarCenter();
        });
    };

    navbar.dataset.navDefaultSurface = defaultSurface();
    setSurface(defaultSurface());
    rebuildObserver();

    if ('ResizeObserver' in window) {
        new ResizeObserver(rebuildObserver).observe(navbar);
    } else {
        window.addEventListener('resize', rebuildObserver, { passive: true });
    }

    window.addEventListener('requesthub:theme-changed', () => {
        window.requestAnimationFrame(() => {
            navbar.dataset.navDefaultSurface = defaultSurface();
            chooseSurfaceAtNavbarCenter();
        });
    });

    document.addEventListener('requesthub:table-scroll-end', () => {
        setSurface(pendingSurface || defaultSurface());
        chooseSurfaceAtNavbarCenter();
    });

    new MutationObserver(() => {
        if (!updatesSuspended()) {
            setSurface(pendingSurface || defaultSurface());
            chooseSurfaceAtNavbarCenter();
        }
    }).observe(body, { attributes: true, attributeFilter: ['class'] });
}());