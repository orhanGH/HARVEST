"""PDF page extraction migrated from the legacy implementation.

PageRecord remains a deliberate compatibility boundary until the new type model
replaces the legacy record in a later phase.
"""

from harvest_ocr.ingest import extract_pdf_pages

__all__ = ["extract_pdf_pages"]
