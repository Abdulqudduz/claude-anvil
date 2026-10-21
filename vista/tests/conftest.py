"""Shared fixtures. Every test runs against a temporary data dir, offline."""

from __future__ import annotations

import pymupdf
import pytest

from vista import config


@pytest.fixture(autouse=True)
def tmp_data_dir(tmp_path, monkeypatch):
    """Point every config path at a per-test directory, never the user's catalog."""
    data = tmp_path / "data"
    monkeypatch.setattr(config, "DATA_DIR", data)
    monkeypatch.setattr(config, "PDF_DIR", data / "pdfs")
    monkeypatch.setattr(config, "DB_PATH", data / "papers.db")
    monkeypatch.setattr(config, "OUT_DIR", tmp_path / "out")
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return data


def make_pdf(pages: list[list[tuple[str, float, bool]]], toc: list | None = None) -> bytes:
    """Build a PDF in memory. Each page is a list of (text, fontsize, bold) lines.

    `toc` is passed to `set_toc` ([[level, title, page], ...]) to give the PDF
    an outline; omit it for an outline-free PDF.
    """
    doc = pymupdf.open()
    for lines in pages:
        page = doc.new_page()
        y = 72.0
        for text, size, bold in lines:
            page.insert_text((72, y), text, fontsize=size, fontname="hebo" if bold else "helv")
            y += size * 1.6
    if toc:
        doc.set_toc(toc)
    data = doc.tobytes()
    doc.close()
    return data


BODY = 10.0


def paper_pages(*, heading_size: float = 14.0, heading_bold: bool = True):
    """A two-page paper: Introduction, Method, Conclusion, Limitations, References."""
    h = lambda t: (t, heading_size, heading_bold)
    b = lambda t: (t, BODY, False)
    return [
        [h("1 Introduction"), b("We introduce a method for things."),
         b("It is quite good at things."), h("2 Method"), b("The method does things.")],
        [h("5 Conclusions and Limitations"), b("We conclude that things work."),
         b("Our approach scales poorly to long inputs."),
         h("6 Future Work"), b("Extending the method to video is open."),
         b("Theory for the non-convex case remains open."),
         h("References"), b("[1] Someone. A paper. 2020.")],
    ]


PAPER_TOC = [
    [1, "1 Introduction", 1],
    [1, "2 Method", 1],
    [1, "5 Conclusions and Limitations", 2],
    [1, "6 Future Work", 2],
    [1, "References", 2],
]
