from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.db.postgres import get_engine

router = APIRouter(prefix="/analytics", tags=["analytics"])


def fetch_one(query: str) -> dict:
    with get_engine().connect() as connection:
        return dict(connection.execute(text(query)).mappings().one())


def fetch_all(query: str) -> list[dict]:
    with get_engine().connect() as connection:
        return [dict(row) for row in connection.execute(text(query)).mappings().all()]


def fetch_all_params(query: str, params: dict) -> list[dict]:
    with get_engine().connect() as connection:
        return [dict(row) for row in connection.execute(text(query), params).mappings().all()]


def fetch_one_params(query: str, params: dict) -> dict:
    with get_engine().connect() as connection:
        return dict(connection.execute(text(query), params).mappings().one())


class NoShowPredictionInput(BaseModel):
    book_staff: str = Field(default="JJ")
    book_tod: str = Field(default="afternoon")
    book_category: str = Field(default="STYLE")
    recency: int = Field(default=30, ge=0, le=365)
    last_noshow: int = Field(default=0, ge=0, le=1)
    last_cumcancel: int = Field(default=0, ge=0, le=50)


@router.get("/overview")
def overview() -> dict:
    metrics = fetch_one(
        """
        select
            coalesce((select sum(amount)::float from receipt_transactions), 0) as revenue,
            coalesce((select count(distinct receipt_number) from receipt_transactions), 0) as receipts,
            coalesce((select count(*) from appointments), 0) as appointments,
            coalesce((select count(*) from cancellations), 0) as cancellations,
            coalesce((select count(*) from no_shows), 0) as no_shows,
            coalesce((select count(*) from services where is_active is true), 0) as active_services,
            coalesce((select count(*) from products where is_active is true), 0) as active_products,
            coalesce((select sum(on_hand * cost)::float from products), 0) as inventory_cost,
            coalesce((
                select count(*) from products
                where is_active is true and on_hand <= minimum_stock
            ), 0) as low_stock_products
        """
    )

    revenue = float(metrics["revenue"] or 0)
    receipts = int(metrics["receipts"] or 0)
    appointments = int(metrics["appointments"] or 0)
    no_shows = int(metrics["no_shows"] or 0)

    metrics["average_ticket"] = round(revenue / receipts, 2) if receipts else 0
    metrics["no_show_rate"] = round((no_shows / appointments) * 100, 2) if appointments else 0
    return metrics


@router.get("/trends")
def trends() -> dict[str, list[dict]]:
    return {
        "revenue_by_day": fetch_all(
            """
            select
                transaction_date as date,
                sum(amount)::float as revenue,
                count(distinct receipt_number) as receipts
            from receipt_transactions
            where transaction_date is not null
            group by transaction_date
            order by transaction_date
            """
        ),
        "appointment_flow": fetch_all(
            """
            with days as (
                select appointment_date as date, count(*) as appointments, 0 as cancellations, 0 as no_shows
                from appointments
                where appointment_date is not null
                group by appointment_date
                union all
                select cancel_date as date, 0, count(*), 0
                from cancellations
                where cancel_date is not null
                group by cancel_date
                union all
                select event_date as date, 0, 0, count(*)
                from no_shows
                where event_date is not null
                group by event_date
            )
            select
                date,
                sum(appointments) as appointments,
                sum(cancellations) as cancellations,
                sum(no_shows) as no_shows
            from days
            group by date
            order by date
            """
        ),
    }


@router.get("/staff")
def staff_performance() -> list[dict]:
    return fetch_all(
        """
        with revenue as (
            select staff, sum(amount)::float as revenue, count(distinct receipt_number) as receipts
            from receipt_transactions
            where staff is not null
            group by staff
        ),
        bookings as (
            select staff, count(*) as appointments
            from appointments
            where staff is not null
            group by staff
        ),
        cancelled as (
            select staff, count(*) as cancellations
            from cancellations
            where staff is not null
            group by staff
        ),
        missed as (
            select staff, count(*) as no_shows
            from no_shows
            where staff is not null
            group by staff
        ),
        staff_names as (
            select staff from revenue
            union select staff from bookings
            union select staff from cancelled
            union select staff from missed
        )
        select
            staff_names.staff,
            coalesce(revenue.revenue, 0) as revenue,
            coalesce(revenue.receipts, 0) as receipts,
            coalesce(bookings.appointments, 0) as appointments,
            coalesce(cancelled.cancellations, 0) as cancellations,
            coalesce(missed.no_shows, 0) as no_shows,
            case
                when coalesce(bookings.appointments, 0) = 0 then 0
                else round((coalesce(missed.no_shows, 0)::numeric / bookings.appointments) * 100, 2)::float
            end as no_show_rate
        from staff_names
        left join revenue on revenue.staff = staff_names.staff
        left join bookings on bookings.staff = staff_names.staff
        left join cancelled on cancelled.staff = staff_names.staff
        left join missed on missed.staff = staff_names.staff
        order by revenue desc, appointments desc
        """
    )


@router.get("/services")
def service_insights() -> dict[str, list[dict]]:
    return {
        "top_receipt_items": fetch_all(
            """
            select
                description,
                count(*) as line_items,
                sum(quantity)::float as quantity,
                sum(amount)::float as revenue
            from receipt_transactions
            where description is not null
            group by description
            order by revenue desc
            limit 10
            """
        ),
        "service_catalog": fetch_all(
            """
            select
                service_code,
                description,
                category,
                price::float as price,
                cost::float as cost,
                is_active
            from services
            order by category, description
            """
        ),
    }


@router.get("/products")
def product_insights() -> dict[str, list[dict]]:
    return {
        "low_stock": fetch_all(
            """
            select
                product_code,
                description,
                brand,
                category,
                price::float as price,
                cost::float as cost,
                on_hand::float as on_hand,
                minimum_stock::float as minimum_stock,
                maximum_stock::float as maximum_stock,
                (on_hand * cost)::float as inventory_cost
            from products
            where is_active is true and on_hand <= minimum_stock
            order by on_hand asc, description
            limit 25
            """
        ),
        "inventory_by_brand": fetch_all(
            """
            select
                coalesce(brand, 'Unknown') as brand,
                count(*) as products,
                sum(on_hand)::float as units,
                sum(on_hand * cost)::float as inventory_cost
            from products
            group by coalesce(brand, 'Unknown')
            order by inventory_cost desc
            limit 10
            """
        ),
    }


@router.get("/ml")
def ml_insights() -> dict[str, list[dict]]:
    return {
        "risk_by_staff": fetch_all(
            """
            select
                payload->>'book_staff' as segment,
                count(*) as bookings,
                avg((payload->>'noshow')::numeric)::float as no_show_probability
            from ml_seed_events
            where payload ? 'book_staff'
            group by payload->>'book_staff'
            having count(*) >= 20
            order by no_show_probability desc, bookings desc
            """
        ),
        "risk_by_time": fetch_all(
            """
            select
                coalesce(payload->>'book_tod', 'unknown') as segment,
                count(*) as bookings,
                avg((payload->>'noshow')::numeric)::float as no_show_probability
            from ml_seed_events
            group by coalesce(payload->>'book_tod', 'unknown')
            order by no_show_probability desc, bookings desc
            """
        ),
        "risk_by_category": fetch_all(
            """
            select
                coalesce(payload->>'book_category', 'unknown') as segment,
                count(*) as bookings,
                avg((payload->>'noshow')::numeric)::float as no_show_probability
            from ml_seed_events
            group by coalesce(payload->>'book_category', 'unknown')
            order by no_show_probability desc, bookings desc
            """
        ),
    }


@router.get("/eda")
def eda() -> dict[str, list[dict]]:
    return {
        "revenue_by_weekday": fetch_all(
            """
            select
                to_char(transaction_date, 'Dy') as label,
                extract(isodow from transaction_date)::int as sort_order,
                sum(amount)::float as revenue,
                count(distinct receipt_number) as receipts
            from receipt_transactions
            where transaction_date is not null
            group by label, sort_order
            order by sort_order
            """
        ),
        "appointments_by_weekday": fetch_all(
            """
            select
                to_char(appointment_date, 'Dy') as label,
                extract(isodow from appointment_date)::int as sort_order,
                count(*) as appointments
            from appointments
            where appointment_date is not null
            group by label, sort_order
            order by sort_order
            """
        ),
        "appointments_by_hour": fetch_all(
            """
            select
                extract(hour from appointment_time)::int as hour,
                count(*) as appointments
            from appointments
            where appointment_time is not null
            group by hour
            order by hour
            """
        ),
        "service_categories": fetch_all(
            """
            select
                coalesce(category, 'Unknown') as label,
                count(*) as services,
                avg(price)::float as average_price
            from services
            group by coalesce(category, 'Unknown')
            order by services desc, label
            """
        ),
        "receipt_amount_histogram": fetch_all(
            """
            select
                case
                    when amount < 25 then '$0-24'
                    when amount < 50 then '$25-49'
                    when amount < 100 then '$50-99'
                    when amount < 150 then '$100-149'
                    when amount < 250 then '$150-249'
                    else '$250+'
                end as label,
                case
                    when amount < 25 then 1
                    when amount < 50 then 2
                    when amount < 100 then 3
                    when amount < 150 then 4
                    when amount < 250 then 5
                    else 6
                end as sort_order,
                count(*) as line_items,
                sum(amount)::float as revenue
            from receipt_transactions
            group by label, sort_order
            order by sort_order
            """
        ),
        "cancel_notice": fetch_all(
            """
            select
                case
                    when days_before <= 0 then 'Same day'
                    when days_before = 1 then '1 day'
                    when days_before <= 3 then '2-3 days'
                    when days_before <= 7 then '4-7 days'
                    else '8+ days'
                end as label,
                case
                    when days_before <= 0 then 1
                    when days_before = 1 then 2
                    when days_before <= 3 then 3
                    when days_before <= 7 then 4
                    else 5
                end as sort_order,
                count(*) as cancellations
            from cancellations
            where days_before is not null
            group by label, sort_order
            order by sort_order
            """
        ),
        "stock_status": fetch_all(
            """
            select
                case
                    when on_hand <= minimum_stock then 'Reorder'
                    when on_hand >= maximum_stock then 'Full'
                    else 'Balanced'
                end as label,
                count(*) as products,
                sum(on_hand * cost)::float as inventory_cost
            from products
            where is_active is true
            group by label
            order by products desc
            """
        ),
        "no_show_by_recency": fetch_all(
            """
            select
                case
                    when (payload->>'recency')::int <= 7 then '0-7 days'
                    when (payload->>'recency')::int <= 30 then '8-30 days'
                    when (payload->>'recency')::int <= 90 then '31-90 days'
                    else '91+ days'
                end as label,
                count(*) as bookings,
                avg((payload->>'noshow')::numeric)::float as no_show_probability
            from ml_seed_events
            where payload ? 'recency' and payload->>'recency' is not null
            group by label
            order by min((payload->>'recency')::int)
            """
        ),
        "appointments_by_month": fetch_all(
            """
            select
                to_char(appointment_date, 'Mon') as label,
                extract(month from appointment_date)::int as sort_order,
                count(*) as appointments,
                count(distinct appointment_id) as unique_slots
            from appointments
            where appointment_date is not null
            group by label, sort_order
            order by sort_order
            """
        ),
        "revenue_by_month": fetch_all(
            """
            select
                to_char(transaction_date, 'Mon') as label,
                extract(month from transaction_date)::int as sort_order,
                sum(amount)::float as revenue,
                count(distinct receipt_number) as receipts
            from receipt_transactions
            where transaction_date is not null
            group by label, sort_order
            order by sort_order
            """
        ),
        "top_staff_revenue": fetch_all(
            """
            select
                staff as label,
                sum(amount)::float as revenue,
                count(distinct receipt_number) as receipts
            from receipt_transactions
            where staff is not null
            group by staff
            order by revenue desc
            limit 10
            """
        ),
        "product_category_inventory": fetch_all(
            """
            select
                coalesce(category, 'Unknown') as label,
                count(*) as products,
                sum(on_hand)::float as units,
                sum(on_hand * cost)::float as inventory_cost
            from products
            where is_active is true
            group by coalesce(category, 'Unknown')
            order by inventory_cost desc
            """
        ),
        "appointment_duration_dist": fetch_all(
            """
            select
                case
                    when extract(hour from (appointment_end_time - appointment_time)) < 1 then '< 1 hour'
                    when extract(hour from (appointment_end_time - appointment_time)) < 2 then '1-2 hours'
                    when extract(hour from (appointment_end_time - appointment_time)) < 3 then '2-3 hours'
                    else '3+ hours'
                end as label,
                count(*) as appointments
            from appointments
            where appointment_time is not null and appointment_end_time is not null
            group by label
            order by count(*) desc
            """
        ),
        "client_frequency_segments": fetch_all(
            """
            select
                case
                    when visit_count = 1 then 'First time'
                    when visit_count <= 3 then '2-3 visits'
                    when visit_count <= 6 then '4-6 visits'
                    else '7+ visits'
                end as label,
                count(*) as clients,
                avg(visit_count)::float as avg_visits
            from (
                select client_id, count(*) as visit_count
                from appointments
                group by client_id
            ) client_stats
            group by label
            order by count(*) desc
            """
        ),
        "cancellation_rate_by_staff": fetch_all(
            """
            select
                staff as label,
                count(*) as cancellations,
                round((count(*)::float / (
                    select count(*) from appointments where staff = cancellations.staff
                )) * 100, 2)::float as cancel_rate
            from cancellations
            where staff is not null
            group by staff
            order by cancel_rate desc
            limit 10
            """
        ),
    }


@router.get("/predict/options")
def prediction_options() -> dict[str, list[str]]:
    return {
        "staff": [
            row["value"]
            for row in fetch_all(
                """
                select distinct payload->>'book_staff' as value
                from ml_seed_events
                where payload->>'book_staff' is not null
                order by value
                """
            )
        ],
        "times": [
            row["value"]
            for row in fetch_all(
                """
                select distinct payload->>'book_tod' as value
                from ml_seed_events
                where payload->>'book_tod' is not null
                order by value
                """
            )
        ],
        "categories": [
            row["value"]
            for row in fetch_all(
                """
                select distinct payload->>'book_category' as value
                from ml_seed_events
                where payload->>'book_category' is not null
                order by value
                """
            )
        ],
    }


def segment_rate(column: str, value: str) -> dict:
    return fetch_one_params(
        f"""
        select
            count(*) as rows,
            coalesce(avg((payload->>'noshow')::numeric)::float, 0) as rate
        from ml_seed_events
        where payload->>:column_name = :value
        """.replace("payload->>:column_name", f"payload->>'{column}'"),
        {"value": value},
    )


@router.post("/predict/no-show")
def predict_no_show(payload: NoShowPredictionInput) -> dict:
    base = fetch_one(
        """
        select
            count(*) as rows,
            avg((payload->>'noshow')::numeric)::float as rate
        from ml_seed_events
        """
    )
    base_rate = float(base["rate"] or 0)

    segments = [
        ("Staff", "book_staff", payload.book_staff, 0.32),
        ("Time", "book_tod", payload.book_tod, 0.2),
        ("Service type", "book_category", payload.book_category, 0.24),
    ]

    score = base_rate * 0.24
    drivers = [{"label": "Baseline", "value": "All bookings", "rate": base_rate, "weight": 0.24}]

    for label, column, value, weight in segments:
        rate_row = segment_rate(column, value)
        rate = float(rate_row["rate"] or base_rate)
        rows = int(rate_row["rows"] or 0)
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
