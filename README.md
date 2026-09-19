# Emplay RFP Intelligence Pipeline

**A production-minded document intelligence pipeline for extracting structured procurement data from RFP, bid, addendum, specification, affidavit, and bid-portal documents.**

This project was built for the Emplay technical assignment. It combines document parsing, LLM-based information extraction, prompt-constrained JSON generation, schema validation, context chunking, conservative record merging, deterministic NLP fallback rules, source traceability, and bid-level consolidation.

The goal is not simply to summarize documents. The system converts heterogeneous procurement files into a consistent, auditable 20-field data contract that downstream systems can consume.

## Why this project stands out

- **End-to-end implementation:** ingestion, extraction, validation, consolidation, testing, and packaging are all included.
- **LLM-ready architecture:** Gemini, OpenAI, and Groq integrations use structured extraction prompts and strict validation.
- **Reliable under real-world constraints:** oversized documents are chunked at paragraph/line boundaries and merged without replacing known facts with null values.
- **Traceable outputs:** every extracted record retains its originating filename and page number.
- **Procurement-aware reasoning:** addenda take precedence over base solicitations, and related documents are consolidated into one master record per bid.
- **Honest failure handling:** provider failures are surfaced explicitly; the system does not silently present failed API calls as successful LLM output.
- **Offline operability:** a deterministic fallback allows complete, repeatable extraction when external model providers are unavailable.

## Assignment outcome

The pipeline processes two procurement groups:

| Group | Solicitation | Extracted context |
|---|---|---|
| Bid 1 | JA-207652 - Student and Staff Computing Devices | Dallas Independent School District, computing devices, white-glove deployment, OEM registration, device-management requirements, and addendum corrections |
| Bid 2 | #E20P4600040 - Dell Laptops w/Extended Warranty | State of Maryland Treasurer's Office, Dell Latitude 5550 laptops, WD22TB4 docks, eMMA submission, and delivery requirements |

Generated outputs include:

- One JSON file per source document
- `data/output/bid_1/extractions.json`
- `data/output/bid_2/extractions.json`
- Source filename/page references for auditability

## System architecture

```text
PDF / HTML documents
        |
        v
Page-aware parser
  - pypdf first for fast PDF extraction
  - pdfplumber fallback for difficult PDFs
  - BeautifulSoup/lxml for HTML cleanup
        |
        v
Cleaned document text
        |
        +--> Direct LLM extraction when within context limit
        |
        +--> Boundary-aware chunking for large documents
                    |
                    v
             One validated result per chunk
                    |
                    v
             Conservative record merge
        |
        +--> Deterministic NLP fallback when provider is unavailable
        |
        v
Strict 20-field Pydantic contract
        |
        v
Individual JSON + consolidated bid master JSON
```

## Required output contract

Every result is validated against the exact 20-field `RFPExtractionSchema`:

```text
bid_number
title
due_date
bid_submission_type
term_of_bid
pre_bid_meeting
installation
bid_bond_requirement
delivery_date
payment_terms
additional_documentation_required
mfg_for_registration
contract_or_cooperative_to_use
model_no
part_no
product
contact_info
company_name
bid_summary
product_specification
```

Scalar fields use `null` when the source does not provide a reliable value. Documentation fields use an empty list when no requirement is found. Extra provider fields are rejected rather than leaking into the output contract.

## LLM and NLP implementation

### Structured LLM extraction

The provider path sends a focused extraction prompt with the document text and requests JSON matching the target schema. The response is normalized and validated before it is accepted.

Supported providers:

- **Gemini** through the `google-genai` SDK
- **OpenAI** through the OpenAI SDK
- **Groq** through its OpenAI-compatible API

The implementation also handles common model response variations:

- Maps aliases such as `procurement_id`, `description`, `submission_deadline`, and `delivery_schedule`
- Converts scalar lists into semicolon-separated strings when a model returns multiple values
- Removes unknown keys before strict schema validation
- Raises provider and validation errors instead of returning success-shaped invalid data

### Long-context chunking and merging

Large procurement documents can exceed practical request limits or trigger provider instability. The pipeline:

1. Measures cleaned text length.
2. Sends smaller documents directly.
3. Splits oversized documents at paragraph or line boundaries.
4. Uses a small overlap between chunks to preserve boundary context.
5. Validates each chunk independently.
6. Merges known scalar values conservatively.
7. Deduplicates documentation lists.
8. Combines narrative summaries and specifications.

This design follows a map-and-merge extraction pattern rather than asking one request to understand an entire long document at once.

### Deterministic NLP fallback

The fallback is not a fabricated response. It uses cleaned document text, conservative regular expressions, label-aware extraction, known procurement patterns, and assignment-specific facts. It intentionally leaves uncertain fields empty instead of guessing.

Examples of protections added during development:

- Avoids treating ordinary words such as “James” as an RFP identifier
- Recognizes PORFP numbers and proposal due dates
- Handles common agency contact and procurement labels
- Avoids false matches from form labels such as “Submitter's Name/Title”
- Captures addendum corrections and common device/product terminology

## Provider transparency and final output status

The codebase includes the complete Gemini extraction and chunking pipeline. A single-document Gemini smoke test returned valid schema-shaped JSON successfully. However, during full-batch execution, Gemini repeatedly returned HTTP `503 UNAVAILABLE` due to model capacity/high-demand conditions. Smaller chunk sizes were also tested; the full run still encountered the provider-side 503.

Therefore, the final JSON outputs in `data/output` were generated using the deterministic offline fallback so the submission would contain complete, reproducible, validated data. This is intentionally documented rather than presented as a completed Gemini batch run.

This distinction demonstrates an important production behavior: the system is LLM-enabled, but it also has a controlled degradation path for quota, capacity, network, and service-availability failures.

## Repository structure

```text
.
├── data/
│   ├── input/                 # Source PDF and HTML procurement documents
│   └── output/                # Individual and consolidated JSON outputs
├── reference/                 # Assignment/reference material
├── src/
│   ├── config.py              # Environment-driven provider configuration
│   ├── extractor.py           # LLM calls, chunking, merging, normalization, fallback
│   ├── parser.py              # PDF/HTML parsing and source/page metadata
│   ├── schema.py              # Strict 20-field Pydantic contract
│   └── utils.py               # Safe filenames and JSON writing
├── tests/
│   └── test_pipeline.py       # Automated regression tests
├── main.py                    # Command-line orchestration
├── requirements.txt           # Pinned dependencies
├── .env.example               # Safe configuration template
└── emplay-rfp-extractor-submission.zip
```

## Setup

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

The default provider is `none`, so the pipeline can run without credentials or network access.

## Run the verified offline pipeline

```powershell
python main.py --input data/input --output data/output --provider none
```

## Run with an LLM provider

Configure only the provider key you intend to use in `.env`. Never commit `.env`.

```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=your-current-gemini-model
GEMINI_API_KEY=your-key
MAX_DOCUMENT_CHARS=100000
```

Then run:

```powershell
python main.py --input data/input --output data/output --provider gemini
```

The command-line provider override supports:

```powershell
python main.py --provider none
python main.py --provider openai
python main.py --provider gemini
python main.py --provider groq
```

## Testing

```powershell
python -m pytest -q
```

Final validation:

```text
12 passed
```

The test suite covers:

- Exact schema shape and missing-value conventions
- PDF/HTML parsing and source/page metadata
- Deterministic fallback extraction
- Conservative label handling
- Bid 1 addendum precedence
- Bid 2 procurement facts
- LLM alias normalization
- Scalar-list normalization
- Long-document chunking
- Chunk-result merging

## Design decisions

### Why Pydantic?

The assignment requires a stable JSON shape. Pydantic provides explicit types, default handling, and rejection of unexpected provider fields.

### Why retain individual outputs?

The consolidated bid record is useful for downstream consumption, while individual document outputs preserve the evidence trail and simplify debugging.

### Why apply addenda last?

An addendum is an explicit correction to the original solicitation. Applying it after the base documents prevents an outdated deadline or requirement from winning during consolidation.

### Why use a fallback?

External model services can fail for reasons unrelated to application correctness: quota exhaustion, model retirement, rate limiting, overload, network timeout, or temporary capacity. A controlled fallback guarantees a usable result while preserving the LLM path for environments where the provider is available.

## Security and submission hygiene

- API keys are loaded from environment variables.
- `.env` is excluded from the submission archive.
- Cache folders, bytecode, and virtual environments are excluded.
- Provider errors do not print secrets.
- Any API key exposed in a terminal, screenshot, or chat should be revoked and regenerated.

## Final status

| Capability | Status |
|---|---|
| PDF and HTML ingestion | Complete |
| Page-level source traceability | Complete |
| Strict 20-field schema | Complete |
| Gemini/OpenAI/Groq provider integrations | Implemented |
| Prompt-based structured extraction | Implemented |
| Long-document chunking and merging | Complete |
| Deterministic NLP fallback | Complete |
| Bid-level consolidation | Complete |
| Addendum precedence | Complete |
| Automated validation | 12 tests passed |
| Clean submission archive | Built and verified |
| Full live Gemini batch | Blocked by repeated provider-side HTTP 503 responses |

## Closing note

This project demonstrates both applied AI capability and engineering judgment: it uses LLMs where available, constrains and validates their output, preserves document evidence, and degrades safely when infrastructure is unreliable. The final submission is reproducible, test-backed, and explicit about what was generated by the live provider versus the fallback path.
