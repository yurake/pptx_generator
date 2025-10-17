"""FastAPI application for draft structuring operations."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status

from .draft_schemas import (AppendixUpdateRequest, DraftBoardResponse,
                            DraftLogEntriesResponse, LayoutHintUpdateRequest,
                            MoveSlideRequest, RevisionResponse,
                            SectionApproveRequest)
from .draft_store import (BoardNotFoundError, DraftStore, RevisionMismatchError,
                          SectionNotFoundError, SlideNotFoundError)


def _create_store() -> DraftStore:
    return DraftStore()


def _get_auth_token() -> str | None:
    return os.environ.get("DRAFT_API_TOKEN")


def create_draft_app(store: DraftStore | None = None) -> FastAPI:
    """Create FastAPI application instance."""

    app = FastAPI(title="Draft Structuring API", version="1.0.0")
    draft_store = store or _create_store()
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

    def require_etag(if_match: Annotated[str | None, Header(alias="If-Match")] = None) -> str:
        if not if_match:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail="If-Match header is required",
            )
        return if_match

    @app.get(
        "/v1/draft/board",
        response_model=DraftBoardResponse,
        responses={404: {"description": "Board not found"}},
        dependencies=[Depends(verify_token)],
    )
    def get_board(spec_id: str = Query(..., min_length=1)) -> Response:
        try:
            board, etag = draft_store.get_board(spec_id)
        except BoardNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

        body = DraftBoardResponse(spec_id=spec_id, revision=etag, board=board)
        return Response(
            content=body.model_dump_json(),
            media_type="application/json",
            headers={"ETag": etag},
        )

    @app.patch(
        "/v1/draft/slides/{slide_id}/hint",
        response_model=RevisionResponse,
        responses={
            404: {"description": "Board or slide not found"},
            412: {"description": "Revision mismatch"},
        },
        dependencies=[Depends(verify_token)],
    )
    def update_layout_hint(
        slide_id: str,
        payload: LayoutHintUpdateRequest,
        request: Request,
        actor: str | None = Depends(get_actor),
        etag: str = Depends(require_etag),
        spec_id: str = Query(..., min_length=1),
    ) -> Response:
        try:
            new_etag = draft_store.update_layout_hint(
                spec_id=spec_id,
                slide_id=slide_id,
                layout_hint=payload.layout_hint,
                notes=payload.notes,
                expected_etag=etag,
                actor=actor,
            )
        except BoardNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except SlideNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except RevisionMismatchError as exc:
            raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=str(exc)) from exc

        body = RevisionResponse(revision=new_etag)
        return Response(
            content=body.model_dump_json(),
            media_type="application/json",
            headers={"ETag": new_etag},
        )

    @app.post(
        "/v1/draft/slides/{slide_id}/move",
        response_model=RevisionResponse,
        responses={
            404: {"description": "Board, slide, or section not found"},
            412: {"description": "Revision mismatch"},
        },
        dependencies=[Depends(verify_token)],
    )
    def move_slide(
        slide_id: str,
        payload: MoveSlideRequest,
        actor: str | None = Depends(get_actor),
        etag: str = Depends(require_etag),
        spec_id: str = Query(..., min_length=1),
    ) -> Response:
        try:
            new_etag = draft_store.move_slide(
                spec_id=spec_id,
                slide_id=slide_id,
                target_section=payload.target_section,
                position=payload.position,
                expected_etag=etag,
                actor=actor,
            )
        except BoardNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except SlideNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except SectionNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except RevisionMismatchError as exc:
            raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=str(exc)) from exc

        body = RevisionResponse(revision=new_etag)
        return Response(
            content=body.model_dump_json(),
            media_type="application/json",
            headers={"ETag": new_etag},
        )

    @app.post(
        "/v1/draft/sections/{section_name}/approve",
        response_model=RevisionResponse,
        responses={
            404: {"description": "Board or section not found"},
            412: {"description": "Revision mismatch"},
        },
        dependencies=[Depends(verify_token)],
    )
    def approve_section(
        section_name: str,
        payload: SectionApproveRequest,
        actor: str | None = Depends(get_actor),
        etag: str = Depends(require_etag),
        spec_id: str = Query(..., min_length=1),
    ) -> Response:
        try:
            new_etag = draft_store.approve_section(
                spec_id=spec_id,
                section_name=section_name,
                expected_etag=etag,
                actor=actor,
                notes=payload.notes,
            )
        except BoardNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except SectionNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except RevisionMismatchError as exc:
            raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=str(exc)) from exc

        body = RevisionResponse(revision=new_etag)
        return Response(
            content=body.model_dump_json(),
            media_type="application/json",
            headers={"ETag": new_etag},
        )

    @app.post(
        "/v1/draft/slides/{slide_id}/appendix",
        response_model=RevisionResponse,
        responses={
            404: {"description": "Board or slide not found"},
            412: {"description": "Revision mismatch"},
        },
        dependencies=[Depends(verify_token)],
    )
    def update_appendix(
        slide_id: str,
        payload: AppendixUpdateRequest,
        actor: str | None = Depends(get_actor),
        etag: str = Depends(require_etag),
        spec_id: str = Query(..., min_length=1),
    ) -> Response:
        try:
            new_etag = draft_store.set_appendix(
                spec_id=spec_id,
                slide_id=slide_id,
                appendix=payload.appendix,
                expected_etag=etag,
                actor=actor,
                notes=payload.notes,
            )
        except BoardNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except SlideNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except RevisionMismatchError as exc:
            raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=str(exc)) from exc

        body = RevisionResponse(revision=new_etag)
        return Response(
            content=body.model_dump_json(),
            media_type="application/json",
            headers={"ETag": new_etag},
        )

    @app.get(
        "/v1/draft/logs",
        response_model=DraftLogEntriesResponse,
        responses={404: {"description": "Board not found"}},
        dependencies=[Depends(verify_token)],
    )
    def list_logs(
        spec_id: str = Query(..., min_length=1),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> DraftLogEntriesResponse:
        try:
            entries, next_offset = draft_store.list_logs(
                spec_id=spec_id,
                limit=limit,
                offset=offset,
            )
        except BoardNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

        return DraftLogEntriesResponse(items=entries, next_offset=next_offset)

    return app
