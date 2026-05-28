"""Document chunker — splits text into overlapping chunks preserving metadata."""

import re

CHUNK_SIZE = 800      # characters per chunk
CHUNK_OVERLAP = 150   # overlap between consecutive chunks


def chunk_text(text: str, source_doc: str, doc_type: str = "unknown") -> list[dict]:
    """Split text into overlapping chunks.

    Returns a list of dicts with keys: text, source_doc, section, doc_type.
    """
    # Normalise whitespace
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    paragraphs = text.split("\n\n")
    chunks: list[dict] = []
    current = ""
    current_section = "Document"

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Detect section headers (lines starting with #, or ALL CAPS short lines)
        first_line = para.split("\n")[0]
        if re.match(r"^#{1,4}\s+", first_line) or (
            len(first_line) < 80 and first_line.isupper()
        ):
            current_section = first_line.lstrip("#").strip()

        if len(current) + len(para) + 2 > CHUNK_SIZE:
            if current:
                chunks.append({
                    "text": current.strip(),
                    "source_doc": source_doc,
                    "section": current_section,
                    "doc_type": doc_type,
                })
                # Overlap: keep last CHUNK_OVERLAP chars
                current = current[-CHUNK_OVERLAP:] + "\n\n" + para
            else:
                current = para
        else:
            current = (current + "\n\n" + para).strip() if current else para

    if current.strip():
        chunks.append({
            "text": current.strip(),
            "source_doc": source_doc,
            "section": current_section,
            "doc_type": doc_type,
        })

    return chunks
