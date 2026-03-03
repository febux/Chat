"""
RBAC (Role-Based Access Control) module for managing permissions and roles in an application.

This module provides classes and functions for managing permissions and roles in an application.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, TIMESTAMP, UUID, Boolean, Column, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base, BaseProps

# Ассоциации
admin_roles = Table(
    "admin_roles",
    Base.metadata,
    Column("admin_id", UUID, ForeignKey("admins.id", ondelete="CASCADE")),
    Column("role_id", UUID, ForeignKey("roles.id", ondelete="CASCADE")),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID, ForeignKey("roles.id", ondelete="CASCADE")),
    Column("permission_id", UUID, ForeignKey("permissions.id", ondelete="CASCADE")),
)

admin_permissions = Table(
    "admin_permissions",
    Base.metadata,
    Column("admin_id", UUID, ForeignKey("admins.id", ondelete="CASCADE")),
    Column("permission_id", UUID, ForeignKey("permissions.id", ondelete="CASCADE")),
)


class Admin(BaseProps):
    """
    Admins in the application.

    Attributes:
        username: Unique username for the admin.
        email: Unique email address for the admin.
        password_hash: Hashed password for the admin.
        is_superadmin: Indicates whether the admin is a superadmin.
        is_active: Indicates whether the admin is active.
        roles: List of roles assigned to the admin.
        direct_permissions: List of permissions directly assigned to the admin.
        audit_logs: List of audit logs associated with the admin.
    """

    __tablename__ = "admins"

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    roles: Mapped[list["Role"]] = relationship(secondary=admin_roles, back_populates="admins")
    direct_permissions: Mapped[list["Permission"]] = relationship(secondary=admin_permissions, back_populates="admins")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="admin")


class Role(BaseProps):
    """
    Roles in the application.

    Attributes:
        name: Unique name for the role.
        description: Optional description for the role.
        admins: List of admins assigned to the role.
        permissions: List of permissions assigned to the role.
    """

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    admins: Mapped[list["Admin"]] = relationship(secondary=admin_roles, back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(secondary=role_permissions, back_populates="roles")


class Permission(BaseProps):
    """
    Permissions in the application.

    Attributes:
        name: Unique name for the permission.
        resource: Resource associated with the permission.
        action: Action associated with the permission.
        conditions: Optional conditions for the permission.
        description: Optional description for the permission.
        roles: List of roles assigned to the permission.
        admins: List of admins directly assigned to the permission.
    """

    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    resource: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(50))
    conditions: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    roles: Mapped[list["Role"]] = relationship(secondary=role_permissions, back_populates="permissions")
    admins: Mapped[list["Admin"]] = relationship(secondary=admin_permissions, back_populates="direct_permissions")


class AuditLog(BaseProps):
    """
    Audit logs for admin actions.

    Attributes:
        admin_id: Unique identifier for the admin.
        action: Action performed on the resource.
        resource_type: Type of the resource.
        resource_id: Unique identifier for the resource.
        details: Additional details about the action performed on the resource.
        ip_address: IP address of the admin performing the action.
        timestamp: Timestamp when the audit log was created.
        admin: Admin associated with the audit log.
    """

    __tablename__ = "audit_logs"

    admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(50))
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    admin: Mapped[Optional["Admin"]] = relationship(back_populates="audit_logs")
