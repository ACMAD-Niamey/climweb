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

    function dropdown(key, label, options, isNumber) {
      if (!options || options.length < 1) return;
      var wrap = document.createElement("div");
      wrap.className = "participant-map__filter-group";
      wrap.innerHTML = '<span class="participant-map__filter-label">' + label + "</span>";

      var selectWrap = document.createElement("div");
      selectWrap.className = "select is-small is-rounded participant-map__filter-select";
      if (state[key] !== null && state[key] !== undefined) {
        selectWrap.classList.add("is-active");
      }

      var sel = document.createElement("select");
      sel.setAttribute("aria-label", label);

      var defaultOpt = document.createElement("option");
      defaultOpt.value = "";
      defaultOpt.textContent = T.all || "All";
      sel.appendChild(defaultOpt);

      options.forEach(function (opt) {
        var option = document.createElement("option");
        option.value = opt.value;
        option.textContent = opt.text;
        if (state[key] !== null && String(state[key]) === String(opt.value)) {
          option.selected = true;
        }
        sel.appendChild(option);
      });

      sel.addEventListener("change", function () {
        var val = this.value;
        if (!val) {
          state[key] = null;
          selectWrap.classList.remove("is-active");
        } else {
          state[key] = isNumber ? parseInt(val, 10) : val;
          selectWrap.classList.add("is-active");
        }
        onChange();
      });

      selectWrap.appendChild(sel);
      wrap.appendChild(selectWrap);
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

    var sortedYears = (dataset.years || []).slice().sort(function (a, b) {
      return b - a;
    });

    dropdown("year", T.year || "Year", sortedYears.map(function (y) {
      return { value: y, text: String(y) };
    }), true);

    if (groups.length) host.hidden = false;
  }

  // ---- table & pagination ----------------------------------------------------

  var PAGE_SIZE = 10;

  function getSortedRows(perCountry, dataset) {
    return Object.keys(perCountry)
      .map(function (iso) {
        var name = (dataset.countries[iso] && dataset.countries[iso].name) || iso;
        return { iso: iso, name: name, total: perCountry[iso].total };
      })
      .filter(function (r) {
        return r.total > 0;
      })
      .sort(function (a, b) {
        return b.total - a.total || a.name.localeCompare(b.name);
      });
  }

  function getPageNumbers(current, total) {
    if (total <= 6) {
      var arr = [];
      for (var i = 1; i <= total; i++) arr.push(i);
      return arr;
    }
    var pages = [1];
    if (current > 3) pages.push("...");
    var start = Math.max(2, current - 1);
    var end = Math.min(total - 1, current + 1);
    for (var p = start; p <= end; p++) {
      if (pages.indexOf(p) === -1) pages.push(p);
    }
    if (current < total - 2) pages.push("...");
    if (pages.indexOf(total) === -1) pages.push(total);
    return pages;
  }

  function renderTable(table, pagination, perCountry, dataset, state, onPageChange) {
    if (!table) return;
    var tbody = table.querySelector("tbody");
    if (!tbody) return;

    var rows = getSortedRows(perCountry, dataset);
    var totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));

    if (state.page > totalPages) state.page = totalPages;
    if (state.page < 1) state.page = 1;

    var start = (state.page - 1) * PAGE_SIZE;
    var pageRows = rows.slice(start, start + PAGE_SIZE);

    tbody.innerHTML = pageRows
      .map(function (r) {
        return (
          '<tr data-iso="' +
          r.iso +
          '"><td>' +
          r.name +
          '</td><td class="has-text-right"><span class="participant-map__badge">' +
          r.total +
          "</span></td></tr>"
        );
      })
      .join("");

    renderPagination(pagination, state.page, totalPages, onPageChange);
  }

  function renderPagination(pagination, currentPage, totalPages, onPageChange) {
    if (!pagination) return;
    if (totalPages <= 1) {
      pagination.hidden = true;
      return;
    }
    pagination.hidden = false;

    var prevBtn = pagination.querySelector('[data-page-action="prev"]');
    var nextBtn = pagination.querySelector('[data-page-action="next"]');
    var pagesWrap = pagination.querySelector("[data-page-numbers]");

    if (prevBtn) {
      prevBtn.disabled = (currentPage <= 1);
      prevBtn.onclick = function () {
        if (currentPage > 1) onPageChange(currentPage - 1);
      };
    }
    if (nextBtn) {
      nextBtn.disabled = (currentPage >= totalPages);
      nextBtn.onclick = function () {
        if (currentPage < totalPages) onPageChange(currentPage + 1);
      };
    }

    if (pagesWrap) {
      var nums = getPageNumbers(currentPage, totalPages);
      pagesWrap.innerHTML = "";
      nums.forEach(function (p) {
        if (p === "...") {
          var ellipsis = document.createElement("span");
          ellipsis.className = "participant-map__pagination-ellipsis";
          ellipsis.innerHTML = "&hellip;";
          pagesWrap.appendChild(ellipsis);
        } else {
          var btn = document.createElement("button");
          btn.type = "button";
          btn.className = "button is-small is-rounded participant-map__pagination-num";
          if (p === currentPage) btn.classList.add("is-active");
          btn.textContent = String(p);
          btn.addEventListener("click", function () {
            if (p !== currentPage) onPageChange(p);
          });
          pagesWrap.appendChild(btn);
        }
      });
    }
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

    var state = { gender: null, category: null, year: null, page: 1 };

    var legendEl = document.getElementById(canvas.getAttribute("data-legend-id"));
    var tableEl = document.getElementById(canvas.getAttribute("data-table-id"));
    var summaryEl = document.getElementById(canvas.getAttribute("data-summary-id"));
    var paginationEl = document.getElementById(canvas.getAttribute("data-pagination-id"));

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

    function updateTable() {
      renderTable(tableEl, paginationEl, current, dataset, state, function (newPage) {
        state.page = newPage;
        updateTable();
      });
    }

    function apply(resetPage) {
      if (resetPage !== false) {
        state.page = 1;
      }
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
      updateTable();
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
          }, dataset, config, tableEl, state, updateTable);
          apply();
          map.resize();

          if (window.ResizeObserver) {
            var ro = new window.ResizeObserver(function () {
              map.resize();
            });
            ro.observe(canvas);
          }
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

  function wireInteractions(map, popup, getCurrent, dataset, config, table, state, updateTable) {
    var hoveredId = null;

    function clearHover() {
      if (hoveredId !== null) {
        map.setFeatureState({ source: "countries", id: hoveredId }, { hover: false });
        hoveredId = null;
      }
      if (table) {
        table.querySelectorAll("tbody tr.is-hovered").forEach(function (tr) {
          tr.classList.remove("is-hovered");
        });
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
      if (table && iso) {
        if (state && updateTable) {
          var allSorted = getSortedRows(getCurrent(), dataset);
          var idx = -1;
          for (var i = 0; i < allSorted.length; i++) {
            if (allSorted[i].iso === iso) {
              idx = i;
              break;
            }
          }
          if (idx !== -1) {
            var targetPage = Math.floor(idx / PAGE_SIZE) + 1;
            if (targetPage !== state.page) {
              state.page = targetPage;
              updateTable();
            }
          }
        }
        var tr = table.querySelector('tbody tr[data-iso="' + iso + '"]');
        if (tr) {
          tr.classList.add("is-hovered");
          tr.scrollIntoView({ block: "nearest", behavior: "smooth" });
        }
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

    if (table) {
      table.addEventListener("mouseover", function (e) {
        var tr = e.target.closest("tr[data-iso]");
        if (!tr) return;
        var iso = tr.getAttribute("data-iso");
        if (!iso || iso === hoveredId) return;
        clearHover();
        hoveredId = iso;
        tr.classList.add("is-hovered");
        map.setFeatureState({ source: "countries", id: iso }, { hover: true });
      });
      table.addEventListener("mouseleave", function () {
        clearHover();
        popup.remove();
      });
    }
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
