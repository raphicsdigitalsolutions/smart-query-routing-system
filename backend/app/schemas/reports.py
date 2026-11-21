"""Metadata and filter contracts shared by PDF/XLSX ticket exports."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class TicketChannel(str, Enum):
    WEB = "web"
    EMAIL = "email"
    WHATSAPP = "whatsapp"


class ReportMeta(BaseModel):
    """Header information rendered into both export formats."""

    generated_at: datetime
    scope: str
    ticket_count: int
