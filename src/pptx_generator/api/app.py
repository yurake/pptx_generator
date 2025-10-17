"""FastAPI application for content approval."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status

from ..models import ContentElements, ContentSlide, ContentTableData
from . import schemas
from .store import (CardState, ContentStore, RevisionMismatchError,
                    SlideNotFoundError, SpecAlreadyExistsError, SpecNotFoundError)


def _create_store() -> ContentStore:
    return ContentStore()


def _get_auth_token() -> str | None:
    return os.environ.get("CONTENT_API_TOKEN")


def create_app(store: ContentStore | None = None) -> FastAPI:
    """Create FastAPI application instance."""

    app = FastAPI(title="Content Approval API", version="1.0.0")
    content_store = store or _create_store()
    api_token = _get_auth_token()

    async def verify_token(authorization: Annotated[str | None, Header(alias="Authorization")] = None) -> None:
        if api_token is None:
            return
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
        token = authorization.split(" ", 1)[1]
        if token != api_token:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

    def get_actor(x_actor: Annotated[str | None, Header(alias="X-Actor")] = None) -> str | None:
        return x_actor

    def get_request_id(x_request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None) -> str | None:
        return x_request_id

    def require_etag(if_match: Annotated[str | None, Header(alias="If-Match")] = None) -> str:
        if not if_match:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail="If-Match header is required",
            )
        return if_match

    @app.post(
        "/v1/content/cards",
        status_code=status.HTTP_201_CREATED,
        response_model=schemas.CreateCardsResponse,
        responses={409: {"model": schemas.ErrorResponse}},
        dependencies=[Depends(verify_token)],
    )
    def create_cards(
        payload: schemas.CreateCardsRequest,
        actor: str | None = Depends(get_actor),
        request_id: str | None = Depends(get_request_id),
    ) -> schemas.CreateCardsResponse:
        cards = []
        for card in payload.cards:
            elements = ContentElements(
                title=card.title,
                body=card.body,
                table_data=card.table_data.to_content_table() if card.table_data else None,
                note=card.note,
            )
            slide = ContentSlide(
                id=card.slide_id,
                intent=card.intent,
                type_hint=card.type_hint,
                elements=elements,
                status="draft",
            )
            cards.append(CardState(slide=slide, story=card.story.model_dump() if card.story else None))

        try:
            etag = content_store.create_cards(payload.spec_id, cards)
        except SpecAlreadyExistsError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_error("conflict", str(exc)),
            ) from exc

        response = schemas.CreateCardsResponse(spec_id=payload.spec_id, revision=etag)
        return Response(
            content=response.model_dump_json(),
            media_type="application/json",
            headers={"ETag": etag},
            status_code=status.HTTP_201_CREATED,
        )

    @app.patch(
        "/v1/content/cards/{slide_id}",
        response_model=schemas.CardUpdateResponse,
        responses={
            404: {"model": schemas.ErrorResponse},
            409: {"model": schemas.ErrorResponse},
            412: {"model": schemas.ErrorResponse},
        },
        dependencies=[Depends(verify_token)],
    )
    def update_card(
        slide_id: str,
        payload: schemas.CardUpdate,
        request: Request,
        actor: str | None = Depends(get_actor),
        request_id: str | None = Depends(get_request_id),
        etag: str = Depends(require_etag),
        spec_id: str = Query(..., min_length=1),
    ) -> Response:
        table = payload.table_data.to_content_table() if payload.table_data else None

        try:
            new_etag, content_hash = content_store.update_card(
                spec_id=spec_id,
                slide_id=slide_id,
                title=payload.title,
                body=payload.body,
                table_data=table,
                note=payload.note,
                intent=payload.intent,
                type_hint=payload.type_hint,
                story=payload.story.model_dump() if payload.story else None,
                autofix_applied=payload.autofix_applied,
                expected_etag=etag,
                actor=actor,
            )
        except SpecNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_error("not_found", str(exc))) from exc
        except SlideNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_error("not_found", str(exc))) from exc
        except RevisionMismatchError as exc:
            raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=_error("conflict", str(exc))) from exc

        body = schemas.CardUpdateResponse(revision=new_etag, content_hash=content_hash)
        return Response(
            content=body.model_dump_json(),
            media_type="application/json",
            headers={"ETag": new_etag},
        )

    @app.post(
        "/v1/content/cards/{slide_id}/approve",
        response_model=schemas.CardApproveResponse,
        responses={
            404: {"model": schemas.ErrorResponse},
            412: {"model": schemas.ErrorResponse},
        },
        dependencies=[Depends(verify_token)],
    )
    def approve_card(
        slide_id: str,
        payload: schemas.CardApproveRequest,
        actor: str | None = Depends(get_actor),
        request_id: str | None = Depends(get_request_id),
        etag: str = Depends(require_etag),
        spec_id: str = Query(..., min_length=1),
    ) -> Response:
        try:
            new_etag, status_value, locked_at = content_store.approve_card(
                spec_id=spec_id,
                slide_id=slide_id,
                notes=payload.notes,
                applied_autofix=payload.applied_autofix,
                expected_etag=etag,
                actor=actor,
            )
        except SpecNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_error("not_found", str(exc))) from exc
        except SlideNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_error("not_found", str(exc))) from exc
        except RevisionMismatchError as exc:
            raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=_error("conflict", str(exc))) from exc

        body = schemas.CardApproveResponse(
            revision=new_etag,
            status=status_value,
            locked_at=locked_at,
        )
        return Response(
            content=body.model_dump_json(),
            media_type="application/json",
            headers={"ETag": new_etag},
        )

    @app.post(
        "/v1/content/cards/{slide_id}/return",
        response_model=schemas.CardReturnResponse,
        responses={
            404: {"model": schemas.ErrorResponse},
            412: {"model": schemas.ErrorResponse},
        },
        dependencies=[Depends(verify_token)],
    )
    def return_card(
        slide_id: str,
        payload: schemas.CardReturnRequest,
        actor: str | None = Depends(get_actor),
        request_id: str | None = Depends(get_request_id),
        etag: str = Depends(require_etag),
        spec_id: str = Query(..., min_length=1),
    ) -> Response:
        try:
            new_etag, status_value = content_store.return_card(
                spec_id=spec_id,
                slide_id=slide_id,
                reason=payload.reason,
                requested_by=payload.requested_by,
                expected_etag=etag,
                actor=actor,
            )
        except SpecNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_error("not_found", str(exc))) from exc
        except SlideNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_error("not_found", str(exc))) from exc
        except RevisionMismatchError as exc:
            raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=_error("conflict", str(exc))) from exc

        body = schemas.CardReturnResponse(revision=new_etag, status=status_value)
        return Response(
            content=body.model_dump_json(),
            media_type="application/json",
            headers={"ETag": new_etag},
        )

    @app.get(
        "/v1/content/cards/{slide_id}",
        response_model=schemas.CardResponse,
        responses={404: {"model": schemas.ErrorResponse}},
        dependencies=[Depends(verify_token)],
    )
    def get_card(
        slide_id: str,
        spec_id: str = Query(..., min_length=1),
    ) -> Response:
        try:
            card_state, etag = content_store.get_card(spec_id, slide_id)
        except SpecNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_error("not_found", str(exc))) from exc
        except SlideNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_error("not_found", str(exc))) from exc

        history = _history_for_slide(content_store, spec_id, slide_id)
        body = schemas.CardResponse(
            spec_id=spec_id,
            slide_id=slide_id,
            title=card_state.slide.elements.title,
            body=list(card_state.slide.elements.body),
            table_data=_table_payload(card_state.slide.elements.table_data),
            note=card_state.slide.elements.note,
            intent=card_state.slide.intent,
            type_hint=card_state.slide.type_hint,
            story=_story_payload(card_state.story),
            status=card_state.slide.status,
            revision=etag,
            history=history,
        )
        return Response(
            content=body.model_dump_json(),
            media_type="application/json",
            headers={"ETag": etag},
        )

    @app.get(
        "/v1/content/logs",
        response_model=schemas.LogsResponse,
        dependencies=[Depends(verify_token)],
    )
    def list_logs(
        spec_id: str | None = Query(default=None),
        action: str | None = Query(default=None),
        since: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> schemas.LogsResponse:
        since_dt = datetime.fromisoformat(since) if since else None
        items, next_offset = content_store.list_logs(
            spec_id=spec_id,
            action=action,
            since=since_dt,
            limit=limit,
            offset=offset,
        )
        response_items = [
            schemas.LogEntry(
                spec_id=item["spec_id"],
                slide_id=item["slide_id"],
                action=item["action"],
                actor=item.get("actor"),
                timestamp=datetime.fromisoformat(item["timestamp"]),
                notes=item.get("notes"),
                applied_autofix=item.get("applied_autofix"),
                ai_grade=item.get("ai_grade"),
            )
            for item in items
        ]
        return schemas.LogsResponse(
            items=response_items,
            next_offset=str(next_offset) if next_offset is not None else None,
        )

    return app


# --------------------------------------------------------------------------- #
# ユーティリティ
# --------------------------------------------------------------------------- #
def _table_payload(table: ContentTableData | None) -> schemas.TableDataPayload | None:
    if table is None:
        return None
    return schemas.TableDataPayload(headers=table.headers, rows=table.rows)


def _story_payload(story: dict | None) -> schemas.StoryMetadata | None:
    if story is None:
        return None
    return schemas.StoryMetadata.model_validate(story)


def _history_for_slide(store: ContentStore, spec_id: str, slide_id: str) -> list[schemas.CardHistoryEntry]:
    logs, _ = store.list_logs(spec_id=spec_id, action=None, since=None, limit=10_000, offset=0)
    entries = []
    for entry in logs:
        if entry["slide_id"] != slide_id:
            continue
        entries.append(
            schemas.CardHistoryEntry(
                action=entry["action"],
                actor=entry.get("actor"),
                timestamp=datetime.fromisoformat(entry["timestamp"]),
                notes=entry.get("notes"),
                applied_autofix=entry.get("applied_autofix"),
                ai_grade=entry.get("ai_grade"),
            )
        )
    entries.sort(key=lambda item: item.timestamp)
    return entries


def _error(code: str, message: str) -> dict[str, str]:
    return {"error": code, "message": message}
