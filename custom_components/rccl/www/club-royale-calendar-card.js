const WEBSOCKET_TIMEOUT_MS = 45000;
const BAR_TOP_OFFSET = 28;
const BAR_LANE_HEIGHT = 27;
const MIN_WEEK_HEIGHT = 108;
const WEEK_BOTTOM_PADDING = 10;
const MIN_GRID_ROWS = 16;
const MAX_GRID_ROWS = 24;
const GRID_ROW_HEIGHT = 56;
const MAX_CALENDAR_VIEWPORT_HEIGHT = 560;

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
    const now = new Date();
    this._month = new Date(now.getFullYear(), now.getMonth(), 1);
  }

  setConfig(config) {
    this._config = config || {};
    if (this._config.month) {
      const month = parseMonth(this._config.month);
      if (month) {
        this._month = month;
      }
    }
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const entitySailings = this._sailingsFromEntities();
    if (entitySailings.length || this._hasClubRoyaleEntitySource()) {
      this._applySailings(entitySailings);
      this._loaded = true;
      this._loading = false;
      this._error = undefined;
      this._render();
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
      this._applySailings(entitySailings);
      this._loaded = true;
      this._error = undefined;
      this._render();
      return;
    }
    this._loading = true;
    this._error = undefined;
    this._render();

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
      this._render();
    }
  }

  _render() {
    if (!this.shadowRoot) {
      return;
    }

    const grid = this._calendarModel();
    const visibleSailings = this._visibleSailings(grid.start, grid.end);
    const segments = this._segments(visibleSailings, grid.start, grid.weekCount);
    const weekLaneCounts = this._weekLaneCounts(segments, grid.weekCount);
    const calendarViewportHeight = this._calendarViewportHeight(weekLaneCounts);
    const selected =
      visibleSailings.find((item) => item.id === this._selectedId) ||
      visibleSailings[0] ||
      this._sailings[0];

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

        button {
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          min-width: 34px;
          height: 32px;
          padding: 0 10px;
          cursor: pointer;
        }

        button:focus-visible,
        .sailing-bar:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
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
    return `
      <div class="weekdays">${weekdays.map((day) => `<div>${day}</div>`).join("")}</div>
      <div class="calendar-shell" tabindex="0" role="region" aria-label="${escapeHtml(monthLabel(this._month))} Club Royale calendar" style="height:${calendarViewportHeight}px;">
        <div class="calendar" style="grid-template-rows:${weekRows};">
          ${grid.days.map((day) => this._dayCell(day)).join("")}
          ${segments.map((segment) => this._segmentBar(segment)).join("")}
        </div>
      </div>
      ${visibleSailings.length ? this._details(selected) : `<div class="state">No Club Royale sailings found for ${escapeHtml(monthLabel(this._month))}.</div>`}
    `;
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
      <div class="details">
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

  _visibleSailings(start, end) {
    return this._sailings
      .map((sailing) => ({
        ...sailing,
        _start: parseDate(sailing.sail_date),
        _end: parseDate(sailing.return_date),
      }))
      .filter((sailing) => sailing._start && sailing._end && sailing._start <= end && sailing._end >= start)
      .sort((a, b) => a._start - b._start || String(a.ship_name).localeCompare(String(b.ship_name)));
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
    const visibleSailings = this._visibleSailings(grid.start, grid.end);
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

  _attachHandlers() {
    this.shadowRoot.querySelectorAll("[data-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const action = button.dataset.action;
        if (action === "previous") {
          this._month = new Date(this._month.getFullYear(), this._month.getMonth() - 1, 1);
        } else if (action === "next") {
          this._month = new Date(this._month.getFullYear(), this._month.getMonth() + 1, 1);
        } else if (action === "today") {
          const now = new Date();
          this._month = new Date(now.getFullYear(), now.getMonth(), 1);
        } else if (action === "refresh") {
          this._loaded = false;
          this._loadData(true);
          return;
        }
        this._render();
      });
    });

    this.shadowRoot.querySelectorAll(".sailing-bar").forEach((bar) => {
      const select = () => {
        this._selectedId = bar.dataset.sailingId;
        this._render();
      };
      bar.addEventListener("mouseenter", select);
      bar.addEventListener("focus", select);
      bar.addEventListener("click", select);
    });
  }

  _applySailings(sailings) {
    this._sailings = sailings;
    if (!this._selectedId || !this._sailings.some((item) => item.id === this._selectedId)) {
      this._selectedId = this._sailings[0]?.id;
    }
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
