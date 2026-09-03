/*
 * Participant choropleth map.
 *
 * Renders one MapLibre GL choropleth of Africa per [data-participant-map-canvas]
 * element on the page, shaded by the number of capacity-building participants per
 * country. All data comes from two adjacent <script type="application/json">
 * blocks (counts + config) written by the participant_map.html partial - the
 * payload is aggregate-only and never contains participant names.
 *
 * No external tiles/fonts are loaded: the base style is a plain background and
 * the only source is the boundaries GeoJSON fetched from the same origin.
 */
(function () {
  "use strict";

  var RAMP = ["#ffe9c9", "#fcd08a", "#f7b05b", "#e8863b", "#c85a1b"];
  var NO_DATA_COLOR = "#e9edf0";
  var BORDER_COLOR = "#9aa7b4";
  var HOVER_BORDER_COLOR = "#1f2937";
  var WATER_COLOR = "#eef3f6";

  var GENDER_LABELS = {
    female: "Female",
    male: "Male",
    other: "Other",
    undisclosed: "Prefer not to say",
  };
  var CATEGORY_LABELS = {
    ojt: "On-the-job training",
    secondment: "Secondment",
  };

  function readJSON(id) {
    var el = id && document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (err) {
      return null;
    }
  }

  function computeBreaks(maxCount) {
    // Four ascending thresholds -> five classes. Kept as whole numbers.
    if (maxCount <= 5) return [2, 3, 4, 5];
    var raw = [2, maxCount * 0.4, maxCount * 0.65, maxCount * 0.85];
    var breaks = [];
    raw.forEach(function (v) {
      var n = Math.max(2, Math.round(v));
      if (breaks.length === 0 || n > breaks[breaks.length - 1]) breaks.push(n);
      else breaks.push(breaks[breaks.length - 1] + 1);
    });
    return breaks;
  }

  function classify(count, breaks) {
    for (var i = breaks.length - 1; i >= 0; i--) {
      if (count >= breaks[i]) return i + 1;
    }
    return 0;
  }

  function buildFillColorExpression(counts, breaks) {
    var expr = ["match", ["get", "iso_a3"]];
    Object.keys(counts).forEach(function (iso) {
      expr.push(iso, RAMP[classify(counts[iso].total, breaks)]);
    });
    expr.push(NO_DATA_COLOR);
    return expr;
  }

  function breakRangeLabels(breaks) {
    // Human labels for each of the five classes, given four thresholds.
    var labels = ["1"];
    for (var i = 0; i < breaks.length; i++) {
      var lo = breaks[i];
      var hi = i + 1 < breaks.length ? breaks[i + 1] - 1 : null;
      labels.push(hi && hi > lo ? lo + "–" + hi : (i + 1 === breaks.length ? lo + "+" : String(lo)));
    }
    return labels;
  }

  function renderLegend(container, breaks, hasNoData) {
    if (!container) return;
    var labels = breakRangeLabels(breaks);
    var html = '<p class="participant-map__legend-title">Participants</p><ul class="participant-map__legend-list">';
    for (var i = 0; i < RAMP.length; i++) {
      html +=
        '<li><span class="participant-map__swatch" style="background:' +
        RAMP[i] +
        '"></span>' +
        labels[i] +
        "</li>";
    }
    if (hasNoData) {
      html +=
        '<li><span class="participant-map__swatch" style="background:' +
        NO_DATA_COLOR +
        '"></span>None</li>';
    }
    html += "</ul>";
    container.innerHTML = html;
  }

  function breakdownRows(obj, labelMap) {
    return Object.keys(obj || {})
      .sort(function (a, b) {
        return obj[b] - obj[a];
      })
      .map(function (key) {
        return (
          '<div class="participant-map__popup-row"><span>' +
          (labelMap[key] || key) +
          "</span><span>" +
          obj[key] +
          "</span></div>"
        );
      })
      .join("");
  }

  function popupHTML(row) {
    return (
      '<div class="participant-map__popup">' +
      '<p class="participant-map__popup-country">' +
      row.name +
      "</p>" +
      '<p class="participant-map__popup-total"><strong>' +
      row.total +
      "</strong> participant" +
      (row.total === 1 ? "" : "s") +
      "</p>" +
      '<div class="participant-map__popup-group">' +
      breakdownRows(row.by_gender, GENDER_LABELS) +
      "</div>" +
      '<div class="participant-map__popup-group">' +
      breakdownRows(row.by_category, CATEGORY_LABELS) +
      "</div>" +
      "</div>"
    );
  }

  function initMap(canvas) {
    if (typeof window.maplibregl === "undefined") return;

    var counts = readJSON(canvas.getAttribute("data-counts-id")) || {};
    var config = readJSON(canvas.getAttribute("data-config-id")) || {};
    var boundariesUrl = config.boundariesUrl;
    if (!boundariesUrl) return;

    var totals = Object.keys(counts).map(function (iso) {
      return counts[iso].total;
    });
    var maxCount = totals.length ? Math.max.apply(null, totals) : 0;
    var breaks = computeBreaks(maxCount);

    var reduceMotion = !!(
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );

    var map = new window.maplibregl.Map({
      container: canvas.id,
      style: {
        version: 8,
        sources: {},
        layers: [{ id: "background", type: "background", paint: { "background-color": WATER_COLOR } }],
      },
      bounds: config.bounds || [-26, -38, 64, 40],
      fitBoundsOptions: { padding: 20, animate: false },
      // Honour the OS "reduce motion" setting for any programmatic camera moves.
      fadeDuration: reduceMotion ? 0 : 300,
      attributionControl: false,
      dragRotate: false,
      pitchWithRotate: false,
      renderWorldCopies: false,
    });

    map.addControl(new window.maplibregl.NavigationControl({ showCompass: false }), "top-right");

    map.on("load", function () {
      fetch(boundariesUrl, { credentials: "same-origin" })
        .then(function (resp) {
          return resp.json();
        })
        .then(function (geojson) {
          map.addSource("countries", { type: "geojson", data: geojson, promoteId: "iso_a3" });

          map.addLayer({
            id: "country-fill",
            type: "fill",
            source: "countries",
            paint: { "fill-color": buildFillColorExpression(counts, breaks), "fill-opacity": 0.92 },
          });

          map.addLayer({
            id: "country-border",
            type: "line",
            source: "countries",
            paint: {
              "line-color": [
                "case",
                ["boolean", ["feature-state", "hover"], false],
                HOVER_BORDER_COLOR,
                BORDER_COLOR,
              ],
              "line-width": [
                "case",
                ["boolean", ["feature-state", "hover"], false],
                1.6,
                0.5,
              ],
            },
          });

          renderLegend(
            document.getElementById(canvas.getAttribute("data-legend-id")),
            breaks,
            Object.keys(counts).length > 0
          );

          wireInteractions(map, canvas, counts);
          map.resize();
        })
        .catch(function () {
          /* leave the accessible list fallback in place */
        });
    });
  }

  function wireInteractions(map, canvas, counts) {
    var popup = new window.maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      className: "participant-map__popup-wrap",
    });
    var hoveredId = null;

    function clearHover() {
      if (hoveredId !== null) {
        map.setFeatureState({ source: "countries", id: hoveredId }, { hover: false });
        hoveredId = null;
      }
    }

    function showFor(feature, lngLat) {
      var iso = feature.id || (feature.properties && feature.properties.iso_a3);
      var row = counts[iso];
      clearHover();
      if (iso) {
        hoveredId = iso;
        map.setFeatureState({ source: "countries", id: iso }, { hover: true });
      }
      if (!row) {
        popup.remove();
        return;
      }
      popup.setLngLat(lngLat).setHTML(popupHTML(row)).addTo(map);
    }

    map.on("mousemove", "country-fill", function (e) {
      if (!e.features.length) return;
      map.getCanvas().style.cursor = "pointer";
      showFor(e.features[0], e.lngLat);
    });

    map.on("mouseleave", "country-fill", function () {
      map.getCanvas().style.cursor = "";
      clearHover();
      popup.remove();
    });

    // Tap support on touch devices.
    map.on("click", "country-fill", function (e) {
      if (!e.features.length) return;
      showFor(e.features[0], e.lngLat);
    });
  }

  function boot() {
    var canvases = document.querySelectorAll("[data-participant-map-canvas]");
    Array.prototype.forEach.call(canvases, initMap);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
