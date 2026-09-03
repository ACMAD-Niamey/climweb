/*
 * Participant choropleth map + filter widget.
 *
 * One interactive MapLibre GL choropleth of Africa per [data-participant-map-canvas]
 * element, shaded by capacity-building participants per country. The viewer can
 * filter by gender, category and intake year; the map, legend and table all
 * update on the client with no extra request.
 *
 * Every payload is aggregate-only (counts + gender/category/year breakdowns) and
 * never contains participant names. Boundaries are fetched once as GeoJSON from a
 * same-origin endpoint and rendered directly - there is no vector-tile server.
 */
(function () {
  "use strict";

  var DEFAULT_RAMP = ["#ffffd4", "#fed98e", "#fe9929", "#d95f0e", "#993404"];
  var DEFAULT_NO_DATA = "#e9edf0";
  var BORDER_COLOR = "#9aa7b4";
  var HOVER_BORDER_COLOR = "#1f2937";
  var WATER_COLOR = "#eef3f6";

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
    if (maxCount <= 5) return [2, 3, 4, 5];
    var raw = [2, maxCount * 0.4, maxCount * 0.65, maxCount * 0.85];
    var breaks = [];
    raw.forEach(function (v) {
      var n = Math.max(2, Math.round(v));
      breaks.push(breaks.length && n <= breaks[breaks.length - 1] ? breaks[breaks.length - 1] + 1 : n);
    });
    return breaks;
  }

  function classify(count, breaks) {
    for (var i = breaks.length - 1; i >= 0; i--) {
      if (count >= breaks[i]) return i + 1;
    }
    return 0;
  }

  function fillExpression(perCountry, breaks, ramp, noData) {
    var expr = ["match", ["get", "iso_a3"]];
    Object.keys(perCountry).forEach(function (iso) {
      if (perCountry[iso].total > 0) {
        expr.push(iso, ramp[classify(perCountry[iso].total, breaks)]);
      }
    });
    if (expr.length === 2) return noData; // nothing matched - flat colour
    expr.push(noData);
    return expr;
  }

  function rangeLabels(breaks) {
    var labels = ["1"];
    for (var i = 0; i < breaks.length; i++) {
      var lo = breaks[i];
      var hi = i + 1 < breaks.length ? breaks[i + 1] - 1 : null;
      labels.push(hi && hi > lo ? lo + "–" + hi : (i + 1 === breaks.length ? lo + "+" : String(lo)));
    }
    return labels;
  }

  function renderLegend(container, breaks, ramp, noData, hasData, T) {
    if (!container) return;
    var labels = rangeLabels(breaks);
    var html = '<p class="participant-map__legend-title">' + (T.participants || "Participants") + "</p>";
    html += '<ul class="participant-map__legend-list">';
    for (var i = 0; i < ramp.length; i++) {
      html += '<li><span class="participant-map__swatch" style="background:' + ramp[i] + '"></span>' + labels[i] + "</li>";
    }
    if (hasData) {
      html += '<li><span class="participant-map__swatch" style="background:' + noData + '"></span>0</li>';
    }
    container.innerHTML = html + "</ul>";
  }

  // ---- filtering / aggregation -------------------------------------------------

  function aggregate(cells, state) {
    var out = {};
    cells.forEach(function (cell) {
      if (state.gender && cell.gender !== state.gender) return;
      if (state.category && cell.category !== state.category) return;
      if (state.year && cell.year !== state.year) return;
      var b = out[cell.iso3] || (out[cell.iso3] = { total: 0, by_gender: {}, by_category: {} });
      b.total += cell.count;
      b.by_gender[cell.gender] = (b.by_gender[cell.gender] || 0) + cell.count;
      b.by_category[cell.category] = (b.by_category[cell.category] || 0) + cell.count;
    });
    return out;
  }

  function total(perCountry) {
    return Object.keys(perCountry).reduce(function (sum, iso) {
      return sum + perCountry[iso].total;
    }, 0);
  }

  // ---- filter UI --------------------------------------------------------------

  function buildFilterUI(host, dataset, config, state, onChange) {
    if (!host) return;
    var T = config.text || {};
    var groups = [];

    function group(key, label, options) {
      if (options.length < 2) return;
      var wrap = document.createElement("div");
      wrap.className = "participant-map__filter-group";
      wrap.innerHTML = '<span class="participant-map__filter-label">' + label + "</span>";
      var buttons = document.createElement("div");
      buttons.className = "buttons has-addons participant-map__filter-buttons";
      [{ value: null, text: T.all || "All" }].concat(options).forEach(function (opt) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "button is-small is-rounded";
        btn.textContent = opt.text;
        if (state[key] === opt.value) btn.classList.add("is-active");
        btn.addEventListener("click", function () {
          state[key] = opt.value;
          buttons.querySelectorAll(".button").forEach(function (b) {
            b.classList.remove("is-active");
          });
          btn.classList.add("is-active");
          onChange();
        });
        buttons.appendChild(btn);
      });
      wrap.appendChild(buttons);
      host.appendChild(wrap);
      groups.push(wrap);
    }

    var genderLabels = (config.labels && config.labels.gender) || {};
    var categoryLabels = (config.labels && config.labels.category) || {};

    group("gender", T.gender || "Gender", (dataset.genders || []).map(function (g) {
      return { value: g, text: genderLabels[g] || g };
    }));
    group("category", T.category || "Category", (dataset.categories || []).map(function (c) {
      return { value: c, text: categoryLabels[c] || c };
    }));
    group("year", T.year || "Year", (dataset.years || []).map(function (y) {
      return { value: y, text: String(y) };
    }));

    if (groups.length) host.hidden = false;
  }

  // ---- table ----------------------------------------------------------------

  function renderTable(table, perCountry, dataset) {
    if (!table) return;
    var tbody = table.querySelector("tbody");
    if (!tbody) return;
    var rows = Object.keys(perCountry)
      .map(function (iso) {
        var name = (dataset.countries[iso] && dataset.countries[iso].name) || iso;
        return { name: name, total: perCountry[iso].total };
      })
      .filter(function (r) {
        return r.total > 0;
      })
      .sort(function (a, b) {
        return b.total - a.total || a.name.localeCompare(b.name);
      });

    tbody.innerHTML = rows
      .map(function (r) {
        return "<tr><td>" + r.name + '</td><td class="has-text-right">' + r.total + "</td></tr>";
      })
      .join("");
  }

  // ---- popup ---------------------------------------------------------------

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

  function popupHTML(name, row, config) {
    var labels = config.labels || {};
    return (
      '<div class="participant-map__popup">' +
      '<p class="participant-map__popup-country">' + name + "</p>" +
      '<p class="participant-map__popup-total"><strong>' + row.total + "</strong> " +
      ((config.text && config.text.participants) || "participants").toLowerCase() + "</p>" +
      '<div class="participant-map__popup-group">' + breakdownRows(row.by_gender, labels.gender || {}) + "</div>" +
      '<div class="participant-map__popup-group">' + breakdownRows(row.by_category, labels.category || {}) + "</div>" +
      "</div>"
    );
  }

  // ---- map ---------------------------------------------------------------

  function initMap(canvas) {
    if (typeof window.maplibregl === "undefined") return;

    var config = readJSON(canvas.getAttribute("data-config-id")) || {};
    var dataset = readJSON(canvas.getAttribute("data-dataset-id")) || { cells: [], countries: {} };
    var boundariesUrl = config.boundariesUrl;
    if (!boundariesUrl) return;

    var colors = config.colors || {};
    var ramp = (colors.ramp && colors.ramp.length === 5 && colors.ramp) || DEFAULT_RAMP;
    var noData = colors.noData || DEFAULT_NO_DATA;
    var T = config.text || {};

    var reduceMotion = !!(
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );

    var state = { gender: null, category: null, year: null };

    var legendEl = document.getElementById(canvas.getAttribute("data-legend-id"));
    var tableEl = document.getElementById(canvas.getAttribute("data-table-id"));
    var summaryEl = document.getElementById(canvas.getAttribute("data-summary-id"));

    var map = new window.maplibregl.Map({
      container: canvas.id,
      style: {
        version: 8,
        sources: {},
        layers: [{ id: "background", type: "background", paint: { "background-color": WATER_COLOR } }],
      },
      bounds: config.bounds || [-26, -38, 64, 40],
      fitBoundsOptions: { padding: 20, animate: false },
      attributionControl: false,
      dragRotate: false,
      pitchWithRotate: false,
      renderWorldCopies: false,
      fadeDuration: reduceMotion ? 0 : 300,
    });
    map.addControl(new window.maplibregl.NavigationControl({ showCompass: false }), "top-right");

    var popup = new window.maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      className: "participant-map__popup-wrap",
    });
    var current = {};

    function apply() {
      current = aggregate(dataset.cells, state);
      var totals = Object.keys(current).map(function (iso) {
        return current[iso].total;
      });
      var max = totals.length ? Math.max.apply(null, totals) : 0;
      var breaks = computeBreaks(max);

      if (map.getLayer("country-fill")) {
        map.setPaintProperty("country-fill", "fill-color", fillExpression(current, breaks, ramp, noData));
      }
      renderLegend(legendEl, breaks, ramp, noData, true, T);
      renderTable(tableEl, current, dataset);
      if (summaryEl) {
        var n = total(current);
        summaryEl.textContent = (T.showing || "Showing %(count)s participants").replace("%(count)s", n);
      }
      popup.remove();
    }

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
            paint: { "fill-color": noData, "fill-opacity": 0.92 },
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
              "line-width": ["case", ["boolean", ["feature-state", "hover"], false], 1.6, 0.5],
            },
          });

          wireInteractions(map, popup, function () {
            return current;
          }, dataset, config);
          apply();
          map.resize();
        })
        .catch(function () {
          /* accessible fallback table stays in place */
        });
    });

    buildFilterUI(
      canvas.closest("[data-participant-map]").querySelector("[data-participant-map-filters]"),
      dataset,
      config,
      state,
      apply
    );
  }

  function wireInteractions(map, popup, getCurrent, dataset, config) {
    var hoveredId = null;

    function clearHover() {
      if (hoveredId !== null) {
        map.setFeatureState({ source: "countries", id: hoveredId }, { hover: false });
        hoveredId = null;
      }
    }

    function show(feature, lngLat) {
      var iso = feature.id || (feature.properties && feature.properties.iso_a3);
      var row = getCurrent()[iso];
      clearHover();
      if (iso) {
        hoveredId = iso;
        map.setFeatureState({ source: "countries", id: iso }, { hover: true });
      }
      if (!row || !row.total) {
        popup.remove();
        return;
      }
      var name = (dataset.countries[iso] && dataset.countries[iso].name) || iso;
      popup.setLngLat(lngLat).setHTML(popupHTML(name, row, config)).addTo(map);
    }

    map.on("mousemove", "country-fill", function (e) {
      if (!e.features.length) return;
      map.getCanvas().style.cursor = "pointer";
      show(e.features[0], e.lngLat);
    });
    map.on("mouseleave", "country-fill", function () {
      map.getCanvas().style.cursor = "";
      clearHover();
      popup.remove();
    });
    map.on("click", "country-fill", function (e) {
      if (e.features.length) show(e.features[0], e.lngLat);
    });
  }

  function boot() {
    document.querySelectorAll("[data-participant-map-canvas]").forEach(initMap);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
