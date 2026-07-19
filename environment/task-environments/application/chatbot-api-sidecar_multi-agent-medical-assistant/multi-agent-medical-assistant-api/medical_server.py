"""Harbor chatbot contract wrapper for an HTTP medical assistant service."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from medical_http import (
    MEDICAL_APPLICATION_ID,
    MEDICAL_CONTEXT,
    MedicalAssistantApplication,
)


class SessionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = None
    application_id: str = Field(
        default=MEDICAL_APPLICATION_ID, alias="applicationId"
    )
    application_context: str = Field(default=MEDICAL_CONTEXT, alias="applicationContext")
    engine: Optional[str] = None
    botType: Optional[str] = None

    @field_validator("application_id")
    @classmethod
    def _known_application(cls, value: str) -> str:
        if value != MEDICAL_APPLICATION_ID:
            raise ValueError("applicationId must be {}".format(MEDICAL_APPLICATION_ID))
        return value


class MessageRequest(SessionRequest):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    session_id: Optional[str] = Field(default=None, alias="sessionId")

    @field_validator("message")
    @classmethod
    def _message_not_empty(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("message must not be empty")
        return text


_application = MedicalAssistantApplication()

app = FastAPI(title="MatrAIx Medical Assistant Chatbot API", version="1.0")


def _context(value: Optional[str]) -> str:
    return value or MEDICAL_CONTEXT


@app.get("/health")
@app.get("/v1/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "applications": [
            {
                "applicationId": MEDICAL_APPLICATION_ID,
                "label": "Medical Assistant",
                "defaultContext": MEDICAL_CONTEXT,
                "contexts": [MEDICAL_CONTEXT],
            }
        ],
    }


@app.get("/ready")
@app.get("/v1/ready")
def ready(
    application_id: str = Query(
        default=MEDICAL_APPLICATION_ID, alias="applicationId"
    ),
    application_context: Optional[str] = Query(
        default=MEDICAL_CONTEXT, alias="applicationContext"
    ),
) -> Dict[str, Any]:
    if application_id != MEDICAL_APPLICATION_ID:
        raise HTTPException(
            status_code=422,
            detail="applicationId must be {}".format(MEDICAL_APPLICATION_ID),
        )
    context = _context(application_context)
    _application.ready(context)
    return {
        "status": "ready",
        "applicationId": MEDICAL_APPLICATION_ID,
        "applicationContext": context,
        "domain": context,
    }


@app.post("/v1/session")
def create_session(body: SessionRequest) -> Dict[str, Any]:
    return _application.create_session(
        title=body.title,
        context=_context(body.application_context),
        engine=body.engine,
        bot_type=body.botType,
    )


@app.post("/v1/messages")
def send_message(body: MessageRequest) -> Dict[str, Any]:
    return _application.send_message(
        session_id=body.session_id,
        message=body.message,
        title=body.title,
        context=_context(body.application_context),
        engine=body.engine,
        bot_type=body.botType,
    )


class UploadRequest(SessionRequest):
    model_config = ConfigDict(populate_by_name=True)

    image_path: str = Field(alias="imagePath")
    text: str = ""
    session_id: Optional[str] = Field(default=None, alias="sessionId")


class ValidateRequest(SessionRequest):
    model_config = ConfigDict(populate_by_name=True)

    validation_result: str = Field(alias="validationResult")
    comments: str = ""
    session_id: Optional[str] = Field(default=None, alias="sessionId")


@app.post("/v1/upload")
def upload_image(body: UploadRequest) -> Dict[str, Any]:
    return _application.upload_image(
        session_id=body.session_id,
        image_path=body.image_path,
        text=body.text,
        context=_context(body.application_context),
    )


@app.post("/v1/validate")
def validate_output(body: ValidateRequest) -> Dict[str, Any]:
    return _application.validate_output(
        session_id=body.session_id,
        validation_result=body.validation_result,
        comments=body.comments,
        context=_context(body.application_context),
    )


@app.get("/v1/conversation")
def conversation(
    session_id: str = Query(alias="sessionId"),
    application_id: str = Query(
        default=MEDICAL_APPLICATION_ID, alias="applicationId"
    ),
) -> Dict[str, Any]:
    if application_id != MEDICAL_APPLICATION_ID:
        raise HTTPException(
            status_code=422,
            detail="applicationId must be {}".format(MEDICAL_APPLICATION_ID),
        )
    return _application.conversation(session_id=session_id)
