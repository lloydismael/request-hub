/* iOS-flavoured Chart.js defaults. Loaded after Chart.js, before chart construction.
   Colours are read from CSS custom properties so the dark-mode toggle re-themes charts. */
(function () {
    'use strict';

    if (typeof Chart === 'undefined') {
        return;
    }

    var FONT = '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';

    function token(name, fallback) {
        var value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return value || fallback;
    }

    function palette() {
        return [
            token('--lg-accent', '#0a84ff'),
            token('--lg-ok', '#30d158'),
            token('--lg-warn', '#ff9f0a'),
            token('--lg-crit', '#ff453a'),
            token('--lg-violet', '#bf5af0'),
            token('--lg-teal', '#40c8e0')
        ];
    }

    function apply() {
        var ink = token('--lg-ink', '#0b1220');
        var inkSoft = token('--lg-ink-soft', 'rgba(11,18,32,0.62)');
        var divider = token('--lg-divider', 'rgba(11,18,32,0.09)');

        Chart.defaults.font.family = FONT;
        Chart.defaults.font.size = 12;
        Chart.defaults.color = inkSoft;
        Chart.defaults.borderColor = divider;

        Chart.defaults.plugins.legend.labels.color = inkSoft;
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.boxWidth = 8;
        Chart.defaults.plugins.legend.labels.padding = 14;

        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(18, 24, 40, 0.86)';
        Chart.defaults.plugins.tooltip.titleColor = '#fff';
        Chart.defaults.plugins.tooltip.bodyColor = 'rgba(255,255,255,0.86)';
        Chart.defaults.plugins.tooltip.borderColor = 'rgba(255,255,255,0.16)';
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        Chart.defaults.plugins.tooltip.cornerRadius = 12;
        Chart.defaults.plugins.tooltip.padding = 10;
        Chart.defaults.plugins.tooltip.displayColors = false;

        if (Chart.defaults.elements.bar) {
            Chart.defaults.elements.bar.borderRadius = 8;
            Chart.defaults.elements.bar.borderSkipped = false;
        }
        if (Chart.defaults.elements.line) {
            Chart.defaults.elements.line.tension = 0.35;
            Chart.defaults.elements.line.borderWidth = 2;
        }
        if (Chart.defaults.elements.point) {
            Chart.defaults.elements.point.radius = 3;
            Chart.defaults.elements.point.hoverRadius = 5;
        }
        if (Chart.defaults.elements.arc) {
            Chart.defaults.elements.arc.borderWidth = 0;
        }

        Chart.defaults.scale.grid.color = divider;
        Chart.defaults.scale.grid.drawTicks = false;
        Chart.defaults.scale.border = Chart.defaults.scale.border || {};
        Chart.defaults.scale.border.display = false;
        Chart.defaults.scale.ticks.color = inkSoft;
        Chart.defaults.scale.ticks.padding = 8;

        window.lgChartPalette = palette();
        window.lgChartInk = ink;
    }

    apply();

    // Re-theme existing charts when the dark-mode toggle flips the body class.
    var toggle = document.getElementById('theme-checkbox');
    if (toggle) {
        toggle.addEventListener('change', function () {
            setTimeout(function () {
                apply();
                var registry = Chart.instances || (Chart.registry && Chart.registry.instances);
                Object.keys(registry || {}).forEach(function (key) {
                    var chart = registry[key];
                    if (chart && typeof chart.update === 'function') {
                        chart.update('none');
                    }
                });
            }, 60);
        });
    }
}());
