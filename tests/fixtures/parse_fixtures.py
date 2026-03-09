"""In-memory ParsedDocument and SectionUnit fixtures for chunk assembler and serialization tests.

No Docling; used to test chunking policy and serialization in isolation.
"""

from app.domain.parse_models import BlockType, ParsedDocument, SectionUnit


def section_unit(
    section_path: list[str],
    block_type: BlockType,
    text: str,
    *,
    source_spans: dict | None = None,
    page_refs: list | None = None,
) -> SectionUnit:
    return SectionUnit(
        section_path=section_path,
        block_type=block_type,
        text=text,
        source_spans=source_spans or {},
        page_refs=page_refs or [],
    )


def parsed_doc_simple_headings(
    document_id: str = "doc1",
    run_id: str = "run1",
) -> ParsedDocument:
    """Simple doc: title + two sections with heading + paragraphs."""
    return ParsedDocument(
        document_id=document_id,
        run_id=run_id,
        source_format="markdown",
        title="Policy Document",
        sections=[
            section_unit(["Introduction"], BlockType.HEADING, "Introduction"),
            section_unit(["Introduction"], BlockType.PARAGRAPH, "This is the intro paragraph."),
            section_unit(["Introduction"], BlockType.PARAGRAPH, "Second intro sentence."),
            section_unit(["Rules"], BlockType.HEADING, "Rules"),
            section_unit(["Rules"], BlockType.PARAGRAPH, "Rule one: do X."),
            section_unit(["Rules"], BlockType.PARAGRAPH, "Rule two: do Y."),
        ],
        tables=[],
        lists=[],
    )


def parsed_doc_with_table(
    document_id: str = "doc2",
    run_id: str = "run2",
) -> ParsedDocument:
    """Doc with a table and nearby explanatory text."""
    return ParsedDocument(
        document_id=document_id,
        run_id=run_id,
        source_format="markdown",
        title="Report",
        sections=[
            section_unit(["Summary"], BlockType.HEADING, "Summary"),
            section_unit(["Summary"], BlockType.PARAGRAPH, "The table below shows key figures."),
            section_unit(["Summary"], BlockType.TABLE, "| A | B |\n| 1 | 2 |"),
            section_unit(["Summary"], BlockType.PARAGRAPH, "Interpretation: A is primary."),
        ],
        tables=[{"caption": "Key figures", "data": [["A", "B"], ["1", "2"]]}],
        lists=[],
    )


def parsed_doc_large_section(
    document_id: str = "doc3",
    run_id: str = "run3",
) -> ParsedDocument:
    """One big section and a subheading so we can test split-by-subheading."""
    long_para = " ".join(["Word"] * 800)  # ~800 tokens
    return ParsedDocument(
        document_id=document_id,
        run_id=run_id,
        source_format="markdown",
        title="Long Doc",
        sections=[
            section_unit(["Main"], BlockType.HEADING, "Main"),
            section_unit(["Main"], BlockType.PARAGRAPH, long_para),
            section_unit(["Main", "Sub"], BlockType.HEADING, "Sub"),
            section_unit(["Main", "Sub"], BlockType.PARAGRAPH, "Sub content."),
        ],
        tables=[],
        lists=[],
    )


def parsed_doc_conditions_and_action(
    document_id: str = "doc4",
    run_id: str = "run4",
) -> ParsedDocument:
    """Regression: conditions vs action (do not mix in one chunk if they are separate)."""
    return ParsedDocument(
        document_id=document_id,
        run_id=run_id,
        source_format="markdown",
        title="Procedure",
        sections=[
            section_unit(["Conditions"], BlockType.HEADING, "Conditions"),
            section_unit(["Conditions"], BlockType.PARAGRAPH, "If X and Y are true."),
            section_unit(["Action"], BlockType.HEADING, "Action"),
            section_unit(["Action"], BlockType.PARAGRAPH, "Then perform Z."),
        ],
        tables=[],
        lists=[],
    )


def parsed_doc_list_of_rules(
    document_id: str = "doc5",
    run_id: str = "run5",
) -> ParsedDocument:
    """Markdown with list of rules."""
    return ParsedDocument(
        document_id=document_id,
        run_id=run_id,
        source_format="markdown",
        title="Rules",
        sections=[
            section_unit(["Permissions"], BlockType.HEADING, "Permissions"),
            section_unit(
                ["Permissions"],
                BlockType.LIST,
                "- Admin may edit.\n- User may view.",
            ),
            section_unit(["Glossary"], BlockType.HEADING, "Glossary"),
            section_unit(["Glossary"], BlockType.PARAGRAPH, "Terms defined here."),
        ],
        tables=[],
        lists=[],
    )
