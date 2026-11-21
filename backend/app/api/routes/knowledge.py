"""Knowledge-base endpoints: staff+ reads, HOD/admin management."""

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_hod_or_admin, require_staff_or_above
from app.db.dependencies import get_db
from app.models import User
from app.schemas.knowledge import (
    KnowledgeDocumentResponse,
    KnowledgeListResponse,
    KnowledgeUpdate,
    KnowledgeVersionListResponse,
)
from app.services.knowledge import (
    create_knowledge_document,
    deactivate_knowledge_document,
    get_knowledge_document,
    list_knowledge_documents,
    list_knowledge_versions,
    update_knowledge_document,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=KnowledgeListResponse)
def get_knowledge_list(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=120),
    approved_only: bool = False,
    active_only: bool = False,
    department_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_staff_or_above),
) -> KnowledgeListResponse:
    return list_knowledge_documents(
        db,
        user,
        skip=skip,
        limit=limit,
        search=search,
        approved_only=approved_only,
        active_only=active_only,
        department_id=department_id,
    )


@router.post(
    "",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_knowledge_document(
    title: str = Form(min_length=1, max_length=255),
    source_type: str = Form(default="text", max_length=20),
    source_key: str | None = Form(default=None, max_length=255),
    content: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    department_id: int | None = Form(default=None, gt=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_hod_or_admin),
) -> KnowledgeDocumentResponse:
    """Upload text or a txt/md/pdf file as a new, unapproved source version."""
    return create_knowledge_document(
        db,
        user=user,
        title=title,
        source_type=source_type,
        source_key=source_key,
        content=content,
        file=file,
        department_id=department_id,
    )


@router.get("/{document_id}", response_model=KnowledgeDocumentResponse)
def get_knowledge_detail(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff_or_above),
) -> KnowledgeDocumentResponse:
    return get_knowledge_document(db, document_id, user)


@router.get("/{document_id}/versions", response_model=KnowledgeVersionListResponse)
def get_knowledge_versions(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff_or_above),
) -> KnowledgeVersionListResponse:
    return list_knowledge_versions(db, user, document_id=document_id)


@router.patch("/{document_id}", response_model=KnowledgeDocumentResponse)
def patch_knowledge_document(
    document_id: int,
    payload: KnowledgeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_hod_or_admin),
) -> KnowledgeDocumentResponse:
    return update_knowledge_document(db, document_id, payload, user)


@router.delete("/{document_id}", response_model=KnowledgeDocumentResponse)
def delete_knowledge_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_hod_or_admin),
) -> KnowledgeDocumentResponse:
    """Deactivate a document; no knowledge row is ever hard-deleted."""
    return deactivate_knowledge_document(db, document_id, user)
