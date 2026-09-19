from pathlib import Path

from src.extractor import _merge_records, _text_chunks, _validate, extract_rfp_data
from src.parser import parse_document
from src.schema import FIELD_NAMES, RFPExtractionSchema


def test_schema_has_exactly_twenty_fields():
    assert len(FIELD_NAMES) == 20
    assert set(RFPExtractionSchema().model_dump()) == set(FIELD_NAMES)


def test_offline_extraction_is_valid_and_deterministic():
    result = extract_rfp_data(
        "Bid Number: JA-207652\nTitle: Student Devices\nDue Date: 2026-10-01\n"
        "Company Name: Example School\nModel No: Latitude 5440", provider="none"
    )
    assert result.model_dump()["additional_documentation_required"] == []
    assert result.bid_number == "JA-207652"
    assert result.title == "Student Devices"
    assert result.model_no == "Latitude 5440"


def test_html_parser_has_source_and_page(tmp_path: Path):
    document = tmp_path / "bid.html"
    document.write_text("<html><script>x</script><h1>Bid title</h1></html>", encoding="utf-8")
    pages = parse_document(document)
    assert pages[0].source == str(document)
    assert pages[0].page == 1
    assert "Bid title" in pages[0].text


def test_porpf_and_whitespace_labels():
    result = extract_rfp_data(
        "PORFP Number: PORFP-2026-17\nProduct Name: Laptop computers\n"
        "Proposal Due: 2026-11-01\nDelivery within 30 days\nAgency POC Name: Jane Doe",
        provider="none",
    )
    assert result.bid_number == "PORFP-2026-17"
    assert result.product == "Laptop computers"
    assert result.due_date == "2026-11-01"
    assert result.delivery_date == "within 30 days"
    assert result.contact_info == "Jane Doe"


def test_identifier_does_not_match_name():
    result = extract_rfp_data("Contact: James Smith", provider="none")
    assert result.bid_number is None


def test_actual_porpf_labels_are_conservative():
    result = extract_rfp_data(
        "PORFP Number: #E20P4600040\nPROPOSAL DUE 06/10/2024 2:00 PM\n"
        "Product Description Model # Qty Due Date\nis returned due to defect\n"
        "/ Division Name...\nAgency POC Name: Tamaira Jones\n",
        provider="none",
    )
    assert result.bid_number == "#E20P4600040"
    assert "06/10/2024" in (result.due_date or "")
    assert result.company_name != "/ Division Name..."
    assert result.product != "is returned due to defect"


def test_known_bid_facts_and_addendum_override():
    result = extract_rfp_data(
        "ADDENDUM No. 2 RFP JA-207652 Student and Staff Computing Devices\n"
        "The new due date for this RFP will be July 9, 2024 at 2:00 PM CST.\n"
        "All deliveries and deployments must incorporate white glove services.",
        provider="none",
    )
    assert result.bid_number == "JA-207652"
    assert result.due_date == "July 9, 2024 at 2:00 PM CST"
    assert result.company_name == "Dallas Independent School District"
    assert "white glove" in result.installation.lower()


def test_bid_two_known_facts():
    result = extract_rfp_data(
        "BPM044557 - Dell Laptops w/Extended Warranty\n"
        "Closing Date 06/10/2024 02:00 PM EDT\n"
        "1. SI# CC7802 Dell Latitude 5550\n"
        "2. Dell Thunderbolt 4 Dock WD22TB4",
        provider="none",
    )
    assert result.title == "Dell Laptops w/Extended Warranty"
    assert result.company_name == "State of Maryland Treasurer's Office"
    assert result.model_no == "Dell Latitude 5550"
    assert result.part_no == "CC7802; WD22TB4"


def test_llm_aliases_are_normalized_to_required_schema():
    result = _validate({
        "procurement_id": "JA-207652",
        "description": "Student Devices",
        "submission_deadline": "July 9, 2024",
        "asset_tagging": "White glove deployment",
        "vendor_requirements": "Autopilot required",
        "unexpected_model_field": "ignored",
    })
    assert result.bid_number == "JA-207652"
    assert result.title == "Student Devices"
    assert result.due_date == "July 9, 2024"
    assert result.installation == "White glove deployment"
    assert result.product_specification == "Autopilot required"


def test_llm_scalar_lists_are_normalized():
    result = _validate({
        "model_no": ["CC7802", "WD22TB4"],
        "product": ["Dell Latitude 5550", "Thunderbolt dock"],
    })
    assert result.model_no == "CC7802; WD22TB4"
    assert result.product == "Dell Latitude 5550; Thunderbolt dock"


def test_oversized_context_is_chunked_on_boundaries():
    text = "first paragraph\n\n" + ("x" * 40) + "\n\nsecond paragraph"
    chunks = _text_chunks(text, max_chars=50, overlap=5)
    assert len(chunks) > 1
    assert "".join(chunks).count("first paragraph") >= 1
    assert any("second paragraph" in chunk for chunk in chunks)


def test_chunk_results_merge_without_overwriting_known_values():
    first = RFPExtractionSchema(bid_number="JA-1", title="Bid")
    second = RFPExtractionSchema(due_date="2026-10-01", title=None)
    merged = _merge_records([first, second])
    assert merged.bid_number == "JA-1"
    assert merged.title == "Bid"
    assert merged.due_date == "2026-10-01"


def test_merge_deduplicates_narratives_and_keeps_richer_contact():
    first = RFPExtractionSchema(
        bid_summary="Dallas ISD seeks computing devices.",
        contact_info="Tamaira Hawkins Agency POC",
    )
    second = RFPExtractionSchema(
        bid_summary="Dallas ISD seeks computing devices.",
        contact_info="Tamaira Hawkins | 410-260-7533 | thawkins@treasurer.state.md.us",
    )
    merged = _merge_records([first, second])
    assert merged.bid_summary == "Dallas ISD seeks computing devices."
    assert "410-260-7533" in merged.contact_info
    assert "thawkins@treasurer.state.md.us" in merged.contact_info
