import json
import os
import sys
from typing import Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from db import DB_FILE, init_db, replace_all


DATA_FILE = os.path.join(BASE_DIR, "data.json")


def main() -> None:
    print("Initializing database at:", DB_FILE)
    init_db()

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
            # Ensure keys
            for k in [
                "users",
                "pets",
                "medical_history",
                "vaccines",
                "weights",
                "appointments",
            ]:
                data.setdefault(k, [])
            replace_all(data)  # Migrate JSON
            print("Migrated existing data.json into the database.")
        except Exception as e:
            print("Warning: could not migrate data.json:", e)
    else:
        # Empty seed
        replace_all(
            {
                "users": [],
                "pets": [],
                "medical_history": [],
                "vaccines": [],
                "weights": [],
                "appointments": [],
            }
        )
        print("Created empty tables.")

    print("Done.")


if __name__ == "__main__":
    main()
