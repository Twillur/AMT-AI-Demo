import pandas as pd
from datetime import datetime
from .db_utils import query

TODAY = "2026-05-23"

def _html_wrap(title: str, subtitle: str, body: str, color: str = "#0d1b2a") -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;max-width:700px;margin:0 auto;padding:20px">
  <div style="background:{color};padding:20px 28px;border-radius:8px 8px 0 0">
    <div style="color:#e8b94f;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase">Advanced Media Trading LLC</div>
    <div style="color:#fff;font-size:18px;font-weight:700;margin-top:4px">{title}</div>
    <div style="color:#aaa;font-size:13px;margin-top:2px">{subtitle}</div>
  </div>
  <div style="background:#fff;border:1px solid #e0e0e0;border-top:none;padding:28px;border-radius:0 0 8px 8px">
    {body}
  </div>
  <div style="text-align:center;padding:12px;font-size:11px;color:#aaa">
    Generated automatically by AMT AI &nbsp;|&nbsp; {TODAY}
  </div>
</body></html>"""


def _table(headers: list, rows: list, col_align: list = None) -> str:
    th = "".join(
        f'<th style="padding:10px 14px;text-align:{"right" if col_align and col_align[i]=="right" else "left"};'
        f'font-weight:700;color:#555;border-bottom:2px solid #e8b94f">{h}</th>'
        for i, h in enumerate(headers)
    )
    tr_html = ""
    for row in rows:
        tds = "".join(
            f'<td style="padding:10px 14px;border-bottom:1px solid #f0f0f0;'
            f'text-align:{"right" if col_align and col_align[i]=="right" else "left"}">{v}</td>'
            for i, v in enumerate(row)
        )
        tr_html += f"<tr>{tds}</tr>"
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:28px">'
        f"<thead><tr style='background:#f8f9fa'>{th}</tr></thead>"
        f"<tbody>{tr_html}</tbody></table>"
    )


def _section(title: str, content: str) -> str:
    return (
        f'<div style="margin-bottom:28px">'
        f'<div style="font-size:16px;font-weight:700;color:#0d1b2a;border-left:4px solid #e8b94f;'
        f'padding-left:12px;margin-bottom:14px">{title}</div>'
        f'{content}</div>'
    )


def _badge(text: str, bg: str, fg: str) -> str:
    return f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:700;background:{bg};color:{fg}">{text}</span>'


STATUS_STYLES = {
    "customs":    ("#721c24", "#f8d7da"),
    "delayed":    ("#856404", "#fff3cd"),
    "in_transit": ("#155724", "#d4edda"),
    "ordered":    ("#004085", "#cce5ff"),
    "delivered":  ("#555",    "#eee"),
}


def distribution_briefing_html() -> str:
    # ── Shipments ─────────────────────────────────────────────
    shipments = query("""
        SELECT s.shipment_ref, s.supplier, s.origin_country,
               s.shipped_date, s.eta, s.status, s.carrier, s.tracking_number,
               po.po_ref
        FROM shipments s
        LEFT JOIN purchase_orders po ON po.id = s.order_id
        WHERE s.status != 'delivered'
        ORDER BY CASE s.status WHEN 'customs' THEN 0 WHEN 'delayed' THEN 1 ELSE 2 END, s.eta
    """)

    if shipments:
        rows = []
        for s in shipments:
            fg, bg = STATUS_STYLES.get(s["status"], ("#333", "#eee"))
            badge = _badge(s["status"].replace("_", " ").title(), bg, fg)
            rows.append([s["shipment_ref"], s["supplier"], s["eta"] or "—", badge, s["tracking_number"] or "—"])
        shipment_html = _table(
            ["Shipment", "Supplier", "ETA", "Status", "Tracking"],
            rows, ["left","left","left","left","left"]
        )
        customs_count = sum(1 for s in shipments if s["status"] == "customs")
        if customs_count:
            shipment_html = (
                f'<div style="background:#f8d7da;border-left:4px solid #721c24;padding:12px 16px;'
                f'border-radius:4px;margin-bottom:16px;font-size:14px;color:#721c24">'
                f'<strong>⚠ {customs_count} shipment(s) on customs hold</strong> — immediate follow-up required.</div>'
                + shipment_html
            )
    else:
        shipment_html = '<p style="color:#888;font-size:14px">No active inbound shipments.</p>'

    # ── Low Stock ──────────────────────────────────────────────
    low = query("""
        SELECT p.brand, p.model, p.category,
               i.qty_on_hand, i.qty_reserved,
               (i.qty_on_hand - i.qty_reserved) AS available,
               i.reorder_point
        FROM inventory i JOIN products p ON p.id = i.product_id
        WHERE (i.qty_on_hand - i.qty_reserved) <= i.reorder_point
        ORDER BY available ASC
        LIMIT 10
    """)

    if low:
        rows = []
        for r in low:
            avail = r["available"]
            color = "#721c24" if avail <= 0 else "#856404"
            rows.append([
                f'{r["brand"]} {r["model"]}',
                r["category"],
                f'<span style="color:{color};font-weight:700">{avail}</span>',
                str(r["qty_on_hand"]),
                str(r["reorder_point"]),
            ])
        low_html = _table(["Product","Category","Available","On Hand","Reorder Point"], rows)
    else:
        low_html = '<p style="color:#888;font-size:14px">All stock levels are healthy.</p>'

    body = _section("Inbound Shipments", shipment_html) + _section("Low Stock Alert", low_html)
    return _html_wrap(
        "Daily Distribution Briefing",
        f"Warehouse & Logistics Summary — {TODAY}",
        body
    )


def finance_overdue_html() -> str:
    rows_db = query("""
        SELECT c.name, c.company, c.country,
               i.invoice_ref, i.issue_date, i.due_date,
               i.amount_aed, i.vat_aed, i.status, i.paid_date
        FROM invoices i JOIN customers c ON c.id = i.customer_id
    """)
    df = pd.DataFrame(rows_db)
    df["due_date"]   = pd.to_datetime(df["due_date"])
    df["issue_date"] = pd.to_datetime(df["issue_date"])
    df["total_aed"]  = df["amount_aed"] + df["vat_aed"]
    df["days_overdue"] = (pd.Timestamp(TODAY) - df["due_date"]).dt.days.clip(lower=0)
    df["days_overdue"] = df["days_overdue"].where(df["status"] != "paid", 0)

    # ── KPI strip ─────────────────────────────────────────────
    total_rev  = df["amount_aed"].sum()
    collected  = df[df["status"]=="paid"]["amount_aed"].sum()
    outstanding= df[df["status"].isin(["unpaid","overdue"])]["amount_aed"].sum()
    overdue_amt= df[df["status"]=="overdue"]["amount_aed"].sum()
    rate       = collected / total_rev * 100 if total_rev else 0

    kpis = [
        ("Total Revenue",   f"AED {total_rev:,.0f}",   "#0d1b2a", "#fff"),
        ("Collected",       f"AED {collected:,.0f}",   "#155724", "#fff"),
        ("Outstanding",     f"AED {outstanding:,.0f}", "#856404", "#fff"),
        ("Overdue (urgent)",f"AED {overdue_amt:,.0f}", "#721c24", "#fff"),
        ("Collection Rate", f"{rate:.0f}%",            "#004085", "#fff"),
    ]
    kpi_html = '<div style="display:flex;gap:10px;margin-bottom:28px;flex-wrap:wrap">'
    for label, val, bg, fg in kpis:
        kpi_html += (
            f'<div style="flex:1;min-width:120px;background:{bg};padding:14px;border-radius:6px;text-align:center">'
            f'<div style="color:{fg};font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:1px">{label}</div>'
            f'<div style="color:{fg};font-size:18px;font-weight:700;margin-top:4px">{val}</div></div>'
        )
    kpi_html += '</div>'

    # ── Aging buckets ──────────────────────────────────────────
    unpaid = df[df["status"].isin(["unpaid","overdue"])].copy()
    def bucket(d):
        if d <= 30:  return "0–30 days"
        elif d <= 60: return "31–60 days"
        elif d <= 90: return "61–90 days"
        else:         return "90+ days"
    unpaid["bucket"] = unpaid["days_overdue"].apply(bucket)
    aging = (unpaid.groupby("bucket")
             .agg(invoices=("invoice_ref","count"), amount=("amount_aed","sum"))
             .reindex(["0–30 days","31–60 days","61–90 days","90+ days"]).fillna(0))

    aging_rows = []
    for bkt, row in aging.iterrows():
        color = "#155724" if bkt == "0–30 days" else "#856404" if bkt == "31–60 days" else "#721c24"
        aging_rows.append([
            f'<span style="color:{color};font-weight:700">{bkt}</span>',
            str(int(row["invoices"])),
            f"AED {row['amount']:,.0f}"
        ])
    aging_html = _table(["Aging Bucket","Invoices","Amount"], aging_rows, ["left","left","right"])

    # ── Top debtors ────────────────────────────────────────────
    debtors = (unpaid.groupby(["name","company"])["amount_aed"].sum()
               .sort_values(ascending=False).reset_index().head(5))
    debtor_rows = [[r["name"], r["company"] or "—", f"AED {r['amount_aed']:,.0f}"]
                   for _, r in debtors.iterrows()]
    debtor_html = _table(["Customer","Company","Outstanding"], debtor_rows, ["left","left","right"])

    body = kpi_html + _section("Aging Report", aging_html) + _section("Top 5 Debtors — Action Required", debtor_html)
    return _html_wrap(
        "Daily Finance Report",
        f"Overdue Invoices & Receivables — {TODAY}",
        body,
        color="#1a1a2e"
    )


def ticket_update_html(ticket_ref: str, customer: str, product: str,
                       new_status: str, technician_notes: str) -> tuple:
    status_map = {
        "diagnosed":      ("Diagnosis Complete",    "Our technicians have completed their initial assessment of your device."),
        "in_repair":      ("Repair In Progress",    "Your device is currently being repaired by our certified technicians."),
        "awaiting_parts": ("Awaiting Parts",        "We are waiting for a specific part to arrive before completing the repair."),
        "ready":          ("Ready for Collection",  "Great news — your device has been repaired and is ready for collection."),
        "closed":         ("Repair Complete",        "Your repair has been completed and the ticket is now closed."),
    }
    status_label, status_msg = status_map.get(new_status, (new_status.replace("_"," ").title(), "Your ticket status has been updated."))
    color = "#155724" if new_status in ("ready","closed") else "#856404" if new_status == "awaiting_parts" else "#004085"
    bg    = "#d4edda"  if new_status in ("ready","closed") else "#fff3cd" if new_status == "awaiting_parts" else "#cce5ff"

    notes_html = f'<p style="margin:16px 0 0;font-size:14px;color:#555"><strong>Technician Notes:</strong> {technician_notes}</p>' if technician_notes else ""
    body = f"""
    <p style="font-size:15px;margin:0 0 16px">Dear {customer},</p>
    <p style="font-size:14px;color:#555;margin:0 0 20px">We have an update on your repair with <strong>AMT Service Center</strong>.</p>
    <div style="background:{bg};border-left:4px solid {color};padding:16px 20px;border-radius:4px;margin-bottom:20px">
      <div style="font-weight:700;color:{color};font-size:15px">{status_label}</div>
      <div style="color:#555;font-size:14px;margin-top:4px">{status_msg}</div>
    </div>
    <table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:20px">
      <tr><td style="padding:9px 14px;border-bottom:1px solid #f0f0f0;color:#888;font-weight:600;width:140px">Ticket</td><td style="padding:9px 14px;border-bottom:1px solid #f0f0f0"><strong>{ticket_ref}</strong></td></tr>
      <tr><td style="padding:9px 14px;border-bottom:1px solid #f0f0f0;color:#888;font-weight:600">Product</td><td style="padding:9px 14px;border-bottom:1px solid #f0f0f0">{product}</td></tr>
      <tr><td style="padding:9px 14px;color:#888;font-weight:600">Status</td><td style="padding:9px 14px">{_badge(status_label, bg, color)}</td></tr>
    </table>
    {notes_html}
    <p style="margin:24px 0 0;font-size:14px">For any queries please contact us at <strong>service@amt.tv</strong> or call +971 4 XXX XXXX.<br><br>
    Kind regards,<br><strong>AMT Service Team</strong></p>"""

    html = _html_wrap("Repair Status Update", f"Ticket {ticket_ref} — {status_label}", body)
    subject = f"[AMT Service] Update on Your Repair — {ticket_ref} | {status_label}"
    return subject, html
