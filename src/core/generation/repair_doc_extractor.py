"""
Repair document extractor: two-pass extraction of repair-specific OKH fields.

Pass 1 (programmatic, always runs, works offline):
  - PDF / text parsing via FileContentParser
  - Heuristics for document type, components, diagnostic codes,
    tools, safety prerequisites, author, and applicable model variants.

Pass 2 (LLM, optional — requires a configured LLMService):
  - Validates and enriches the programmatic results.
  - Extracts from unstructured prose that regex cannot reach.
  - Infers skill_level, estimated_time_minutes, and applies_to_models from context.
  - Cross-checks part numbers (filters false positives like page numbers).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models.okh import Component, DocumentationType, RepairGuide

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Section-header keyword sets (lowercase)
# ---------------------------------------------------------------------------

_FAULT_CODE_HEADERS = {
    "error code",
    "fault code",
    "alarm code",
    "trouble code",
    "indicator guide",
    "error message",
    "error condition",
    "diagnostic",
    "system controller indicator",
    "troubleshooting guide",
    "warning code",
    "status code",
}

_PARTS_HEADERS = {
    "parts list",
    "parts catalog",
    "bill of materials",
    "bom",
    "replacement parts",
    "spare parts",
    "pos.no",
    "part.no",
    "part no",
    "item no",
    "item number",
    "part number",
    "component list",
    "service parts",
    "recommended spare",
    "field-replaceable",
}

_TOOLS_HEADERS = {
    "tools required",
    "tools needed",
    "tools:",  # iFixit PDF style
    "tools",  # iFixit sometimes omits the colon
    "equipment required",
    "tools and materials",
    "what you need",
    "what you'll need",  # iFixit web style
    "materials required",
    "required tools",
    "you will need",
    "required equipment",
}

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Explicit part-number callouts (P/N, Part No., etc.)
# \b after the abbreviation prevents matching inside words like "pneumatic"
_PN_EXPLICIT = re.compile(
    r"(?i)(?:p/?n|part\s+(?:no\.?|number|#))\b\s*:?\s*([A-Z0-9][A-Z0-9\-/\.]{2,25})",
)

# Words that look like P/Ns but are actually column headers or common nouns
_PN_BLACKLIST = {
    "description",
    "qty",
    "quantity",
    "ref",
    "reference",
    "notes",
    "unit",
    "price",
    "no",
    "yes",
    "na",
    "tbd",
    "see",
    "above",
    "below",
}

# Parts-table rows: optional position number + part-number-like token + description.
# Single-space separation (\s+) handles Frigidaire-style compact tables as well as
# wider-spaced formats.
_TABLE_ROW = re.compile(r"^\s*(?:\d+\s+)?([A-Z0-9][A-Z0-9\-/\.]{2,20})\s+(.{5,80})\s*$")

# Diagnostic/error codes
_DIAG_WORD = re.compile(r"(?<!\w)([A-Z]{2,8}(?:ERR|ALM|FLT|WARN|FAULT))(?!\w)")
_DIAG_BANG = re.compile(r"!([A-Z]{2,8})\b")
_DIAG_APPLIANCE = re.compile(r"\b([FEP]\d{1,2}[A-Z]?)\b")

# iFixit / technician author attribution
_AUTHOR = re.compile(
    r"(?i)(?:written\s+by|author|prepared\s+by|service\s+technician|technician)\s*:?\s*([A-Z][a-zA-Z\s\.]{2,40}?)(?:\s*\n|\s*$)",
)

# Model applicability
_APPLIES_TO = re.compile(
    r"(?i)(?:applies\s+to|compatible\s+with|for\s+use\s+with|models?)\s*:?\s*([A-Z0-9][A-Z0-9,\s/\-&\.]{2,120}?)(?:\n|$)",
)

# Safety prerequisites at start of procedure
_SAFETY_PREREQ_LINE = re.compile(
    r"(?i)(?:^|\n)\s*(?:WARNING|CAUTION|DANGER|IMPORTANT)\s*:?\s*(.{10,200}?)(?:\n|$)",
    re.MULTILINE,
)
_UNPLUG_LINE = re.compile(
    r"(?i)\b(?:unplug|disconnect\s+power|power\s+off|de-energize|shut\s+off|turn\s+off|switch\s+off)\b.{0,80}",
)
_NEVER_LINE = re.compile(r"(?i)\bnever\b.{5,120}", re.MULTILINE)

# List items
_LIST_ITEM = re.compile(r"^\s*[-*•·]\s*(.+)$", re.MULTILINE)
# Require at least one space after the delimiter so "13.25mm" isn't mistaken for "13. 25mm"
_NUMBERED_ITEM = re.compile(r"^\s*\d+[.)]\s+(.+)$", re.MULTILINE)

# Document-type classification keywords
_DOCTYPE_KEYWORDS: Dict[DocumentationType, List[str]] = {
    DocumentationType.TROUBLESHOOTING_GUIDE: [
        "troubleshoot",
        "fault code",
        "error code",
        "alarm",
        "diagnostic",
        "problem",
        "corrective action",
        "symptom",
    ],
    DocumentationType.PARTS_CATALOG: [
        "parts catalog",
        "parts list",
        "pos.no",
        "pos. no",
        "part.no",
        "part no",
        "part number",
        "exploded",
        "bill of materials",
        "spare parts",
    ],
    DocumentationType.SERVICE_MANUAL: [
        "service manual",
        "technical manual",
        "calibration",
        "maintenance schedule",
        "preventive maintenance",
        "field service",
        "periodic inspection",
    ],
    DocumentationType.OPERATIONS_MANUAL: [
        "operations manual",
        "operator manual",
        "user manual",
        "operating instructions",
        "operator guide",
        "user guide",
    ],
    DocumentationType.DISASSEMBLY_GUIDE: [
        "disassembly",
        "teardown",
        "removal",
        "reassembly",
        "take apart",
    ],
}

_DOCTYPE_FILENAME: Dict[str, DocumentationType] = {
    "troubleshoot": DocumentationType.TROUBLESHOOTING_GUIDE,
    "parts": DocumentationType.PARTS_CATALOG,
    "catalog": DocumentationType.PARTS_CATALOG,
    "service": DocumentationType.SERVICE_MANUAL,
    "technical": DocumentationType.SERVICE_MANUAL,
    "operations": DocumentationType.OPERATIONS_MANUAL,
    "operator": DocumentationType.OPERATIONS_MANUAL,
    "user": DocumentationType.OPERATIONS_MANUAL,
    "disassembly": DocumentationType.DISASSEMBLY_GUIDE,
    "teardown": DocumentationType.DISASSEMBLY_GUIDE,
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class RepairExtractionResult:
    """Structured output from the repair document extractor."""

    components: List[Component] = field(default_factory=list)
    repair_guides: List[RepairGuide] = field(default_factory=list)
    documentation_type: Optional[DocumentationType] = None
    source_files: List[str] = field(default_factory=list)
    llm_enhanced: bool = False
    notes: List[str] = field(default_factory=list)

    def to_patch(self) -> Dict[str, Any]:
        """Returns a dict suitable for merging into an OKHManifest."""
        patch: Dict[str, Any] = {}
        if self.components:
            patch["components"] = [c.to_dict() for c in self.components]
        if self.repair_guides:
            patch["repair_guides"] = [g.to_dict() for g in self.repair_guides]
        if self.documentation_type:
            patch["documentation_type"] = self.documentation_type.value
        return patch


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


class RepairDocExtractor:
    """
    Two-pass extractor for repair documents.

    Usage (offline / programmatic only):
        extractor = RepairDocExtractor()
        result = extractor.extract([Path("fresenius-2008h-troubleshooting.pdf")])

    Usage (with optional LLM enhancement):
        result = await extractor.extract_with_llm(
            [Path("fresenius-2008h-troubleshooting.pdf")],
            llm_service=service,
        )
    """

    # Ignore tokens that are clearly position indices, short codes, or section refs:
    # - \d{1,4}[A-Z]? : page/position numbers (18A, 5B, 99)
    # - [A-Z]{1,2}\d? : very short letter codes (AC, B1)
    # - \d+(?:\.\d+)+[A-Z]? : section numbers (1.0, 2.4.2, 2.1A)
    _PN_IGNORE = re.compile(r"^(?:\d{1,4}[A-Z]?|[A-Z]{1,2}\d?|\d+(?:\.\d+)+[A-Z]?)$")

    def extract(self, file_paths: List[Path]) -> RepairExtractionResult:
        """Programmatic extraction. Works offline, no LLM required."""
        result = RepairExtractionResult(source_files=[p.name for p in file_paths])

        for path in file_paths:
            try:
                text = self._extract_text(path)
            except Exception as exc:
                result.notes.append(f"Could not read {path.name}: {exc}")
                continue

            if not text:
                result.notes.append(f"No text extracted from {path.name}")
                continue

            # Document type (first file wins if unresolved)
            if result.documentation_type is None:
                result.documentation_type = self._classify_doc_type(text, path.name)

            # Components from parts tables
            components = self._extract_components(text)
            result.components.extend(components)

            # A guide synthesised from this document's tools/safety/author
            guide = self._build_repair_guide(text, path.name, result.documentation_type)
            if guide:
                result.repair_guides.append(guide)

        # Deduplicate components by name (last wins so later files can override)
        seen: Dict[str, Component] = {}
        for c in result.components:
            seen[c.name.lower()] = c
        result.components = list(seen.values())

        return result

    async def extract_with_llm(
        self,
        file_paths: List[Path],
        llm_service: Any,
    ) -> RepairExtractionResult:
        """
        Programmatic pass followed by optional LLM enrichment.

        ``llm_service`` should be an initialised LLMService instance.
        If it is None (or raises on generation), the programmatic result
        is returned unchanged and a note is appended.
        """
        result = self.extract(file_paths)

        if llm_service is None:
            result.notes.append("LLM service not provided; skipping enhancement pass.")
            return result

        # Collect raw texts for the LLM
        texts: Dict[str, str] = {}
        for path in file_paths:
            try:
                text = self._extract_text(path)
                if text:
                    texts[path.name] = text
            except Exception:
                pass

        if not texts:
            result.notes.append("No text available for LLM pass.")
            return result

        try:
            result = await self._llm_enhance(result, texts, llm_service)
            result.llm_enhanced = True
        except Exception as exc:
            result.notes.append(
                f"LLM enhancement failed; using programmatic results: {exc}"
            )

        return result

    # ------------------------------------------------------------------
    # Private: text extraction
    # ------------------------------------------------------------------

    def _extract_text(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        raw = (
            self._extract_pdf(file_path)
            if suffix == ".pdf"
            else file_path.read_text(errors="replace")
        )
        return self._normalise_whitespace(raw)

    def _extract_pdf(self, file_path: Path) -> str:
        from .utils.file_content_parser import FileContentParser

        parser = FileContentParser()
        text = parser._extract_pdf_text(file_path)
        return text or ""

    @staticmethod
    def _normalise_whitespace(text: str) -> str:
        """Replace tabs with spaces and collapse runs of 3+ spaces to two."""
        text = text.replace("\t", " ")
        text = re.sub(r" {3,}", "  ", text)
        return text

    # ------------------------------------------------------------------
    # Private: document type
    # ------------------------------------------------------------------

    def _classify_doc_type(
        self, text: str, filename: str
    ) -> Optional[DocumentationType]:
        # Filename gives the strongest signal
        name_lower = filename.lower()
        for kw, dtype in _DOCTYPE_FILENAME.items():
            if kw in name_lower:
                return dtype

        # Content scoring
        text_lower = text.lower()
        scores: Dict[DocumentationType, int] = {}
        for dtype, keywords in _DOCTYPE_KEYWORDS.items():
            scores[dtype] = sum(text_lower.count(kw) for kw in keywords)

        best = max(scores, key=lambda d: scores[d])
        if scores[best] > 0:
            return best
        return None

    # ------------------------------------------------------------------
    # Private: component extraction
    # ------------------------------------------------------------------

    def _extract_components(self, text: str) -> List[Component]:
        components: List[Component] = []

        # Step 1: find all sections that look like parts tables
        parts_sections = self._extract_section_texts(text, _PARTS_HEADERS)

        # Step 2: extract diagnostic-code context for later mapping
        diag_pairs = self._extract_diagnostic_codes_with_context(text)

        # Step 3: parse parts from table sections
        for section_text in parts_sections:
            components.extend(self._parse_parts_section(section_text, diag_pairs))

        # Step 4: pick up explicit P/N callouts outside tables
        table_pns = {c.part_number for c in components if c.part_number}
        for match in _PN_EXPLICIT.finditer(text):
            pn = match.group(1).strip().rstrip(".:,;")
            if pn in table_pns or self._PN_IGNORE.match(pn):
                continue
            if pn.lower() in _PN_BLACKLIST:
                continue

            # Look for a description on the same line, after the P/N
            line_end = text.find("\n", match.end())
            after = text[
                match.end() : line_end if line_end != -1 else match.end() + 80
            ].strip()
            # Strip trailing dotleaders ("............ 5-3") and trailing punctuation
            after = re.sub(r"\.{3,}.*$", "", after).strip()
            after = after.rstrip(")].,:;")

            if 3 < len(after) < 70 and after.lower() not in _PN_BLACKLIST:
                name = after
            else:
                # Fall back to the P/N itself — still useful for the LLM pass
                name = pn

            components.append(Component(name=name, part_number=pn, replaceable=True))
            table_pns.add(pn)

        return components

    def _parse_parts_section(
        self,
        section_text: str,
        diag_pairs: List[Tuple[str, str]],
    ) -> List[Component]:
        """Parse components from a section identified as a parts table."""
        components: List[Component] = []
        diag_map = self._build_diag_map(diag_pairs)

        for line in section_text.splitlines():
            m = _TABLE_ROW.match(line)
            if not m:
                continue
            token, description = m.group(1), m.group(2).strip()

            # Skip header-like rows (strip trailing punctuation before comparing)
            if token.rstrip(".:,;").lower() in {
                "pos",
                "item",
                "part",
                "ref",
                "qty",
                "no",
                "description",
            }:
                continue
            if self._PN_IGNORE.match(token):
                continue
            # Skip tokens that don't look like part numbers (e.g. "RECEIVING", "CHECK")
            if not self._looks_like_pn(token):
                continue

            name = description[:80]
            # Accept as P/N if it contains a letter, or is a long numeric string
            # (manufacturer codes like 316571702) but not short position indices.
            pn = (
                token
                if (re.search(r"[A-Z]", token) or (token.isdigit() and len(token) >= 5))
                else None
            )

            codes = diag_map.get(name.lower(), [])
            consumable = self._is_consumable(name)
            component = Component(
                name=name,
                part_number=pn,
                replaceable=True,
                consumable=consumable,
                diagnostic_codes=codes,
            )
            components.append(component)

        return components

    @staticmethod
    def _looks_like_pn(token: str) -> bool:
        """Return True only if the token plausibly looks like a part number."""
        has_digit = bool(re.search(r"\d", token))
        has_sep = bool(re.search(r"[-/.]", token))
        # Long digit string (e.g. manufacturer catalogue number 316571702)
        if token.isdigit():
            return len(token) >= 5
        # Reject US phone numbers like "800-227-2572"
        if re.match(r"^\d{3}-\d{3}-\d{4}$", token):
            return False
        if "/" in token:
            segs = token.split("/")
            # Reject "QUARTERLY/1000", "P/N", "A/C" — first segment is all letters
            if segs[0].isalpha():
                return False
            # Reject voltage/frequency specs "100/120/220/240V", "50/60Hz":
            # all segments numeric after stripping trailing letters
            stripped = [re.sub(r"[A-Za-z]+$", "", s) for s in segs]
            if all(s.isdigit() and s for s in stripped):
                return False
        # Must contain at least one digit; separators alone aren't sufficient
        # (filters "U.S.", "SPECIFICATIONS." etc.)
        return has_digit

    def _is_consumable(self, name: str) -> bool:
        """Heuristically identify consumable components."""
        consumable_hints = {
            "filter",
            "catalyst",
            "seal",
            "gasket",
            "o-ring",
            "bulb",
            "lamp",
            "battery",
            "belt",
            "pad",
            "brush",
            "cartridge",
            "fuse",
        }
        name_lower = name.lower()
        return any(h in name_lower for h in consumable_hints)

    # ------------------------------------------------------------------
    # Private: diagnostic codes
    # ------------------------------------------------------------------

    def _extract_diagnostic_codes_with_context(
        self, text: str
    ) -> List[Tuple[str, str]]:
        """
        Returns (code, surrounding_context) pairs extracted from fault-code
        sections and inline error-code patterns.
        """
        pairs: List[Tuple[str, str]] = []

        # Prioritise dedicated fault-code sections
        fault_sections = self._extract_section_texts(text, _FAULT_CODE_HEADERS)
        search_text = "\n".join(fault_sections) if fault_sections else text

        for pattern in (_DIAG_WORD, _DIAG_BANG, _DIAG_APPLIANCE):
            for m in pattern.finditer(search_text):
                code = m.group(1)
                start = max(0, m.start() - 80)
                ctx = search_text[start : m.end() + 80].replace("\n", " ").strip()
                pairs.append((code, ctx))

        return pairs

    def _build_diag_map(
        self, diag_pairs: List[Tuple[str, str]]
    ) -> Dict[str, List[str]]:
        """Map component name keywords → list of diagnostic codes."""
        code_map: Dict[str, List[str]] = {}
        for code, ctx in diag_pairs:
            ctx_lower = ctx.lower()
            for word in ctx_lower.split():
                word = word.strip(".,;:()")
                if len(word) > 3 and not word.isupper():
                    if word not in code_map:
                        code_map[word] = []
                    if code not in code_map[word]:
                        code_map[word].append(code)
        return code_map

    # ------------------------------------------------------------------
    # Private: tools
    # ------------------------------------------------------------------

    def _extract_tools(self, text: str) -> List[str]:
        tools: List[str] = []
        sections = self._extract_section_texts(text, _TOOLS_HEADERS, max_lines=30)
        for section in sections:
            found: List[str] = []
            for m in _LIST_ITEM.finditer(section):
                tool = m.group(1).strip()
                if 3 < len(tool) < 80:
                    found.append(tool)
            for m in _NUMBERED_ITEM.finditer(section):
                tool = m.group(1).strip()
                if 3 < len(tool) < 80:
                    found.append(tool)
            # Fallback for iFixit-style plain-line lists (no bullet markers).
            # Stop at the first step marker so guide steps aren't collected.
            if not found:
                for line in section.splitlines():
                    line = line.strip()
                    # Hard stop: iFixit step headers and dash-prefixed instructions
                    if re.match(r"^(?:step\s+\d|—\s*\w)", line, re.IGNORECASE):
                        break
                    # Skip quantity markers, bare numbers, and NOTE/WARNING lines
                    if re.match(r"^\(\d+\)$", line):
                        continue
                    if re.match(
                        r"^(?:note|warning|caution|danger|important)\s*:",
                        line,
                        re.IGNORECASE,
                    ):
                        continue
                    if not re.search(r"[A-Za-z]", line):
                        continue
                    if 5 < len(line) < 80:
                        found.append(line)
            tools.extend(found)
        return list(dict.fromkeys(tools))  # deduplicate, preserve order

    # ------------------------------------------------------------------
    # Private: safety prerequisites
    # ------------------------------------------------------------------

    def _extract_safety_prereqs(self, text: str) -> List[str]:
        prereqs: List[str] = []

        # Explicit WARNING/CAUTION/DANGER blocks
        for m in _SAFETY_PREREQ_LINE.finditer(text):
            stmt = m.group(1).strip().rstrip(".")
            if 10 < len(stmt) < 200:
                prereqs.append(stmt)

        # "Never …" statements (strong prohibitions)
        for m in _NEVER_LINE.finditer(text[:3000]):  # usually near document start
            stmt = m.group(0).strip().rstrip(".")
            if 10 < len(stmt) < 160:
                prereqs.append(stmt)

        # "Unplug / disconnect power" lines
        for m in _UNPLUG_LINE.finditer(text[:5000]):
            stmt = m.group(0).strip().rstrip(".")
            if 10 < len(stmt) < 160:
                prereqs.append(stmt)

        # Deduplicate (exact match)
        seen: set = set()
        unique: List[str] = []
        for p in prereqs:
            key = p.lower()
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique[:10]  # cap at 10 hard gates

    # ------------------------------------------------------------------
    # Private: author
    # ------------------------------------------------------------------

    def _extract_author(self, text: str) -> Optional[str]:
        m = _AUTHOR.search(text[:3000])
        if m:
            # Collapse tabs/runs of spaces left by PDF extraction
            author = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(".,")
            if 3 < len(author) < 60:
                return author
        return None

    # ------------------------------------------------------------------
    # Private: applies-to models
    # ------------------------------------------------------------------

    def _extract_applies_to_models(self, text: str) -> List[str]:
        models: List[str] = []
        for m in _APPLIES_TO.finditer(text[:5000]):
            raw = m.group(1).strip()
            # Split on commas, slashes, "and", "or"
            parts = re.split(r"[,/]|\band\b|\bor\b", raw, flags=re.IGNORECASE)
            for part in parts:
                model = part.strip().rstrip(".")
                if 1 < len(model) < 50:
                    models.append(model)
        return list(dict.fromkeys(models))[:10]

    # ------------------------------------------------------------------
    # Private: build repair guide from a single document
    # ------------------------------------------------------------------

    def _build_repair_guide(
        self,
        text: str,
        filename: str,
        doc_type: Optional[DocumentationType],
    ) -> Optional[RepairGuide]:
        """
        Build a RepairGuide from a document only when it contains actionable
        repair/maintenance content (i.e. tools or safety prerequisites).
        Pure parts catalogs are skipped.
        """
        if doc_type == DocumentationType.PARTS_CATALOG:
            return None

        tools = self._extract_tools(text)
        safety = self._extract_safety_prereqs(text)
        author = self._extract_author(text)
        models = self._extract_applies_to_models(text)

        # Only create a guide if there's meaningful actionable content
        if not tools and not safety:
            return None

        # Title from filename (strip extension and convert underscores)
        stem = Path(filename).stem.replace("_", " ").replace("-", " ").title()
        title = stem[:100]

        return RepairGuide(
            title=title,
            path=filename,
            author=author,
            tools_required=tools,
            safety_prerequisites=safety,
            applies_to_models=models,
            metadata={"source_file": filename},
        )

    # ------------------------------------------------------------------
    # Private: section extraction utility
    # ------------------------------------------------------------------

    def _extract_section_texts(
        self,
        text: str,
        header_keywords: set,
        max_lines: int = 60,
    ) -> List[str]:
        """
        Return sub-strings of ``text`` that follow a line matching any keyword
        in ``header_keywords``, up to ``max_lines`` lines or the next section.
        """
        lines = text.splitlines()
        sections: List[str] = []
        in_section = False
        section_lines: List[str] = []
        line_count = 0

        for line in lines:
            ll = line.lower().strip()
            is_header = any(kw in ll for kw in header_keywords)

            if is_header:
                if in_section and section_lines:
                    sections.append("\n".join(section_lines))
                in_section = True
                section_lines = []
                line_count = 0
                continue

            if in_section:
                section_lines.append(line)
                line_count += 1
                if line_count >= max_lines:
                    sections.append("\n".join(section_lines))
                    in_section = False
                    section_lines = []

        if in_section and section_lines:
            sections.append("\n".join(section_lines))

        return sections

    # ------------------------------------------------------------------
    # Private: LLM enhancement pass
    # ------------------------------------------------------------------

    async def _llm_enhance(
        self,
        result: RepairExtractionResult,
        texts: Dict[str, str],
        llm_service: Any,
    ) -> RepairExtractionResult:
        from ..llm.models.requests import LLMRequestConfig, LLMRequestType
        from ..llm.models.responses import LLMResponseStatus
        from ..services.base import ServiceStatus

        if llm_service.status != ServiceStatus.ACTIVE:
            await llm_service.initialize()

        # Combine text, capped to ~12k chars to stay within a single call budget
        combined = "\n\n---\n\n".join(
            f"[{name}]\n{text[:6000]}" for name, text in texts.items()
        )[:12000]

        existing_components = json.dumps(
            [c.to_dict() for c in result.components], indent=2
        )
        existing_guides = json.dumps(
            [g.to_dict() for g in result.repair_guides], indent=2
        )

        prompt = f"""You are an expert at extracting structured repair information from technical documentation.

## Source documents
{combined}

## Programmatically extracted data (validate and enrich this)

### Components found:
{existing_components}

### Repair guides found:
{existing_guides}

## Task
Validate, correct, and enrich the extracted data. Return a JSON object with:
- `components`: list of component objects (name, part_number, consumable, replaceable,
  failure_modes, diagnostic_codes, repair_notes)
- `repair_guides`: list of guide objects (title, path, author, skill_level,
  estimated_time_minutes, tools_required, safety_prerequisites, applies_to_models)
- `documentation_type`: one of "parts-catalog", "service-manual",
  "troubleshooting-guide", "operations-manual", "disassembly-guide", or null
- `notes`: list of strings describing anything uncertain or notable

Rules:
1. Keep all valid programmatic entries; correct obvious errors.
2. Add components or guides present in the text but missed programmatically.
3. Remove components that are clearly not hardware parts (page numbers, section
   headers, measurement units, etc.).
4. For each diagnostic code, try to map it to its component (diagnostic_codes field).
5. Infer skill_level ("beginner", "intermediate", "expert") and
   estimated_time_minutes where the text gives enough clues.
6. Return only valid JSON — no explanation outside the JSON object.
"""

        config = LLMRequestConfig(max_tokens=4000, temperature=0.1)
        response = await llm_service.generate(
            prompt=prompt,
            request_type=LLMRequestType.ANALYSIS,
            config=config,
        )

        if response.status != LLMResponseStatus.SUCCESS:
            result.notes.append(f"LLM call failed: {response.error_message}")
            return result

        return self._merge_llm_response(result, response.content)

    def _merge_llm_response(
        self, result: RepairExtractionResult, content: str
    ) -> RepairExtractionResult:
        """Parse LLM JSON and merge into result."""
        data = self._parse_json_from_llm(content)
        if data is None:
            result.notes.append(
                "LLM returned unparseable JSON; keeping programmatic results."
            )
            return result

        # Components
        raw_components = data.get("components", [])
        if raw_components:
            result.components = [
                Component(
                    name=c.get("name", ""),
                    part_number=c.get("part_number"),
                    consumable=bool(c.get("consumable", False)),
                    replaceable=bool(c.get("replaceable", True)),
                    failure_modes=c.get("failure_modes", []),
                    diagnostic_codes=c.get("diagnostic_codes", []),
                    repair_notes=c.get("repair_notes"),
                    notes=c.get("notes"),
                )
                for c in raw_components
                if c.get("name")
            ]

        # Repair guides
        raw_guides = data.get("repair_guides", [])
        if raw_guides:
            result.repair_guides = [
                RepairGuide(
                    title=g.get("title", ""),
                    path=g.get("path", ""),
                    author=g.get("author"),
                    skill_level=g.get("skill_level"),
                    estimated_time_minutes=g.get("estimated_time_minutes"),
                    tools_required=g.get("tools_required", []),
                    safety_prerequisites=g.get("safety_prerequisites", []),
                    applies_to_models=g.get("applies_to_models", []),
                    metadata=g.get("metadata", {}),
                )
                for g in raw_guides
                if g.get("title") and g.get("path")
            ]

        # Documentation type
        raw_type = data.get("documentation_type")
        if raw_type:
            try:
                result.documentation_type = DocumentationType(raw_type)
            except ValueError:
                result.notes.append(
                    f"Unknown documentation_type from LLM: {raw_type!r}"
                )

        # Notes
        result.notes.extend(data.get("notes", []))

        return result

    @staticmethod
    def _parse_json_from_llm(content: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON from LLM response, with recovery."""
        # Try markdown code block first
        for marker in ("```json", "```"):
            if marker in content:
                start = content.find(marker) + len(marker)
                end = content.find("```", start)
                if end > start:
                    candidate = content[start:end].strip()
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        pass

        # Fall back to first { … last }
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                # Fix trailing commas and retry
                fixed = re.sub(r",(\s*[}\]])", r"\1", content[start : end + 1])
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

        return None
