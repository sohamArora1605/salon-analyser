from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.db.mongo import get_db


router = APIRouter(prefix="/analytics", tags=["analytics"])


def _df_for(collection_name: str, projection: dict | None = None) -> pd.DataFrame:
    db = get_db()
    cursor = db[collection_name].find({}, projection or None)
    records = list(cursor)
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    return df


class NoShowPredictionInput(BaseModel):
    book_staff: str = Field(default="JJ")
    book_tod: str = Field(default="afternoon")
    book_category: str = Field(default="STYLE")
    recency: int = Field(default=30, ge=0, le=365)
    last_noshow: int = Field(default=0, ge=0, le=1)
    last_cumcancel: int = Field(default=0, ge=0, le=50)


@router.get("/overview")
def overview() -> dict:
    db = get_db()
    receipts = _df_for("receipt_transactions")

    revenue = float(receipts["amount"].sum()) if not receipts.empty else 0
    receipts_count = int(receipts["receipt_number"].nunique()) if not receipts.empty else 0

    appointments = db.appointments.count_documents({})
    cancellations = db.cancellations.count_documents({})
    no_shows = db.no_shows.count_documents({})

    services = _df_for("services")
    products = _df_for("products")

    active_services = int(services[services.get("is_active") == True].shape[0]) if not services.empty else 0
    active_products = int(products[products.get("is_active") == True].shape[0]) if not products.empty else 0

    if not products.empty and "on_hand" in products and "cost" in products:
        inventory_cost = float((products["on_hand"].fillna(0) * products["cost"].fillna(0)).sum())
    else:
        inventory_cost = 0.0

    low_stock_products = 0
    if not products.empty and {"on_hand", "minimum_stock"}.issubset(products.columns):
        low_stock_products = int(products[(products["is_active"] == True) & (products["on_hand"] <= products["minimum_stock"])].shape[0])

    metrics = {
        "revenue": revenue,
        "receipts": receipts_count,
        "appointments": int(appointments),
        "cancellations": int(cancellations),
        "no_shows": int(no_shows),
        "active_services": active_services,
        "active_products": active_products,
        "inventory_cost": inventory_cost,
        "low_stock_products": low_stock_products,
    }

    metrics["average_ticket"] = round(revenue / receipts_count, 2) if receipts_count else 0
    metrics["no_show_rate"] = round((no_shows / appointments) * 100, 2) if appointments else 0
    return metrics


@router.get("/trends")
def trends() -> dict[str, list[dict]]:
    receipts = _df_for("receipt_transactions")
    appointments = _df_for("appointments")
    cancellations = _df_for("cancellations")
    no_shows = _df_for("no_shows")

    result: dict[str, list[dict]] = {}

    if not receipts.empty and "transaction_date" in receipts:
        r = receipts.dropna(subset=["transaction_date"]).copy()
        r["transaction_date"] = pd.to_datetime(r["transaction_date"])
        grp = r.groupby(r["transaction_date"].dt.date)
        result["revenue_by_day"] = [
            {"date": str(k), "revenue": float(v["amount"].sum()), "receipts": int(v["receipt_number"].nunique())}
            for k, v in grp
        ]
    else:
        result["revenue_by_day"] = []

    # appointment flow: combine dates
    frames = []
    if not appointments.empty and "appointment_date" in appointments:
        a = appointments.dropna(subset=["appointment_date"]).copy()
        a["appointment_date"] = pd.to_datetime(a["appointment_date"])
        a = a.groupby(a["appointment_date"].dt.date).size().rename("appointments").reset_index()
        a.columns = ["date", "appointments"]
        frames.append(a.set_index("date"))
    if not cancellations.empty and "cancel_date" in cancellations:
        c = cancellations.dropna(subset=["cancel_date"]).copy()
        c["cancel_date"] = pd.to_datetime(c["cancel_date"])
        c = c.groupby(c["cancel_date"].dt.date).size().rename("cancellations").reset_index()
        c.columns = ["date", "cancellations"]
        frames.append(c.set_index("date"))
    if not no_shows.empty and "event_date" in no_shows:
        n = no_shows.dropna(subset=["event_date"]).copy()
        n["event_date"] = pd.to_datetime(n["event_date"])
        n = n.groupby(n["event_date"].dt.date).size().rename("no_shows").reset_index()
        n.columns = ["date", "no_shows"]
        frames.append(n.set_index("date"))

    if frames:
        combined = pd.concat(frames, axis=1).fillna(0).reset_index()
        combined = combined.sort_values(by="date")
        result["appointment_flow"] = [
            {"date": str(row["date"]), "appointments": int(row.get("appointments", 0)), "cancellations": int(row.get("cancellations", 0)), "no_shows": int(row.get("no_shows", 0))}
            for _, row in combined.iterrows()
        ]
    else:
        result["appointment_flow"] = []

    return result


@router.get("/staff")
def staff_performance() -> list[dict]:
    db = get_db()
    receipts = _df_for("receipt_transactions")
    appointments = _df_for("appointments")
    cancellations = _df_for("cancellations")
    no_shows = _df_for("no_shows")

    revenue = (
        receipts.dropna(subset=["staff"]).groupby("staff").agg({"amount": "sum", "receipt_number": pd.Series.nunique}).reset_index()
        if not receipts.empty
        else pd.DataFrame(columns=["staff", "amount", "receipt_number"])
    )
    revenue = revenue.rename(columns={"amount": "revenue", "receipt_number": "receipts"})

    bookings = (
        appointments.dropna(subset=["staff"]).groupby("staff").size().rename("appointments").reset_index()
        if not appointments.empty
        else pd.DataFrame(columns=["staff", "appointments"])
    )

    cancelled = (
        cancellations.dropna(subset=["staff"]).groupby("staff").size().rename("cancellations").reset_index()
        if not cancellations.empty
        else pd.DataFrame(columns=["staff", "cancellations"])
    )

    missed = (
        no_shows.dropna(subset=["staff"]).groupby("staff").size().rename("no_shows").reset_index()
        if not no_shows.empty
        else pd.DataFrame(columns=["staff", "no_shows"])
    )

    staffs = set(revenue["staff"]).union(bookings.get("staff", set())).union(cancelled.get("staff", set())).union(missed.get("staff", set()))

    rows: list[dict[str, Any]] = []
    for staff in staffs:
        rev_row = revenue[revenue["staff"] == staff]
        book_row = bookings[bookings["staff"] == staff]
        can_row = cancelled[cancelled["staff"] == staff]
        miss_row = missed[missed["staff"] == staff]

        rev = float(rev_row["revenue"].iloc[0]) if not rev_row.empty else 0.0
        recpts = int(rev_row["receipts"].iloc[0]) if not rev_row.empty else 0
        apps = int(book_row["appointments"].iloc[0]) if not book_row.empty else 0
        canc = int(can_row["cancellations"].iloc[0]) if not can_row.empty else 0
        ms = int(miss_row["no_shows"].iloc[0]) if not miss_row.empty else 0

        no_show_rate = round((ms / apps) * 100, 2) if apps else 0

        rows.append({
            "staff": staff,
            "revenue": rev,
            "receipts": recpts,
            "appointments": apps,
            "cancellations": canc,
            "no_shows": ms,
            "no_show_rate": no_show_rate,
        })

    rows = sorted(rows, key=lambda r: (r["revenue"], r["appointments"]), reverse=True)
    return rows


@router.get("/services")
def service_insights() -> dict[str, list[dict]]:
    receipts = _df_for("receipt_transactions")
    services = _df_for("services")

    top_receipt_items = []
    if not receipts.empty and "description" in receipts:
        grp = receipts.dropna(subset=["description"]).groupby("description").agg({"description": "size", "quantity": "sum", "amount": "sum"})
        grp = grp.rename(columns={"description": "line_items", "quantity": "quantity", "amount": "revenue"})
        top_receipt_items = [
            {"description": idx, "line_items": int(row["line_items"]), "quantity": float(row["quantity"]), "revenue": float(row["revenue"])}
            for idx, row in grp.sort_values(by="revenue", ascending=False).head(10).iterrows()
        ]

    service_catalog = []
    if not services.empty:
        for _, row in services.sort_values(by=["category", "description"]).iterrows():
            service_catalog.append(
                {
                    "service_code": row.get("service_code") or row.get("service_code"),
                    "description": row.get("description"),
                    "category": row.get("category"),
                    "price": float(row.get("price") or 0),
                    "cost": float(row.get("cost") or 0),
                    "is_active": bool(row.get("is_active")),
                }
            )

    return {"top_receipt_items": top_receipt_items, "service_catalog": service_catalog}


@router.get("/products")
def product_insights() -> dict[str, list[dict]]:
    products = _df_for("products")
    out = {"low_stock": [], "inventory_by_brand": []}
    if not products.empty:
        if {"product_code", "on_hand", "cost", "minimum_stock", "is_active"}.issubset(products.columns):
            low = products[(products["is_active"] == True) & (products["on_hand"] <= products["minimum_stock"])].sort_values(by=["on_hand", "description"]).head(25)
            out["low_stock"] = [
                {
                    "product_code": row.get("product_code"),
                    "description": row.get("description"),
                    "brand": row.get("brand"),
                    "category": row.get("category"),
                    "price": float(row.get("price") or 0),
                    "cost": float(row.get("cost") or 0),
                    "on_hand": float(row.get("on_hand") or 0),
                    "minimum_stock": float(row.get("minimum_stock") or 0),
                    "maximum_stock": float(row.get("maximum_stock") or 0),
                    "inventory_cost": float((row.get("on_hand") or 0) * (row.get("cost") or 0)),
                }
                for _, row in low.iterrows()
            ]

        grp = products.fillna({}).groupby(products["brand"].fillna("Unknown")).agg({"product_code": "count", "on_hand": "sum"})
        grp["inventory_cost"] = products.groupby(products["brand"].fillna("Unknown")).apply(lambda d: (d["on_hand"].fillna(0) * d["cost"].fillna(0)).sum())
        out["inventory_by_brand"] = [
            {"brand": idx, "products": int(row["product_code"]), "units": float(row["on_hand"]), "inventory_cost": float(row["inventory_cost"])}
            for idx, row in grp.sort_values(by="inventory_cost", ascending=False).head(10).iterrows()
        ]

    return out


@router.get("/ml")
def ml_insights() -> dict[str, list[dict]]:
    df = _df_for("ml_seed_events")
    if df.empty or "payload" not in df:
        return {"risk_by_staff": [], "risk_by_time": [], "risk_by_category": []}

    payloads = pd.json_normalize(df["payload"]).replace({pd.NA: None})
    payloads["noshow"] = pd.to_numeric(payloads.get("noshow", pd.Series([])), errors="coerce").fillna(0)

    def agg_by(key: str):
        if key not in payloads:
            return []
        g = payloads.groupby(payloads[key].fillna("unknown")).agg({"noshow": ["mean", "count"]})
        g.columns = ["no_show_probability", "bookings"]
        g = g.reset_index()
        g = g[g["bookings"] >= 20]
        g = g.sort_values(by=["no_show_probability", "bookings"], ascending=[False, False])
        return [
            {"segment": row[key] if row[key] else "unknown", "bookings": int(row["bookings"]), "no_show_probability": float(row["no_show_probability"]) }
            for _, row in g.iterrows()
        ]

    return {"risk_by_staff": agg_by("book_staff"), "risk_by_time": agg_by("book_tod"), "risk_by_category": agg_by("book_category")}


@router.get("/eda")
def eda() -> dict[str, list[dict]]:
    receipts = _df_for("receipt_transactions")
    appointments = _df_for("appointments")
    services = _df_for("services")
    products = _df_for("products")
    cancellations = _df_for("cancellations")
    ml = _df_for("ml_seed_events")

    out: dict[str, list[dict]] = {}

    # revenue_by_weekday
    if not receipts.empty and "transaction_date" in receipts:
        r = receipts.dropna(subset=["transaction_date"]).copy()
        r["transaction_date"] = pd.to_datetime(r["transaction_date"]).dt.day_name()
        g = r.groupby("transaction_date").agg({"amount": "sum", "receipt_number": pd.Series.nunique}).reset_index()
        out["revenue_by_weekday"] = [ {"label": row["transaction_date"], "revenue": float(row["amount"]), "receipts": int(row["receipt_number"])} for _, row in g.iterrows() ]
    else:
        out["revenue_by_weekday"] = []

    # appointments_by_weekday
    if not appointments.empty and "appointment_date" in appointments:
        a = appointments.dropna(subset=["appointment_date"]).copy()
        a["dow"] = pd.to_datetime(a["appointment_date"]).dt.day_name()
        g = a.groupby("dow").size().reset_index(name="appointments")
        out["appointments_by_weekday"] = [ {"label": row["dow"], "appointments": int(row["appointments"])} for _, row in g.iterrows() ]
    else:
        out["appointments_by_weekday"] = []

    # appointments_by_hour
    if not appointments.empty and "appointment_time" in appointments:
        at = appointments.dropna(subset=["appointment_time"]).copy()
        at["hour"] = pd.to_datetime(at["appointment_time"].astype(str), errors="coerce").dt.hour
        g = at.groupby("hour").size().reset_index(name="appointments")
        out["appointments_by_hour"] = [ {"hour": int(row["hour"]), "appointments": int(row["appointments"])} for _, row in g.iterrows() ]
    else:
        out["appointments_by_hour"] = []

    # service_categories
    if not services.empty and "category" in services:
        g = services.groupby(services["category"].fillna("Unknown")).agg({"service_code": "count", "price": "mean"}).reset_index()
        out["service_categories"] = [ {"label": row["category"], "services": int(row["service_code"]), "average_price": float(row["price"] or 0)} for _, row in g.iterrows() ]
    else:
        out["service_categories"] = []

    # receipt_amount_histogram (simple bins)
    if not receipts.empty and "amount" in receipts:
        bins = [0,25,50,100,150,250,1e9]
        labels = ["$0-24","$25-49","$50-99","$100-149","$150-249","$250+"]
        receipts["bin"] = pd.cut(receipts["amount"].fillna(0), bins=bins, labels=labels, right=False)
        g = receipts.groupby("bin").agg({"amount": "sum", "receipt_number": pd.Series.nunique}).reset_index()
        out["receipt_amount_histogram"] = [ {"label": row["bin"], "line_items": int(receipts[receipts["bin"]==row["bin"]].shape[0]), "revenue": float(row["amount"])} for _, row in g.iterrows() ]
    else:
        out["receipt_amount_histogram"] = []

    # cancel_notice
    if not cancellations.empty and "days_before" in cancellations:
        c = cancellations.copy()
        def bucket_days(x):
            if x <= 0: return "Same day"
            if x == 1: return "1 day"
            if x <= 3: return "2-3 days"
            if x <= 7: return "4-7 days"
            return "8+ days"
        c["label"] = c["days_before"].apply(bucket_days)
        g = c.groupby("label").size().reset_index(name="cancellations")
        out["cancel_notice"] = [ {"label": row["label"], "cancellations": int(row["cancellations"])} for _, row in g.iterrows() ]
    else:
        out["cancel_notice"] = []

    # stock_status
    if not products.empty and {"on_hand","minimum_stock","maximum_stock"}.issubset(products.columns):
        def status(r):
            if r["on_hand"] <= r["minimum_stock"]: return "Reorder"
            if r["on_hand"] >= r["maximum_stock"]: return "Full"
            return "Balanced"
        products["status"] = products.apply(lambda r: status(r), axis=1)
        g = products.groupby("status").agg({"product_code": "count", "on_hand": "sum"}).reset_index()
        out["stock_status"] = [ {"label": row["status"], "products": int(row["product_code"]), "inventory_cost": float((products[products["status"]==row["status"]]["on_hand"]*products[products["status"]==row["status"]]["cost"]).sum())} for _, row in g.iterrows() ]
    else:
        out["stock_status"] = []

    # no_show_by_recency
    if not ml.empty and "payload" in ml:
        p = pd.json_normalize(ml["payload"]).copy()
        if "recency" in p:
            p["recency"] = pd.to_numeric(p["recency"], errors="coerce").fillna(9999)
            def rec_bucket(x):
                if x <= 7: return "0-7 days"
                if x <= 30: return "8-30 days"
                if x <= 90: return "31-90 days"
                return "91+ days"
            p["label"] = p["recency"].apply(rec_bucket)
            p["noshow"] = pd.to_numeric(p.get("noshow", pd.Series([])), errors="coerce").fillna(0)
            g = p.groupby("label").agg({"noshow": ["mean", "count"]})
            g.columns = ["no_show_probability", "bookings"]
            g = g.reset_index()
            out["no_show_by_recency"] = [ {"label": row["label"], "bookings": int(row["bookings"]), "no_show_probability": float(row["no_show_probability"])} for _, row in g.iterrows() ]
        else:
            out["no_show_by_recency"] = []
    else:
        out["no_show_by_recency"] = []

    # appointments_by_month
    def _ym(d: pd.Series, col: str):
        return pd.to_datetime(d[col]).dt.to_period("M").dt.to_timestamp()

    if not appointments.empty and "appointment_date" in appointments:
        a = appointments.dropna(subset=["appointment_date"]).copy()
        a["ym"] = pd.to_datetime(a["appointment_date"]).dt.to_period("M").astype(str)
        g = a.groupby("ym").size().reset_index(name="appointments")
        g = g.sort_values(by="ym")
        out["appointments_by_month"] = [{"month": row["ym"], "appointments": int(row["appointments"])} for _, row in g.iterrows()]
    else:
        out["appointments_by_month"] = []

    # revenue_by_month
    if not receipts.empty and "transaction_date" in receipts:
        r = receipts.dropna(subset=["transaction_date"]).copy()
        r["ym"] = pd.to_datetime(r["transaction_date"]).dt.to_period("M").astype(str)
        g = r.groupby("ym").agg({"amount": "sum", "receipt_number": pd.Series.nunique}).reset_index()
        g = g.sort_values(by="ym")
        out["revenue_by_month"] = [
            {"month": row["ym"], "revenue": float(row["amount"]), "receipts": int(row["receipt_number"])}
            for _, row in g.iterrows()
        ]
    else:
        out["revenue_by_month"] = []

    # top_staff_revenue
    if not receipts.empty and "staff" in receipts:
        s = receipts.dropna(subset=["staff"]).copy()
        grp = s.groupby("staff").agg({"amount": "sum", "receipt_number": pd.Series.nunique}).reset_index()
        grp = grp.rename(columns={"amount": "revenue", "receipt_number": "receipts"})
        grp = grp.sort_values(by="revenue", ascending=False).head(10)
        out["top_staff_revenue"] = [
            {"staff": row["staff"], "revenue": float(row["revenue"]), "receipts": int(row["receipts"]) }
            for _, row in grp.iterrows()
        ]
    else:
        out["top_staff_revenue"] = []

    # product_category_inventory
    if not products.empty and {"category", "on_hand", "cost"}.issubset(products.columns):
        p = products.copy()
        p["category"] = p["category"].fillna("Unknown")
        grp = p.groupby("category").agg({"product_code": "count", "on_hand": "sum"}).reset_index()
        grp["inventory_cost"] = p.groupby("category").apply(lambda d: (d["on_hand"].fillna(0) * d["cost"].fillna(0)).sum()).values
        grp = grp.sort_values(by="inventory_cost", ascending=False).head(25)
        out["product_category_inventory"] = [
            {"category": row["category"], "products": int(row["product_code"]), "units": float(row["on_hand"]), "inventory_cost": float(row["inventory_cost"]) }
            for _, row in grp.iterrows()
        ]
    else:
        out["product_category_inventory"] = []

    # client_frequency_segments: detect client id column heuristically
    client_cols = [c for c in receipts.columns if c.lower() in ("client_id","customer_id","client_code","client","customer","member_id")]
    if not receipts.empty and client_cols:
        cid = client_cols[0]
        r = receipts.dropna(subset=[cid]).copy()
        visits = r.groupby(cid).size().rename("visits").reset_index()
        def bucket_visits(n):
            if n == 1:
                return "1"
            if 2 <= n <= 3:
                return "2-3"
            if 4 <= n <= 6:
                return "4-6"
            return "7+"
        visits["segment"] = visits["visits"].apply(bucket_visits)
        seg = visits.groupby("segment").agg({cid: "count", "visits": "sum"}).rename(columns={cid: "customers"}).reset_index()
        out["client_frequency_segments"] = [ {"segment": row["segment"], "customers": int(row["customers"]), "visits": int(row["visits"])} for _, row in seg.iterrows() ]
    else:
        out["client_frequency_segments"] = []

    # cancellation_rate_by_staff
    if not cancellations.empty and "staff" in cancellations:
        can = cancellations.dropna(subset=["staff"]).copy()
        can_cnt = can.groupby("staff").size().rename("cancellations").reset_index()
        apps_by_staff = appointments.dropna(subset=["staff"]).groupby("staff").size().rename("appointments").reset_index() if not appointments.empty and "staff" in appointments else pd.DataFrame(columns=["staff","appointments"])
        merged = pd.merge(apps_by_staff, can_cnt, on="staff", how="outer").fillna(0)
        merged["cancellation_rate"] = merged.apply(lambda r: (r["cancellations"]/r["appointments"]*100) if r["appointments"] else 0, axis=1)
        out["cancellation_rate_by_staff"] = [ {"staff": row["staff"], "appointments": int(row["appointments"]), "cancellations": int(row["cancellations"]), "cancellation_rate": round(float(row["cancellation_rate"]),2)} for _, row in merged.iterrows() ]
    else:
        out["cancellation_rate_by_staff"] = []

    return out


@router.get("/predict/options")
def prediction_options() -> dict[str, list[str]]:
    ml = _df_for("ml_seed_events")
    if ml.empty or "payload" not in ml:
        return {"staff": [], "times": [], "categories": []}
    p = pd.json_normalize(ml["payload"]).replace({pd.NA: None})
    return {
        "staff": sorted([v for v in p.get("book_staff", pd.Series([])).dropna().unique().tolist()]),
        "times": sorted([v for v in p.get("book_tod", pd.Series([])).dropna().unique().tolist()]),
        "categories": sorted([v for v in p.get("book_category", pd.Series([])).dropna().unique().tolist()]),
    }


def _segment_rate(column: str, value: str) -> dict:
    ml = _df_for("ml_seed_events")
    if ml.empty or "payload" not in ml:
        return {"rows": 0, "rate": 0}
    p = pd.json_normalize(ml["payload"]).replace({pd.NA: None})
    if column not in p:
        return {"rows": 0, "rate": 0}
    sel = p[p[column] == value]
    rows = len(sel)
    rate = float(sel.get("noshow", pd.Series([])).dropna().astype(float).mean() or 0)
    return {"rows": rows, "rate": rate}


@router.post("/predict/no-show")
def predict_no_show(payload: NoShowPredictionInput) -> dict:
    ml = _df_for("ml_seed_events")
    if ml.empty or "payload" not in ml:
        base_rate = 0.0
    else:
        p = pd.json_normalize(ml["payload"]).replace({pd.NA: None})
        base_rate = float(p.get("noshow", pd.Series([])).dropna().astype(float).mean() or 0)

    segments = [
        ("Staff", "book_staff", payload.book_staff, 0.32),
        ("Time", "book_tod", payload.book_tod, 0.2),
        ("Service type", "book_category", payload.book_category, 0.24),
    ]

    score = base_rate * 0.24
    drivers = [{"label": "Baseline", "value": "All bookings", "rate": base_rate, "weight": 0.24}]

    for label, column, value, weight in segments:
        seg = _segment_rate(column, value)
        rate = float(seg["rate"] or base_rate)
        rows = int(seg["rows"] or 0)
        score += rate * weight
        drivers.append({"label": label, "value": value, "rate": rate, "rows": rows, "weight": weight})

    recency_adjustment = 0
    if payload.recency <= 7:
        recency_adjustment += 0.035
    elif payload.recency >= 90:
        recency_adjustment += 0.02

    if payload.last_noshow:
        recency_adjustment += 0.12
    if payload.last_cumcancel >= 3:
        recency_adjustment += 0.06
    elif payload.last_cumcancel >= 1:
        recency_adjustment += 0.025

    probability = max(0.01, min(0.85, score + recency_adjustment))
    if probability >= 0.22:
        risk_level = "High"
        recommendation = "Ask for confirmation and consider a deposit or shorter reminder window."
    elif probability >= 0.12:
        risk_level = "Medium"
        recommendation = "Send a reminder and confirm the appointment the day before."
    else:
        risk_level = "Low"
        recommendation = "Standard reminder cadence is enough."

    return {
        "probability": round(probability, 4),
        "risk_level": risk_level,
        "recommendation": recommendation,
        "model": "Segment-weighted no-show probability model",
        "drivers": drivers,
        "adjustments": {
            "recency_days": payload.recency,
            "last_noshow": payload.last_noshow,
            "last_cumcancel": payload.last_cumcancel,
            "adjustment": round(recency_adjustment, 4),
        },
    }
