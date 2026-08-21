(function () {
    'use strict';

    const DIRECTION_KEY = 'reqHubPageTransitionDirection';
    const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';

    const prefersReducedMotion = () => (
        window.matchMedia(REDUCED_MOTION_QUERY).matches ||
        document.body.classList.contains('pref-reduce-motion')
    );

    const setDirection = (direction) => {
        if (prefersReducedMotion()) return;

        document.documentElement.dataset.pageTransitionDirection = direction;
        try {
            sessionStorage.setItem(DIRECTION_KEY, direction);
        } catch (_) {}
    };

    const isEligibleNavigation = (event, link) => {
        if (
            event.defaultPrevented ||
            event.button !== 0 ||
            event.metaKey ||
            event.ctrlKey ||
            event.shiftKey ||
            event.altKey ||
            !link ||
            link.hasAttribute('download') ||
            link.dataset.noPageTransition !== undefined ||
            (link.target && link.target.toLowerCase() !== '_self')
        ) {
            return false;
        }

        const href = link.getAttribute('href');
        if (!href || href.startsWith('#')) return false;

        let destination;
        try {
            destination = new URL(link.href, window.location.href);
        } catch (_) {
            return false;
        }

        if (!/^https?:$/.test(destination.protocol) || destination.origin !== window.location.origin) {
            return false;
        }

        const currentWithoutHash = window.location.href.split('#', 1)[0];
        const destinationWithoutHash = destination.href.split('#', 1)[0];
        return currentWithoutHash !== destinationWithoutHash;
    };

    document.addEventListener('click', (event) => {
        const link = event.target.closest('a[href]');
        if (isEligibleNavigation(event, link)) setDirection('forward');
    }, { capture: true, passive: true });

    window.addEventListener('pageswap', (event) => {
        const activation = event.activation;
        if (!activation || activation.navigationType !== 'traverse') return;

        const fromIndex = activation.from && activation.from.index;
        const toIndex = activation.entry && activation.entry.index;
        setDirection(
            Number.isInteger(fromIndex) && Number.isInteger(toIndex) && toIndex > fromIndex
                ? 'forward'
                : 'back'
        );
    });

    window.addEventListener('popstate', () => setDirection('back'));

}());