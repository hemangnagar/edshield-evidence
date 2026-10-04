"""Residual scoring on the final de-identified output.

The question is not "did the detector flag it" but "is the identifying text
still there". Everything here reads the output text and the acted-on entity
offsets that `edshield.deidentify()` returns; nothing is imported from
edshield's evaluator.

Definitions (brief §3):

Normalize   NFKC, casefold, collapse whitespace; an offset map takes every
            normalized position back to the original text.
Full residual  the normalized gold string occurs in the normalized output as a
            whole word (word boundaries on both sides). Gold strings that
            carry punctuation ("415-555-0199", "maya.c@gmail.com") are also
            matched after stripping everything but letters and digits from
            both sides, with the boundary check done in the normalized
            output. y_pred = 0 if found, else 1.
Partial residual  the longest token of the gold string (>= 3 chars) that
            survives as a whole word in the output when the full string does
            not. Reported, not gated.
Word view   whitespace tokens of the original; y_true = 1 if the token
            overlaps a gold span; y_pred = 1 if the token's text is absent at
            its aligned position in the output (replaced or removed). Tokens
            inside a removed region are y_pred = 1.
Label confusion  for each gold span, the labels of the acted-on entities that
            touched it. Reported, not gated.
Over-redaction sample  up to 50 removed tokens with y_true = 0, with context.

Known conservative bias: a surrogate that happens to equal a gold string
(method `replace`) counts as a residual. The judge cannot know it is a
surrogate, and neither can a reader of the output.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

Span = Tuple[int, int, str]

OVER_REDACTION_SAMPLE = 50
CONTEXT_CHARS = 40
MIN_PARTIAL_TOKEN = 3

_TOKEN_RE = re.compile(r"\S+")
_WORD_RE = re.compile(r"\w+")


# --- Normalization -------------------------------------------------------------

def normalize(text: str) -> Tuple[str, List[int]]:
    """Return (normalized text, offset map). `offset_map[i]` is the index in
    `text` of the character that produced normalized position `i`."""
    out: List[str] = []
    omap: List[int] = []
    prev_space = True  # drop leading whitespace
    for i, ch in enumerate(text):
        if ch.isspace():
            if not prev_space:
                out.append(" ")
                omap.append(i)
                prev_space = True
            continue
        for c in unicodedata.normalize("NFKC", ch).casefold():
            if c.isspace():
                if not prev_space:
                    out.append(" ")
                    omap.append(i)
                    prev_space = True
                continue
            out.append(c)
            omap.append(i)
            prev_space = False
    if out and out[-1] == " ":
        out.pop()
        omap.pop()
    return "".join(out), omap


def _is_word_char(c: str) -> bool:
    return c.isalnum() or c == "_"


def _strip_edges(s: str) -> str:
    """Drop leading/trailing characters that are not letters or digits."""
    i, j = 0, len(s)
    while i < j and not s[i].isalnum():
        i += 1
    while j > i and not s[j - 1].isalnum():
        j -= 1
    return s[i:j]


def find_whole_word(needle: str, hay: str) -> Optional[Tuple[int, int]]:
    """First whole-word occurrence of `needle` in `hay` (both normalized)."""
    needle = _strip_edges(needle)
    if not needle:
        return None
    m = re.search(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", hay)
    return (m.start(), m.end()) if m else None


def _compact(s: str) -> Tuple[str, List[int]]:
    chars, omap = [], []
    for i, c in enumerate(s):
        if c.isalnum():
            chars.append(c)
            omap.append(i)
    return "".join(chars), omap


def find_compact(needle: str, hay: str) -> Optional[Tuple[int, int]]:
    """Match after stripping everything but letters and digits from both sides.
    The match must still sit on word boundaries in `hay`, so "4155550199"
    matches "415-555-0199" and "415 555 0199" but not "94155550199"."""
    cn, _ = _compact(needle)
    if len(cn) < 2:
        return None
    ch, cmap = _compact(hay)
    for m in re.finditer(re.escape(cn), ch):
        hs, he = cmap[m.start()], cmap[m.end() - 1] + 1
        before = hay[hs - 1] if hs > 0 else " "
        after = hay[he] if he < len(hay) else " "
        if not _is_word_char(before) and not _is_word_char(after):
            return (hs, he)
    return None


def _needs_compact(needle: str) -> bool:
    inner = _strip_edges(needle)
    return any(not (c.isalnum() or c.isspace()) for c in inner)


def find_residual(gold_text: str, out_norm: str) -> Optional[Tuple[int, int]]:
    """Position of the full residual in the normalized output, or None."""
    gn, _ = normalize(gold_text)
    hit = find_whole_word(gn, out_norm)
    if hit is None and _needs_compact(gn):
        hit = find_compact(gn, out_norm)
    return hit


def partial_residual(gold_text: str, out_norm: str) -> Optional[str]:
    """Longest token (>= 3 chars) of the gold string that survives as a whole word."""
    gn, _ = normalize(gold_text)
    for tok in sorted(set(_WORD_RE.findall(gn)), key=lambda t: (-len(t), t)):
        if len(tok) < MIN_PARTIAL_TOKEN:
            break
        if re.search(r"(?<!\w)" + re.escape(tok) + r"(?!\w)", out_norm):
            return tok
    return None


# --- Results -------------------------------------------------------------------

@dataclass
class IdentifierOutcome:
    index: int
    label: str
    text: str
    start: int
    end: int
    full_residual: bool
    residual_at: Optional[Tuple[int, int]]  # in original output coordinates
    partial: Optional[str]
    touched: List[str]  # labels of acted-on entities overlapping the gold span

    @property
    def y_pred(self) -> int:
        return 0 if self.full_residual else 1


@dataclass
class WordOutcome:
    index: int
    start: int
    end: int
    text: str
    y_true: int
    y_pred: int


@dataclass
class DocScore:
    doc_id: str
    identifiers: List[IdentifierOutcome]
    words: List[WordOutcome]
    over_redactions: List[dict]
    aligned: bool
    n_acted: int
    self_reported_leaks: int = 0

    @property
    def has_gold(self) -> bool:
        return bool(self.identifiers)

    @property
    def document_handled(self) -> bool:
        return not any(i.full_residual for i in self.identifiers)

    def label_confusion(self) -> Dict[str, Dict[str, int]]:
        table: Dict[str, Dict[str, int]] = {}
        for i in self.identifiers:
            row = table.setdefault(i.label, {})
            for t in (i.touched or ["none"]):
                row[t] = row.get(t, 0) + 1
        return table


def _acted_regions(text: str, entities: Iterable, replacements: Optional[dict]) -> List[Tuple[int, int, str, Optional[str]]]:
    """(start, end, original, rendered) for every acted-on entity, sorted and
    clipped to the text; rendered is None when it is not known."""
    regions = []
    for e in entities:
        s, t = max(0, int(e.start)), min(len(text), int(e.end))
        if t <= s:
            continue
        original = text[s:t]
        rendered = None
        if replacements:
            rendered = replacements.get(getattr(e, "text", original), replacements.get(original))
        regions.append((s, t, original, rendered))
    regions.sort()
    return regions


def _align(text: str, output: str, regions: Sequence[Tuple[int, int, str, Optional[str]]]) -> Optional[List[Tuple[int, int, int]]]:
    """Map untouched segments of `text` to their positions in `output`.
    Returns [(orig_start, orig_end, out_start)] or None when the output does
    not reproduce the untouched text where the entity offsets say it should."""
    segments = []
    cursor, out_cursor = 0, 0
    for idx, (s, t, original, rendered) in enumerate(regions):
        seg = text[cursor:s]
        if not output.startswith(seg, out_cursor):
            return None
        segments.append((cursor, s, out_cursor))
        out_cursor += len(seg)
        # Skip the rendered replacement: known length, or search for the next untouched segment.
        if rendered is not None and output.startswith(rendered, out_cursor):
            out_cursor += len(rendered)
        else:
            nxt_start = regions[idx + 1][0] if idx + 1 < len(regions) else len(text)
            nxt = text[t:nxt_start]
            if not nxt:
                if idx + 1 < len(regions):
                    return None  # two replacements back to back with unknown lengths
                out_cursor = len(output)
            else:
                pos = output.find(nxt, out_cursor)
                if pos < 0:
                    return None
                out_cursor = pos
        cursor = t
    tail = text[cursor:]
    if not output.startswith(tail, out_cursor):
        return None
    segments.append((cursor, len(text), out_cursor))
    return segments


def score_document(doc_id: str, text: str, gold_spans: Sequence[Span], result,
                   sample_over_redactions: int = OVER_REDACTION_SAMPLE) -> DocScore:
    """Score one document. `result` is what `edshield.deidentify()` returned:
    it needs `.deidentified_text`, `.entities` (objects with start, end,
    label, text) and, optionally, `.replacements` and `.leaks`."""
    output = result.deidentified_text
    entities = list(result.entities)
    replacements = getattr(result, "replacements", None) or {}
    out_norm, out_map = normalize(output)

    regions = _acted_regions(text, entities, replacements)
    removed = [(s, t) for s, t, original, rendered in regions if rendered != original]

    identifiers: List[IdentifierOutcome] = []
    for i, (s, t, label) in enumerate(gold_spans):
        gold_text = text[s:t]
        hit = find_residual(gold_text, out_norm)
        found = hit is not None
        at = (out_map[hit[0]], out_map[hit[1] - 1] + 1) if found else None
        touched = sorted({e.label for e in entities if int(e.start) < t and s < int(e.end)})
        identifiers.append(IdentifierOutcome(
            index=i, label=label, text=gold_text, start=s, end=t, full_residual=found, residual_at=at,
            partial=None if found else partial_residual(gold_text, out_norm), touched=touched,
        ))

    # A region rendered unchanged (method `keep`) is untouched text for alignment purposes.
    segments = _align(text, output, [r for r in regions if r[3] != r[2]])
    aligned = segments is not None

    def present_at_aligned(ws: int, we: int) -> bool:
        if not aligned:
            return not any(ws < rt and rs < we for rs, rt in removed)
        for os_, oe, out_start in segments:
            if os_ <= ws and we <= oe:
                pos = out_start + (ws - os_)
                return output[pos:pos + (we - ws)] == text[ws:we]
        return False  # the token crosses into a replaced region

    words: List[WordOutcome] = []
    over: List[dict] = []
    for j, m in enumerate(_TOKEN_RE.finditer(text)):
        ws, we = m.start(), m.end()
        y_true = int(any(ws < ge and gs < we for gs, ge, _ in gold_spans))
        in_removed = any(ws < rt and rs < we for rs, rt in removed)
        y_pred = 1 if in_removed or not present_at_aligned(ws, we) else 0
        words.append(WordOutcome(j, ws, we, m.group(), y_true, y_pred))
        if y_pred == 1 and y_true == 0 and len(over) < sample_over_redactions:
            over.append({
                "doc_id": doc_id, "token": m.group(), "start": ws, "end": we,
                "context": text[max(0, ws - CONTEXT_CHARS):min(len(text), we + CONTEXT_CHARS)],
                "labels": sorted({e.label for e in entities if int(e.start) < we and ws < int(e.end)}),
            })

    return DocScore(
        doc_id=doc_id, identifiers=identifiers, words=words, over_redactions=over,
        aligned=aligned, n_acted=len(regions), self_reported_leaks=len(getattr(result, "leaks", []) or []),
    )
