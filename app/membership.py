"""
Initiative membership — who belongs where, and in what role.
============================================================
Project: Erdpuls / Solidarity Financing — Michel Garand
Added August 2026 with migration 018.

Two role systems sit side by side and answer different questions:

  * The GLOBAL role (users.role) answers WHAT a person may do at all:
    create offerings, moderate, administer.
  * The MEMBERSHIP role answers WHERE they may do it.

Both must allow an action. Membership never grants a capability the
global role withholds — it only narrows where that capability applies.
A global member who is made an initiative facilitator still cannot run
financing, because financing needs the global facilitator role too.

Platform admins and moderators are deliberately not listed as members:
their oversight is global and outlives any one place. Listing them
everywhere would make the record of who actually belongs to an
initiative less true, not more.

Changelog:
  v0.1 (August 2026) — first version: roles, level comparison, and the
      queries the routers use to decide access.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

# Membership roles, deliberately few.
MEMBERSHIP_ROLES = ("member", "facilitator", "steward")

MEMBERSHIP_LEVELS = {
    "member": 10,       # belongs here; no financing powers
    "facilitator": 30,  # may run financing here
    "steward": 50,      # may also manage this initiative's membership
}

# Global roles whose oversight is platform-wide and not place-bound.
GLOBAL_OVERSIGHT_ROLES = ("moderator", "admin")


def membership_level(role: str) -> int:
    return MEMBERSHIP_LEVELS.get((role or "").strip().lower(), 0)


def has_global_oversight(user) -> bool:
    """True for platform admins and moderators.

    Their access is not place-bound, so they are not required to hold a
    membership in every initiative in order to see it.
    """
    return getattr(user, "role", None) in GLOBAL_OVERSIGHT_ROLES


def get_membership(db: Session, user_id, initiative_id):
    """Return this user's membership row for an initiative, or None."""
    return db.execute(text("""
        SELECT role FROM erdpuls_threshold.initiative_members
        WHERE user_id = :u AND initiative_id = :i
    """), {"u": str(user_id), "i": str(initiative_id)}).mappings().first()


def member_at_least(db: Session, user, initiative_id, required: str) -> bool:
    """Does this user hold at least `required` in this initiative?

    Platform oversight passes without a membership row. Everyone else
    needs one at or above the required level.
    """
    if has_global_oversight(user):
        return True
    m = get_membership(db, user.id, initiative_id)
    if not m:
        return False
    return membership_level(m["role"]) >= membership_level(required)


def initiatives_for(db: Session, user, required: str = "member"):
    """Initiatives this user may act in at the required level.

    Used to fill the initiative selector when creating an offering, so a
    person is offered only the places they actually belong to. Platform
    oversight sees them all.
    """
    if has_global_oversight(user):
        return db.execute(text("""
            SELECT id, name, location, slug FROM erdpuls_threshold.initiatives
            ORDER BY sort_order
        """)).mappings().all()

    allowed = [r for r, lvl in MEMBERSHIP_LEVELS.items()
               if lvl >= membership_level(required)]
    return db.execute(text("""
        SELECT i.id, i.name, i.location, i.slug
        FROM erdpuls_threshold.initiatives i
        JOIN erdpuls_threshold.initiative_members m ON m.initiative_id = i.id
        WHERE m.user_id = :u AND m.role = ANY(:roles)
        ORDER BY i.sort_order
    """), {"u": str(user.id), "roles": allowed}).mappings().all()


def members_of(db: Session, initiative_id):
    """Everyone who belongs to an initiative, with their global role too.

    Both roles are shown together because either one can be the reason a
    person cannot do something, and a steward looking at this list needs
    to see which.
    """
    return db.execute(text("""
        SELECT m.id, m.role AS membership_role, m.added_at, m.note,
               u.id AS user_id, u.email, u.name, u.role AS global_role
        FROM erdpuls_threshold.initiative_members m
        JOIN erdpuls_threshold.users u ON u.id = m.user_id
        WHERE m.initiative_id = :i
        ORDER BY u.name NULLS LAST, u.email
    """), {"i": str(initiative_id)}).mappings().all()
