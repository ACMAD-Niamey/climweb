(function () {
    'use strict';

    const FALLBACK_CATEGORIES = [
        {key: 'weather', label: 'Weather'},
        {key: 'drought', label: 'Drought'},
        {key: 'climate', label: 'Climate'},
        {key: 'flood', label: 'Flood'},
    ];
    const RASTER_SOURCE_ID = 'mhz-raster-source';
    const RASTER_LAYER_ID = 'mhz-raster-layer';

    let map = null;
    let activeToken = 0;
    let groupedLayers = {};
    let config = {};
    let warnedCategoryFailure = false;

    const baseStyle = {
        version: 8,
        glyphs: 'https://tiles.basemaps.cartocdn.com/fonts/{fontstack}/{range}.pbf',
        sources: {
            voyager: {
                type: 'raster',
                tiles: [
                    'https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png',
                    'https://b.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png',
                    'https://c.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png',
                    'https://d.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png',
                ],
                tileSize: 256,
                attribution: '&copy; OpenStreetMap &copy; CARTO',
            },
        },
        layers: [{
            id: 'voyager-layer',
            source: 'voyager',
            type: 'raster',
            minzoom: 0,
            maxzoom: 22,
        }],
    };

    function joinUrl(base, path) {
        return `${base.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`;
    }

    function fetchJson(url, timeoutMs) {
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), timeoutMs || 15000);
        return fetch(url, {signal: controller.signal})
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status} for ${url}`);
                }
                return response.json();
            })
            .finally(() => window.clearTimeout(timeout));
    }

    function normalizeList(payload) {
        if (Array.isArray(payload)) {
            return payload;
        }
        if (payload && Array.isArray(payload.results)) {
            return payload.results;
        }
        if (payload && Array.isArray(payload.layers)) {
            return payload.layers;
        }
        return [];
    }

    function parseBounds(value) {
        if (!value) {
            return null;
        }
        try {
            const parsed = JSON.parse(value.replace(/'/g, '"'));
            if (Array.isArray(parsed) && parsed.length === 4 && parsed.every(Number.isFinite)) {
                return [[parsed[0], parsed[1]], [parsed[2], parsed[3]]];
            }
        } catch (error) {
            return null;
        }
        return null;
    }

    function loadCategories() {
        return fetchJson(joinUrl(config.apiBaseUrl, '/api/catalog/hazard-categories/'))
            .then((payload) => {
                const categories = normalizeList(payload)
                    .map((category) => ({
                        key: category.key || category.slug || category.name,
                        label: category.label || category.title || category.name || category.key,
                    }))
                    .filter((category) => category.key && category.label);
                return categories.length ? categories : FALLBACK_CATEGORIES;
            })
            .catch(() => FALLBACK_CATEGORIES);
    }

    function loadLayers() {
        const url = joinUrl(config.apiBaseUrl, `/api/catalog/ui/layers?project=${encodeURIComponent(config.projectSlug)}`);
        return fetchJson(url).then((payload) => normalizeList(payload).filter((layer) => {
            return layer && layer.icon && layer.icon.url && layer.dataset && layer.dataset.id;
        }));
    }

    function inferCategory(layer) {
        if (layer.hazard_category) {
            if (typeof layer.hazard_category === 'string') {
                return layer.hazard_category;
            }
            return layer.hazard_category.key || layer.hazard_category.slug || layer.hazard_category.name;
        }

        const text = [
            layer.title,
            layer.name,
            layer.description,
            layer.dataset && layer.dataset.id,
            layer.dataset && layer.dataset.type,
        ].filter(Boolean).join(' ').toLowerCase();

        if (/drought|spi|spei|vci|vegetation|soil moisture|rainfall deficit/.test(text)) {
            return 'drought';
        }
        if (/flood|inundation|river|streamflow|water level/.test(text)) {
            return 'flood';
        }
        if (/climate|temperature|rainfall|precipitation|seasonal|forecast|anomaly/.test(text)) {
            return 'climate';
        }
        if (/weather|storm|wind|heat|hazard|warning/.test(text)) {
            return 'weather';
        }
        return 'weather';
    }

    function groupByCategory(layers, categories) {
        const grouped = {};
        categories.forEach((category) => {
            grouped[category.key] = [];
        });
        layers.forEach((layer) => {
            const key = inferCategory(layer);
            if (!grouped[key]) {
                grouped[key] = [];
            }
            grouped[key].push(layer);
        });
        return grouped;
    }

    function visibleTabs(categories, grouped) {
        return categories.filter((category) => grouped[category.key] && grouped[category.key].length).slice(0, 4);
    }

    function createMap(mount) {
        map = new maplibregl.Map({
            container: mount,
            style: baseStyle,
            center: [17, 2],
            zoom: 2.4,
            scrollZoom: false,
            attributionControl: false,
        });
        map.addControl(new maplibregl.NavigationControl({showCompass: false}), 'top-right');
        map.addControl(new maplibregl.AttributionControl({compact: true}), 'bottom-right');

        const bounds = parseBounds(config.countryBounds);
        if (bounds) {
            map.fitBounds(bounds, {padding: 20, duration: 0});
        }
    }

    function clearByClass(mount, className) {
        mount.querySelectorAll(`.${className}`).forEach((node) => node.remove());
    }

    function renderTabs(mount, tabs) {
        clearByClass(mount, 'mhz-tabs');
        const wrapper = document.createElement('div');
        wrapper.className = 'mhz-tabs';
        tabs.forEach((tab) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'mhz-tab';
            button.dataset.key = tab.key;
            button.textContent = tab.label;
            button.addEventListener('click', () => activateCategory(mount, tab.key));
            wrapper.appendChild(button);
        });
        mount.appendChild(wrapper);
    }

    function setActiveTab(mount, key) {
        mount.querySelectorAll('.mhz-tab').forEach((tab) => {
            tab.classList.toggle('is-active', tab.dataset.key === key);
        });
    }

    function renderLegend(mount, legend) {
        clearByClass(mount, 'mhz-legend');
        const entries = Object.entries(legend || {});
        if (!entries.length) {
            return;
        }
        const wrapper = document.createElement('div');
        wrapper.className = 'mhz-legend';
        entries.forEach(([label, color]) => {
            const row = document.createElement('div');
            row.className = 'mhz-legend-row';
            const dot = document.createElement('span');
            dot.className = 'mhz-legend-dot';
            dot.style.backgroundColor = color;
            const text = document.createElement('span');
            text.textContent = label;
            row.appendChild(dot);
            row.appendChild(text);
            wrapper.appendChild(row);
        });
        mount.appendChild(wrapper);
    }

    function renderDateChip(mount, dateText) {
        clearByClass(mount, 'mhz-date-chip');
        if (!dateText) {
            return;
        }
        const chip = document.createElement('div');
        chip.className = 'mhz-date-chip';
        chip.textContent = `${config.msgLatest}: ${dateText}`;
        mount.appendChild(chip);
    }

    function showNoData(mount, visible) {
        clearByClass(mount, 'mhz-nodata');
        if (!visible) {
            return;
        }
        const overlay = document.createElement('div');
        overlay.className = 'mhz-nodata';
        overlay.textContent = config.msgNoData;
        mount.appendChild(overlay);
    }

    function showUnavailable(mount) {
        mount.innerHTML = '';
        const panel = document.createElement('div');
        panel.className = 'mhz-unavailable';
        panel.textContent = config.msgUnavailable;
        mount.appendChild(panel);
    }

    function removeRasterLayer() {
        if (!map) {
            return;
        }
        if (map.getLayer(RASTER_LAYER_ID)) {
            map.removeLayer(RASTER_LAYER_ID);
        }
        if (map.getSource(RASTER_SOURCE_ID)) {
            map.removeSource(RASTER_SOURCE_ID);
        }
    }

    function addRasterLayer(tileUrl) {
        const addLayer = () => {
            removeRasterLayer();
            map.addSource(RASTER_SOURCE_ID, {
                type: 'raster',
                tiles: [tileUrl],
                tileSize: 256,
            });
            map.addLayer({
                id: RASTER_LAYER_ID,
                type: 'raster',
                source: RASTER_SOURCE_ID,
                paint: {'raster-opacity': 0.82},
            });
        };

        if (map.loaded()) {
            addLayer();
        } else {
            map.once('load', addLayer);
        }
    }

    function newestDate(availability) {
        if (availability && availability.max) {
            return availability.max;
        }
        const dates = availability && Array.isArray(availability.available) ? availability.available.slice() : [];
        dates.sort().reverse();
        return dates[0] || null;
    }

    function visualizationTileUrl(payload) {
        if (payload && Array.isArray(payload.titiler_url) && payload.titiler_url[0]) {
            return payload.titiler_url[0];
        }
        if (payload && payload.titiler_info && Array.isArray(payload.titiler_info.tiles)) {
            return payload.titiler_info.tiles[0];
        }
        return null;
    }

    function activateCategory(mount, key) {
        const token = ++activeToken;
        const layers = groupedLayers[key] || [];
        const layer = layers[0];

        setActiveTab(mount, key);
        showNoData(mount, false);
        renderDateChip(mount, null);
        renderLegend(mount, layer && layer.legend);
        removeRasterLayer();

        if (!layer) {
            showNoData(mount, true);
            return;
        }

        const dataset = layer.dataset;
        const cadence = dataset.cadence || 'monthly';
        const availabilityUrl = joinUrl(
            config.apiBaseUrl,
            `/api/catalog/datasets/${encodeURIComponent(dataset.id)}/availability/?cadence=${encodeURIComponent(cadence)}`
        );

        fetchJson(availabilityUrl)
            .then((availability) => {
                if (token !== activeToken) {
                    return null;
                }
                const date = newestDate(availability);
                if (!date) {
                    showNoData(mount, true);
                    return null;
                }
                renderDateChip(mount, date);
                const visualizationUrl = joinUrl(
                    config.apiBaseUrl,
                    `/api/catalog/datasets/${encodeURIComponent(dataset.id)}/visualization/?cadence=${encodeURIComponent(cadence)}&date=${encodeURIComponent(date)}`
                );
                return fetchJson(visualizationUrl);
            })
            .then((visualization) => {
                if (token !== activeToken || !visualization) {
                    return;
                }
                const tileUrl = visualizationTileUrl(visualization);
                if (!tileUrl) {
                    showNoData(mount, true);
                    return;
                }
                addRasterLayer(tileUrl);
            })
            .catch((error) => {
                if (!warnedCategoryFailure) {
                    console.warn('Multi-Hazard category load failed', error);
                    warnedCategoryFailure = true;
                }
                if (token === activeToken) {
                    renderDateChip(mount, null);
                    removeRasterLayer();
                    showNoData(mount, true);
                }
            });
    }

    function init() {
        const mount = document.getElementById('multi-hazard-map');
        if (!mount) {
            return;
        }

        config = {
            apiBaseUrl: mount.dataset.apiBaseUrl || '',
            projectSlug: mount.dataset.projectSlug || 'multi-hazard',
            countryBounds: mount.dataset.countryBounds || '',
            languageCode: mount.dataset.languageCode || 'en',
            msgLatest: mount.dataset.msgLatest || 'Latest',
            msgNoData: mount.dataset.msgNoData || 'No data available for this category',
            msgUnavailable: mount.dataset.msgUnavailable || 'Map data is temporarily unavailable',
        };

        if (!config.apiBaseUrl || !window.maplibregl) {
            showUnavailable(mount);
            return;
        }

        Promise.all([loadCategories(), loadLayers()])
            .then(([categories, layers]) => {
                if (!layers.length) {
                    showUnavailable(mount);
                    return;
                }
                groupedLayers = groupByCategory(layers, categories);
                const tabs = visibleTabs(categories, groupedLayers);
                if (!tabs.length) {
                    showUnavailable(mount);
                    return;
                }
                mount.innerHTML = '';
                createMap(mount);
                renderTabs(mount, tabs);
                activateCategory(mount, tabs[0].key);
            })
            .catch((error) => {
                console.warn('Multi-Hazard map unavailable', error);
                showUnavailable(mount);
            });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}());
