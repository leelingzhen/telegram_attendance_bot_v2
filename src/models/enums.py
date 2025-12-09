from enum import Enum


class AccessCategory(str, Enum):
    PUBLIC = "public"
    GUEST = "guest"
    MEMBER = "member"
    ADMIN = "admin"

class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"


class UserRecordStatus(str, Enum):
    NEW = "new"
    UPDATED = "updated"
    EXISTS = "exists"