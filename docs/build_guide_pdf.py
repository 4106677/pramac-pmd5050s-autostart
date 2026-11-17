#!/usr/bin/env python3
"""Owner guide PDF: one A4 page per language (RU, UA, EN) from docs/owner-guide-{ru,uk,en}.md,
with the Wi-Fi name / password / page address in a box at the top of each page.

usage: python3 docs/build_guide_pdf.py <setup network password> [out.pdf]
needs: pip install "reportlab<4.3"; Arial from macOS (/System/Library/Fonts/Supplemental).
The PDF contains the password, so it is gitignored: never commit it (the repository is public).
"""
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

DOCS = Path(__file__).resolve().parent
ap_pw = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else str(DOCS / "owner-guide.pdf")

LANG = {  # file suffix -> page texts
    "ru": dict(sub="Блок автозапуска на ESP32 для генератора Pramac PMD5050S", net="Сеть Wi-Fi блока", pw="Пароль",
               page="Страница дома", foot="Автозапуск генератора Pramac · инструкция владельца",
               sticker=("пароль — на наклейке блока", "пароль — в рамке вверху и на наклейке блока")),
    "uk": dict(sub="Блок автозапуску на ESP32 для генератора Pramac PMD5050S", net="Мережа Wi-Fi блока", pw="Пароль",
               page="Сторінка вдома", foot="Автозапуск генератора Pramac · інструкція власника",
               sticker=("пароль — на наклейці блока", "пароль — у рамці вгорі та на наклейці блока")),
    "en": dict(sub="ESP32 autostart unit for the Pramac PMD5050S generator", net="Unit's Wi-Fi network",
               pw="Password", page="Page at home", foot="Pramac generator autostart · owner's guide",
               sticker=("the password is on the unit's label", "the password is in the box above and on the unit's label")),
}

F = "/System/Library/Fonts/Supplemental/"
pdfmetrics.registerFont(TTFont("Arial", F + "Arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", F + "Arial Bold.ttf"))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial", boldItalic="Arial-Bold")

INK, ACCENT, MUTED, PANEL = (colors.HexColor(c) for c in ("#1d2329", "#1f6f43", "#5b6670", "#eef5f0"))
body = ParagraphStyle("body", fontName="Arial", fontSize=9.8, leading=13, textColor=INK)
title = ParagraphStyle("title", parent=body, fontName="Arial-Bold", fontSize=18, leading=22, spaceAfter=2)
sub = ParagraphStyle("sub", parent=body, textColor=MUTED, fontSize=10.5, spaceAfter=10)
h2 = ParagraphStyle("h2", parent=body, fontName="Arial-Bold", fontSize=12.5, leading=16, textColor=ACCENT,
                    spaceBefore=7, spaceAfter=3)
box_k = ParagraphStyle("bk", parent=body, textColor=MUTED, fontSize=9.5, leading=12)
box_v = ParagraphStyle("bv", parent=body, fontName="Arial-Bold", fontSize=15, leading=19)


def inline(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return re.sub(r"`(.+?)`", r"<b>\1</b>", t)


def bullets(items, ordered):
    return ListFlowable([ListItem(Paragraph(inline(i), body), leftIndent=14) for i in items],
                        bulletType="1" if ordered else "bullet", start="1" if ordered else None,
                        bulletFontName="Arial-Bold" if ordered else "Arial", bulletFontSize=10.5,
                        bulletColor=ACCENT, leftIndent=16, spaceAfter=4)


def wifi_box(L):
    cell = lambda k, v: [Paragraph(k, box_k), Paragraph(v, box_v)]
    t = Table([[cell(L["net"], "Generator-Pramac"), cell(L["pw"], ap_pw), cell(L["page"], "generator.local")]],
              colWidths=[62 * mm, 50 * mm, 58 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PANEL), ("BOX", (0, 0), (-1, -1), 0.8, ACCENT),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 7),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 9)]))
    return t


def language_story(code):
    L = LANG[code]
    raw = (DOCS / f"owner-guide-{code}.md").read_text(encoding="utf-8")
    assert L["sticker"][0] in raw, (code, "sticker phrase not found")
    raw = raw.replace(*L["sticker"])
    plain = lambda x: x.strip() and not re.match(r"^(#|- |\d+\. |  )", x)
    lines = []
    for ln in raw.splitlines():  # wrapped lines of one paragraph -> one line
        if lines and plain(ln) and plain(lines[-1]):
            lines[-1] += " " + ln.strip()
        else:
            lines.append(ln)
    story, section, items, ordered = [], [], [], False

    def flush_list():
        nonlocal items
        if items:
            section.append(bullets(items, ordered))
            items = []

    def flush_section():
        nonlocal section
        flush_list()
        if section:
            story.append(KeepTogether(section[:2]) if len(section) > 1 else section[0])
            story.extend(section[2:])
        section = []

    for ln in lines:
        if ln.startswith("# "):
            story += [Paragraph(inline(ln[2:]), title), Paragraph(L["sub"], sub), wifi_box(L), Spacer(1, 4)]
        elif ln.startswith("## "):
            flush_section()
            section.append(Paragraph(inline(ln[3:]), h2))
        elif re.match(r"^\d+\. ", ln):
            if items and not ordered:
                flush_list()
            ordered = True
            items.append(re.sub(r"^\d+\. ", "", ln))
        elif ln.startswith("- "):
            if items and ordered:
                flush_list()
            ordered = False
            items.append(ln[2:])
        elif ln.startswith("  ") and items:
            items[-1] += " " + ln.strip()
        elif ln.strip():
            flush_list()
            section.append(Paragraph(inline(ln), body))
        else:
            flush_list()
    flush_section()
    return story


ORDER = ["ru", "uk", "en"]
story = []
for i, code in enumerate(ORDER):
    if i:
        story.append(PageBreak())
    story += language_story(code)


def footer(c, d):
    code = ORDER[min(d.page, len(ORDER)) - 1]
    c.saveState()
    c.setFont("Arial", 8.5)
    c.setFillColor(MUTED)
    c.drawString(18 * mm, 10 * mm, LANG[code]["foot"])
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, {"ru": "RU", "uk": "UA", "en": "EN"}[code] + f" · {d.page}/{len(ORDER)}")
    c.restoreState()


doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=13 * mm,
                        bottomMargin=15 * mm, title="Pramac generator autostart — owner's guide (RU / UA / EN)",
                        author="", subject="Owner's guide")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("wrote", out, "pages:", doc.page)
assert doc.page == len(ORDER), "a language does not fit on one page"
