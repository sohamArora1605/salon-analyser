from fastapi import APIRouter

from app.core.config import settings
from app.data.manifest import DATASETS
from app.data.profiler import profile_all

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("")
def list_datasets() -> list[dict[str, str]]:
    return [dataset.__dict__ for dataset in DATASETS]


@router.get("/profile")
def dataset_profile() -> list[dict]:
    raw_dir = settings.resolve_path(settings.data_raw_dir)
    return profile_all(raw_dir)

