(function () {
    'use strict';

    const FALLBACK_CATEGORIES = [
        { key: 'weather', label: 'Weather' },
        { key: 'drought', label: 'Drought' },
        { key: 'climate', label: 'Climate' },
        { key: 'flood', label: 'Flood' },
    ];

    // Fallback tab set, used only when NO layer has been flagged
    // display_on_homepage in the Multi-Hazard admin. Order here is the fixed
    // display order, independent of API order. Once layers are flagged, tabs
    // come from their hazard_category instead (see flaggedTabs).
    const CORE_CATEGORY_KEYS = ['weather', 'drought', 'climate', 'flood'];
    const RASTER_SOURCE_ID = 'mhz-raster-source';
    const RASTER_LAYER_ID = 'mhz-raster-layer';

    // "Always on top" overlay layers (e.g. the countries boundary). These are
    // driven entirely by the Multi-Hazard catalog: any layer flagged both
    // display_on_homepage and always_on_top in the Multi-Hazard admin is
    // rendered here, above the hazard raster, and every addRasterLayer() call
    // inserts the hazard raster *below* them so switching tabs never buries
    // them. Populated by addTopLayers().
    const TOP_LAYER_PREFIX = 'mhz-top-';
    let topLayerIds = [];

    // The catalog API's hazard-categories endpoint returns icon_url as null
    // in production, so tab icons come from this local set instead — thin
    // stroke-style SVGs matching the rest of the redesign's icon language.
    // Keyed by category key; TAB_ICONS.default covers any category the API
    // returns that isn't one of the four core tabs.
    const TAB_ICONS = {
        weather: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M8 15a4 4 0 1 1 .6-7.96A5.5 5.5 0 0 1 19 9.5 3.5 3.5 0 0 1 18.5 16H8Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M5 3v1.5M2 6.5h1.5M8.5 2v1.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
        drought: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M12 3c3 4 6 7.5 6 11a6 6 0 1 1-12 0c0-3.5 3-7 6-11Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>',
        climate: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/><path d="M3 12h18M12 3c2.5 2.5 3.75 5.5 3.75 9s-1.25 6.5-3.75 9c-2.5-2.5-3.75-5.5-3.75-9S9.5 5.5 12 3Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>',
        flood: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M3 15c1.5 1.3 3 1.3 4.5 0s3-1.3 4.5 0 3 1.3 4.5 0 3-1.3 4.5 0M3 19c1.5 1.3 3 1.3 4.5 0s3-1.3 4.5 0 3 1.3 4.5 0 3-1.3 4.5 0" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
        default: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.6"/></svg>',
    };

    let map = null;
    let tabsRow = null;
    let activeToken = 0;
    let groupedLayers = {};
    let config = {};
    let warnedCategoryFailure = false;

    // WHY Esri and not CARTO: CARTO retired its anonymous (no-token) basemap
    // tile endpoints — requests to basemaps.cartocdn.com without a CARTO
    // account access token now get rate-limited / 403'd, which is what broke
    // this map. Esri's World Light Gray Base is genuinely key-free for web use
    // (attribution required) and gives a clean, muted canvas for the hazard
    // overlays. This mirrors the basemap the Vue home map already switched to.
    // No `glyphs` entry is needed here: every layer on this map is raster, so
    // MapLibre never loads a font stack.
    const baseStyle = {
        version: 8,
        sources: {
            basemap: {
                type: 'raster',
                tiles: [
                    'https://services.arcgisonline.com/arcgis/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
                ],
                tileSize: 256,
                attribution: '&copy; Esri &copy; OpenStreetMap contributors',
            },
        },
        layers: [{
            id: 'basemap-layer',
            source: 'basemap',
            type: 'raster',
            minzoom: 0,
            maxzoom: 16,
        }],
    };

    function joinUrl(base, path) {
        return `${base.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`;
    }

    function fetchJson(url, timeoutMs) {
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), timeoutMs || 15000);
        return fetch(url, { signal: controller.signal })
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
                        // Preserved so flaggedTabs() can order tabs the same
                        // way the Multi-Hazard viewer orders its categories.
                        order: Number.isFinite(category.order) ? category.order : 0,
                    }))
                    .filter((category) => category.key && category.label);
                return categories.length ? categories : FALLBACK_CATEGORIES;
            })
            .catch(() => FALLBACK_CATEGORIES);
    }

    function loadLayers() {
        // Return every layer — homepage selection (which layers, and whether
        // an overlay is always-on-top) is decided from each layer's `ui`
        // block by partitionHomepageLayers(), not filtered out here.
        const url = joinUrl(config.apiBaseUrl, `/api/catalog/ui/layers?project=${encodeURIComponent(config.projectSlug)}`);
        return fetchJson(url).then((payload) => normalizeList(payload).filter((layer) => layer && layer.id));
    }

    function hasDataset(layer) {
        return !!(layer && layer.dataset && layer.dataset.id);
    }

    function normalizeOpacity(value, fallback) {
        // The catalog stores opacity inconsistently — most layers use a 0-100
        // percentage (e.g. 50), a few use a 0-1 fraction (e.g. 0.85). Treat
        // anything greater than 1 as a percentage.
        let opacity = typeof value === 'number' ? value : fallback;
        if (!Number.isFinite(opacity)) {
            return fallback;
        }
        if (opacity > 1) {
            opacity = opacity / 100;
        }
        return Math.min(1, Math.max(0, opacity));
    }

    function partitionHomepageLayers(layers) {
        // A layer reaches the homepage only if it is flagged
        // ui.display_on_homepage in the Multi-Hazard admin. Of those,
        // ui.always_on_top layers become permanent overlays (rendered from
        // their WMS/XYZ tile.template); the rest drive the category tabs.
        const flagged = layers.filter((layer) => layer.ui && layer.ui.display_on_homepage);
        return {
            topLayers: flagged.filter((layer) => layer.ui.always_on_top && layer.tile && layer.tile.template),
            dataLayers: flagged.filter((layer) => !layer.ui.always_on_top && hasDataset(layer)),
        };
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
        // Anything that doesn't match a known category (heat, agriculture,
        // exposure, boundary layers, etc.) must NOT fall through to
        // 'weather' — this homepage card only has 4 tabs, so an unmatched
        // layer should simply be excluded from all of them, not silently
        // misrepresented as a weather dataset.
        return 'other';
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

    function flaggedTabs(categories, grouped) {
        // Alignment mode: one tab per hazard_category that has a
        // display_on_homepage layer, ordered by the catalog's category order
        // (the same order the Multi-Hazard viewer uses).
        const byKey = {};
        categories.forEach((category) => {
            byKey[category.key] = category;
        });
        return Object.keys(grouped)
            .filter((key) => key !== 'other' && grouped[key] && grouped[key].length)
            .map((key) => byKey[key] || { key: key, label: key, order: 0 })
            .sort((a, b) => (a.order || 0) - (b.order || 0));
    }

    function visibleTabs(categories, grouped) {
        // Fallback mode (nothing flagged display_on_homepage yet): restrict to
        // the fixed Weather/Drought/Climate/Flood set, in that order. A
        // category only shows up if it actually has layers assigned to it.
        const byKey = {};
        categories.forEach((category) => {
            byKey[category.key] = category;
        });
        return CORE_CATEGORY_KEYS
            .map((key) => byKey[key] || FALLBACK_CATEGORIES.find((category) => category.key === key))
            .filter((category) => category && grouped[category.key] && grouped[category.key].length);
    }

    function createMap(mount) {
        map = new maplibregl.Map({
            container: mount,
            style: baseStyle,
            center: [17, 2],
            zoom: 1, // Dummy initial zoom, overridden by fitBounds
            scrollZoom: false,
            attributionControl: false,
        });
        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
        map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');

        const bounds = parseBounds(config.countryBounds);
        if (bounds) {
            map.fitBounds(bounds, { padding: 20, duration: 0 });
        } else {
            // Default to fitting the entire African continent
            map.fitBounds([[-20.0, -35.0], [52.0, 38.0]], { padding: 20, duration: 0 });
        }
    }

    function clearByClass(mount, className) {
        mount.querySelectorAll(`.${className}`).forEach((node) => node.remove());
    }

    function renderTabs(mount, tabs) {
        // Tabs render into the docked #multi-hazard-tabs row (in normal page
        // flow, a sibling of the map), not into the map mount itself — this
        // keeps them clear of the map's own floating legend/date-chip/zoom
        // controls. `mount` is still threaded through for the click handler's
        // closure over the map div that activateCategory operates on.
        if (!tabsRow) {
            return;
        }
        tabsRow.innerHTML = '';
        tabs.forEach((tab) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'mhz-tab';
            button.dataset.key = tab.key;
            // Icon HTML comes only from the local, hardcoded TAB_ICONS set
            // (never from API/user data); the label is set via textContent
            // on a separate span so it's always safely escaped.
            button.innerHTML = TAB_ICONS[tab.key] || TAB_ICONS.default;
            const labelSpan = document.createElement('span');
            labelSpan.textContent = tab.label;
            button.appendChild(labelSpan);
            button.addEventListener('click', () => activateCategory(mount, tab.key));
            tabsRow.appendChild(button);
        });
    }

    function setActiveTab(key) {
        if (!tabsRow) {
            return;
        }
        tabsRow.querySelectorAll('.mhz-tab').forEach((tab) => {
            tab.classList.toggle('is-active', tab.dataset.key === key);
        });
    }

    // Above this many classes, a per-segment label under each strip
    // segment gets too cramped to read inside the legend's ~240px width -
    // fall back to labelling just the two ends, with the full label still
    // reachable per-segment via the native title tooltip on hover/tap.
    const LEGEND_STRIP_LABEL_LIMIT = 4;

    function datasetTitle(layer) {
        if (!layer) {
            return null;
        }
        // Field name varies by how a given dataset was catalogued upstream -
        // fall back through the ones the catalog API is known to use rather
        // than assume one, same pattern as loadCategories()'s label fallback.
        const dataset = layer.dataset || {};
        return layer.title || layer.name || dataset.title || dataset.name || dataset.id || null;
    }

    function renderLegend(mount, legend, title) {
        clearByClass(mount, 'mhz-legend');
        const entries = Object.entries(legend || {});
        if (!entries.length) {
            return;
        }
        const wrapper = document.createElement('div');
        wrapper.className = 'mhz-legend';

        if (title) {
            const heading = document.createElement('div');
            heading.className = 'mhz-legend-title';
            heading.textContent = title;
            wrapper.appendChild(heading);
        }

        const strip = document.createElement('div');
        strip.className = 'mhz-legend-strip';
        entries.forEach(([label, color]) => {
            const segment = document.createElement('span');
            segment.className = 'mhz-legend-segment';
            segment.style.backgroundColor = color;
            segment.title = label;
            strip.appendChild(segment);
        });
        wrapper.appendChild(strip);

        const labels = document.createElement('div');
        labels.className = 'mhz-legend-labels';
        if (entries.length <= LEGEND_STRIP_LABEL_LIMIT) {
            entries.forEach(([label]) => {
                const item = document.createElement('span');
                item.textContent = label;
                labels.appendChild(item);
            });
        } else {
            const first = document.createElement('span');
            first.textContent = entries[0][0];
            const last = document.createElement('span');
            last.textContent = entries[entries.length - 1][0];
            labels.appendChild(first);
            labels.appendChild(last);
        }
        wrapper.appendChild(labels);

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
        if (tabsRow) {
            tabsRow.innerHTML = '';
        }
        mount.innerHTML = '';
        const panel = document.createElement('div');
        panel.className = 'mhz-unavailable';
        panel.textContent = config.msgUnavailable;
        mount.appendChild(panel);
    }

    function firstTopLayerId() {
        // beforeId for addRasterLayer — the hazard raster is inserted directly
        // below the first always-on-top overlay so the overlays always stay on
        // top. Undefined until addTopLayers() has run (or when nothing is
        // flagged always_on_top), in which case the raster goes on top and the
        // overlays are stacked above it once they're added.
        if (!map) {
            return undefined;
        }
        return topLayerIds.find((id) => map.getLayer(id));
    }

    function addTopLayers(topLayers) {
        if (!map || !topLayers.length) {
            return;
        }
        const add = () => {
            topLayers.forEach((layer, index) => {
                const layerId = `${TOP_LAYER_PREFIX}${index}`;
                const sourceId = `${layerId}-source`;
                if (map.getLayer(layerId)) {
                    return;
                }
                const ui = layer.ui || {};
                // tile.template is a full WMS GetMap / XYZ URL from the
                // catalog — MapLibre substitutes {bbox-epsg-3857} (WMS) or
                // {z}/{x}/{y} (XYZ) per tile.
                map.addSource(sourceId, {
                    type: 'raster',
                    tiles: [layer.tile.template],
                    tileSize: 256,
                });
                map.addLayer({
                    id: layerId,
                    type: 'raster',
                    source: sourceId,
                    minzoom: Number.isFinite(ui.minzoom) ? ui.minzoom : 0,
                    maxzoom: Number.isFinite(ui.maxzoom) ? ui.maxzoom : 22,
                    paint: { 'raster-opacity': normalizeOpacity(ui.opacity, 1) },
                });
                topLayerIds.push(layerId);
            });
        };

        if (map.loaded()) {
            add();
        } else {
            map.once('load', add);
        }
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
                paint: { 'raster-opacity': 0.82 },
            }, firstTopLayerId());
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

        setActiveTab(key);
        showNoData(mount, false);
        renderDateChip(mount, null);
        renderLegend(mount, layer && layer.legend, datasetTitle(layer));
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
        tabsRow = document.getElementById('multi-hazard-tabs');

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

                const { topLayers, dataLayers } = partitionHomepageLayers(layers);

                // Alignment with the Multi-Hazard viewer: once layers are
                // flagged display_on_homepage in the Multi-Hazard admin, the
                // homepage shows exactly those. Until any hazard layer is
                // flagged, fall back to the curated Weather/Drought/Climate/
                // Flood set so the card is never empty.
                const aligned = dataLayers.length > 0;
                let tabLayers = dataLayers;
                if (!aligned) {
                    console.info(
                        'Multi-Hazard: no layers flagged display_on_homepage — '
                        + 'showing the curated fallback set. Flag layers in the '
                        + 'Multi-Hazard admin to control what appears here.'
                    );
                    tabLayers = layers.filter((layer) => layer.icon && layer.icon.url && hasDataset(layer));
                }

                groupedLayers = groupByCategory(tabLayers, categories);
                const tabs = aligned
                    ? flaggedTabs(categories, groupedLayers)
                    : visibleTabs(categories, groupedLayers);

                if (!tabs.length && !topLayers.length) {
                    showUnavailable(mount);
                    return;
                }

                mount.innerHTML = '';
                createMap(mount);
                addTopLayers(topLayers);
                renderTabs(mount, tabs);
                if (tabs.length) {
                    activateCategory(mount, tabs[0].key);
                }
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
