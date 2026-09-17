"""
ingest_fixtures.py — Pre-load demo documents into the Knowledge Base

Run this once after generating fixtures to seed the KB for demos:
  python scripts/ingest_fixtures.py

This ingests:
  1. sample_sop.txt        — Electrical Maintenance SOP (SOP-ELE-012)
  2. sample_board_brief.txt — Board briefing on capex approval
"""
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

FIXTURE_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def main():
    print("\n🗂  SovereignForge — Ingesting Demo Documents into Knowledge Base\n")

    try:
        from tools.knowledge_base import ingest_text, get_kb_stats
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you have activated the venv and installed sentence-transformers")
        sys.exit(1)

    docs = [
        ("sample_sop.txt",         "SOP-ELE-012",      "manual"),
        ("sample_board_brief.txt",  "MRPL-CAPEX-BRIEF", "report"),
    ]

    for filename, source_name, doc_type in docs:
        fpath = FIXTURE_DIR / filename
        if not fpath.exists():
            print(f"  ⚠️  Not found: {fpath} — run generate_fixtures.py first")
            continue

        text = fpath.read_text(encoding="utf-8")
        print(f"  📄 Ingesting {filename} as '{source_name}'...")
        result = ingest_text(text, source_name=source_name, doc_type=doc_type)

        if result["success"]:
            print(f"     ✅ Added {result['chunks_added']} chunks")
        else:
            print(f"     ❌ {result['error']}")

    # Summary
    stats = get_kb_stats()
    print(f"\n✅ Knowledge Base ready: {stats['total_chunks']} total chunks")
    print(f"   Sources: {list(stats['sources'].keys())}")
    print(f"   KB stored at: {stats['kb_dir']}\n")


if __name__ == "__main__":
    main()
