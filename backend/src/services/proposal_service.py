"""
Proposal Service
Manages proposal lifecycle: create, send, track, respond.

Features:
- Full CRUD operations
- Status transitions (draft -> sent -> viewed -> accepted/rejected/expired)
- Automatic expiration handling
- Integration with notifications
- WhatsApp delivery support
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from ..core.supabase_client import supabase
from ..models.proposal import (
    Proposal, ProposalCreate, ProposalUpdate,
    ProposalStatus, ProposalInfo
)
from .notification import notification_service, NotificationType, NotificationPriority

logger = logging.getLogger(__name__)

# Table name
PROPOSALS_TABLE = "iagenericanexma_proposals"
LEADS_TABLE = "iagenericanexma_leads"


class ProposalService:
    """
    Service for managing proposals.

    Handles:
    - Proposal CRUD operations
    - Status transitions
    - View/response tracking
    - Expiration management
    - Notification triggers
    """

    # ==================== CRUD Operations ====================

    async def get_proposal(self, proposal_id: int) -> Optional[Proposal]:
        """Get proposal by ID"""
        try:
            response = supabase.table(PROPOSALS_TABLE).select("*").eq("id", proposal_id).limit(1).execute()
            if response.data and len(response.data) > 0:
                return Proposal(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting proposal {proposal_id}: {e}")
            return None

    async def list_proposals(
        self,
        company_id: int,
        lead_id: Optional[int] = None,
        status: Optional[ProposalStatus] = None,
        active_only: bool = False
    ) -> List[Proposal]:
        """
        List proposals for a company.

        Args:
            company_id: Company ID
            lead_id: Optional filter by lead
            status: Optional filter by status
            active_only: If True, exclude expired/rejected/accepted
        """
        try:
            query = supabase.table(PROPOSALS_TABLE).select("*").eq("company_id", company_id)

            if lead_id:
                query = query.eq("lead_id", lead_id)

            if status:
                query = query.eq("status", status.value if isinstance(status, ProposalStatus) else status)

            if active_only:
                query = query.not_.in_("status", ["accepted", "rejected", "expired"])

            response = query.order("created_at", desc=True).execute()
            return [Proposal(**p) for p in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Error listing proposals: {e}")
            return []

    async def create_proposal(self, proposal: ProposalCreate) -> Optional[Proposal]:
        """
        Create a new proposal.

        Sets expira_em based on validade_dias.
        """
        try:
            data = proposal.model_dump(exclude_none=True)

            # Calculate expiration date
            data["expira_em"] = (datetime.utcnow() + timedelta(days=proposal.validade_dias)).isoformat()

            response = supabase.table(PROPOSALS_TABLE).insert(data).execute()

            if response.data and len(response.data) > 0:
                created = Proposal(**response.data[0])
                logger.info(f"Proposal {created.id} created for lead {proposal.lead_id}")
                return created
            return None
        except Exception as e:
            logger.error(f"Error creating proposal: {e}")
            return None

    async def update_proposal(
        self,
        proposal_id: int,
        update: ProposalUpdate
    ) -> Optional[Proposal]:
        """Update a proposal"""
        try:
            data = update.model_dump(exclude_none=True)

            # Handle status enum
            if "status" in data and isinstance(data["status"], ProposalStatus):
                data["status"] = data["status"].value

            if not data:
                return await self.get_proposal(proposal_id)

            response = supabase.table(PROPOSALS_TABLE).update(data).eq("id", proposal_id).execute()

            if response.data and len(response.data) > 0:
                return Proposal(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating proposal {proposal_id}: {e}")
            return None

    async def delete_proposal(self, proposal_id: int) -> bool:
        """Delete a proposal"""
        try:
            # First, clear proposta_ativa_id from any leads pointing to this proposal
            supabase.table(LEADS_TABLE).update(
                {"proposta_ativa_id": None}
            ).eq("proposta_ativa_id", proposal_id).execute()

            # Delete the proposal
            response = supabase.table(PROPOSALS_TABLE).delete().eq("id", proposal_id).execute()
            return len(response.data) > 0 if response.data else False
        except Exception as e:
            logger.error(f"Error deleting proposal {proposal_id}: {e}")
            return False

    # ==================== Status Transitions ====================

    async def send_proposal(
        self,
        proposal_id: int,
        message: Optional[str] = None
    ) -> Optional[Proposal]:
        """
        Mark proposal as sent and set it as the lead's active proposal.

        Args:
            proposal_id: Proposal ID
            message: Optional custom message (for WhatsApp delivery)

        Returns:
            Updated proposal
        """
        try:
            proposal = await self.get_proposal(proposal_id)
            if not proposal:
                return None

            if proposal.status != ProposalStatus.DRAFT:
                logger.warning(f"Proposal {proposal_id} is not in draft status")
                return proposal

            # Update proposal status
            now = datetime.utcnow()
            expira_em = now + timedelta(days=proposal.validade_dias)

            response = supabase.table(PROPOSALS_TABLE).update({
                "status": ProposalStatus.SENT.value,
                "enviada_em": now.isoformat(),
                "expira_em": expira_em.isoformat()
            }).eq("id", proposal_id).execute()

            if not response.data:
                return None

            updated = Proposal(**response.data[0])

            # Set as active proposal for the lead
            await self._set_lead_active_proposal(proposal.lead_id, proposal_id)

            # Send notification
            await notification_service.send_notification(
                company_id=proposal.company_id,
                notification_type=NotificationType.PROPOSAL_REQUESTED,
                title="Proposta Enviada",
                message=f"Proposta '{proposal.titulo}' enviada para o lead",
                lead_id=proposal.lead_id,
                data={
                    "proposal_id": proposal_id,
                    "titulo": proposal.titulo,
                    "valores": proposal.valores
                }
            )

            logger.info(f"Proposal {proposal_id} sent to lead {proposal.lead_id}")
            return updated

        except Exception as e:
            logger.error(f"Error sending proposal {proposal_id}: {e}")
            return None

    async def mark_viewed(
        self,
        proposal_id: int,
        viewer_info: Optional[Dict[str, Any]] = None
    ) -> Optional[Proposal]:
        """
        Mark proposal as viewed.

        Args:
            proposal_id: Proposal ID
            viewer_info: Optional info about the viewer

        Returns:
            Updated proposal
        """
        try:
            proposal = await self.get_proposal(proposal_id)
            if not proposal:
                return None

            # Only update if not already viewed
            if proposal.visualizada_em:
                return proposal

            update_data = {
                "status": ProposalStatus.VIEWED.value,
                "visualizada_em": datetime.utcnow().isoformat()
            }

            if viewer_info:
                metadata = proposal.metadata or {}
                metadata["viewer_info"] = viewer_info
                update_data["metadata"] = metadata

            response = supabase.table(PROPOSALS_TABLE).update(update_data).eq("id", proposal_id).execute()

            if response.data:
                updated = Proposal(**response.data[0])

                # Send notification about view
                await notification_service.send_notification(
                    company_id=proposal.company_id,
                    notification_type=NotificationType.INFO,
                    title="Proposta Visualizada",
                    message=f"Lead visualizou a proposta '{proposal.titulo}'",
                    lead_id=proposal.lead_id,
                    data={"proposal_id": proposal_id},
                    priority=NotificationPriority.HIGH
                )

                logger.info(f"Proposal {proposal_id} marked as viewed")
                return updated

            return None
        except Exception as e:
            logger.error(f"Error marking proposal {proposal_id} as viewed: {e}")
            return None

    async def accept_proposal(
        self,
        proposal_id: int,
        acceptance_details: Optional[Dict[str, Any]] = None
    ) -> Optional[Proposal]:
        """
        Accept a proposal.

        Args:
            proposal_id: Proposal ID
            acceptance_details: Optional details about acceptance

        Returns:
            Updated proposal
        """
        try:
            proposal = await self.get_proposal(proposal_id)
            if not proposal:
                return None

            update_data = {
                "status": ProposalStatus.ACCEPTED.value,
                "respondida_em": datetime.utcnow().isoformat()
            }

            if acceptance_details:
                metadata = proposal.metadata or {}
                metadata["acceptance_details"] = acceptance_details
                update_data["metadata"] = metadata

            response = supabase.table(PROPOSALS_TABLE).update(update_data).eq("id", proposal_id).execute()

            if response.data:
                updated = Proposal(**response.data[0])

                # Clear active proposal (it's now accepted)
                await self._clear_lead_active_proposal(proposal.lead_id)

                # Send high-priority notification
                await notification_service.send_notification(
                    company_id=proposal.company_id,
                    notification_type=NotificationType.LEAD_QUALIFIED,
                    title="Proposta Aceita!",
                    message=f"Lead aceitou a proposta '{proposal.titulo}'!",
                    lead_id=proposal.lead_id,
                    data={
                        "proposal_id": proposal_id,
                        "valores": proposal.valores,
                        "acceptance_details": acceptance_details
                    },
                    priority=NotificationPriority.URGENT
                )

                logger.info(f"Proposal {proposal_id} accepted")
                return updated

            return None
        except Exception as e:
            logger.error(f"Error accepting proposal {proposal_id}: {e}")
            return None

    async def reject_proposal(
        self,
        proposal_id: int,
        reason: Optional[str] = None,
        counter_offer: Optional[Dict[str, Any]] = None
    ) -> Optional[Proposal]:
        """
        Reject a proposal.

        Args:
            proposal_id: Proposal ID
            reason: Rejection reason
            counter_offer: Optional counter-offer from lead

        Returns:
            Updated proposal
        """
        try:
            proposal = await self.get_proposal(proposal_id)
            if not proposal:
                return None

            metadata = proposal.metadata or {}
            if reason:
                metadata["rejection_reason"] = reason
            if counter_offer:
                metadata["counter_offer"] = counter_offer

            update_data = {
                "status": ProposalStatus.REJECTED.value,
                "respondida_em": datetime.utcnow().isoformat(),
                "metadata": metadata
            }

            response = supabase.table(PROPOSALS_TABLE).update(update_data).eq("id", proposal_id).execute()

            if response.data:
                updated = Proposal(**response.data[0])

                # Clear active proposal
                await self._clear_lead_active_proposal(proposal.lead_id)

                # Send notification
                notification_message = f"Lead rejeitou a proposta '{proposal.titulo}'"
                if reason:
                    notification_message += f". Motivo: {reason}"

                await notification_service.send_notification(
                    company_id=proposal.company_id,
                    notification_type=NotificationType.INFO,
                    title="Proposta Rejeitada",
                    message=notification_message,
                    lead_id=proposal.lead_id,
                    data={
                        "proposal_id": proposal_id,
                        "reason": reason,
                        "counter_offer": counter_offer
                    },
                    priority=NotificationPriority.HIGH
                )

                logger.info(f"Proposal {proposal_id} rejected: {reason}")
                return updated

            return None
        except Exception as e:
            logger.error(f"Error rejecting proposal {proposal_id}: {e}")
            return None

    async def mark_negotiating(
        self,
        proposal_id: int,
        negotiation_notes: Optional[str] = None
    ) -> Optional[Proposal]:
        """
        Mark proposal as in negotiation.

        Args:
            proposal_id: Proposal ID
            negotiation_notes: Optional notes about negotiation

        Returns:
            Updated proposal
        """
        try:
            proposal = await self.get_proposal(proposal_id)
            if not proposal:
                return None

            metadata = proposal.metadata or {}
            if negotiation_notes:
                metadata["negotiation_notes"] = metadata.get("negotiation_notes", [])
                metadata["negotiation_notes"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "note": negotiation_notes
                })

            response = supabase.table(PROPOSALS_TABLE).update({
                "status": ProposalStatus.NEGOTIATING.value,
                "metadata": metadata
            }).eq("id", proposal_id).execute()

            if response.data:
                logger.info(f"Proposal {proposal_id} marked as negotiating")
                return Proposal(**response.data[0])

            return None
        except Exception as e:
            logger.error(f"Error marking proposal {proposal_id} as negotiating: {e}")
            return None

    async def expire_proposal(self, proposal_id: int) -> Optional[Proposal]:
        """Mark proposal as expired"""
        try:
            response = supabase.table(PROPOSALS_TABLE).update({
                "status": ProposalStatus.EXPIRED.value
            }).eq("id", proposal_id).execute()

            if response.data:
                proposal = Proposal(**response.data[0])

                # Clear active proposal
                await self._clear_lead_active_proposal(proposal.lead_id)

                logger.info(f"Proposal {proposal_id} expired")
                return proposal

            return None
        except Exception as e:
            logger.error(f"Error expiring proposal {proposal_id}: {e}")
            return None

    # ==================== Batch Operations ====================

    async def expire_due_proposals(self) -> int:
        """
        Expire all proposals that are past their expiration date.

        Returns:
            Number of proposals expired
        """
        try:
            now = datetime.utcnow().isoformat()

            # Find expired proposals
            response = supabase.table(PROPOSALS_TABLE).select("id, lead_id").in_(
                "status", ["draft", "sent", "viewed", "negotiating"]
            ).lt("expira_em", now).execute()

            if not response.data:
                return 0

            count = 0
            for proposal_data in response.data:
                # Update status
                supabase.table(PROPOSALS_TABLE).update({
                    "status": ProposalStatus.EXPIRED.value
                }).eq("id", proposal_data["id"]).execute()

                # Clear active proposal for lead
                await self._clear_lead_active_proposal(proposal_data["lead_id"])
                count += 1

            if count > 0:
                logger.info(f"Expired {count} proposals")

            return count
        except Exception as e:
            logger.error(f"Error expiring due proposals: {e}")
            return 0

    # ==================== Lead Active Proposal ====================

    async def _set_lead_active_proposal(self, lead_id: int, proposal_id: int):
        """Set the active proposal for a lead"""
        try:
            supabase.table(LEADS_TABLE).update({
                "proposta_ativa_id": proposal_id
            }).eq("id", lead_id).execute()
        except Exception as e:
            logger.error(f"Error setting active proposal for lead {lead_id}: {e}")

    async def _clear_lead_active_proposal(self, lead_id: int):
        """Clear the active proposal for a lead"""
        try:
            supabase.table(LEADS_TABLE).update({
                "proposta_ativa_id": None
            }).eq("id", lead_id).execute()
        except Exception as e:
            logger.error(f"Error clearing active proposal for lead {lead_id}: {e}")

    async def get_lead_active_proposal(self, lead_id: int) -> Optional[Proposal]:
        """Get the active proposal for a lead"""
        try:
            # Get lead's active proposal ID
            lead_response = supabase.table(LEADS_TABLE).select("proposta_ativa_id").eq(
                "id", lead_id
            ).limit(1).execute()

            if not lead_response.data or not lead_response.data[0].get("proposta_ativa_id"):
                return None

            proposal_id = lead_response.data[0]["proposta_ativa_id"]
            return await self.get_proposal(proposal_id)
        except Exception as e:
            logger.error(f"Error getting active proposal for lead {lead_id}: {e}")
            return None

    # ==================== Utility Methods ====================

    async def get_proposal_info(self, proposal_id: int) -> Optional[ProposalInfo]:
        """Get proposal info for agent context"""
        proposal = await self.get_proposal(proposal_id)
        if proposal:
            return ProposalInfo.from_proposal(proposal)
        return None

    async def get_proposal_stats(self, company_id: int) -> Dict[str, Any]:
        """Get proposal statistics for a company"""
        try:
            proposals = await self.list_proposals(company_id)

            stats = {
                "total": len(proposals),
                "by_status": {},
                "sent_this_month": 0,
                "acceptance_rate": 0.0,
                "avg_response_time_hours": None
            }

            # Count by status
            for status in ProposalStatus:
                stats["by_status"][status.value] = sum(
                    1 for p in proposals
                    if (p.status.value if isinstance(p.status, ProposalStatus) else p.status) == status.value
                )

            # Sent this month
            now = datetime.utcnow()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            stats["sent_this_month"] = sum(
                1 for p in proposals
                if p.enviada_em and p.enviada_em >= month_start
            )

            # Acceptance rate
            sent_proposals = [p for p in proposals if p.enviada_em]
            if sent_proposals:
                accepted = sum(
                    1 for p in sent_proposals
                    if (p.status.value if isinstance(p.status, ProposalStatus) else p.status) == ProposalStatus.ACCEPTED.value
                )
                stats["acceptance_rate"] = accepted / len(sent_proposals)

            return stats
        except Exception as e:
            logger.error(f"Error getting proposal stats: {e}")
            return {}


# Singleton instance
proposal_service = ProposalService()
