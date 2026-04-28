"""MAIBA — My AI Bibliography Assistant.

No code yet. See ARCHITECTURE.md §2 for the open design questions that gate
the first commit. After those are decided, this package will hold:

- detect.py    — find gaps in library items
- resolve.py   — query Crossref / OpenAlex / Semantic Scholar / arXiv / DataCite
- apply.py     — write back with provenance tags
- backends/    — LibraryBackend implementations (Zotero, RIS, ...)
- cli.py       — command-line entry point
"""

__version__ = "0.0.0"
