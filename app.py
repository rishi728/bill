from flask import Flask, render_template, request, jsonify, send_file
import json, os, io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import KeepTogether

app = Flask(__name__)

DATA_FILE = "data.json"

# ── default data ──────────────────────────────────────────
DEFAULT_DATA = {
    "settings": {
        "labName": "Dr. Joshi Microbiology Lab Pvt Ltd",
        "labAddr": "402/403, Shiv Centre, Above Hotel Vishwajyoti,",
        "labPhone": "8169913628",
        "labEmail": "skajoshi@yahoo.co.in",
        "pan": "AAJCD2074K",
        "gst": "",
        "license": "",
        "invPrefix": "S",
        "bankName": "HDFC",
        "bankAcName": "Dr. Joshi Microbiology lab Pvt Ltd",
        "bankAc": "50200068667972",
        "bankType": "Current A/C",
        "bankIfsc": "",
        "terms": "Payment request by crossed a/c Payee cheque / NEFT / RTGS only.\nCheque must be drawn in favour of \"Dr.Joshi Microbiology lab Pvt Ltd\""
    },
    "masterTests": [
        {"name": "Medical Microbiology Laboratory Investigations", "rate": 61900, "hsn": "None"},
        {"name": "Complete Blood Count (CBC)", "rate": 350, "hsn": "999313"},
        {"name": "Blood Glucose (Fasting)", "rate": 80, "hsn": "999313"},
        {"name": "Lipid Profile", "rate": 500, "hsn": "999313"},
        {"name": "Liver Function Test (LFT)", "rate": 600, "hsn": "999313"},
        {"name": "Kidney Function Test (KFT)", "rate": 500, "hsn": "999313"},
        {"name": "Thyroid Profile (T3/T4/TSH)", "rate": 700, "hsn": "999313"},
        {"name": "Urine Routine & Microscopy", "rate": 150, "hsn": "999313"},
        {"name": "HbA1c", "rate": 400, "hsn": "999313"},
    ],
    "bills": []
}

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except:
            pass
    return json.loads(json.dumps(DEFAULT_DATA))

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ── routes ────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/data", methods=["GET"])
def get_data():
    return jsonify(load_data())

@app.route("/api/settings", methods=["POST"])
def update_settings():
    data = load_data()
    data["settings"] = request.json
    save_data(data)
    return jsonify({"ok": True})

@app.route("/api/master-tests", methods=["POST"])
def update_master_tests():
    data = load_data()
    data["masterTests"] = request.json
    save_data(data)
    return jsonify({"ok": True})

@app.route("/api/bills", methods=["GET"])
def get_bills():
    data = load_data()
    return jsonify(data.get("bills", []))

@app.route("/api/bills", methods=["POST"])
def save_bill():
    data = load_data()
    bill = request.json
    bill["id"] = int(datetime.now().timestamp() * 1000)
    bill["savedAt"] = datetime.now().isoformat()
    data["bills"].insert(0, bill)
    save_data(data)
    return jsonify({"ok": True, "id": bill["id"]})

@app.route("/api/bills/<int:bill_id>", methods=["DELETE"])
def delete_bill(bill_id):
    data = load_data()
    data["bills"] = [b for b in data["bills"] if b.get("id") != bill_id]
    save_data(data)
    return jsonify({"ok": True})

@app.route("/api/pdf/<int:bill_id>")
def generate_pdf(bill_id):
    data = load_data()
    bill = next((b for b in data["bills"] if b.get("id") == bill_id), None)
    if not bill:
        return "Bill not found", 404
    pdf_bytes = build_pdf(bill, data["settings"])
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Invoice_{bill.get('invoiceNo','bill')}.pdf"
    )

@app.route("/api/pdf-preview", methods=["POST"])
def pdf_preview():
    payload = request.json
    data = load_data()
    s = payload.get("settings") or data["settings"]
    pdf_bytes = build_pdf(payload["bill"], s)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        download_name=f"Invoice_{payload['bill'].get('invoiceNo','preview')}.pdf"
    )

# ── PDF builder ───────────────────────────────────────────
def num_to_words(n):
    ones = ['','ONE','TWO','THREE','FOUR','FIVE','SIX','SEVEN','EIGHT','NINE','TEN',
            'ELEVEN','TWELVE','THIRTEEN','FOURTEEN','FIFTEEN','SIXTEEN','SEVENTEEN',
            'EIGHTEEN','NINETEEN']
    tens_w = ['','','TWENTY','THIRTY','FORTY','FIFTY','SIXTY','SEVENTY','EIGHTY','NINETY']
    if n == 0: return 'ZERO'
    def h(num):
        if num == 0: return ''
        if num < 20: return ones[num] + ' '
        if num < 100: return tens_w[num//10] + (' ' + ones[num%10] if num%10 else '') + ' '
        return ones[num//100] + ' HUNDRED ' + h(num%100)
    s, rem = '', int(round(n))
    if rem >= 10000000: s += h(rem//10000000) + 'CRORE '; rem %= 10000000
    if rem >= 100000:   s += h(rem//100000)   + 'LAKH ';  rem %= 100000
    if rem >= 1000:     s += h(rem//1000)     + 'THOUSAND '; rem %= 1000
    if rem >= 100:      s += h(rem//100)      + 'HUNDRED '; rem %= 100
    if rem > 0:         s += h(rem)
    return s.strip() + ' ONLY'

def build_pdf(bill, s):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=10*mm, rightMargin=10*mm,
                            topMargin=8*mm, bottomMargin=8*mm)

    W = A4[0] - 20*mm  # usable width
    story = []

    base_style = ParagraphStyle('base', fontName='Helvetica', fontSize=8, leading=10)
    bold_style = ParagraphStyle('bold', fontName='Helvetica-Bold', fontSize=8, leading=10)
    center_style = ParagraphStyle('center', fontName='Helvetica', fontSize=8, leading=10, alignment=TA_CENTER)
    right_style  = ParagraphStyle('right',  fontName='Helvetica', fontSize=8, leading=10, alignment=TA_RIGHT)

    # ── HEADER ──
    header_data = [
        [Paragraph('<font size="7">GST INVOICE</font>', center_style)],
        [Paragraph(f'<font size="14"><b>{s.get("labName","")}</b></font>', center_style)],
        [Paragraph(f'<font size="7">Office Address : {s.get("labAddr","")} &nbsp; Cell : {s.get("labPhone","")} , Email: {s.get("labEmail","")}</font>', center_style)],
    ]
    header_table = Table(header_data, colWidths=[W])
    header_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(header_table)

    # ── META ROW ──
    meta_left = [
        [Paragraph(f'<b>PAn No :</b> {s.get("pan","")}', base_style)],
        [Paragraph('Tax is Payable on reverse Charges (Yes/No)', base_style)],
        [Paragraph(f'<b>Vendor Code :</b> &nbsp;&nbsp; <b>Order / Po No. :</b> {bill.get("poNo","")}', base_style)],
        [Paragraph(f'<b>Proposal No. :</b> &nbsp;&nbsp; <b>Order Date :</b> {bill.get("orderDate","")}', base_style)],
    ]
    meta_right = [
        [Paragraph(f'<b>Invoice No. :</b> {bill.get("invoiceNo","")}', base_style)],
        [Paragraph(f'<b>Date :</b>{bill.get("invDate","")}', base_style)],
        [Paragraph(f'<b>License key :</b> {s.get("license","")}', base_style)],
        [Paragraph('', base_style)],
    ]
    meta_left_t  = Table(meta_left,  colWidths=[W*0.6])
    meta_right_t = Table(meta_right, colWidths=[W*0.4])
    meta_left_t.setStyle(TableStyle([('BOTTOMPADDING',(0,0),(-1,-1),1),('TOPPADDING',(0,0),(-1,-1),1)]))
    meta_right_t.setStyle(TableStyle([('BOTTOMPADDING',(0,0),(-1,-1),1),('TOPPADDING',(0,0),(-1,-1),1)]))

    meta_outer = Table([[meta_left_t, meta_right_t]], colWidths=[W*0.6, W*0.4])
    meta_outer.setStyle(TableStyle([
        ('BOX',    (0,0),(-1,-1), 0.5, colors.black),
        ('LINEBEFORE',(1,0),(1,-1), 0.5, colors.black),
        ('BOTTOMPADDING',(0,0),(-1,-1),3),
        ('TOPPADDING',(0,0),(-1,-1),3),
        ('LEFTPADDING',(0,0),(-1,-1),4),
    ]))
    story.append(meta_outer)

    # ── BILL TO / SHIP TO ──
    client_addr = f"{bill.get('clientAddr1','')}\n{bill.get('clientCity','')} {bill.get('clientPin','')}"
    bill_to = Paragraph(f"<b>Bill to :</b><br/><b>{bill.get('clientName','')}</b><br/>{bill.get('clientAddr1','')}<br/>{bill.get('clientCity','')} {bill.get('clientPin','')}", base_style)
    ship_to = Paragraph(f"<b>Ship to :</b><br/>{bill.get('clientName','')}<br/>{bill.get('clientAddr1','')}", base_style)
    bill_ship = Table([[bill_to, ship_to]], colWidths=[W*0.5, W*0.5])
    bill_ship.setStyle(TableStyle([
        ('BOX',        (0,0),(-1,-1), 0.5, colors.black),
        ('LINEBEFORE', (1,0),(1,-1),  0.5, colors.black),
        ('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('TOPPADDING',  (0,0),(-1,-1),5),
        ('LEFTPADDING', (0,0),(-1,-1),4),
    ]))
    story.append(bill_ship)

    # ── ITEMS TABLE ──
    item_header = [
        Paragraph('<b>Sr.No.</b>', center_style),
        Paragraph('<b>Item Details</b>', base_style),
        Paragraph('<b>HSN/SAC\nCode</b>', center_style),
        Paragraph('<b>Unit</b>', center_style),
        Paragraph('<b>Qty.</b>', center_style),
        Paragraph('<b>Rate</b>', center_style),
        Paragraph('<b>GST\n%</b>', center_style),
        Paragraph('<b>Disc\n%</b>', center_style),
        Paragraph('<b>Amount\nRs.</b>', right_style),
    ]
    item_rows = [item_header]
    tests = bill.get("tests", [])
    for i, t in enumerate(tests):
        base  = float(t.get("qty",1)) * float(t.get("rate",0))
        disc_a = base * float(t.get("disc",0)) / 100
        taxable = base - disc_a
        amt = taxable + taxable * float(t.get("gst",0)) / 100
        item_rows.append([
            Paragraph(str(i+1), center_style),
            Paragraph(str(t.get("desc","")), base_style),
            Paragraph(str(t.get("hsn","None")), center_style),
            Paragraph(str(t.get("unit","NOS")), center_style),
            Paragraph(f"{float(t.get('qty',1)):.2f}", center_style),
            Paragraph(f"{float(t.get('rate',0)):,.2f}", right_style),
            Paragraph(str(t.get("gst",0)), center_style),
            Paragraph(f"{float(t.get('disc',0)):.2f}", center_style),
            Paragraph(f"{amt:,.2f}", right_style),
        ])
    # filler rows
    for _ in range(max(0, 6 - len(tests))):
        item_rows.append([Paragraph("&nbsp;", base_style)] * 9)

    col_w = [10*mm, W-10*mm-14*mm-10*mm-10*mm-18*mm-10*mm-10*mm-18*mm,
             14*mm, 10*mm, 10*mm, 18*mm, 10*mm, 10*mm, 18*mm]
    items_t = Table(item_rows, colWidths=col_w, repeatRows=1)
    items_t.setStyle(TableStyle([
        ('BOX',         (0,0),(-1,-1), 0.5, colors.black),
        ('INNERGRID',   (0,0),(-1,-1), 0.3, colors.grey),
        ('BACKGROUND',  (0,0),(-1,0),  colors.white),
        ('FONTNAME',    (0,0),(-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',    (0,0),(-1,-1), 7),
        ('BOTTOMPADDING',(0,0),(-1,-1),2),
        ('TOPPADDING',  (0,0),(-1,-1),2),
        ('LEFTPADDING', (0,0),(-1,-1),3),
        ('RIGHTPADDING',(0,0),(-1,-1),3),
    ]))
    story.append(items_t)

    # ── TOTALS ──
    grand = float(bill.get("grand", 0))
    sub   = float(bill.get("subtotalNet", 0)) - float(bill.get("totalCgst",0)) - float(bill.get("totalSgst",0))
    extra = float(bill.get("extraCharges",0))
    disc  = float(bill.get("totalDisc",0)) + float(bill.get("extraDisc",0))
    cgst  = float(bill.get("totalCgst",0))
    sgst  = float(bill.get("totalSgst",0))
    igst  = float(bill.get("totalIgst",0))
    roff  = float(bill.get("roundOff",0))
    words = num_to_words(grand)
    remarks = bill.get("remarks","")

    words_cell = Paragraph(
        f'<b>Amount in words :</b><br/><b>{words}</b>' + (f'<br/><i>{remarks}</i>' if remarks else ''),
        base_style
    )
    totals_data = [
        ['SubTotal',     f'{sub:,.2f}'],
        ['Fright',       '0.00'],
        ['Extra Charges',f'{extra:,.2f}'],
        ['Discount',     f'{disc:,.2f}'],
        ['CGST Amt',     f'{cgst:,.2f}'],
        ['SGST Amt',     f'{sgst:,.2f}'],
        ['IGST Amt',     f'{igst:,.2f}'],
        ['Round Off',    f'{roff:,.2f}'],
        ['Grandtotal',   f'{grand:,.2f}'],
    ]
    totals_t = Table(
        [[Paragraph(r[0], bold_style if r[0]=='Grandtotal' else base_style),
          Paragraph(r[1], right_style)] for r in totals_data],
        colWidths=[30*mm, 20*mm]
    )
    totals_t.setStyle(TableStyle([
        ('BOX',       (0,0),(-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0),(-1,-1), 0.3, colors.lightgrey),
        ('LINEABOVE', (0,-1),(-1,-1), 1, colors.black),
        ('FONTSIZE',  (0,0),(-1,-1), 7),
        ('FONTNAME',  (0,-1),(-1,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING',(0,0),(-1,-1),2),
        ('TOPPADDING',  (0,0),(-1,-1),2),
        ('LEFTPADDING', (0,0),(-1,-1),3),
        ('RIGHTPADDING',(0,0),(-1,-1),3),
    ]))
    totals_row = Table([[words_cell, totals_t]], colWidths=[W - 50*mm, 50*mm])
    totals_row.setStyle(TableStyle([
        ('BOX',       (0,0),(-1,-1), 0.5, colors.black),
        ('LINEBEFORE',(1,0),(1,-1),  0.5, colors.black),
        ('VALIGN',    (0,0),(-1,-1), 'TOP'),
        ('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',  (0,0),(-1,-1),4),
        ('LEFTPADDING', (0,0),(-1,-1),4),
    ]))
    story.append(totals_row)

    # ── GST BREAKDOWN ──
    gst_map = {}
    for t in tests:
        r = float(t.get("gst",0))
        if r not in gst_map: gst_map[r] = {"taxable":0,"cgst":0,"sgst":0,"igst":0}
        base  = float(t.get("qty",1)) * float(t.get("rate",0))
        disc_a = base * float(t.get("disc",0)) / 100
        tx    = base - disc_a
        gst_map[r]["taxable"] += tx
        gst_map[r]["cgst"]    += tx * r / 2 / 100
        gst_map[r]["sgst"]    += tx * r / 2 / 100

    gst_header = [Paragraph(f'<b>{h}</b>', center_style) for h in
                  ['GST(%)', 'Taxable Value', 'SGST AMT', 'CGST AMT', 'IGST AMT', 'Total AMT']]
    gst_rows = [gst_header]
    for rate_pct in [0, 5, 12, 18, 28]:
        g = gst_map.get(rate_pct, {})
        tx   = g.get("taxable", 0)
        cg   = g.get("cgst", 0)
        sg   = g.get("sgst", 0)
        ig   = g.get("igst", 0)
        tot  = cg + sg + ig
        gst_rows.append([
            Paragraph(f'{rate_pct}%', center_style),
            Paragraph(f'{tx:.2f}' if tx else '', center_style),
            Paragraph(f'{sg:.2f}', center_style),
            Paragraph(f'{cg:.2f}', center_style),
            Paragraph(f'{ig:.2f}', center_style),
            Paragraph(f'{tot:.2f}', center_style),
        ])
    gst_cw = [W/6]*6
    gst_t = Table(gst_rows, colWidths=gst_cw)
    gst_t.setStyle(TableStyle([
        ('BOX',       (0,0),(-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0),(-1,-1), 0.3, colors.grey),
        ('BACKGROUND',(0,0),(-1,0),  colors.Color(0.95,0.95,0.95)),
        ('FONTSIZE',  (0,0),(-1,-1), 7),
        ('BOTTOMPADDING',(0,0),(-1,-1),2),
        ('TOPPADDING',  (0,0),(-1,-1),2),
    ]))
    story.append(gst_t)

    # ── OUTSTANDING ──
    out_t = Table([[Paragraph(f'<b>Total Outstanding : {grand:,.2f}</b>', base_style)]],
                  colWidths=[W])
    out_t.setStyle(TableStyle([
        ('BOX',(0,0),(-1,-1),0.5,colors.black),
        ('BOTTOMPADDING',(0,0),(-1,-1),3),
        ('TOPPADDING',  (0,0),(-1,-1),3),
        ('LEFTPADDING', (0,0),(-1,-1),4),
    ]))
    story.append(out_t)

    # ── FOOTER ──
    terms_text  = (s.get("terms","") or "").replace("\n","<br/>")
    bank_text   = (f'Bank Name : {s.get("bankName","")}<br/>'
                   f'A/C Name : {s.get("bankAcName","")}<br/>'
                   f'A/C No : {s.get("bankAc","")}<br/>'
                   f'({s.get("bankType","")})<br/>'
                   f'{("IFSC : "+s.get("bankIfsc","")) if s.get("bankIfsc") else ""}')
    sign_text   = (f'<b>{s.get("labName","")}</b><br/><br/><br/><br/>Authorised Signatory')
    footer_t = Table([
        [Paragraph(f'<b>Terms &amp; Conditions</b><br/>{terms_text}', base_style),
         Paragraph(f'<b>Bank Details :</b><br/>{bank_text}', base_style),
         Paragraph(sign_text, center_style)]
    ], colWidths=[W/3, W/3, W/3])
    footer_t.setStyle(TableStyle([
        ('BOX',       (0,0),(-1,-1), 0.5, colors.black),
        ('LINEBEFORE',(1,0),(1,-1),  0.5, colors.black),
        ('LINEBEFORE',(2,0),(2,-1),  0.5, colors.black),
        ('VALIGN',    (0,0),(-1,-1), 'TOP'),
        ('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('TOPPADDING',  (0,0),(-1,-1),5),
        ('LEFTPADDING', (0,0),(-1,-1),4),
    ]))
    story.append(footer_t)

    doc.build(story)
    return buf.getvalue()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
