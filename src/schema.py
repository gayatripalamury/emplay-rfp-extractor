"""Validated output contract for the RFP extraction pipeline."""
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RFPExtractionSchema(BaseModel):
    """The 20 fields requested by the assignment, with no extra keys allowed."""

    model_config = ConfigDict(extra="forbid")

    bid_number: Optional[str] = Field(None, description="Bid or RFP identifier")
    title: Optional[str] = None
    due_date: Optional[str] = None
    bid_submission_type: Optional[str] = None
    term_of_bid: Optional[str] = None
    pre_bid_meeting: Optional[str] = None
    installation: Optional[str] = None
    bid_bond_requirement: Optional[str] = None
    delivery_date: Optional[str] = None
    payment_terms: Optional[str] = None
    additional_documentation_required: List[str] = Field(default_factory=list)
    mfg_for_registration: Optional[str] = None
    contract_or_cooperative_to_use: Optional[str] = None
    model_no: Optional[str] = None
    part_no: Optional[str] = None
    product: Optional[str] = None
    contact_info: Optional[str] = None
    company_name: Optional[str] = None
    bid_summary: Optional[str] = None
    product_specification: Optional[str] = None


FIELD_NAMES = tuple(RFPExtractionSchema.model_fields)
BidSchema = RFPExtractionSchema