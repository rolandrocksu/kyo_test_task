import enum
from sqlalchemy import Column, Integer, String, Date, Enum as SQLEnum
from .base import Base

class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_email = Column(String, nullable=False, index=True)
    department = Column(String, nullable=True, index=True)
    leave_type = Column(String, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(SQLEnum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False)
    manager_email = Column(String, nullable=True)
    approved_by = Column(String, nullable=True)
    conversation_id = Column(String, nullable=True, index=True)
    raw_subject = Column(String, nullable=True)
    raw_body = Column(String, nullable=True)
    mailhog_id = Column(String, unique=True, nullable=True)
