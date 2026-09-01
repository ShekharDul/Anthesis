"""Local-first FastAPI delivery surface for Anthesis."""

from __future__ import annotations

import asyncio
import base64
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Literal, cast

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from anthesis import __version__
from anthesis.audio.errors import (
    AudioDecodeError,
    AudioLimitError,
    AudioNotFoundError,
    AudioProcessingError,
    AudioTooShortError,
    SilentAudioError,
)
from anthesis.processing import (
    AnalysisDocument,
    GenerationManifest,
    ProcessingConfig,
    analyze_file,
    generate_file,
)
from anthesis.rendering import RenderConfig

API_VERSION = "v1"
MAX_WEB_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_CONCURRENT_JOBS = 2
PROCESSING_SLOT_TIMEOUT_SECONDS = 0.15
_CHUNK_SIZE = 1024 * 1024
_SAFE_SUFFIX = re.compile(r"^\.[a-zA-Z0-9]{1,8}$")


class ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class HealthResponse(ApiModel):
    status: Literal["ok"] = "ok"
    version: str
    api_version: str


class EncodedImage(ApiModel):
    media_type: Literal["image/png"] = "image/png"
    base64: str


class GenerateResponse(ApiModel):
    manifest: GenerationManifest
    image: EncodedImage


class ErrorResponse(ApiModel):
    code: str
    message: str


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply conservative browser and cache policy to every local response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response


def _public_audio_message(error: AudioProcessingError) -> str:
    if isinstance(error, AudioDecodeError):
        return "The uploaded file could not be decoded as supported audio."
    if isinstance(error, AudioLimitError):
        return "The uploaded audio exceeds a processing limit."
    if isinstance(error, AudioTooShortError):
        return "The uploaded audio is too short after removing silence."
    if isinstance(error, SilentAudioError):
        return "The uploaded audio contains no usable signal."
    if isinstance(error, AudioNotFoundError):
        return "The staged upload is unavailable."
    return "The uploaded audio could not be processed."


@asynccontextmanager
async def _staged_upload(upload: UploadFile) -> AsyncIterator[Path]:
    suffix = Path(upload.filename or "upload").suffix
    suffix = suffix if _SAFE_SUFFIX.fullmatch(suffix) else ".audio"
    with TemporaryDirectory(prefix="anthesis-upload-") as directory:
        path = Path(directory) / f"input{suffix.lower()}"
        total = 0
        try:
            with path.open("wb") as destination:
                while chunk := await upload.read(_CHUNK_SIZE):
                    total += len(chunk)
                    if total > MAX_WEB_UPLOAD_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail={
                                "code": "upload_too_large",
                                "message": "Audio upload exceeds the 100 MiB web limit.",
                            },
                        )
                    destination.write(chunk)
            if total == 0:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "empty_upload", "message": "The uploaded file is empty."},
                )
            yield path
        finally:
            await upload.close()


@asynccontextmanager
async def _processing_slot(request: Request) -> AsyncIterator[None]:
    semaphore = cast(asyncio.Semaphore, request.app.state.processing_semaphore)
    try:
        await asyncio.wait_for(semaphore.acquire(), timeout=PROCESSING_SLOT_TIMEOUT_SECONDS)
    except TimeoutError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "processor_busy",
                "message": "Anthesis is already processing its maximum number of songs.",
            },
            headers={"Retry-After": "2"},
        ) from error
    try:
        yield
    finally:
        semaphore.release()


def create_app() -> FastAPI:
    """Create an isolated application for production and tests."""

    application = FastAPI(
        title="Anthesis API",
        version=__version__,
        description="Deterministic music-to-flower analysis and rendering.",
    )
    application.state.processing_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @application.exception_handler(AudioProcessingError)
    async def audio_error_handler(_request: Request, error: AudioProcessingError) -> JSONResponse:
        response = ErrorResponse(code=type(error).__name__, message=_public_audio_message(error))
        return JSONResponse(status_code=422, content=response.model_dump(mode="json"))

    @application.get(f"/api/{API_VERSION}/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(version=__version__, api_version=API_VERSION)

    @application.post(f"/api/{API_VERSION}/analyze", response_model=AnalysisDocument)
    async def analyze(
        request: Request,
        audio: Annotated[UploadFile, File(description="Music audio file")],
    ) -> AnalysisDocument:
        async with _processing_slot(request), _staged_upload(audio) as path:
            return await run_in_threadpool(analyze_file, path)

    @application.post(f"/api/{API_VERSION}/generate", response_model=GenerateResponse)
    async def generate(
        request: Request,
        audio: Annotated[UploadFile, File(description="Music audio file")],
        width: Annotated[int, Query(ge=256, le=2_048)] = 900,
        height: Annotated[int, Query(ge=256, le=2_048)] = 1_200,
        supersampling: Annotated[int, Query(ge=1, le=2)] = 2,
    ) -> GenerateResponse:
        render = RenderConfig(width=width, height=height, supersampling=supersampling)
        config = ProcessingConfig(render=render)
        async with _processing_slot(request), _staged_upload(audio) as path:
            generated = await run_in_threadpool(generate_file, path, config)
        return GenerateResponse(
            manifest=generated.manifest,
            image=EncodedImage(base64=base64.b64encode(generated.png).decode("ascii")),
        )

    return application


app = create_app()
