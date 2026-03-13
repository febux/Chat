from enum import Enum


class ChannelType(Enum):
    DIRECT = "direct"
    GROUP = "group"


class MemberRole(Enum):
    MEMBER = "member"
    ADMIN = "admin"
