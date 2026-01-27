"""
Erdpuls Collective Threshold Model - Role Definitions and Permissions

This module defines the role hierarchy and permissions for the platform.
"""
from enum import Enum
from typing import List, Set


class UserRole(str, Enum):
    """
    User roles in order of increasing privilege level.
    
    MEMBER: Default role for new registrations
        - Can browse offerings
        - Can register intention to participate
        - Can contribute to offerings
        - Cannot create offerings
    
    CREATOR: Approved to create offerings
        - All MEMBER permissions
        - Can create offerings (go to 'draft' status for review)
        - Can manage their own offerings
    
    FACILITATOR: Trusted creator with direct publishing
        - All CREATOR permissions
        - Offerings go directly to 'open' status (no review needed)
        - Can be assigned as facilitator for other offerings
    
    MODERATOR: Content and community management
        - All FACILITATOR permissions
        - Can approve/reject draft offerings
        - Can manage registrations across offerings
        - Can view all contributions (for operational purposes)
    
    ADMIN: Full system access
        - All permissions
        - User management (assign roles)
        - System settings (rates, fund)
        - Can delete any content
    """
    MEMBER = "member"
    CREATOR = "creator"
    FACILITATOR = "facilitator"
    MODERATOR = "moderator"
    ADMIN = "admin"


# Role hierarchy level (higher = more privileges)
ROLE_LEVELS = {
    UserRole.MEMBER: 10,
    UserRole.CREATOR: 20,
    UserRole.FACILITATOR: 30,
    UserRole.MODERATOR: 50,
    UserRole.ADMIN: 100,
}


# Human-readable role names (trilingual)
ROLE_NAMES = {
    UserRole.MEMBER: {
        'en': 'Member',
        'de': 'Mitglied',
        'pl': 'Członek'
    },
    UserRole.CREATOR: {
        'en': 'Creator',
        'de': 'Ersteller',
        'pl': 'Twórca'
    },
    UserRole.FACILITATOR: {
        'en': 'Facilitator',
        'de': 'Moderator',
        'pl': 'Facilitator'
    },
    UserRole.MODERATOR: {
        'en': 'Moderator',
        'de': 'Moderator',
        'pl': 'Moderator'
    },
    UserRole.ADMIN: {
        'en': 'Administrator',
        'de': 'Administrator',
        'pl': 'Administrator'
    },
}


# Role descriptions (trilingual)
ROLE_DESCRIPTIONS = {
    UserRole.MEMBER: {
        'en': 'Can participate in and contribute to offerings',
        'de': 'Kann an Angeboten teilnehmen und beitragen',
        'pl': 'Może uczestniczyć i wspierać oferty'
    },
    UserRole.CREATOR: {
        'en': 'Can create offerings (require approval)',
        'de': 'Kann Angebote erstellen (erfordert Genehmigung)',
        'pl': 'Może tworzyć oferty (wymagają zatwierdzenia)'
    },
    UserRole.FACILITATOR: {
        'en': 'Trusted creator - offerings published directly',
        'de': 'Vertrauenswürdiger Ersteller - Angebote werden direkt veröffentlicht',
        'pl': 'Zaufany twórca - oferty publikowane bezpośrednio'
    },
    UserRole.MODERATOR: {
        'en': 'Can approve offerings and manage community',
        'de': 'Kann Angebote genehmigen und Community verwalten',
        'pl': 'Może zatwierdzać oferty i zarządzać społecznością'
    },
    UserRole.ADMIN: {
        'en': 'Full system access',
        'de': 'Voller Systemzugriff',
        'pl': 'Pełny dostęp do systemu'
    },
}


class Permission(str, Enum):
    """Individual permissions that can be checked"""
    # Offering permissions
    VIEW_OFFERINGS = "view_offerings"
    PARTICIPATE = "participate"
    CONTRIBUTE = "contribute"
    CREATE_OFFERING = "create_offering"
    PUBLISH_OFFERING_DIRECT = "publish_offering_direct"
    MANAGE_OWN_OFFERING = "manage_own_offering"
    APPROVE_OFFERINGS = "approve_offerings"
    MANAGE_ALL_OFFERINGS = "manage_all_offerings"
    DELETE_OFFERINGS = "delete_offerings"
    
    # User/registration permissions
    VIEW_REGISTRATIONS = "view_registrations"
    MANAGE_REGISTRATIONS = "manage_registrations"
    VIEW_CONTRIBUTIONS = "view_contributions"
    MANAGE_CONTRIBUTIONS = "manage_contributions"
    
    # Admin permissions
    VIEW_USERS = "view_users"
    MANAGE_USERS = "manage_users"
    ASSIGN_ROLES = "assign_roles"
    MANAGE_SETTINGS = "manage_settings"
    MANAGE_FUND = "manage_fund"


# Role -> Permissions mapping
ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.MEMBER: {
        Permission.VIEW_OFFERINGS,
        Permission.PARTICIPATE,
        Permission.CONTRIBUTE,
    },
    UserRole.CREATOR: {
        Permission.VIEW_OFFERINGS,
        Permission.PARTICIPATE,
        Permission.CONTRIBUTE,
        Permission.CREATE_OFFERING,
        Permission.MANAGE_OWN_OFFERING,
    },
    UserRole.FACILITATOR: {
        Permission.VIEW_OFFERINGS,
        Permission.PARTICIPATE,
        Permission.CONTRIBUTE,
        Permission.CREATE_OFFERING,
        Permission.PUBLISH_OFFERING_DIRECT,
        Permission.MANAGE_OWN_OFFERING,
    },
    UserRole.MODERATOR: {
        Permission.VIEW_OFFERINGS,
        Permission.PARTICIPATE,
        Permission.CONTRIBUTE,
        Permission.CREATE_OFFERING,
        Permission.PUBLISH_OFFERING_DIRECT,
        Permission.MANAGE_OWN_OFFERING,
        Permission.APPROVE_OFFERINGS,
        Permission.VIEW_REGISTRATIONS,
        Permission.MANAGE_REGISTRATIONS,
        Permission.VIEW_CONTRIBUTIONS,
    },
    UserRole.ADMIN: {
        # All permissions
        Permission.VIEW_OFFERINGS,
        Permission.PARTICIPATE,
        Permission.CONTRIBUTE,
        Permission.CREATE_OFFERING,
        Permission.PUBLISH_OFFERING_DIRECT,
        Permission.MANAGE_OWN_OFFERING,
        Permission.APPROVE_OFFERINGS,
        Permission.MANAGE_ALL_OFFERINGS,
        Permission.DELETE_OFFERINGS,
        Permission.VIEW_REGISTRATIONS,
        Permission.MANAGE_REGISTRATIONS,
        Permission.VIEW_CONTRIBUTIONS,
        Permission.MANAGE_CONTRIBUTIONS,
        Permission.VIEW_USERS,
        Permission.MANAGE_USERS,
        Permission.ASSIGN_ROLES,
        Permission.MANAGE_SETTINGS,
        Permission.MANAGE_FUND,
    },
}


def get_role_level(role: str) -> int:
    """Get the privilege level for a role"""
    try:
        return ROLE_LEVELS[UserRole(role)]
    except (ValueError, KeyError):
        return 0


def has_permission(role: str, permission: Permission) -> bool:
    """Check if a role has a specific permission"""
    try:
        user_role = UserRole(role)
        return permission in ROLE_PERMISSIONS.get(user_role, set())
    except ValueError:
        return False


def has_role_or_higher(user_role: str, required_role: str) -> bool:
    """Check if user's role is equal to or higher than the required role"""
    return get_role_level(user_role) >= get_role_level(required_role)


def can_create_offering(role: str) -> bool:
    """Check if user can create offerings"""
    return has_permission(role, Permission.CREATE_OFFERING)


def can_publish_direct(role: str) -> bool:
    """Check if user's offerings bypass review"""
    return has_permission(role, Permission.PUBLISH_OFFERING_DIRECT)


def can_approve_offerings(role: str) -> bool:
    """Check if user can approve draft offerings"""
    return has_permission(role, Permission.APPROVE_OFFERINGS)


def can_manage_users(role: str) -> bool:
    """Check if user can manage other users"""
    return has_permission(role, Permission.MANAGE_USERS)


def get_role_name(role: str, lang: str = 'en') -> str:
    """Get the human-readable name for a role"""
    try:
        return ROLE_NAMES[UserRole(role)].get(lang, ROLE_NAMES[UserRole(role)]['en'])
    except (ValueError, KeyError):
        return role.capitalize()


def get_role_description(role: str, lang: str = 'en') -> str:
    """Get the description for a role"""
    try:
        return ROLE_DESCRIPTIONS[UserRole(role)].get(lang, ROLE_DESCRIPTIONS[UserRole(role)]['en'])
    except (ValueError, KeyError):
        return ""


def get_all_roles() -> List[UserRole]:
    """Get all roles in order of privilege"""
    return sorted(ROLE_LEVELS.keys(), key=lambda r: ROLE_LEVELS[r])


def get_assignable_roles(assigner_role: str) -> List[UserRole]:
    """Get roles that can be assigned by a user with the given role"""
    assigner_level = get_role_level(assigner_role)
    
    # Users can only assign roles below their own level
    # Exception: admins can assign any role including admin
    if assigner_role == UserRole.ADMIN.value:
        return list(UserRole)
    
    return [role for role in UserRole if ROLE_LEVELS[role] < assigner_level]
