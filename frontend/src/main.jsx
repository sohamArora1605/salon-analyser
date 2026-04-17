import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

const endpoints = {
  overview: "/analytics/overview",
  trends: "/analytics/trends",
  staff: "/analytics/staff",
  services: "/analytics/services",
  products: "/analytics/products",
  ml: "/analytics/ml",
  eda: "/analytics/eda",
  predictionOptions: "/analytics/predict/options",
};

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const number = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1,
});

function formatDate(value) {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(new Date(value));
}

async function getJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`${path}: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function postJson(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`${path}: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

function useDashboardData() {
  const [state, setState] = useState({ status: "loading", data: null, error: "" });

  useEffect(() => {
    let active = true;
    Promise.all(Object.entries(endpoints).map(async ([key, path]) => [key, await getJson(path)]))
      .then((entries) => {
        if (active) {
          setState({ status: "ready", data: Object.fromEntries(entries), error: "" });
        }
      })
      .catch((error) => {
        if (active) {
          setState({ status: "error", data: null, error: error.message });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return state;
}

function KpiCard({ label, value, note, tone = "ink" }) {
  return (
    <article className={`kpi ${tone}`}>
      <p>{label}</p>
      <strong>{value}</strong>
      <span>{note}</span>
    </article>
  );
}

function Panel({ title, note, children, className = "" }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <section className={`panel ${className} ${expanded ? "expanded" : ""}`}>
      <div className="panel-title" onClick={() => setExpanded(!expanded)} style={{ cursor: "pointer" }}>
        <h2>{title}</h2>
        <p>{note}</p>
        <button className="expand-btn" title={expanded ? "Collapse" : "Expand"}>
          {expanded ? "−" : "+"}
        </button>
      </div>
      {(expanded || className.includes("wide")) && children}
    </section>
  );
}

function Bars({ data, labelKey, valueKey, valueLabel, limit = 8, interactive = false }) {
  const [hoverId, setHoverId] = useState(null);
  const [sortBy, setSortBy] = useState("value");
  
  const sorted = useMemo(() => {
    const copy = [...data];
    if (sortBy === "label") copy.sort((a, b) => String(a[labelKey]).localeCompare(String(b[labelKey])));
    else copy.sort((a, b) => Number(b[valueKey]) - Number(a[valueKey]));
    return copy;
  }, [data, sortBy, labelKey, valueKey]);

  const rows = sorted.slice(0, limit);
  const max = Math.max(...rows.map((row) => Number(row[valueKey]) || 0), 1);

  return (
    <div className="bars">
      {interactive && (
        <div className="chart-controls">
          <button onClick={() => setSortBy("value")} className={sortBy === "value" ? "active" : ""}>
            By Value
          </button>
          <button onClick={() => setSortBy("label")} className={sortBy === "label" ? "active" : ""}>
            By Name
          </button>
        </div>
      )}
      {rows.map((row) => {
        const value = Number(row[valueKey]) || 0;
        const isHovered = hoverId === row[labelKey];
        return (
          <div
            className="bar-row"
            key={`${row[labelKey]}-${value}`}
            onMouseEnter={() => interactive && setHoverId(row[labelKey])}
            onMouseLeave={() => interactive && setHoverId(null)}
          >
            <div className="bar-label">
              <span title={row[labelKey]}>{row[labelKey] || "Unknown"}</span>
              <strong className={isHovered ? "highlight" : ""}>{valueLabel ? valueLabel(value) : number.format(value)}</strong>
            </div>
            <div className="bar-track" aria-hidden="true">
              <div className="bar-fill" style={{ width: `${Math.max((value / max) * 100, 2)}%`, opacity: isHovered ? 1 : 0.7 }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function VerticalBars({ data, labelKey, valueKey, valueLabel, interactive = false }) {
  const [hoverId, setHoverId] = useState(null);
  const max = Math.max(...data.map((row) => Number(row[valueKey]) || 0), 1);
  
  return (
    <div className="vertical-bars">
      {data.map((row) => {
        const value = Number(row[valueKey]) || 0;
        const isHovered = hoverId === row[labelKey];
        return (
          <div
            className="vbar"
            key={`${row[labelKey]}-${value}`}
            onMouseEnter={() => interactive && setHoverId(row[labelKey])}
            onMouseLeave={() => interactive && setHoverId(null)}
          >
            <strong className={isHovered ? "highlight" : ""}>{valueLabel ? valueLabel(value) : number.format(value)}</strong>
            <div className="vbar-track">
              <div style={{ height: `${Math.max((value / max) * 100, 2)}%`, opacity: isHovered ? 1 : 0.7 }} />
            </div>
            <span title={row[labelKey]}>{row[labelKey]}</span>
          </div>
        );
      })}
    </div>
  );
}

function TrendLine({ points, valueKey, color = "#187c76", interactive = false }) {
  const [hoverId, setHoverId] = useState(null);
  const chart = useMemo(() => {
    const rows = points.slice(-46);
    const values = rows.map((row) => Number(row[valueKey]) || 0);
    const max = Math.max(...values, 1);
    const width = 640;
    const height = 180;
    const step = rows.length > 1 ? width / (rows.length - 1) : width;
    const path = rows
      .map((row, index) => {
        const x = index * step;
        const y = height - ((Number(row[valueKey]) || 0) / max) * (height - 16) - 8;
        return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
      })
      .join(" ");

    return { rows, path, width, height, step, max };
  }, [points, valueKey]);

  return (
    <div className="trend">
      <svg viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label="Trend chart">
        <path d={chart.path} fill="none" stroke={color} strokeWidth="4" strokeLinecap="round" />
        {interactive && chart.rows.map((row, index) => (
          <circle
            key={index}
            cx={index * chart.step}
            cy={chart.height - ((Number(row[valueKey]) || 0) / chart.max) * (chart.height - 16) - 8}
            r="4"
            fill={hoverId === index ? color : "transparent"}
            stroke={color}
            strokeWidth="2"
            style={{ cursor: "pointer" }}
            onMouseEnter={() => setHoverId(index)}
            onMouseLeave={() => setHoverId(null)}
            title={`${formatDate(row.date)}: ${valueLabel ? valueLabel(Number(row[valueKey])) : number.format(Number(row[valueKey]))}`}
          />
        ))}
      </svg>
      <div className="trend-axis">
        <span>{chart.rows[0] ? formatDate(chart.rows[0].date) : ""}</span>
        {hoverId !== null && chart.rows[hoverId] && (
          <span className="hover-date">{formatDate(chart.rows[hoverId].date)}: {number.format(Number(chart.rows[hoverId][valueKey]))}</span>
        )}
        <span>{chart.rows.at(-1) ? formatDate(chart.rows.at(-1).date) : ""}</span>
      </div>
    </div>
  );
}

function MultiLine({ points, interactive = false }) {
  const [hoverId, setHoverId] = useState(null);
  const chart = useMemo(() => {
    const rows = points.slice(-52);
    const keys = ["appointments", "cancellations", "no_shows"];
    const max = Math.max(...rows.flatMap((row) => keys.map((key) => Number(row[key]) || 0)), 1);
    const width = 640;
    const height = 190;
    const step = rows.length > 1 ? width / (rows.length - 1) : width;
    const lines = keys.map((key) => ({
      key,
      path: rows
        .map((row, index) => {
          const x = index * step;
          const y = height - ((Number(row[key]) || 0) / max) * (height - 16) - 8;
          return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
        })
        .join(" "),
    }));
    return { rows, lines, width, height, step, max };
  }, [points]);

  const colors = { appointments: "#187c76", cancellations: "#d85845", no_shows: "#d5a51f" };
  return (
    <div className="trend">
      <svg viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label="Appointment flow chart">
        {chart.lines.map((line) => (
          <path key={line.key} d={line.path} fill="none" stroke={colors[line.key]} strokeWidth="4" strokeLinecap="round" />
        ))}
        {interactive && chart.rows.map((row, index) => (
          <g key={index} onMouseEnter={() => setHoverId(index)} onMouseLeave={() => setHoverId(null)} style={{ cursor: "pointer" }}>
            {chart.lines.map((line) => (
              <circle
                key={`${line.key}-${index}`}
                cx={index * chart.step}
                cy={chart.height - ((Number(row[line.key]) || 0) / chart.max) * (chart.height - 16) - 8}
                r={hoverId === index ? 5 : 3}
                fill={colors[line.key]}
                opacity={hoverId === index ? 1 : 0.4}
              />
            ))}
          </g>
        ))}
      </svg>
      <div className="legend">
        {chart.lines.map((line) => (
          <span key={line.key}>
            <i style={{ background: colors[line.key] }} />
            {line.key.replace("_", "-")}
          </span>
        ))}
      </div>
    </div>
  );
}

function Donut({ data, labelKey, valueKey, interactive = false }) {
  const [hoverId, setHoverId] = useState(null);
  const total = data.reduce((sum, row) => sum + (Number(row[valueKey]) || 0), 0) || 1;
  let offset = 25;
  const palette = ["#187c76", "#d85845", "#d5a51f", "#51606f", "#8d5a4a", "#2d8b57"];

  return (
    <div className="donut-wrap">
      <svg viewBox="0 0 42 42" className="donut" role="img" aria-label="Share chart">
        <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="#ebe9e1" strokeWidth="7" />
        {data.map((row, index) => {
          const value = Number(row[valueKey]) || 0;
          const dash = (value / total) * 100;
          const isHovered = hoverId === row[labelKey];
          const segment = (
            <circle
              key={row[labelKey]}
              cx="21"
              cy="21"
              r="15.915"
              fill="transparent"
              stroke={palette[index % palette.length]}
              strokeWidth={isHovered ? "8" : "7"}
              strokeDasharray={`${dash} ${100 - dash}`}
              strokeDashoffset={offset}
              style={{ cursor: interactive ? "pointer" : "default" }}
              onMouseEnter={() => interactive && setHoverId(row[labelKey])}
              onMouseLeave={() => interactive && setHoverId(null)}
            />
          );
          offset -= dash;
          return segment;
        })}
      </svg>
      <div className="donut-list">
        {data.map((row, index) => (
          <span
            key={row[labelKey]}
            className={hoverId === row[labelKey] ? "highlight" : ""}
            onMouseEnter={() => interactive && setHoverId(row[labelKey])}
            onMouseLeave={() => interactive && setHoverId(null)}
            style={{ cursor: interactive ? "pointer" : "default" }}
          >
            <i style={{ background: palette[index % palette.length] }} />
            {row[labelKey]}: {number.format(row[valueKey])}
          </span>
        ))}
      </div>
    </div>
  );
}

function Scatter({ data, interactive = false }) {
  const [hoverId, setHoverId] = useState(null);
  const maxX = Math.max(...data.map((row) => Number(row.inventory_cost) || 0), 1);
  const maxY = Math.max(...data.map((row) => Number(row.units) || 0), 1);
  return (
    <div className="scatter-wrap">
      <svg className="scatter" viewBox="0 0 520 240" role="img" aria-label="Inventory scatter chart">
        <line x1="36" y1="206" x2="500" y2="206" stroke="#e0ddd8" strokeWidth="1" />
        <line x1="36" y1="20" x2="36" y2="206" stroke="#e0ddd8" strokeWidth="1" />
        {data.map((row, index) => {
          const x = 36 + ((Number(row.inventory_cost) || 0) / maxX) * 448;
          const y = 206 - ((Number(row.units) || 0) / maxY) * 170;
          const radius = 5 + Math.min(Number(row.products) || 0, 20) * 0.45;
          const isHovered = hoverId === row.brand;
          return (
            <circle
              key={row.brand}
              cx={x}
              cy={y}
              r={isHovered ? radius + 2 : radius}
              fill={isHovered ? "#187c76" : "#c1d5d2"}
              stroke={isHovered ? "#187c76" : "transparent"}
              strokeWidth="2"
              style={{ cursor: interactive ? "pointer" : "default" }}
              onMouseEnter={() => interactive && setHoverId(row.brand)}
              onMouseLeave={() => interactive && setHoverId(null)}
              title={`${row.brand}: $${number.format(row.inventory_cost)} (${number.format(row.units)} units)`}
            />
          );
        })}
      </svg>
      {hoverId && (
        <div className="scatter-tooltip">
          {data.find((row) => row.brand === hoverId) && (
            <>
              <strong>{hoverId}</strong>
              <p>${number.format(data.find((row) => row.brand === hoverId).inventory_cost)}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function StaffTable({ rows, interactive = false }) {
  const [sortBy, setSortBy] = useState("revenue");
  const [hoverId, setHoverId] = useState(null);

  const sorted = useMemo(() => {
    const copy = [...rows];
    if (sortBy === "appointments") copy.sort((a, b) => b.appointments - a.appointments);
    else if (sortBy === "risk") copy.sort((a, b) => (b.no_show_rate || 0) - (a.no_show_rate || 0));
    else copy.sort((a, b) => b.revenue - a.revenue);
    return copy;
  }, [rows, sortBy]);

  return (
    <div className="table-wrap">
      {interactive && (
        <div className="chart-controls">
          <button onClick={() => setSortBy("revenue")} className={sortBy === "revenue" ? "active" : ""}>
            Revenue
          </button>
          <button onClick={() => setSortBy("appointments")} className={sortBy === "appointments" ? "active" : ""}>
            Bookings
          </button>
          <button onClick={() => setSortBy("risk")} className={sortBy === "risk" ? "active" : ""}>
            Risk
          </button>
        </div>
      )}
      <table>
        <thead>
          <tr>
            <th>Staff</th>
            <th>Revenue</th>
            <th>Bookings</th>
            <th>No-shows</th>
            <th>Risk</th>
          </tr>
        </thead>
        <tbody>
          {sorted.slice(0, 10).map((row) => (
            <tr
              key={row.staff}
              className={hoverId === row.staff ? "highlight" : ""}
              onMouseEnter={() => interactive && setHoverId(row.staff)}
              onMouseLeave={() => interactive && setHoverId(null)}
            >
              <td>{row.staff}</td>
              <td>{currency.format(row.revenue || 0)}</td>
              <td>{row.appointments}</td>
              <td>{row.no_shows}</td>
              <td>
                <span className={`risk-badge ${(row.no_show_rate || 0) > 15 ? "high" : (row.no_show_rate || 0) > 5 ? "medium" : "low"}`}>
                  {number.format(row.no_show_rate || 0)}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RiskList({ title, rows, interactive = false }) {
  return (
    <Panel title={title} note="Higher values need tighter confirmations.">
      <Bars
        data={rows}
        labelKey="segment"
        valueKey="no_show_probability"
        valueLabel={(value) => `${number.format(value * 100)}%`}
        limit={6}
        interactive={interactive}
      />
    </Panel>
  );
}

function Predictor({ options }) {
  const [form, setForm] = useState({
    book_staff: options.staff?.[0] || "JJ",
    book_tod: options.times?.[0] || "afternoon",
    book_category: options.categories?.[0] || "STYLE",
    recency: 30,
    last_noshow: 0,
    last_cumcancel: 0,
  });
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("idle");

  async function submit(event) {
    event.preventDefault();
    setStatus("loading");
    try {
      const prediction = await postJson("/analytics/predict/no-show", {
        ...form,
        recency: Number(form.recency),
        last_noshow: Number(form.last_noshow),
        last_cumcancel: Number(form.last_cumcancel),
      });
      setResult(prediction);
      setStatus("ready");
    } catch (error) {
      setResult({ error: error.message });
      setStatus("error");
    }
  }

  return (
    <section className="predictor">
      <div>
        <p className="eyebrow">Prediction lab</p>
        <h2>Estimate no-show risk for a new booking.</h2>
      </div>
      <form onSubmit={submit}>
        <label>
          Staff
          <select value={form.book_staff} onChange={(event) => setForm({ ...form, book_staff: event.target.value })}>
            {(options.staff || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Time
          <select value={form.book_tod} onChange={(event) => setForm({ ...form, book_tod: event.target.value })}>
            {(options.times || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Category
          <select value={form.book_category} onChange={(event) => setForm({ ...form, book_category: event.target.value })}>
            {(options.categories || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Days since last visit
          <input min="0" max="365" type="number" value={form.recency} onChange={(event) => setForm({ ...form, recency: event.target.value })} />
        </label>
        <label>
          Last booking was a no-show
          <select value={form.last_noshow} onChange={(event) => setForm({ ...form, last_noshow: event.target.value })}>
            <option value="0">No</option>
            <option value="1">Yes</option>
          </select>
        </label>
        <label>
          Past cancellations
          <input min="0" max="50" type="number" value={form.last_cumcancel} onChange={(event) => setForm({ ...form, last_cumcancel: event.target.value })} />
        </label>
        <button type="submit" className="predict-btn">{status === "loading" ? "Scoring..." : "Predict risk"}</button>
      </form>
      {result && (
        <div className={`prediction-result ${result.risk_level?.toLowerCase() || "error"}`}>
          {result.error ? (
            <strong>{result.error}</strong>
          ) : (
            <>
              <p>{result.model}</p>
              <strong>{number.format(result.probability * 100)}%</strong>
              <span>{result.risk_level} risk. {result.recommendation}</span>
            </>
          )}
        </div>
      )}
    </section>
  );
}

function Dashboard({ data }) {
  const overview = data.overview;
  const staff = data.staff || [];
  const services = data.services || {};
  const products = data.products || {};
  const ml = data.ml || {};
  const eda = data.eda || {};

  return (
    <main>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Salon pulse</p>
          <h1>EDA, predictions, bookings, revenue, stock, and no-show risk in one working view.</h1>
        </div>
        <img
          src="https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=900&q=80"
          alt="Salon stylist working with a client"
        />
      </section>

      <section className="kpi-grid" aria-label="Key metrics">
        <KpiCard label="Revenue" value={currency.format(overview.revenue)} note={`${overview.receipts} receipts`} tone="green" />
        <KpiCard label="Average Ticket" value={currency.format(overview.average_ticket)} note="Per receipt" tone="coral" />
        <KpiCard label="Appointments" value={number.format(overview.appointments)} note={`${overview.cancellations} cancellations`} />
        <KpiCard label="No-show Rate" value={`${overview.no_show_rate}%`} note={`${overview.no_shows} missed visits`} tone="yellow" />
        <KpiCard label="Low Stock" value={overview.low_stock_products} note={`${overview.active_products} active products`} tone="red" />
        <KpiCard label="Inventory Cost" value={currency.format(overview.inventory_cost)} note="On-hand retail cost" tone="green" />
      </section>

      <Predictor options={data.predictionOptions || {}} />

      <section className="split">
        <Panel title="Revenue Run" note="Daily receipt value from imported transactions." className="wide">
          <TrendLine points={data.trends.revenue_by_day} valueKey="revenue" interactive={true} />
        </Panel>
        <Panel title="Top Services" note="Receipt items ranked by revenue.">
          <Bars data={services.top_receipt_items || []} labelKey="description" valueKey="revenue" valueLabel={(value) => currency.format(value)} limit={6} interactive={true} />
        </Panel>
      </section>

      <section className="eda-grid">
        <Panel title="Revenue By Weekday" note="Day-of-week revenue distribution.">
          <VerticalBars data={eda.revenue_by_weekday || []} labelKey="label" valueKey="revenue" valueLabel={(value) => currency.format(value)} interactive={true} />
        </Panel>
        <Panel title="Bookings By Hour" note="Appointment demand by clock hour.">
          <VerticalBars data={(eda.appointments_by_hour || []).map((row) => ({ ...row, label: `${row.hour}:00` }))} labelKey="label" valueKey="appointments" interactive={true} />
        </Panel>
        <Panel title="Receipt Size Histogram" note="Line item count by amount band.">
          <VerticalBars data={eda.receipt_amount_histogram || []} labelKey="label" valueKey="line_items" interactive={true} />
        </Panel>
        <Panel title="Service Category Mix" note="Catalog shape by category.">
          <Donut data={eda.service_categories || []} labelKey="label" valueKey="services" interactive={true} />
        </Panel>
        <Panel title="Revenue by Month" note="Monthly revenue trends and receipt counts.">
          <Bars data={eda.revenue_by_month || []} labelKey="label" valueKey="revenue" valueLabel={(value) => currency.format(value)} interactive={true} />
        </Panel>
        <Panel title="Appointments by Month" note="Monthly appointment volume and distribution.">
          <Bars data={eda.appointments_by_month || []} labelKey="label" valueKey="appointments" interactive={true} />
        </Panel>
        <Panel title="Cancel Notice" note="How early clients cancel.">
          <Bars data={eda.cancel_notice || []} labelKey="label" valueKey="cancellations" interactive={true} />
        </Panel>
        <Panel title="Stock Status" note="Retail inventory by reorder state.">
          <Donut data={eda.stock_status || []} labelKey="label" valueKey="products" interactive={true} />
        </Panel>
        <Panel title="Top Staff Revenue" note="Revenue leaders by team member.">
          <Bars data={eda.top_staff_revenue || []} labelKey="label" valueKey="revenue" valueLabel={(value) => currency.format(value)} limit={8} interactive={true} />
        </Panel>
        <Panel title="Product Category Inventory" note="Inventory value by product category.">
          <Bars data={eda.product_category_inventory || []} labelKey="label" valueKey="inventory_cost" valueLabel={(value) => currency.format(value)} interactive={true} />
        </Panel>
        <Panel title="Cancellation Rate by Staff" note="Who has the highest cancellation rate.">
          <Bars data={eda.cancellation_rate_by_staff || []} labelKey="label" valueKey="cancel_rate" valueLabel={(value) => `${number.format(value)}%`} interactive={true} />
        </Panel>
        <Panel title="Client Frequency" note="Customer segmentation by visit count.">
          <Donut data={eda.client_frequency_segments || []} labelKey="label" valueKey="clients" interactive={true} />
        </Panel>
      </section>

      <section className="split">
        <Panel title="Appointment Flow" note="Bookings, cancellations, and no-shows over time.">
          <MultiLine points={data.trends.appointment_flow || []} interactive={true} />
        </Panel>
        <Panel title="Inventory Scatter" note="Brand inventory cost and units.">
          <Scatter data={products.inventory_by_brand || []} interactive={true} />
        </Panel>
      </section>

      <section className="split">
        <Panel title="Staff Performance" note="Revenue and appointment reliability by team member.">
          <StaffTable rows={staff} interactive={true} />
        </Panel>
        <Panel title="Stock Watch" note="Products at or below minimum stock.">
          <div className="stock-list">
            {(products.low_stock || []).slice(0, 8).map((item) => (
              <article className="stock-item" key={item.product_code}>
                <div>
                  <strong>{item.description}</strong>
                  <span>{item.brand || "Unknown brand"}</span>
                </div>
                <p>{number.format(item.on_hand)} on hand</p>
              </article>
            ))}
          </div>
        </Panel>
      </section>

      <section className="risk-grid">
        <RiskList title="Risk By Staff" rows={ml.risk_by_staff || []} interactive={true} />
        <RiskList title="Risk By Time" rows={ml.risk_by_time || []} interactive={true} />
        <RiskList title="Risk By Service Type" rows={ml.risk_by_category || []} interactive={true} />
        <RiskList title="Risk By Recency" rows={eda.no_show_by_recency || []} interactive={true} />
      </section>
    </main>
  );
}

function App() {
  const { status, data, error } = useDashboardData();

  if (status === "loading") {
    return <div className="state">Loading salon analytics...</div>;
  }

  if (status === "error") {
    return (
      <div className="state">
        <strong>Could not load analytics.</strong>
        <span>{error}</span>
      </div>
    );
  }

  return <Dashboard data={data} />;
}

createRoot(document.getElementById("root")).render(<App />);

  return (
    <div className="donut-wrap">
      <svg viewBox="0 0 42 42" className="donut" role="img" aria-label="Share chart">
        <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="#ebe9e1" strokeWidth="7" />
        {data.map((row, index) => {
          const value = Number(row[valueKey]) || 0;
          const dash = (value / total) * 100;
          const segment = (
            <circle
              key={row[labelKey]}
              cx="21"
              cy="21"
              r="15.915"
              fill="transparent"
              stroke={palette[index % palette.length]}
              strokeWidth="7"
              strokeDasharray={`${dash} ${100 - dash}`}
              strokeDashoffset={offset}
            />
          );
          offset -= dash;
          return segment;
        })}
      </svg>
      <div className="donut-list">
        {data.map((row, index) => (
          <span key={row[labelKey]}>
            <i style={{ background: palette[index % palette.length] }} />
            {row[labelKey]}: {number.format(row[valueKey])}
          </span>
        ))}
      </div>
    </div>
  );
}

function Scatter({ data }) {
  const maxX = Math.max(...data.map((row) => Number(row.inventory_cost) || 0), 1);
  const maxY = Math.max(...data.map((row) => Number(row.units) || 0), 1);
  return (
    <svg className="scatter" viewBox="0 0 520 240" role="img" aria-label="Inventory scatter chart">
      <line x1="36" y1="206" x2="500" y2="206" />
      <line x1="36" y1="20" x2="36" y2="206" />
      {data.map((row) => {
        const x = 36 + ((Number(row.inventory_cost) || 0) / maxX) * 448;
        const y = 206 - ((Number(row.units) || 0) / maxY) * 170;
        const radius = 5 + Math.min(Number(row.products) || 0, 20) * 0.45;
        return <circle key={row.brand} cx={x} cy={y} r={radius} />;
      })}
    </svg>
  );
}

function StaffTable({ rows }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Staff</th>
            <th>Revenue</th>
            <th>Bookings</th>
            <th>No-shows</th>
            <th>Risk</th>
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 10).map((row) => (
            <tr key={row.staff}>
              <td>{row.staff}</td>
              <td>{currency.format(row.revenue || 0)}</td>
              <td>{row.appointments}</td>
              <td>{row.no_shows}</td>
              <td>{number.format(row.no_show_rate || 0)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RiskList({ title, rows }) {
  return (
    <Panel title={title} note="Higher values need tighter confirmations.">
      <Bars
        data={rows}
        labelKey="segment"
        valueKey="no_show_probability"
        valueLabel={(value) => `${number.format(value * 100)}%`}
        limit={6}
      />
    </Panel>
  );
}

function Predictor({ options }) {
  const [form, setForm] = useState({
    book_staff: options.staff?.[0] || "JJ",
    book_tod: options.times?.[0] || "afternoon",
    book_category: options.categories?.[0] || "STYLE",
    recency: 30,
    last_noshow: 0,
    last_cumcancel: 0,
  });
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("idle");

  async function submit(event) {
    event.preventDefault();
    setStatus("loading");
    try {
      const prediction = await postJson("/analytics/predict/no-show", {
        ...form,
        recency: Number(form.recency),
        last_noshow: Number(form.last_noshow),
        last_cumcancel: Number(form.last_cumcancel),
      });
      setResult(prediction);
      setStatus("ready");
    } catch (error) {
      setResult({ error: error.message });
      setStatus("error");
    }
  }

  return (
    <section className="predictor">
      <div>
        <p className="eyebrow">Prediction lab</p>
        <h2>Estimate no-show risk for a new booking.</h2>
      </div>
      <form onSubmit={submit}>
        <label>
          Staff
          <select value={form.book_staff} onChange={(event) => setForm({ ...form, book_staff: event.target.value })}>
            {(options.staff || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Time
          <select value={form.book_tod} onChange={(event) => setForm({ ...form, book_tod: event.target.value })}>
            {(options.times || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Category
          <select value={form.book_category} onChange={(event) => setForm({ ...form, book_category: event.target.value })}>
            {(options.categories || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Days since last visit
          <input min="0" max="365" type="number" value={form.recency} onChange={(event) => setForm({ ...form, recency: event.target.value })} />
        </label>
        <label>
          Last booking was a no-show
          <select value={form.last_noshow} onChange={(event) => setForm({ ...form, last_noshow: event.target.value })}>
            <option value="0">No</option>
            <option value="1">Yes</option>
          </select>
        </label>
        <label>
          Past cancellations
          <input min="0" max="50" type="number" value={form.last_cumcancel} onChange={(event) => setForm({ ...form, last_cumcancel: event.target.value })} />
        </label>
        <button type="submit">{status === "loading" ? "Scoring..." : "Predict risk"}</button>
      </form>
      {result && (
        <div className={`prediction-result ${result.risk_level?.toLowerCase() || "error"}`}>
          {result.error ? (
            <strong>{result.error}</strong>
          ) : (
            <>
              <p>{result.model}</p>
              <strong>{number.format(result.probability * 100)}%</strong>
              <span>{result.risk_level} risk. {result.recommendation}</span>
            </>
          )}
        </div>
      )}
    </section>
  );
}

function Dashboard({ data }) {
  const overview = data.overview;
  const staff = data.staff || [];
  const services = data.services || {};
  const products = data.products || {};
  const ml = data.ml || {};
  const eda = data.eda || {};

  return (
    <main>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Salon pulse</p>
          <h1>EDA, predictions, bookings, revenue, stock, and no-show risk in one working view.</h1>
        </div>
        <img
          src="https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=900&q=80"
          alt="Salon stylist working with a client"
        />
      </section>

      <section className="kpi-grid" aria-label="Key metrics">
        <KpiCard label="Revenue" value={currency.format(overview.revenue)} note={`${overview.receipts} receipts`} tone="green" />
        <KpiCard label="Average Ticket" value={currency.format(overview.average_ticket)} note="Per receipt" tone="coral" />
        <KpiCard label="Appointments" value={number.format(overview.appointments)} note={`${overview.cancellations} cancellations`} />
        <KpiCard label="No-show Rate" value={`${overview.no_show_rate}%`} note={`${overview.no_shows} missed visits`} tone="yellow" />
        <KpiCard label="Low Stock" value={overview.low_stock_products} note={`${overview.active_products} active products`} tone="red" />
        <KpiCard label="Inventory Cost" value={currency.format(overview.inventory_cost)} note="On-hand retail cost" tone="green" />
      </section>

      <Predictor options={data.predictionOptions || {}} />

      <section className="split">
        <Panel title="Revenue Run" note="Daily receipt value from imported transactions." className="wide">
          <TrendLine points={data.trends.revenue_by_day} valueKey="revenue" />
        </Panel>
        <Panel title="Top Services" note="Receipt items ranked by revenue.">
          <Bars data={services.top_receipt_items || []} labelKey="description" valueKey="revenue" valueLabel={(value) => currency.format(value)} limit={6} />
        </Panel>
      </section>

      <section className="eda-grid">
        <Panel title="Revenue By Weekday" note="Day-of-week revenue distribution.">
          <VerticalBars data={eda.revenue_by_weekday || []} labelKey="label" valueKey="revenue" valueLabel={(value) => currency.format(value)} />
        </Panel>
        <Panel title="Bookings By Hour" note="Appointment demand by clock hour.">
          <VerticalBars data={(eda.appointments_by_hour || []).map((row) => ({ ...row, label: `${row.hour}:00` }))} labelKey="label" valueKey="appointments" />
        </Panel>
        <Panel title="Receipt Size Histogram" note="Line item count by amount band.">
          <VerticalBars data={eda.receipt_amount_histogram || []} labelKey="label" valueKey="line_items" />
        </Panel>
        <Panel title="Service Category Mix" note="Catalog shape by category.">
          <Donut data={eda.service_categories || []} labelKey="label" valueKey="services" />
        </Panel>
        <Panel title="Cancel Notice" note="How early clients cancel.">
          <Bars data={eda.cancel_notice || []} labelKey="label" valueKey="cancellations" />
        </Panel>
        <Panel title="Stock Status" note="Retail inventory by reorder state.">
          <Donut data={eda.stock_status || []} labelKey="label" valueKey="products" />
        </Panel>
      </section>

      <section className="split">
        <Panel title="Appointment Flow" note="Bookings, cancellations, and no-shows over time.">
          <MultiLine points={data.trends.appointment_flow || []} />
        </Panel>
        <Panel title="Inventory Scatter" note="Brand inventory cost and units.">
          <Scatter data={products.inventory_by_brand || []} />
          <Bars data={products.inventory_by_brand || []} labelKey="brand" valueKey="inventory_cost" valueLabel={(value) => currency.format(value)} limit={5} />
        </Panel>
      </section>

      <section className="split">
        <Panel title="Staff Performance" note="Revenue and appointment reliability by team member.">
          <StaffTable rows={staff} />
        </Panel>
        <Panel title="Stock Watch" note="Products at or below minimum stock.">
          <div className="stock-list">
            {(products.low_stock || []).slice(0, 8).map((item) => (
              <article className="stock-item" key={item.product_code}>
                <div>
                  <strong>{item.description}</strong>
                  <span>{item.brand || "Unknown brand"}</span>
                </div>
                <p>{number.format(item.on_hand)} on hand</p>
              </article>
            ))}
          </div>
        </Panel>
      </section>

      <section className="risk-grid">
        <RiskList title="Risk By Staff" rows={ml.risk_by_staff || []} />
        <RiskList title="Risk By Time" rows={ml.risk_by_time || []} />
        <RiskList title="Risk By Service Type" rows={ml.risk_by_category || []} />
      </section>
    </main>
  );
}
