from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from app.api.dependencies import require_admin
from app.db import DbSession
from app.errors import AppError, error_docs
from app.models import User
from app.schemas.imports import ImportReport
from app.services.imports import MAX_FILE_BYTES, import_tracks
from app.services.notifications import notify_subscribers

router = APIRouter(tags=["catalog"])
MAX_ENVELOPE_BYTES = MAX_FILE_BYTES + 16 * 1024
UPLOAD_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["file"],
                    "properties": {"file": {"type": "string", "format": "binary"}},
                }
            }
        },
    }
}


def authorize_upload(_admin: Annotated[User, Depends(require_admin)], session: DbSession) -> None:
    session.commit()


async def csv_content(request: Request) -> bytes:
    if (
        request.headers.get("content-type", "").split(";")[0].strip().lower()
        != "multipart/form-data"
    ):
        raise AppError(415, "unsupported_media_type", "Use multipart/form-data")

    async def bounded_stream():
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_ENVELOPE_BYTES:
                raise AppError(413, "upload_too_large", "Multipart request exceeds 144 KiB")
            yield chunk

    parser = MultiPartParser(request.headers, bounded_stream(), max_files=1, max_fields=0)
    try:
        form = await parser.parse()
    except MultiPartException:
        raise AppError(422, "invalid_upload", "Expected a single multipart file") from None
    try:
        upload = form.get("file")
        if not isinstance(upload, UploadFile) or not (upload.filename or "").lower().endswith(
            ".csv"
        ):
            raise AppError(422, "invalid_upload", "Expected a .csv file in the file field")
        content = await upload.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            raise AppError(413, "file_too_large", "CSV exceeds 128 KiB")
        return content
    finally:
        await form.close()


@router.post(
    "/tracks/import",
    dependencies=[Depends(authorize_upload)],
    openapi_extra=UPLOAD_BODY,
    responses=error_docs(401, 403, 413, 415, 422),
)
def import_csv(
    content: Annotated[bytes, Depends(csv_content)],
    session: DbSession,
    background: BackgroundTasks,
    request: Request,
) -> ImportReport:
    report, created_ids = import_tracks(session, content)
    if created_ids:
        background.add_task(notify_subscribers, request.app.state.engine, created_ids)
    return report
