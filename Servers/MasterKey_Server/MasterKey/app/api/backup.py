from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.current_device import get_verified_primary_device
from app.models.device import Device
from app.schemas.backup import BackupUploadResponse
from app.services.backup_service import BackupService

router = APIRouter(prefix="/backup", tags=["backup"])

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {".exe", ".masterkey"}


@router.post("/upload", response_model=BackupUploadResponse)
async def upload_backup(
    file: UploadFile = File(...),
    device: Device = Depends(get_verified_primary_device),
    db: AsyncSession = Depends(get_db),
):
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    backup = await BackupService.save_user_backup(
        db=db,
        device=device,
        user_id=str(device.user_id),
        file=file,
        max_size_bytes=MAX_FILE_SIZE_BYTES,
        file_extension=file_ext,
    )

    return BackupUploadResponse(
        success=True,
        size_bytes=backup.size_bytes,
        updated_at=backup.updated_at,
    )
