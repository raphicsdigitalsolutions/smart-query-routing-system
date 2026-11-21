"""SQLAlchemy ORM models for the communication hub.

All models share ``app.db.base.Base``. Importing this package registers every
table in the metadata used by Alembic.
"""

from app.db.base import Base
from app.models.agent_run import AgentRun
from app.models.announcement import Announcement
from app.models.audit_log import AuditLog
from app.models.department import Department
from app.models.instructor_leave import InstructorLeave
from app.models.knowledge_document import KnowledgeDocument
from app.models.message import Message
from app.models.message_attachment import MessageAttachment
from app.models.notification import Notification
from app.models.ticket import Ticket
from app.models.ticket_ai_analysis import TicketAiAnalysis
from app.models.ticket_assignment_history import TicketAssignmentHistory
from app.models.ticket_status_history import TicketStatusHistory
from app.models.user import User
from app.models.user_api_key import UserApiKey
from app.models.user_oauth_account import UserOauthAccount

__all__ = [
    "AgentRun",
    "Announcement",
    "AuditLog",
    "Base",
    "Department",
    "InstructorLeave",
    "KnowledgeDocument",
    "Message",
    "MessageAttachment",
    "Notification",
    "Ticket",
    "TicketAiAnalysis",
    "TicketAssignmentHistory",
    "TicketStatusHistory",
    "User",
    "UserApiKey",
    "UserOauthAccount",
]
