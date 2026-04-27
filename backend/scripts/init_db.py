from app.db.mongo import get_db


def main() -> None:
    db = get_db()
    # Ensure collections exist by creating them and adding basic indexes where useful
    collections = [
        "source_datasets",
        "appointments",
        "cancellations",
        "no_shows",
        "products",
        "services",
        "receipt_transactions",
        "ml_seed_events",
    ]
    for name in collections:
        if name not in db.list_collection_names():
            db.create_collection(name)

    # Example index: ensure unique source file tracking
    try:
        db.source_datasets.create_index("file_name", unique=True)
    except Exception:
        pass

    print("Initialized MongoDB collections.")


if __name__ == "__main__":
    main()
