from __future__ import annotations

from pprint import pprint

from app.db.mongo import get_db


def main():
    db = get_db()
    cols = db.list_collection_names()
    print(f"Found {len(cols)} collections:\n")
    for c in cols:
        count = db[c].count_documents({})
        print(f"Collection: {c} — count: {count}")
        sample = db[c].find_one()
        print("Sample doc:")
        pprint(sample)
        print("---\n")


if __name__ == '__main__':
    main()
