const WEBSOCKET_TIMEOUT_MS = 45000;
const BAR_TOP_OFFSET = 28;
const BAR_LANE_HEIGHT = 27;
const MIN_WEEK_HEIGHT = 108;
const WEEK_BOTTOM_PADDING = 10;
const MIN_GRID_ROWS = 16;
const MAX_GRID_ROWS = 24;
const GRID_ROW_HEIGHT = 56;
const MAX_CALENDAR_VIEWPORT_HEIGHT = 560;
const FILTER_DEFINITIONS = [
  { key: "ship", label: "Ship", all: "All ships" },
  { key: "offer_type", label: "Offer type", all: "All offer types" },
  { key: "offer", label: "Offer", all: "All offers" },
  { key: "departure", label: "Departure", all: "All departures" },
  { key: "nights", label: "Nights", all: "All nights" },
];

class RCCLClubRoyaleCalendarCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = undefined;
    this._sailings = [];
    this._loading = false;
    this._loaded = false;
    this._error = undefined;
    this._selectedId = undefined;
    this._calendarScrollTop = 0;
    this._resetCalendarScrollOnRender = false;
    this._configInitialized = false;
    this._filters = {};
    this._sailingsDataSignature = "";
    this._pendingRender = false;
    this._openFilterKey = undefined;
    this._filterPanelScrollTop = {};
    const now = new Date();
    this._month = new Date(now.getFullYear(), now.getMonth(), 1);
  }

  setConfig(config) {
    this._config = config || {};
    if (this._config.month) {
      const month = parseMonth(this._config.month);
      if (month) {
        const monthChanged =
          month.getFullYear() !== this._month.getFullYear() ||
          month.getMonth() !== this._month.getMonth();
        this._month = month;
        this._resetCalendarScrollOnRender = this._configInitialized && monthChanged;
      }
    }
    this._configInitialized = true;
    this._renderOrDefer();
  }

  set hass(hass) {
    this._hass = hass;
    const entitySailings = this._sailingsFromEntities();
    if (entitySailings.length || this._hasClubRoyaleEntitySource()) {
      if (this._applyEntitySailings(entitySailings)) {
        this._renderOrDefer();
      }
      return;
    }
    if (!this._loaded && !this._loading) {
      this._loadData();
    }
  }

  connectedCallback() {
    this._render();
  }

  getCardSize() {
    return this._estimatedGridRows();
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: this._estimatedGridRows() };
  }

  _sendWebsocket(message) {
    const sender = this._hass?.connection?.sendMessagePromise
      ? this._hass.connection.sendMessagePromise.bind(this._hass.connection)
      : this._hass?.callWS?.bind(this._hass);
    if (!sender) {
      return Promise.reject(new Error("Home Assistant websocket API is unavailable"));
    }

    const configuredTimeout = Number(this._config.timeout_ms || WEBSOCKET_TIMEOUT_MS);
    return withTimeout(
      sender(message),
      configuredTimeout > 0 ? configuredTimeout : WEBSOCKET_TIMEOUT_MS,
      "Timed out waiting for Club Royale sailings"
    );
  }

  async _loadData(force = false) {
    if (!this._hass || this._loading || (this._loaded && !force)) {
      return;
    }
    const entitySailings = this._sailingsFromEntities();
    if (entitySailings.length || this._hasClubRoyaleEntitySource()) {
      if (this._applyEntitySailings(entitySailings)) {
        this._renderOrDefer();
      }
      return;
    }
    this._loading = true;
    this._error = undefined;
    this._renderOrDefer();

    try {
      const message = { type: "rccl/club_royale_sailings" };
      const entryId = this._config.entry_id || this._entryIdFromEntities();
      if (entryId) {
        message.entry_id = entryId;
      }
      const result = await this._sendWebsocket(message);
      this._applySailings(Array.isArray(result.sailings) ? result.sailings : []);
      if (!this._sailings.length && Array.isArray(result.errors) && result.errors.length) {
        this._error = result.errors.map((item) => item.message).join("; ");
      }
      this._loaded = true;
    } catch (err) {
      this._error = err?.message || String(err);
    } finally {
      this._loading = false;
      this._renderOrDefer();
    }
  }

  _render() {
    if (!this.shadowRoot) {
      return;
    }
    this._pendingRender = false;

    const calendarScrollTop = this._resetCalendarScrollOnRender
      ? 0
      : this._currentCalendarScrollTop();
    const filterPanelKey = this._openFilterKey;
    const filterPanelScrollTop = this._currentFilterPanelScrollTop(filterPanelKey);
    this._resetCalendarScrollOnRender = false;
    const grid = this._calendarModel();
    const filteredSailings = this._filteredSailings();
    const visibleSailingRows = this._visibleSailings(grid.start, grid.end, filteredSailings);
    const visibleSailings = this._displaySailings(visibleSailingRows);
    const segments = this._segments(visibleSailings, grid.start, grid.weekCount);
    const weekLaneCounts = this._weekLaneCounts(segments, grid.weekCount);
    const calendarViewportHeight = this._calendarViewportHeight(weekLaneCounts);
    const selected =
      visibleSailings.find((item) => item.id === this._selectedId) ||
      visibleSailings[0] ||
      this._sailings[0];
    if (selected && visibleSailings.some((item) => String(item.id) === String(selected.id))) {
      this._selectedId = selected.id;
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }

        ha-card {
          height: 100%;
          overflow: hidden;
        }

        .card {
          box-sizing: border-box;
          display: flex;
          flex-direction: column;
          height: 100%;
          min-height: 0;
          padding: 16px;
        }

        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 14px;
        }

        .title {
          min-width: 0;
        }

        h2 {
          margin: 0;
          font-size: 20px;
          font-weight: 650;
          letter-spacing: 0;
        }

        .meta {
          margin-top: 2px;
          color: var(--secondary-text-color);
          font-size: 13px;
        }

        .controls {
          display: flex;
          align-items: center;
          gap: 6px;
          flex-shrink: 0;
        }

        button,
        summary {
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
        }

        button {
          min-width: 34px;
          height: 32px;
          padding: 0 10px;
          cursor: pointer;
        }

        button:focus-visible,
        summary:focus-visible,
        input:focus-visible,
        .sailing-bar:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        .filters {
          display: grid;
          grid-template-columns: repeat(5, minmax(108px, 1fr)) auto;
          gap: 8px;
          align-items: end;
          margin-bottom: 12px;
        }

        .filter-menu {
          min-width: 0;
          position: relative;
        }

        .filter-summary-label {
          color: var(--secondary-text-color);
          font-size: 11px;
          font-weight: 650;
          line-height: 1;
        }

        .filter-summary {
          box-sizing: border-box;
          display: flex;
          position: relative;
          flex-direction: column;
          align-items: flex-start;
          justify-content: space-between;
          gap: 3px;
          min-height: 42px;
          padding: 6px 22px 6px 9px;
          cursor: pointer;
          list-style: none;
        }

        .filter-summary::-webkit-details-marker {
          display: none;
        }

        .filter-summary-value {
          min-width: 0;
          width: 100%;
          overflow: hidden;
          text-align: left;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .filter-summary::after {
          content: "v";
          color: var(--secondary-text-color);
          font-size: 10px;
          position: absolute;
          right: 9px;
          top: 50%;
          transform: translateY(-50%);
        }

        .filter-menu[open] .filter-summary::after {
          content: "^";
        }

        .filter-panel {
          position: absolute;
          z-index: 5;
          inset-inline: 0;
          top: calc(100% + 4px);
          box-sizing: border-box;
          max-height: 240px;
          overflow: auto;
          padding: 8px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
          box-shadow: 0 4px 14px rgba(0, 0, 0, 0.22);
        }

        .filter-actions {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 6px;
          margin-bottom: 6px;
        }

        .filter-actions button {
          width: 100%;
          min-width: 0;
          padding: 0 8px;
          font-size: 12px;
        }

        .filter-options {
          display: grid;
          gap: 4px;
        }

        .filter-option {
          display: flex;
          align-items: flex-start;
          gap: 7px;
          min-width: 0;
          padding: 4px 2px;
          font-size: 12px;
          line-height: 1.25;
        }

        .filter-option input {
          flex: 0 0 auto;
          margin: 1px 0 0;
        }

        .filter-option span {
          min-width: 0;
          overflow-wrap: anywhere;
        }

        .filter-empty {
          color: var(--secondary-text-color);
          font-size: 12px;
          padding: 4px 2px;
        }

        .filter-reset {
          white-space: nowrap;
        }

        .weekdays {
          display: grid;
          grid-template-columns: repeat(7, minmax(0, 1fr));
          gap: 4px;
          color: var(--secondary-text-color);
          font-size: 12px;
          text-align: center;
          margin-bottom: 4px;
        }

        .calendar {
          position: relative;
          display: grid;
          grid-template-columns: repeat(7, minmax(0, 1fr));
          grid-auto-rows: auto;
          gap: 4px;
        }

        .calendar-shell {
          border-radius: 8px;
          max-height: 62vh;
          min-height: 320px;
          overflow-x: hidden;
          overflow-y: auto;
          overscroll-behavior: contain;
          padding-right: 2px;
          scrollbar-gutter: stable;
        }

        .day {
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          min-width: 0;
          padding: 6px;
          background: color-mix(in srgb, var(--card-background-color) 94%, var(--primary-color));
          overflow: hidden;
        }

        .day.other-month {
          opacity: 0.55;
        }

        .day.today {
          border-color: var(--primary-color);
          box-shadow: inset 0 0 0 1px var(--primary-color);
        }

        .day-number {
          font-size: 12px;
          font-weight: 650;
        }

        .sailing-bar {
          align-self: start;
          z-index: 2;
          height: 24px;
          border: 0;
          border-radius: 999px;
          color: white;
          padding: 0 9px;
          margin-left: 3px;
          margin-right: 3px;
          font-size: 12px;
          line-height: 24px;
          text-align: left;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.22);
        }

        .sailing-bar.continues-left {
          border-top-left-radius: 4px;
          border-bottom-left-radius: 4px;
        }

        .sailing-bar.continues-right {
          border-top-right-radius: 4px;
          border-bottom-right-radius: 4px;
        }

        .sailing-bar.selected {
          box-shadow: 0 0 0 2px var(--card-background-color), 0 0 0 4px var(--primary-color);
        }

        .state {
          min-height: 160px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--secondary-text-color);
          text-align: center;
        }

        .details {
          margin-top: 14px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          padding: 12px;
          background: color-mix(in srgb, var(--card-background-color) 96%, var(--primary-color));
        }

        .details-title {
          font-weight: 700;
          margin-bottom: 8px;
        }

        .detail-grid {
          display: grid;
          grid-template-columns: minmax(96px, 132px) minmax(0, 1fr);
          gap: 5px 12px;
          font-size: 13px;
        }

        .detail-label {
          color: var(--secondary-text-color);
        }

        .detail-value {
          min-width: 0;
          overflow-wrap: anywhere;
        }

        @media (max-width: 640px) {
          .card {
            padding: 12px;
          }

          .header {
            align-items: flex-start;
            flex-direction: column;
          }

          .filters {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }

          .filter-reset {
            grid-column: 1 / -1;
          }

          .filter-panel {
            max-height: 220px;
          }

          .calendar-shell {
            max-height: 58vh;
            min-height: 300px;
          }

          .sailing-bar {
            font-size: 11px;
            padding: 0 7px;
          }

          .detail-grid {
            grid-template-columns: 1fr;
            gap: 2px;
          }

          .detail-label {
            margin-top: 6px;
          }
        }
      </style>

      <ha-card>
        <div class="card">
          <div class="header">
            <div class="title">
              <h2>${escapeHtml(this._config.title || "Club Royale Sailings")}</h2>
              <div class="meta">${escapeHtml(monthLabel(this._month))} - ${visibleSailings.length} sailing${visibleSailings.length === 1 ? "" : "s"}</div>
            </div>
            <div class="controls">
              <button type="button" data-action="previous" aria-label="Previous month">&lsaquo;</button>
              <button type="button" data-action="today">Today</button>
              <button type="button" data-action="next" aria-label="Next month">&rsaquo;</button>
              <button type="button" data-action="refresh" aria-label="Refresh">&#8635;</button>
            </div>
          </div>
          ${this._body(grid, visibleSailings, segments, selected, weekLaneCounts, calendarViewportHeight)}
        </div>
      </ha-card>
    `;
    this._attachHandlers();
    this._restoreCalendarScroll(calendarScrollTop);
    this._restoreFilterPanelScroll(filterPanelKey, filterPanelScrollTop);
  }

  _body(grid, visibleSailings, segments, selected, weekLaneCounts, calendarViewportHeight) {
    if (this._loading && !this._loaded) {
      return `<div class="state">Loading Club Royale sailings...</div>`;
    }
    if (this._error) {
      return `<div class="state">${escapeHtml(this._error)}</div>`;
    }
    if (!this._loaded && !this._hass) {
      return `<div class="state">Waiting for Home Assistant data...</div>`;
    }

    const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const weekRows = weekLaneCounts.map((count) => `${this._weekRowHeight(count)}px`).join(" ");
    const emptyMessage = this._hasActiveFilters()
      ? `No Club Royale sailings match the selected filters for ${monthLabel(this._month)}.`
      : `No Club Royale sailings found for ${monthLabel(this._month)}.`;
    return `
      ${this._filterBar()}
      <div class="weekdays">${weekdays.map((day) => `<div>${day}</div>`).join("")}</div>
      <div class="calendar-shell" tabindex="0" role="region" aria-label="${escapeHtml(monthLabel(this._month))} Club Royale calendar" style="height:${calendarViewportHeight}px;">
        <div class="calendar" style="grid-template-rows:${weekRows};">
          ${grid.days.map((day) => this._dayCell(day)).join("")}
          ${segments.map((segment) => this._segmentBar(segment)).join("")}
        </div>
      </div>
      ${visibleSailings.length ? this._details(selected) : `<div class="state">${escapeHtml(emptyMessage)}</div>`}
    `;
  }

  _filterBar() {
    const filters = FILTER_DEFINITIONS.map((definition) => this._filterMenu(definition)).join("");
    const resetDisabled = this._hasActiveFilters() ? "" : " disabled";
    return `
      <div class="filters" aria-label="Club Royale sailing filters">
        ${filters}
        <button type="button" class="filter-reset" data-action="reset-filters"${resetDisabled}>Reset filters</button>
      </div>
    `;
  }

  _filterMenu(definition) {
    const options = this._filterOptions(definition.key);
    const selected = this._filterSelection(definition.key);
    const isOpen = this._openFilterKey === definition.key ? " open" : "";
    const checked = (option) => selected === undefined || selected.has(option.value);
    return `
      <details class="filter-menu" data-filter-open data-filter-key="${escapeHtml(definition.key)}"${isOpen}>
        <summary class="filter-summary" aria-label="${escapeHtml(definition.label)} filter">
          <span class="filter-summary-label">${escapeHtml(definition.label)}</span>
          <span class="filter-summary-value">${escapeHtml(this._filterSummary(definition, options))}</span>
        </summary>
        <div class="filter-panel" data-filter-panel="${escapeHtml(definition.key)}" role="group" aria-label="${escapeHtml(definition.label)} filter values">
          <div class="filter-actions">
            <button type="button" data-filter-bulk="select-all" data-filter-key="${escapeHtml(definition.key)}">Select all</button>
            <button type="button" data-filter-bulk="deselect-all" data-filter-key="${escapeHtml(definition.key)}">Deselect all</button>
          </div>
          <div class="filter-options">
            ${
              options.length
                ? options
                    .map(
                      (option) => `
                        <label class="filter-option">
                          <input
                            type="checkbox"
                            data-filter-key="${escapeHtml(definition.key)}"
                            data-filter-value="${escapeHtml(option.value)}"
                            ${checked(option) ? "checked" : ""}
                          >
                          <span>${escapeHtml(option.label)}</span>
                        </label>
                      `,
                    )
                    .join("")
                : `<div class="filter-empty">No values available</div>`
            }
          </div>
        </div>
      </details>
    `;
  }

  _filterSummary(definition, options) {
    const selected = this._filterSelection(definition.key);
    if (selected === undefined) {
      return definition.all;
    }
    if (!selected.size) {
      return "None selected";
    }
    if (selected.size === 1) {
      return options.find((option) => selected.has(option.value))?.label || "1 selected";
    }
    return `${selected.size} selected`;
  }

  _dayCell(day) {
    const classes = ["day"];
    if (day.date.getMonth() !== this._month.getMonth()) {
      classes.push("other-month");
    }
    if (sameDay(day.date, new Date())) {
      classes.push("today");
    }
    return `
      <div class="${classes.join(" ")}" style="grid-column:${day.column};grid-row:${day.row};">
        <div class="day-number">${day.date.getDate()}</div>
      </div>
    `;
  }

  _segmentBar(segment) {
    const sailing = segment.sailing;
    const classes = ["sailing-bar"];
    if (segment.continuesLeft) {
      classes.push("continues-left");
    }
    if (segment.continuesRight) {
      classes.push("continues-right");
    }
    if (sailing.id === this._selectedId) {
      classes.push("selected");
    }
    return `
      <button
        type="button"
        class="${classes.join(" ")}"
        data-sailing-id="${escapeHtml(sailing.id)}"
        style="grid-column:${segment.column} / span ${segment.span};grid-row:${segment.week + 1};margin-top:${BAR_TOP_OFFSET + segment.lane * BAR_LANE_HEIGHT}px;background:${segment.color};"
        title="${escapeHtml(sailing.calendar_title)}"
      >${escapeHtml(sailing.calendar_title)}</button>
    `;
  }

  _details(sailing) {
    if (!sailing) {
      return "";
    }
    return `
      <div class="details" data-sailing-details>
        ${this._detailsContent(sailing)}
      </div>
    `;
  }

  _detailsContent(sailing) {
    const rows = [
      ["Impacts", `${formatDate(sailing.sail_date)} through ${formatDate(sailing.return_date)}`],
      ["Sailing", sailing.sailing_type || sailing.itinerary_description || sailing.itinerary_name],
      ["Ship", sailing.ship_name],
      ["Departure", portLabel(sailing.departure_port)],
      ["Cabin", sailing.cabin_guarantee || roomTypeLabel(sailing.room_types)],
      ["Offer type", compactJoin([sailing.offer_type, sailing.offer_occupancy_label], " - ")],
      ["Offer", compactJoin([sailing.offer_name, sailing.offer_code], " - ")],
      ["Reserve by", formatDate(sailing.reserve_by_date)],
      ["Sail by", formatDate(sailing.sail_by_date)],
    ].filter((row) => row[1]);

    return `
      <div class="details-title">${escapeHtml(sailing.calendar_title)}</div>
      <div class="detail-grid">
        ${rows
          .map(
            ([label, value]) => `
              <div class="detail-label">${escapeHtml(label)}</div>
              <div class="detail-value">${escapeHtml(value)}</div>
            `,
          )
          .join("")}
      </div>
    `;
  }

  _calendarModel() {
    const first = new Date(this._month.getFullYear(), this._month.getMonth(), 1);
    const last = new Date(this._month.getFullYear(), this._month.getMonth() + 1, 0);
    const start = addDays(first, -first.getDay());
    const end = addDays(last, 6 - last.getDay());
    const days = [];
    for (let date = new Date(start), index = 0; date <= end; date = addDays(date, 1), index += 1) {
      days.push({
        date: new Date(date),
        row: Math.floor(index / 7) + 1,
        column: (index % 7) + 1,
      });
    }
    return { start, end, days, weekCount: days.length / 7 };
  }

  _visibleSailings(start, end, sailings = this._filteredSailings()) {
    return sailings
      .map((sailing) => ({
        ...sailing,
        _start: parseDate(sailing.sail_date),
        _end: parseDate(sailing.return_date),
      }))
      .filter((sailing) => sailing._start && sailing._end && sailing._start <= end && sailing._end >= start)
      .sort((a, b) => a._start - b._start || String(a.ship_name).localeCompare(String(b.ship_name)));
  }

  _displaySailings(sailings) {
    const grouped = new Map();
    for (const sailing of sailings) {
      const key = this._sailingGroupKey(sailing);
      const current = grouped.get(key);
      grouped.set(key, current ? this._preferredSailing(current, sailing) : sailing);
    }
    return Array.from(grouped.values()).sort(
      (left, right) =>
        left._start - right._start ||
        String(left.ship_name || "").localeCompare(String(right.ship_name || "")) ||
        String(left.id || "").localeCompare(String(right.id || "")),
    );
  }

  _sailingGroupKey(sailing) {
    return String(
      sailing.source_sailing_id ||
        `${sailing.ship_code || sailing.ship_name || ""}:${sailing.sail_date || ""}:${sailing.return_date || ""}`,
    );
  }

  _preferredSailing(left, right) {
    const leftExpiry = offerExpiryTime(left);
    const rightExpiry = offerExpiryTime(right);
    if (leftExpiry !== rightExpiry) {
      return leftExpiry < rightExpiry ? left : right;
    }
    const leftOffer = compactJoin([left.offer_name, left.offer_code], " ");
    const rightOffer = compactJoin([right.offer_name, right.offer_code], " ");
    return leftOffer.localeCompare(rightOffer) <= 0 ? left : right;
  }

  _filteredSailings() {
    return this._sailings.filter((sailing) =>
      FILTER_DEFINITIONS.every((definition) => {
        const selected = this._filterSelection(definition.key);
        return selected === undefined || selected.has(this._filterValue(sailing, definition.key));
      }),
    );
  }

  _filterSelection(key) {
    if (!Object.prototype.hasOwnProperty.call(this._filters, key)) {
      return undefined;
    }
    const values = Array.isArray(this._filters[key]) ? this._filters[key] : [this._filters[key]];
    return new Set(values.map((value) => String(value)));
  }

  _filterOptions(key) {
    const values = new Map();
    for (const sailing of this._sailings) {
      const value = this._filterValue(sailing, key);
      if (value) {
        values.set(value, { value, label: value });
      }
    }
    const options = Array.from(values.values());
    if (key === "nights") {
      return options.sort((left, right) => Number(left.value.match(/\d+/)?.[0] || 0) - Number(right.value.match(/\d+/)?.[0] || 0));
    }
    return options.sort((left, right) => left.label.localeCompare(right.label));
  }

  _filterValue(sailing, key) {
    if (key === "ship") {
      return sailing.ship_name || sailing.ship_code || "";
    }
    if (key === "offer_type") {
      return compactJoin([sailing.offer_type, sailing.offer_occupancy_label], " - ");
    }
    if (key === "offer") {
      return compactJoin([sailing.offer_name, sailing.offer_code], " - ");
    }
    if (key === "departure") {
      return portLabel(sailing.departure_port);
    }
    if (key === "nights") {
      const nights = Number(sailing.total_nights);
      if (!Number.isFinite(nights) || nights <= 0) {
        return "";
      }
      return `${nights} night${nights === 1 ? "" : "s"}`;
    }
    return "";
  }

  _hasActiveFilters() {
    return FILTER_DEFINITIONS.some((definition) =>
      Object.prototype.hasOwnProperty.call(this._filters, definition.key)
    );
  }

  _normalizeFilterState() {
    const nextFilters = {};
    for (const definition of FILTER_DEFINITIONS) {
      if (!Object.prototype.hasOwnProperty.call(this._filters, definition.key)) {
        continue;
      }
      const available = new Set(this._filterOptions(definition.key).map((option) => option.value));
      const selected = this._filterSelection(definition.key);
      const values = Array.from(selected || []).filter((value) => available.has(value));
      if (values.length && values.length < available.size) {
        nextFilters[definition.key] = values;
      } else if (!values.length && selected?.size === 0) {
        nextFilters[definition.key] = [];
      }
    }
    this._filters = nextFilters;
  }

  _segments(sailings, gridStart, weekCount) {
    const segments = [];
    for (const sailing of sailings) {
      for (let week = 0; week < weekCount; week += 1) {
        const weekStart = addDays(gridStart, week * 7);
        const weekEnd = addDays(weekStart, 6);
        const segmentStart = sailing._start > weekStart ? sailing._start : weekStart;
        const segmentEnd = sailing._end < weekEnd ? sailing._end : weekEnd;
        if (segmentStart > segmentEnd) {
          continue;
        }
        const column = segmentStart.getDay() + 1;
        const span = daysBetween(segmentStart, segmentEnd) + 1;
        segments.push({
          sailing,
          week,
          column,
          span,
          continuesLeft: sailing._start < segmentStart,
          continuesRight: sailing._end > segmentEnd,
          color: colorFor(sailing.ship_name || sailing.ship_code || sailing.id),
        });
      }
    }
    return assignLanes(segments);
  }

  _weekLaneCounts(segments, weekCount) {
    const counts = Array.from({ length: weekCount }, () => 0);
    for (const segment of segments) {
      counts[segment.week] = Math.max(counts[segment.week], segment.lane + 1);
    }
    return counts;
  }

  _weekRowHeight(laneCount) {
    return Math.max(
      MIN_WEEK_HEIGHT,
      BAR_TOP_OFFSET + Math.max(laneCount, 1) * BAR_LANE_HEIGHT + WEEK_BOTTOM_PADDING,
    );
  }

  _calendarContentHeight(weekLaneCounts) {
    const rowHeights = weekLaneCounts.map((count) => this._weekRowHeight(count));
    const rowGaps = Math.max(0, rowHeights.length - 1) * 4;
    return rowHeights.reduce((sum, height) => sum + height, 0) + rowGaps;
  }

  _calendarViewportHeight(weekLaneCounts) {
    return Math.min(
      this._calendarContentHeight(weekLaneCounts),
      MAX_CALENDAR_VIEWPORT_HEIGHT,
    );
  }

  _estimatedGridRows() {
    const grid = this._calendarModel();
    const visibleSailings = this._displaySailings(
      this._visibleSailings(grid.start, grid.end),
    );
    const segments = this._segments(visibleSailings, grid.start, grid.weekCount);
    const weekLaneCounts = this._weekLaneCounts(segments, grid.weekCount);
    const calendarHeight = this._calendarViewportHeight(weekLaneCounts);
    const detailsHeight = visibleSailings.length ? 210 : 90;
    const headerHeight = 118;
    return Math.max(
      MIN_GRID_ROWS,
      Math.min(
        MAX_GRID_ROWS,
        Math.ceil((headerHeight + calendarHeight + detailsHeight) / GRID_ROW_HEIGHT),
      ),
    );
  }

  _currentCalendarScrollTop() {
    const shell = this.shadowRoot?.querySelector(".calendar-shell");
    if (shell) {
      return shell.scrollTop;
    }
    return this._calendarScrollTop || this._storedCalendarScrollTop();
  }

  _restoreCalendarScroll(scrollTop) {
    const targetScrollTop = Math.max(0, Number(scrollTop) || 0);
    this._calendarScrollTop = targetScrollTop;
    this._saveCalendarScrollTop(targetScrollTop);
    const shell = this.shadowRoot?.querySelector(".calendar-shell");
    if (!shell) {
      return;
    }

    const applyScrollTop = () => {
      shell.scrollTop = targetScrollTop;
      this._calendarScrollTop = shell.scrollTop;
      this._saveCalendarScrollTop(this._calendarScrollTop);
    };
    applyScrollTop();
    shell.addEventListener(
      "scroll",
      () => {
        this._calendarScrollTop = shell.scrollTop;
        this._saveCalendarScrollTop(this._calendarScrollTop);
      },
      { passive: true },
    );
    window.requestAnimationFrame?.(applyScrollTop);
  }

  _storedCalendarScrollTop() {
    try {
      return Math.max(
        0,
        Number(window.sessionStorage?.getItem(this._calendarScrollStorageKey())) || 0,
      );
    } catch (err) {
      return 0;
    }
  }

  _saveCalendarScrollTop(scrollTop) {
    try {
      window.sessionStorage?.setItem(
        this._calendarScrollStorageKey(),
        String(Math.max(0, Number(scrollTop) || 0)),
      );
    } catch (err) {
      // Storage can be unavailable in some embedded browser contexts.
    }
  }

  _calendarScrollStorageKey() {
    const month = `${this._month.getFullYear()}-${String(this._month.getMonth() + 1).padStart(2, "0")}`;
    const scope = this._config.entry_id || this._entryIdFromEntities() || this._config.title || "default";
    return `rccl:club-royale-calendar:${scope}:${month}`;
  }

  _filterPanelElement(key = this._openFilterKey) {
    if (!key) {
      return undefined;
    }
    return Array.from(this.shadowRoot?.querySelectorAll("[data-filter-panel]") || []).find(
      (panel) => panel.dataset.filterPanel === key,
    );
  }

  _currentFilterPanelScrollTop(key = this._openFilterKey) {
    const panel = this._filterPanelElement(key);
    if (panel) {
      return panel.scrollTop;
    }
    return this._filterPanelScrollTop[key] || 0;
  }

  _saveFilterPanelScrollTop(key, scrollTop) {
    if (!key) {
      return;
    }
    this._filterPanelScrollTop[key] = Math.max(0, Number(scrollTop) || 0);
  }

  _restoreFilterPanelScroll(key = this._openFilterKey, scrollTop = this._currentFilterPanelScrollTop(key)) {
    const panel = this._filterPanelElement(key);
    if (!panel) {
      return;
    }
    const targetScrollTop = Math.max(0, Number(scrollTop) || 0);
    this._saveFilterPanelScrollTop(key, targetScrollTop);

    const applyScrollTop = () => {
      panel.scrollTop = targetScrollTop;
      this._saveFilterPanelScrollTop(key, panel.scrollTop);
    };
    applyScrollTop();
    panel.addEventListener(
      "scroll",
      () => this._saveFilterPanelScrollTop(key, panel.scrollTop),
      { passive: true },
    );
    window.requestAnimationFrame?.(applyScrollTop);
  }

  _selectSailing(sailingId) {
    if (!sailingId || sailingId === this._selectedId) {
      return;
    }
    this._selectedId = sailingId;
    this._syncSelectedSailing();
  }

  _setFilter(key, value) {
    if (!FILTER_DEFINITIONS.some((definition) => definition.key === key)) {
      return;
    }
    if (value) {
      this._filters[key] = [String(value)];
    } else {
      delete this._filters[key];
    }
    this._afterFilterChanged();
  }

  _setFilterItem(key, value, checked) {
    const options = this._filterOptions(key).map((option) => option.value);
    if (!options.length) {
      return;
    }
    const available = new Set(options);
    if (!available.has(value)) {
      return;
    }
    const current = this._filterSelection(key);
    const selected = current === undefined ? new Set(options) : new Set(current);
    if (checked) {
      selected.add(value);
    } else {
      selected.delete(value);
    }

    if (selected.size === options.length) {
      delete this._filters[key];
    } else {
      this._filters[key] = options.filter((option) => selected.has(option));
    }
    this._openFilterKey = key;
    this._afterFilterChanged();
  }

  _selectAllFilterOptions(key) {
    if (!FILTER_DEFINITIONS.some((definition) => definition.key === key)) {
      return;
    }
    delete this._filters[key];
    this._openFilterKey = key;
    this._afterFilterChanged();
  }

  _deselectAllFilterOptions(key) {
    if (!FILTER_DEFINITIONS.some((definition) => definition.key === key)) {
      return;
    }
    this._filters[key] = [];
    this._openFilterKey = key;
    this._afterFilterChanged();
  }

  _afterFilterChanged() {
    this._resetCalendarScrollOnRender = true;
    const grid = this._calendarModel();
    const visibleSailings = this._displaySailings(
      this._visibleSailings(grid.start, grid.end, this._filteredSailings()),
    );
    if (!visibleSailings.some((sailing) => String(sailing.id) === String(this._selectedId))) {
      this._selectedId = visibleSailings[0]?.id;
    }
    this._render();
  }

  _resetFilters() {
    if (!this._hasActiveFilters()) {
      return;
    }
    this._filters = {};
    this._openFilterKey = undefined;
    this._resetCalendarScrollOnRender = true;
    const grid = this._calendarModel();
    this._selectedId = this._displaySailings(
      this._visibleSailings(grid.start, grid.end, this._sailings),
    )[0]?.id;
    this._render();
  }

  _renderOrDefer() {
    if (this._hasFocusedFilterControl()) {
      this._pendingRender = true;
      return;
    }
    this._render();
  }

  _hasFocusedFilterControl() {
    const active = this.shadowRoot?.activeElement;
    return Boolean(
      active?.dataset?.filterKey ||
        active?.matches?.("[data-filter-key]") ||
        this.shadowRoot?.querySelector("[data-filter-open][open]")
    );
  }

  _flushDeferredRender() {
    if (!this._pendingRender || this._hasFocusedFilterControl()) {
      return;
    }
    this._pendingRender = false;
    this._render();
  }

  _applyEntitySailings(entitySailings) {
    const dataChanged = this._sailingsSignature(entitySailings) !== this._sailingsDataSignature;
    const stateChanged = !this._loaded || this._loading || this._error !== undefined;
    if (dataChanged) {
      this._applySailings(entitySailings);
    }
    this._loaded = true;
    this._loading = false;
    this._error = undefined;
    return dataChanged || stateChanged;
  }

  _syncSelectedSailing() {
    const selectedId = String(this._selectedId || "");
    this.shadowRoot?.querySelectorAll(".sailing-bar").forEach((bar) => {
      bar.classList.toggle("selected", bar.dataset.sailingId === selectedId);
    });

    const selected = this._sailings.find((sailing) => String(sailing.id) === selectedId);
    const details = this.shadowRoot?.querySelector("[data-sailing-details]");
    if (selected && details) {
      details.innerHTML = this._detailsContent(selected);
    }
  }

  _attachHandlers() {
    this.shadowRoot.querySelectorAll("[data-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const action = button.dataset.action;
        if (action === "previous") {
          this._month = new Date(this._month.getFullYear(), this._month.getMonth() - 1, 1);
          this._resetCalendarScrollOnRender = true;
        } else if (action === "next") {
          this._month = new Date(this._month.getFullYear(), this._month.getMonth() + 1, 1);
          this._resetCalendarScrollOnRender = true;
        } else if (action === "today") {
          const now = new Date();
          this._month = new Date(now.getFullYear(), now.getMonth(), 1);
          this._resetCalendarScrollOnRender = true;
        } else if (action === "refresh") {
          this._loaded = false;
          this._loadData(true);
          return;
        } else if (action === "reset-filters") {
          this._resetFilters();
          return;
        }
        this._render();
      });
    });

    this.shadowRoot.querySelectorAll("[data-filter-open]").forEach((details) => {
      details.addEventListener("toggle", () => {
        const filterKey = details.dataset.filterKey;
        if (details.open) {
          this._openFilterKey = filterKey;
          this.shadowRoot.querySelectorAll("[data-filter-open]").forEach((other) => {
            if (other !== details) {
              this._saveFilterPanelScrollTop(
                other.dataset.filterKey,
                this._currentFilterPanelScrollTop(other.dataset.filterKey),
              );
              other.open = false;
            }
          });
          this._restoreFilterPanelScroll(filterKey);
          return;
        }
        this._saveFilterPanelScrollTop(filterKey, this._currentFilterPanelScrollTop(filterKey));
        if (this._openFilterKey === filterKey) {
          this._openFilterKey = undefined;
        }
        if (window.requestAnimationFrame) {
          window.requestAnimationFrame(() => this._flushDeferredRender());
          return;
        }
        window.setTimeout(() => this._flushDeferredRender(), 0);
      });
    });

    this.shadowRoot.querySelectorAll("[data-filter-value]").forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        this._setFilterItem(
          checkbox.dataset.filterKey,
          checkbox.dataset.filterValue,
          checkbox.checked,
        );
      });
    });

    this.shadowRoot.querySelectorAll("[data-filter-bulk]").forEach((button) => {
      button.addEventListener("click", () => {
        if (button.dataset.filterBulk === "select-all") {
          this._selectAllFilterOptions(button.dataset.filterKey);
          return;
        }
        if (button.dataset.filterBulk === "deselect-all") {
          this._deselectAllFilterOptions(button.dataset.filterKey);
        }
      });
    });

    this.shadowRoot.querySelectorAll(".sailing-bar").forEach((bar) => {
      const select = () => this._selectSailing(bar.dataset.sailingId);
      bar.addEventListener("mouseenter", select);
      bar.addEventListener("focus", select);
      bar.addEventListener("click", select);
    });
  }

  _applySailings(sailings) {
    this._sailings = sailings;
    this._sailingsDataSignature = this._sailingsSignature(sailings);
    this._normalizeFilterState();
    if (!this._selectedId || !this._sailings.some((item) => String(item.id) === String(this._selectedId))) {
      this._selectedId = this._sailings[0]?.id;
    }
  }

  _sailingsSignature(sailings) {
    return stableStringify(sailings);
  }

  _sailingsFromEntities() {
    if (!this._hass?.states) {
      return [];
    }
    return Object.entries(this._hass.states)
      .map(([entityId, state]) => this._sailingFromEntity(entityId, state))
      .filter(Boolean)
      .sort((left, right) =>
        `${left.sail_date || ""}:${left.ship_name || ""}`.localeCompare(
          `${right.sail_date || ""}:${right.ship_name || ""}`
        )
      );
  }

  _sailingFromEntity(entityId, state) {
    const attrs = state?.attributes || {};
    if (attrs.integration !== "rccl" || attrs.entity_kind !== "club_royale_sailing") {
      return undefined;
    }
    const sailDate = attrs.sail_date || state.state;
    if (!sailDate || sailDate === "unknown" || sailDate === "unavailable") {
      return undefined;
    }
    const id = String(attrs.sailing_id || attrs.id || entityId);
    const itineraryName = attrs.itinerary_name || attrs.friendly_name || "Club Royale sailing";
    const shipName = attrs.ship_name || "";
    return {
      ...attrs,
      id,
      entity_id: entityId,
      sail_date: sailDate,
      calendar_title: attrs.calendar_title || (shipName ? `${itineraryName} - ${shipName}` : itineraryName),
    };
  }

  _hasClubRoyaleEntitySource() {
    return Object.values(this._hass?.states || {}).some((state) => {
      const attrs = state?.attributes || {};
      return attrs.integration === "rccl" && String(attrs.entity_kind || "").startsWith("club_royale");
    });
  }

  _entryIdFromEntities() {
    if (!this._hass || !this._hass.entities) {
      return undefined;
    }
    const entityIds = Object.keys(this._hass.states || {}).filter((entityId) =>
      entityId.startsWith("sensor.rccl_") ||
      entityId.startsWith("sensor.royal_caribbean") ||
      entityId.startsWith("calendar.rccl_") ||
      entityId.startsWith("calendar.royal_caribbean"),
    );
    for (const entityId of entityIds) {
      const entryId = this._hass.entities[entityId]?.config_entry_id;
      if (entryId) {
        return entryId;
      }
    }
    for (const [entityId, entity] of Object.entries(this._hass.entities)) {
      if (
        entityId.startsWith("sensor.") ||
        entityId.startsWith("calendar.")
      ) {
        const name = `${entity.name || ""} ${entity.translation_key || ""}`.toLowerCase();
        if (name.includes("royal caribbean") || name.includes("rccl")) {
          return entity.config_entry_id;
        }
      }
    }
    return undefined;
  }
}

function assignLanes(segments) {
  const byWeek = new Map();
  for (const segment of segments) {
    const weekSegments = byWeek.get(segment.week) || [];
    weekSegments.push(segment);
    byWeek.set(segment.week, weekSegments);
  }
  for (const weekSegments of byWeek.values()) {
    const lanes = [];
    weekSegments.sort((a, b) => a.column - b.column || b.span - a.span);
    for (const segment of weekSegments) {
      const end = segment.column + segment.span - 1;
      let lane = lanes.findIndex((laneEnd) => segment.column > laneEnd);
      if (lane === -1) {
        lane = lanes.length;
        lanes.push(end);
      } else {
        lanes[lane] = end;
      }
      segment.lane = lane;
    }
  }
  return segments;
}

function parseMonth(value) {
  const match = String(value).match(/^(\d{4})-(\d{2})$/);
  if (!match) {
    return undefined;
  }
  return new Date(Number(match[1]), Number(match[2]) - 1, 1);
}

function parseDate(value) {
  if (!value) {
    return undefined;
  }
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) {
    return undefined;
  }
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

function addDays(date, days) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);
}

function daysBetween(start, end) {
  return Math.round((stripTime(end) - stripTime(start)) / 86400000);
}

function stripTime(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function sameDay(left, right) {
  return (
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  );
}

function monthLabel(date) {
  return date.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function formatDate(value) {
  const date = parseDate(value);
  if (!date) {
    return "";
  }
  return date.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function offerExpiryTime(sailing) {
  const reserveByDate = parseDate(sailing.reserve_by_date);
  if (reserveByDate) {
    return reserveByDate.getTime();
  }
  const sailByDate = parseDate(sailing.sail_by_date);
  if (sailByDate) {
    return sailByDate.getTime();
  }
  return Number.POSITIVE_INFINITY;
}

function compactJoin(values, separator) {
  return values.filter((value) => value !== undefined && value !== null && value !== "").join(separator);
}

function portLabel(port) {
  if (!port) {
    return "";
  }
  return compactJoin([port.name, port.code], " - ");
}

function roomTypeLabel(roomTypes) {
  if (!Array.isArray(roomTypes)) {
    return "";
  }
  return roomTypes.map((room) => room.name || room.code).filter(Boolean).join(" / ");
}

function colorFor(value) {
  const palette = ["#1d4ed8", "#0f766e", "#b45309", "#7c3aed", "#be123c", "#047857"];
  let hash = 0;
  for (const char of String(value || "sailing")) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  return palette[hash % palette.length];
}

function stableStringify(value) {
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  }
  if (value && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

function withTimeout(promise, timeoutMs, message) {
  let timeoutId;
  const timeout = new Promise((_, reject) => {
    timeoutId = window.setTimeout(() => reject(new Error(message)), timeoutMs);
  });
  return Promise.race([promise, timeout]).finally(() => window.clearTimeout(timeoutId));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

customElements.define("rccl-club-royale-calendar-card", RCCLClubRoyaleCalendarCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "rccl-club-royale-calendar-card",
  name: "RCCL Club Royale Calendar",
  preview: false,
  description: "Browse Club Royale offer sailings by impacted calendar date range.",
  documentationURL: "https://github.com/javaDevJT/ha-rccl",
});
