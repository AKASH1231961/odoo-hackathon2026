from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm


def generate_invoice_pdf(invoice) -> bytes:
    """
    Generate a professional A4 PDF invoice using ReportLab.
    Includes: header, customer info, line items table, totals, payment instructions.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    elements = []

    # ── Header ──────────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=colors.HexColor("#1e3a8a"),
        spaceAfter=4,
    )
    elements.append(Paragraph("BRIGHTLOOP SOFTWARE", title_style))
    elements.append(Paragraph(f"Invoice #{invoice.invoice_number}", styles["Heading2"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1e3a8a")))
    elements.append(Spacer(1, 8))

    # ── Customer + Invoice Meta ──────────────────────────────────────────────
    customer_name = getattr(invoice.customer, "full_name", None) or getattr(invoice.customer, "email", "N/A")
    meta = [
        ["Bill To:", customer_name, "Invoice #:", invoice.invoice_number],
        ["Email:", invoice.customer.email, "Issue Date:", str(invoice.issued_at.date()) if invoice.issued_at else "—"],
        ["", "", "Due Date:", str(invoice.due_date)],
        ["", "", "Status:", invoice.status.value.upper()],
    ]
    meta_table = Table(meta, colWidths=[35 * mm, 75 * mm, 35 * mm, 40 * mm])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 12))

    # ── Line Items ───────────────────────────────────────────────────────────
    header = ["Description", "Qty", "Unit Price", "Tax", "Discount", "Line Total"]
    rows = [header]
    for line in invoice.lines:
        rows.append([
            line.description or "—",
            str(line.quantity),
            f"{float(line.unit_price):,.2f}",
            f"{float(line.tax_amount):,.2f}",
            f"{float(line.discount):,.2f}",
            f"{float(line.line_total):,.2f}",
        ])

    items_table = Table(rows, colWidths=[65 * mm, 15 * mm, 28 * mm, 22 * mm, 22 * mm, 28 * mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 10))

    # ── Totals ───────────────────────────────────────────────────────────────
    totals = [
        ["Subtotal", f"{float(invoice.subtotal):,.2f}"],
        ["Tax", f"{float(invoice.tax_total):,.2f}"],
        ["Discount", f"- {float(invoice.discount_total):,.2f}"],
        ["Grand Total", f"{float(invoice.grand_total):,.2f}"],
    ]
    totals_table = Table(totals, colWidths=[50 * mm, 30 * mm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.HexColor("#1e3a8a")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 20))

    # ── Payment Instructions ─────────────────────────────────────────────────
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("<b>Payment Instructions</b>", styles["Normal"]))
    elements.append(Paragraph(
        "Please pay via bank transfer, card, or UPI by the due date shown above. "
        "Reference your invoice number in the payment description.",
        styles["Normal"],
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()

