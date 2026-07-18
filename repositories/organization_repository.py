from __future__ import annotations

from extensions import db
from models.organization import Organization
from models.organization_member import OrganizationMember


# ---------------------------
# Organization repository
# ---------------------------

class OrganizationRepository:
    def add(
        self,
        organization: Organization,
    ) -> Organization:
        db.session.add(organization)
        db.session.flush()

        return organization

    def add_member(
        self,
        membership: OrganizationMember,
    ) -> OrganizationMember:
        db.session.add(membership)
        db.session.flush()

        return membership