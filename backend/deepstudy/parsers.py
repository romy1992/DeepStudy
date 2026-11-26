"""Lettura statica. Questi parser non importano, non eseguono e non caricano modelli."""
from __future__ import annotations

import ast
import csv
import io
import json
import re
import shutil
import subprocess
import zlib
from dataclasses import dataclass


INDEX_VERSION = "catalog-1"
MAX_CHUNK_CHARS = 1_000_000


@dataclass(frozen=True)
class ChunkDraft:
    locator: str
    text: str
    quality: str


@dataclass(frozen=True)
class ParseResult:
    extraction_state: str
    error_code: str | None
    error_message: str | None
    retryable: bool
    chunks: tuple[ChunkDraft, ...]
    warnings: tuple[str, ...]


def _failed(code: str, message: str, *, retryable: bool = False) -> ParseResult:
    return ParseResult("failed", code, message, retryable, (), ())


def _defer(code: str, message: str) -> ParseResult:
    return ParseResult("deferred", code, message, True, (), ())


def _limit(text: str) -> tuple[str, str, str | None]:
    if len(text) <= MAX_CHUNK_CHARS:
        return text, "extracted", None
    return text[:MAX_CHUNK_CHARS], "truncated", "Testo troncato al limite di catalogazione."


def parse_python(text: str) -> ParseResult:
    warnings: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        body, quality, warning = _limit(text)
        if warning:
            warnings.append(warning)
        line_count = text.count("\n") + (0 if text.endswith("\n") or text == "" else 1)
        return ParseResult(
            "ready", None, None, False,
            (ChunkDraft(f"lines:1-{max(line_count, 1)}", body, "parse_error"),),
            tuple(["Sintassi Python non valida: il file è archiviato come testo e non è stato eseguito.", *warnings]),
        )
    chunks: list[ChunkDraft] = []
    for node in tree.body:
        segment = ast.get_source_segment(text, node) or ""
        if not segment.strip():
            continue
        limited, quality, warning = _limit(segment)
        if warning:
            warnings.append(warning)
        end = getattr(node, "end_lineno", None) or node.lineno
        chunks.append(ChunkDraft(f"lines:{node.lineno}-{end}", limited, quality))
    if not chunks and text.strip():
        limited, quality, warning = _limit(text)
        if warning:
            warnings.append(warning)
        chunks.append(ChunkDraft(f"lines:1-{text.count(chr(10)) + 1}", limited, quality))
    if not chunks:
        warnings.append("File Python vuoto.")
    return ParseResult("ready", None, None, False, tuple(chunks), tuple(warnings))


def parse_notebook(text: str) -> ParseResult:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return _failed("invalid_notebook", "Il notebook non è un JSON valido.")
    if not isinstance(data, dict) or not isinstance(data.get("cells"), list):
        return _failed("invalid_notebook", "Il notebook non contiene un elenco di celle.")
    chunks: list[ChunkDraft] = []
    warnings: list[str] = []
    for index, cell in enumerate(data["cells"]):
        if not isinstance(cell, dict):
            return _failed("invalid_notebook", f"La cella {index} non è un oggetto.")
        cell_type = cell.get("cell_type")
        if cell_type not in ("code", "markdown", "raw"):
            return _failed("invalid_notebook", f"La cella {index} ha un tipo non riconosciuto.")
        source = cell.get("source")
        if isinstance(source, list):
            if not all(isinstance(part, str) for part in source):
                return _failed("invalid_notebook", f"La cella {index} non ha un sorgente testuale.")
            source = "".join(source)
        elif not isinstance(source, str):
            return _failed("invalid_notebook", f"La cella {index} non ha un sorgente testuale.")
        limited, quality, warning = _limit(source)
        if warning:
            warnings.append(warning)
        chunks.append(ChunkDraft(f"cell:{index}", limited, quality))
    if not chunks:
        warnings.append("Notebook senza celle.")
    return ParseResult("ready", None, None, False, tuple(chunks), tuple(warnings))


def parse_text(text: str, *, empty_message: str) -> ParseResult:
    if not text.strip():
        return ParseResult("ready", None, None, False, (), (empty_message,))
    limited, quality, warning = _limit(text)
    warnings = (warning,) if warning else ()
    lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    return ParseResult("ready", None, None, False, (ChunkDraft(f"lines:1-{max(lines, 1)}", limited, quality),), warnings)


def parse_table(text: str, delimiter: str) -> ParseResult:
    if not text.strip():
        return ParseResult("ready", None, None, False, (), ("File tabellare vuoto.",))
    sample = text[:1_000_000]
    reader = csv.reader(io.StringIO(sample), delimiter=delimiter)
    first: list[str] | None = None
    count = 0
    for count, row in enumerate(reader, start=1):
        if first is None:
            first = row
        if count >= 100_000:
            break
    truncated = len(text) > len(sample) or count >= 100_000
    header = ", ".join(first or [])
    summary = f"Righe profilate: {count}. Prima riga: {header}"
    warnings = ("Profilo parziale: il dataset non è stato copiato per intero.",) if truncated else ()
    return ParseResult("ready", None, None, False, (ChunkDraft("csv:profile", summary, "profile"),), warnings)


def _pdf_unescape(data: bytes) -> str:
    output = bytearray()
    index = 0
    while index < len(data):
        if data[index] == 0x5C and index + 1 < len(data):
            mapped = {ord("n"): b"\n", ord("r"): b"\r", ord("t"): b"\t", ord("("): b"(", ord(")"): b")", ord("\\"): b"\\"}
            if data[index + 1] in mapped:
                output.extend(mapped[data[index + 1]])
                index += 2
                continue
        output.append(data[index])
        index += 1
    return output.decode("utf-8", errors="replace").strip()


def _pdf_blobs(data: bytes) -> list[bytes]:
    blobs = [data]
    for match in re.finditer(br"stream\r?\n", data):
        start = match.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        raw = data[start:end]
        if raw.endswith(b"\r\n"):
            raw = raw[:-2]
        elif raw.endswith(b"\n"):
            raw = raw[:-1]
        header = data[max(0, match.start() - 400):match.start()]
        if b"FlateDecode" in header:
            try:
                blobs.append(zlib.decompress(raw))
            except zlib.error:
                continue
        else:
            blobs.append(raw)
    return blobs


def parse_pdf(data: bytes) -> ParseResult:
    if not data.startswith(b"%PDF-"):
        return _failed("invalid_pdf", "Il file non è un PDF valido.")
    pages = len(re.findall(br"/Type\s*/Page(?!s)", data))
    pieces: list[str] = []
    pattern = re.compile(br"\((?:\\.|[^\\)])*\)")
    for blob in _pdf_blobs(data):
        for match in re.finditer(br"\((?:\\.|[^\\)])*\)\s*Tj", blob):
            literal = match.group(0)
            literal = literal[:literal.rfind(b")")]
            text = _pdf_unescape(literal[1:])
            if text:
                pieces.append(text)
        for array in re.finditer(br"\[(.*?)\]\s*TJ", blob, re.S):
            for part in pattern.finditer(array.group(1)):
                text = _pdf_unescape(part.group(0)[1:-1])
                if text:
                    pieces.append(text)
    extracted = "\n".join(pieces).strip()
    if not extracted:
        return _defer("ocr_unavailable", "PDF senza testo estraibile. OCR non eseguito e il file non è stato promosso a testo revisionato.")
    limited, quality, warning = _limit(extracted)
    locator = "page:1" if pages == 1 else "pdf:text"
    warnings = []
    if pages != 1:
        warnings.append("Il testo PDF non è stato associato pagina per pagina.")
    if warning:
        warnings.append(warning)
    return ParseResult("ready", None, None, False, (ChunkDraft(locator, limited, quality),), tuple(warnings))


def ocr_engine() -> str | None:
    return shutil.which("tesseract")


def parse_image(path_bytes: bytes, path: str) -> ParseResult:
    png = path_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    jpeg = path_bytes.startswith(b"\xff\xd8\xff")
    if not png and not jpeg:
        return _failed("invalid_image", "L'immagine non ha un'intestazione PNG o JPEG riconosciuta.")
    engine = ocr_engine()
    if not engine:
        return _defer("ocr_unavailable", "Immagine rilevata. OCR non disponibile: nessun testo è stato inventato né marcato come revisionato.")
    try:
        completed = subprocess.run(
            [engine, path, "stdout", "-l", "eng"],
            capture_output=True, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return _defer("ocr_failed", "OCR non riuscito. Il file originale non è stato modificato.")
    if completed.returncode != 0:
        return _defer("ocr_failed", "OCR non riuscito. Il file originale non è stato modificato.")
    text = completed.stdout.decode("utf-8", errors="replace").strip()
    if not text:
        return _defer("ocr_empty", "OCR senza testo. L'immagine resta fuori dal corpus revisionato.")
    limited, _, warning = _limit(text)
    warnings = ["Testo OCR non revisionato (L01 aperta)."]
    if warning:
        warnings.append(warning)
    return ParseResult("ready", None, None, False, (ChunkDraft("image:ocr", limited, "ocr_unverified"),), tuple(warnings))
