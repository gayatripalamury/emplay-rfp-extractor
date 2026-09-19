"""CLI for processing individual documents and Bid 1/Bid 2 groups."""
import argparse
import os
import shutil
from pathlib import Path

from src.extractor import _merge_records, extract_rfp_data, extract_with_sources
from src.parser import parse_document
from src.schema import RFPExtractionSchema
from src.utils import safe_stem, write_json


def group_name(path: Path) -> str:
    name = path.name.lower()
    return "Bid 2" if any(token in name for token in ("dell", "porfp", "mercury", "contract_affidavit")) else "Bid 1"


def process(input_dir: Path, output_dir: Path, provider: str | None = None) -> list[Path]:
    files = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in (".pdf", ".html", ".htm"))
    # Rebuild generated artifacts so removed/renamed inputs cannot leave stale JSON.
    if output_dir.exists():
        def _remove_readonly(func, path, _exc):
            os.chmod(path, 0o700)
            func(path)
        shutil.rmtree(output_dir, onerror=_remove_readonly)
    output_dir.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[tuple[Path, dict]]] = {"Bid 1": [], "Bid 2": []}
    outputs = []
    for path in files:
        result = extract_with_sources(parse_document(path), provider)
        target = write_json(output_dir / f"{safe_stem(path)}.json", result)
        outputs.append(target)
        grouped[group_name(path)].append((path, result))
    for name, entries in grouped.items():
        if entries:
            # Addenda are processed last so their explicit corrections win.
            entries.sort(key=lambda item: ("addendum" not in item[0].name.lower(), item[0].name.lower()))
            documents = [record for _, record in entries]
            combined_text = "\n\n".join(
                page.text
                for path, _ in entries
                for page in parse_document(path)
            )
            master_record = extract_rfp_data(combined_text, provider)
            # Preserve richer per-document facts, such as a phone/email contact,
            # when the combined extraction only returns a short label.
            master_record = _merge_records(
                [master_record]
                + [RFPExtractionSchema.model_validate(record["data"]) for _, record in entries]
            )
            master = master_record.model_dump()
            for path, record in entries:
                if "addendum 2" in path.name.lower() and record["data"].get("due_date"):
                    master["due_date"] = record["data"]["due_date"]
            sources = [source for record in documents for source in record["sources"]]
            write_json(output_dir / name.replace(" ", "_").lower() / "extractions.json",
                       {"bid_group": name, "data": master, "sources": sources})
    return outputs


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--input", type=Path, default=Path("data/input"))
    cli.add_argument("--output", type=Path, default=Path("data/output"))
    cli.add_argument("--provider", choices=["none", "openai", "gemini", "groq"], default=None)
    args = cli.parse_args()
    for output in process(args.input, args.output, args.provider):
        print(output)


if __name__ == "__main__":
    main()