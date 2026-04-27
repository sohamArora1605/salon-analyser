from __future__ import annotations

import datetime
import pandas as pd

from app.core.config import settings
from app.data.manifest import DATASETS
from app.db.mongo import get_db


def parse_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.date


def parse_time(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%I:%M:%S %p", errors="coerce").dt.time


def clean_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def clean_optional_number(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series([pd.NA] * len(frame), dtype="Float64")
    return clean_number(frame[column])


def clean_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def clean_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().map({"true": True, "false": False})


def ingest_source_metadata(connection, file_name: str, domain: str, table: str, description: str, row_count: int) -> None:
    db = connection
    db.source_datasets.replace_one(
        {"file_name": file_name},
        {
            "file_name": file_name,
            "domain": domain,
            "target_table": table,
            "description": description,
            "row_count": row_count,
            "loaded_at": pd.Timestamp.now().to_pydatetime(),
        },
        upsert=True,
    )


def ingest_frame(connection, table_name: str, frame: pd.DataFrame) -> None:
    db = connection
    def _serialize(v):
        try:
            if pd.isna(v):
                return None
        except Exception:
            pass
        if isinstance(v, pd.Timestamp):
            return v.to_pydatetime()
        if isinstance(v, datetime.datetime):
            return v
        if isinstance(v, (datetime.date, datetime.time)):
            # convert date/time to ISO string
            return v.isoformat()
        return v

    records = (
        frame.astype(object)
        .where(pd.notna(frame), None)
        .applymap(_serialize)
        .to_dict(orient="records")
    )
    if records:
        db[table_name].insert_many(records)


def reset_target_tables(connection) -> None:
    db = connection
    for name in [
        "source_datasets",
        "appointments",
        "cancellations",
        "no_shows",
        "products",
        "services",
        "receipt_transactions",
        "ml_seed_events",
    ]:
        if name in db.list_collection_names():
            db[name].delete_many({})


def main() -> None:
    raw_dir = settings.resolve_path(settings.data_raw_dir)
    db = get_db()
    reset_target_tables(db)
    for dataset in DATASETS:
        path = raw_dir / dataset.file_name
        if not path.exists():
            print(f"Skipping missing file: {path}")
            continue

        frame = pd.read_csv(path)
        ingest_source_metadata(
            db,
            dataset.file_name,
            dataset.domain,
            dataset.target_table,
            dataset.description,
            len(frame),
        )

        if dataset.file_name == "Future Bookings (All Clients)0.csv":
            out = pd.DataFrame(
                {
                    "source_file": dataset.file_name,
                    "client_code": frame["Code"],
                    "staff": frame["Staff"],
                    "service_code": frame["Service"],
                    "appointment_date": parse_date(frame["Date"]),
                    "appointment_time": parse_time(frame["Time"]),
                    "time_int": clean_int(frame["TimeInt"]),
                }
            )
            ingest_frame(db, "appointments", out)

        elif dataset.file_name in {"Client Cancellations0.csv", "salon_noshow_data.csv"}:
            client_column = "Client code" if "Client code" in frame.columns else "Code"
            out = pd.DataFrame(
                {
                    "source_file": dataset.file_name,
                    "cancel_date": parse_date(frame["Cancel Date"]),
                    "client_code": frame.get(client_column),
                    "service_code": frame["Service"],
                    "service_price": clean_optional_number(frame, "Service Price"),
                    "staff": frame["Staff"],
                    "booking_date": parse_date(frame["Booking Date"]),
                    "canceled_by": frame.get("Canceled By"),
                    "cancel_description": frame.get("Cancel Description"),
                    "days_before": clean_int(frame["Days"]),
                }
            )
            ingest_frame(db, "cancellations", out)

        elif dataset.file_name == "No-Show Report0.csv":
            out = pd.DataFrame(
                {
                    "source_file": dataset.file_name,
                    "event_date": parse_date(frame["Date"]),
                    "client_code": frame["Code"],
                    "service_code": frame["Service"],
                    "staff": frame["Staff"],
                }
            )
            ingest_frame(db, "no_shows", out)

        elif dataset.file_name == "Product Listing (Retail)0.csv":
            out = pd.DataFrame(
                {
                    "source_file": dataset.file_name,
                    "is_active": clean_bool(frame["IsActive"]),
                    "product_code": frame["Code"],
                    "description": frame["Description"],
                    "supplier": frame["Supplier"],
                    "brand": frame["Brand"],
                    "category": frame["Category"],
                    "price": clean_number(frame["Price"]),
                    "on_hand": clean_number(frame["On Hand"]),
                    "minimum_stock": clean_number(frame["Minimum"]),
                    "maximum_stock": clean_number(frame["Maximum"]),
                    "cost": clean_number(frame["Cost"]),
                    "cogs": clean_number(frame["COG"]),
                    "ytd": clean_number(frame["YTD"]),
                    "is_package": clean_bool(frame["Package"]),
                }
            )
            ingest_frame(db, "products", out)

        elif dataset.file_name == "Service Listing0.csv":
            out = pd.DataFrame(
                {
                    "source_file": dataset.file_name,
                    "is_active": clean_bool(frame["IsActive"]),
                    "service_code": frame["Code"],
                    "description": frame["Desc"],
                    "category": frame["Cate"],
                    "price": clean_number(frame["Price"]),
                    "cost": clean_number(frame["Cost"]),
                }
            )
            ingest_frame(db, "services", out)

        elif dataset.file_name == "Receipt Transactions0.csv":
            out = pd.DataFrame(
                {
                    "source_file": dataset.file_name,
                    "receipt_number": frame["Receipt"].astype(str),
                    "transaction_date": parse_date(frame["Date"]),
                    "description": frame["Description"],
                    "client_code": frame["Client"],
                    "staff": frame["Staff"],
                    "quantity": clean_number(frame["Quantity"]),
                    "amount": clean_number(frame["Amount"]),
                    "gst": clean_number(frame["GST"]),
                    "pst": clean_number(frame["PST"]),
                }
            )
            ingest_frame(db, "receipt_transactions", out)

        else:
            payload_frame = frame.astype(object).where(pd.notna(frame), None)
            out = pd.DataFrame(
                {
                    "source_file": dataset.file_name,
                    "payload": payload_frame.to_dict(orient="records"),
                }
            )
            ingest_frame(db, "ml_seed_events", out)

        print(f"Ingested {dataset.file_name} -> {dataset.target_table}")


if __name__ == "__main__":
    main()
