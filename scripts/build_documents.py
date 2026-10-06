"""Build Word versions of the Markdown submission documents using only stdlib."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def paragraph_xml(text: str, style: str = "Normal") -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    preserve = ' xml:space="preserve"' if text.startswith(" ") or text.endswith(" ") else ""
    run = f'<w:r><w:t{preserve}>{escape(text)}</w:t></w:r>'
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>{run}</w:p>'


def convert_markdown(markdown: str) -> str:
    paragraphs = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# "):
            paragraphs.append(paragraph_xml(line[2:], "Title"))
        elif line.startswith("## "):
            paragraphs.append(paragraph_xml(line[3:], "Heading1"))
        elif line.startswith("### "):
            paragraphs.append(paragraph_xml(line[4:], "Heading2"))
        elif line.startswith("> "):
            paragraphs.append(paragraph_xml(line[2:], "Quote"))
        elif line.startswith("- "):
            paragraphs.append(paragraph_xml("•  " + line[2:], "ListParagraph"))
        else:
            paragraphs.append(paragraph_xml(line))
    return "".join(paragraphs)


def create_docx(markdown_path: Path, output_path: Path, title: str) -> None:
    body = convert_markdown(markdown_path.read_text(encoding="utf-8"))
    document = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>{body}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="720" w:right="800" w:bottom="720" w:left="800" w:header="360" w:footer="360" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="21"/><w:color w:val="33443A"/></w:rPr></w:rPrDefault>
  <w:pPrDefault><w:pPr><w:spacing w:after="90" w:line="270" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:spacing w:before="0" w:after="160"/></w:pPr><w:rPr><w:b/><w:sz w:val="36"/><w:color w:val="285B3C"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="220" w:after="80"/></w:pPr><w:rPr><w:b/><w:sz w:val="27"/><w:color w:val="285B3C"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="150" w:after="50"/></w:pPr><w:rPr><w:b/><w:sz w:val="23"/><w:color w:val="45584A"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="360"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="240"/></w:pPr><w:rPr><w:i/><w:color w:val="66756B"/></w:rPr></w:style>
</w:styles>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>'''
    document_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
 <dc:title>{escape(title)}</dc:title><dc:creator>Candidate</dc:creator>
</cp:coreProperties>'''
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/styles.xml", styles)
        archive.writestr("word/_rels/document.xml.rels", document_rels)
        archive.writestr("docProps/core.xml", core)


if __name__ == "__main__":
    create_docx(
        DOCS / "written-responses.md",
        DOCS / "written-responses.docx",
        "Datastraw Hiring Assignment — Written Responses",
    )
    create_docx(
        DOCS / "architecture.md",
        DOCS / "architecture.docx",
        "Datastraw CX Reply Platform — Architecture",
    )
    print("Built docs/written-responses.docx and docs/architecture.docx")
