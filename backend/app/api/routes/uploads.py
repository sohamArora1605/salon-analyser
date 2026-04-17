from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.storage import upload_bytes

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/image")
async def upload_image(file: UploadFile = File(...)) -> dict[str, str | None]:
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    uploaded = upload_bytes(content, file.filename or "image", file.content_type)
    return {
        "bucket": uploaded.bucket,
        "key": uploaded.key,
        "public_url": uploaded.public_url,
    }
