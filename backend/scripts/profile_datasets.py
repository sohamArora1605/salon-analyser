import json

from app.core.config import settings
from app.data.profiler import profile_all


def main() -> None:
    raw_dir = settings.resolve_path(settings.data_raw_dir)
    output_path = settings.resolve_path(settings.data_profile_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    profiles = profile_all(raw_dir)
    output_path.write_text(json.dumps(profiles, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

