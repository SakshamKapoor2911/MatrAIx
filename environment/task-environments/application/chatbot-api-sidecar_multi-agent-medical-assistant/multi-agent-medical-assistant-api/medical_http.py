"""HTTP-backed medical assistant adapter for the Harbor chatbot API."""

from __future__ import annotations

import datetime as _dt
import json
import mimetypes
import os
import threading
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from fastapi import HTTPException

MEDICAL_APPLICATION_ID = "medical_assistant"
MEDICAL_CONTEXT = "medical_consultation"


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(prefix: str) -> str:
    return "{}_{}".format(prefix, uuid.uuid4().hex[:12])


@dataclass(frozen=True)
class MedicalAssistantConfig:
    base_url: str = "http://127.0.0.1:8000"
    timeout_seconds: float = 180.0

    @classmethod
    def from_env(
        cls, environ: Optional[Mapping[str, str]] = None
    ) -> "MedicalAssistantConfig":
        env = os.environ if environ is None else environ
        return cls(
            base_url=env.get("MEDICAL_ASSISTANT_URL", "http://127.0.0.1:8000").rstrip(
                "/"
            ),
            timeout_seconds=float(env.get("MEDICAL_ASSISTANT_TIMEOUT_SECONDS", "180")),
        )

    def to_public_metadata(self) -> Dict[str, Any]:
        return {
            "applicationId": MEDICAL_APPLICATION_ID,
            "product": "Multi-Agent Medical Assistant",
            "agent": "HTTP-backed FastAPI medical chatbot",
            "upstream": self.base_url,
            "safety": {
                "mode": "medical information and triage support",
                "requiresClinicianValidation": True,
            },
        }


@dataclass
class MedicalSession:
    id: str
    title: str = "New medical chat"
    messages: List[Dict[str, str]] = field(default_factory=list)
    turns: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now)
    cookie: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "config": {
                "applicationId": MEDICAL_APPLICATION_ID,
                "applicationContext": MEDICAL_CONTEXT,
            },
            "messages": [dict(message) for message in self.messages],
            "turns": [dict(turn) for turn in self.turns],
            "createdAt": self.created_at,
        }


class MedicalHttpClient:
    def __init__(self, config: MedicalAssistantConfig) -> None:
        self.config = config

    def health(self) -> Dict[str, Any]:
        payload, _cookie = self._request_json(method="GET", path="/health")
        return payload

    def chat(
        self, *, message: str, history: List[Dict[str, str]], cookie: Optional[str]
    ) -> tuple[Dict[str, Any], Optional[str]]:
        return self._request_json(
            method="POST",
            path="/chat",
            body={
                "query": message,
                "conversation_history": [dict(item) for item in history],
            },
            cookie=cookie,
        )

    def upload(
        self,
        *,
        image_path: str,
        text: str = "",
        cookie: Optional[str] = None,
    ) -> tuple[Dict[str, Any], Optional[str]]:
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError("image not found: {}".format(image_path))
        return self._request_multipart(
            path="/upload",
            fields={"text": text or ""},
            files={"image": path},
            cookie=cookie,
        )

    def validate(
        self,
        *,
        validation_result: str,
        comments: str = "",
        cookie: Optional[str] = None,
    ) -> tuple[Dict[str, Any], Optional[str]]:
        fields = {"validation_result": validation_result}
        if comments:
            fields["comments"] = comments
        return self._request_multipart(path="/validate", fields=fields, files={}, cookie=cookie)

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        body: Optional[Mapping[str, Any]] = None,
        cookie: Optional[str] = None,
    ) -> tuple[Dict[str, Any], Optional[str]]:
        url = "{}{}".format(self.config.base_url, path)
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(dict(body)).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if cookie:
            headers["Cookie"] = cookie
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(
                request, timeout=self.config.timeout_seconds
            ) as response:
                raw = response.read().decode("utf-8")
                set_cookie = response.headers.get("Set-Cookie")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise HTTPException(status_code=exc.code, detail=detail) from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise RuntimeError(
                "medical assistant upstream unavailable: {}".format(exc)
            ) from exc
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise RuntimeError("medical assistant returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("medical assistant returned non-object JSON")
        cookie_value = set_cookie.split(";", 1)[0] if set_cookie else None
        return payload, cookie_value

    def _request_multipart(
        self,
        *,
        path: str,
        fields: Mapping[str, str],
        files: Mapping[str, Path],
        cookie: Optional[str] = None,
    ) -> tuple[Dict[str, Any], Optional[str]]:
        boundary = "----MatrAIxBoundary{}".format(uuid.uuid4().hex)
        body = bytearray()
        for key, value in fields.items():
            body.extend("--{}\r\n".format(boundary).encode("utf-8"))
            body.extend(
                'Content-Disposition: form-data; name="{}"\r\n\r\n'.format(key).encode(
                    "utf-8"
                )
            )
            body.extend(str(value).encode("utf-8"))
            body.extend(b"\r\n")
        for key, file_path in files.items():
            filename = file_path.name
            content_type = (
                mimetypes.guess_type(filename)[0] or "application/octet-stream"
            )
            body.extend("--{}\r\n".format(boundary).encode("utf-8"))
            body.extend(
                (
                    'Content-Disposition: form-data; name="{}"; filename="{}"\r\n'
                    "Content-Type: {}\r\n\r\n"
                )
                .format(key, filename, content_type)
                .encode("utf-8")
            )
            body.extend(file_path.read_bytes())
            body.extend(b"\r\n")
        body.extend("--{}--\r\n".format(boundary).encode("utf-8"))
        url = "{}{}".format(self.config.base_url, path)
        headers = {
            "Accept": "application/json",
            "Content-Type": "multipart/form-data; boundary={}".format(boundary),
        }
        if cookie:
            headers["Cookie"] = cookie
        request = urllib.request.Request(
            url, data=bytes(body), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.config.timeout_seconds
            ) as response:
                raw = response.read().decode("utf-8")
                set_cookie = response.headers.get("Set-Cookie")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise HTTPException(status_code=exc.code, detail=detail) from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise RuntimeError(
                "medical assistant upstream unavailable: {}".format(exc)
            ) from exc
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise RuntimeError("medical assistant returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("medical assistant returned non-object JSON")
        cookie_value = set_cookie.split(";", 1)[0] if set_cookie else None
        return payload, cookie_value


class MedicalAssistantService:
    def __init__(
        self,
        *,
        client: Optional[MedicalHttpClient] = None,
        config: Optional[MedicalAssistantConfig] = None,
    ) -> None:
        self.config = config or MedicalAssistantConfig.from_env()
        self.client = client or MedicalHttpClient(self.config)
        self._sessions: Dict[str, MedicalSession] = {}
        self._guard = threading.RLock()

    def ready(self) -> None:
        payload = self.client.health()
        status = str(payload.get("status", "ok")).lower()
        if status not in {"ok", "healthy", "ready"}:
            raise RuntimeError(
                "medical assistant health check returned status={!r}".format(status)
            )

    def create_session(self, title: Optional[str] = None) -> MedicalSession:
        session = MedicalSession(
            id=_new_id("med_ses"),
            title=(title or "").strip() or "New medical chat",
        )
        with self._guard:
            self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Optional[MedicalSession]:
        with self._guard:
            return self._sessions.get(session_id)

    def chat(self, *, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        if session_id:
            session = self.get_session(session_id)
            if session is None:
                raise KeyError("unknown session: {}".format(session_id))
        else:
            session = self.create_session()
        return self.run_turn(session.id, message)

    def upload_image(
        self, *, image_path: str, text: str = "", session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if session_id:
            session = self.get_session(session_id)
            if session is None:
                raise KeyError("unknown session: {}".format(session_id))
        else:
            session = self.create_session()
        user_text = (text or "").strip() or "[Uploaded image: {}]".format(image_path)
        with self._guard:
            cookie = session.cookie
        payload, next_cookie = self.client.upload(
            image_path=image_path, text=text or "", cookie=cookie
        )
        assistant_message = str(payload.get("response") or payload.get("reply") or "")
        agent = str(payload.get("agent") or "Medical Assistant")
        turn = self._build_turn(session, user_text, assistant_message, agent, payload)
        with self._guard:
            if next_cookie:
                session.cookie = next_cookie
            session.messages.append({"role": "user", "content": user_text})
            session.messages.append({"role": "assistant", "content": assistant_message})
            session.turns.append(turn)
        return dict(turn)

    def validate_output(
        self,
        *,
        validation_result: str,
        comments: str = "",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if session_id:
            session = self.get_session(session_id)
            if session is None:
                raise KeyError("unknown session: {}".format(session_id))
        else:
            session = self.create_session()
        user_text = "[Validation: {}{}]".format(
            validation_result,
            " — {}".format(comments) if comments else "",
        )
        with self._guard:
            cookie = session.cookie
        payload, next_cookie = self.client.validate(
            validation_result=validation_result,
            comments=comments,
            cookie=cookie,
        )
        assistant_message = str(
            payload.get("response") or payload.get("message") or payload.get("reply") or ""
        )
        agent = str(payload.get("agent") or "Medical Assistant")
        turn = self._build_turn(session, user_text, assistant_message, agent, payload)
        with self._guard:
            if next_cookie:
                session.cookie = next_cookie
            session.messages.append({"role": "user", "content": user_text})
            session.messages.append({"role": "assistant", "content": assistant_message})
            session.turns.append(turn)
        return dict(turn)

    def run_turn(self, session_id: str, message: str) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if session is None:
            raise KeyError("unknown session: {}".format(session_id))
        user_text = (message or "").strip()
        if not user_text:
            raise ValueError("message must not be empty")

        with self._guard:
            history = [dict(existing) for existing in session.messages]
            cookie = session.cookie
        payload, next_cookie = self.client.chat(
            message=user_text, history=history, cookie=cookie
        )
        assistant_message = str(payload.get("response") or payload.get("reply") or "")
        agent = str(payload.get("agent") or "Medical Assistant")
        turn = self._build_turn(session, user_text, assistant_message, agent, payload)

        with self._guard:
            if next_cookie:
                session.cookie = next_cookie
            session.messages.append({"role": "user", "content": user_text})
            session.messages.append({"role": "assistant", "content": assistant_message})
            session.turns.append(turn)
        return dict(turn)

    def _build_turn(
        self,
        session: MedicalSession,
        user_message: str,
        assistant_message: str,
        agent: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "turnId": _new_id("med_turn"),
            "conversationId": session.id,
            "backend": MEDICAL_APPLICATION_ID,
            "userMessage": user_message,
            "assistantMessage": assistant_message,
            "agent": agent,
            "rawToolOutputs": payload,
            "metadata": self.config.to_public_metadata(),
            "createdAt": _utc_now(),
        }


class MedicalAssistantApplication:
    application_id = MEDICAL_APPLICATION_ID
    default_context = MEDICAL_CONTEXT
    contexts = (MEDICAL_CONTEXT,)

    def __init__(self, service: Optional[MedicalAssistantService] = None) -> None:
        self.service = service or MedicalAssistantService()

    def ready(self, context: str) -> None:
        if context != self.default_context:
            raise HTTPException(status_code=422, detail="unknown applicationContext")
        self.service.ready()

    def create_session(
        self,
        *,
        title: Optional[str],
        context: str,
        engine: Optional[str],
        bot_type: Optional[str],
    ) -> Dict[str, Any]:
        del engine, bot_type
        if context != self.default_context:
            raise HTTPException(status_code=422, detail="unknown applicationContext")
        session = self.service.create_session(title=title)
        payload = session.to_dict()
        return {
            "sessionId": session.id,
            "applicationId": self.application_id,
            "applicationContext": context,
            "config": dict(payload["config"]),
            "session": payload,
        }

    def send_message(
        self,
        *,
        session_id: Optional[str],
        message: str,
        title: Optional[str],
        context: str,
        engine: Optional[str],
        bot_type: Optional[str],
    ) -> Dict[str, Any]:
        del title, engine, bot_type
        if context != self.default_context:
            raise HTTPException(status_code=422, detail="unknown applicationContext")
        try:
            turn = self.service.chat(message=message, session_id=session_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="session not found")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        session = self.service.get_session(str(turn["conversationId"]))
        messages = [dict(item) for item in session.messages] if session else []
        return {
            "sessionId": turn["conversationId"],
            "applicationId": self.application_id,
            "applicationContext": self.default_context,
            "reply": turn.get("assistantMessage") or "",
            "turn": turn,
            "messages": messages,
        }

    def upload_image(
        self,
        *,
        session_id: Optional[str],
        image_path: str,
        text: str,
        context: str,
    ) -> Dict[str, Any]:
        if context != self.default_context:
            raise HTTPException(status_code=422, detail="unknown applicationContext")
        try:
            turn = self.service.upload_image(
                image_path=image_path, text=text, session_id=session_id
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="session not found")
        except FileNotFoundError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        session = self.service.get_session(str(turn["conversationId"]))
        messages = [dict(item) for item in session.messages] if session else []
        return {
            "sessionId": turn["conversationId"],
            "applicationId": self.application_id,
            "applicationContext": self.default_context,
            "reply": turn.get("assistantMessage") or "",
            "turn": turn,
            "messages": messages,
        }

    def validate_output(
        self,
        *,
        session_id: Optional[str],
        validation_result: str,
        comments: str,
        context: str,
    ) -> Dict[str, Any]:
        if context != self.default_context:
            raise HTTPException(status_code=422, detail="unknown applicationContext")
        try:
            turn = self.service.validate_output(
                validation_result=validation_result,
                comments=comments,
                session_id=session_id,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="session not found")
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        session = self.service.get_session(str(turn["conversationId"]))
        messages = [dict(item) for item in session.messages] if session else []
        return {
            "sessionId": turn["conversationId"],
            "applicationId": self.application_id,
            "applicationContext": self.default_context,
            "reply": turn.get("assistantMessage") or "",
            "turn": turn,
            "messages": messages,
        }

    def conversation(self, *, session_id: str) -> Dict[str, Any]:
        session = self.service.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        payload = session.to_dict()
        return {
            "sessionId": session.id,
            "applicationId": self.application_id,
            "applicationContext": self.default_context,
            "domain": self.default_context,
            "messages": payload["messages"],
            "turns": payload["turns"],
        }
