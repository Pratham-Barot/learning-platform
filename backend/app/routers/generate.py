from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.dependencies import get_current_user
from app.jobs import get_job, start_generation_job
from app.models import User
from app.schemas import GenerateResponse, JobStatusResponse

from output_languages import SUPPORTED_OUTPUT_LANGUAGE_CODES, normalize_output_language

router = APIRouter(prefix="/api/generate", tags=["generate"])


@router.post("", response_model=GenerateResponse)
async def start_generate(
    source_type: str = Form(...),
    youtube_url: str | None = Form(None),
    web_url: str | None = Form(None),
    output_language: str = Form("en"),
    file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
):
    if source_type not in {"youtube", "document", "web"}:
        raise HTTPException(status_code=400, detail="Invalid source type.")

    if output_language not in SUPPORTED_OUTPUT_LANGUAGE_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported output language. Choose one of: {', '.join(sorted(SUPPORTED_OUTPUT_LANGUAGE_CODES))}.",
        )

    if source_type == "youtube" and not youtube_url:
        raise HTTPException(status_code=400, detail="YouTube URL is required.")
    if source_type == "web" and not web_url:
        raise HTTPException(status_code=400, detail="Web URL is required.")
    if source_type == "document" and not file:
        raise HTTPException(status_code=400, detail="Please upload a PDF or TXT file.")

    file_content = None
    filename = None
    if file is not None:
        file_content = await file.read()
        filename = file.filename

    job_id = start_generation_job(
        user_id=current_user.id,
        source_type=source_type,
        youtube_url=youtube_url,
        web_url=web_url,
        filename=filename,
        file_content=file_content,
        output_language=normalize_output_language(output_language),
    )
    return GenerateResponse(job_id=job_id)


@router.get("/{job_id}/status", response_model=JobStatusResponse)
def generate_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    job = get_job(job_id, user_id=current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobStatusResponse(**job)
