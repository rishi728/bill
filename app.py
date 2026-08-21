from flask import Flask, render_template, request, jsonify, send_file
import json, os, io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

app = Flask(__name__)

# Always store data.json next to app.py, works on any system
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")

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
        {"name": "Complete Blood Count (CBC)",    "rate": 350,   "hsn": "999313"},
        {"name": "Blood Glucose (Fasting)",       "rate": 80,    "hsn": "999313"},
        {"name": "Lipid Profile",                 "rate": 500,   "hsn": "999313"},
        {"name": "Liver Function Test (LFT)",     "rate": 600,   "hsn": "999313"},
        {"name": "Kidney Function Test (KFT)",    "rate": 500,   "hsn": "999313"},
        {"name": "Thyroid Profile (T3/T4/TSH)",   "rate": 700,   "hsn": "999313"},
        {"name": "Urine Routine & Microscopy",    "rate": 150,   "hsn": "999313"},
        {"name": "HbA1c",                         "rate": 400,   "hsn": "999313"},
    ],
    "bills": []
}

# ── helpers ───────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_DATA))

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ── routes ────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/data")
def get_data():
    return jsonify(load_data())

@app.route("/api/settings", methods=["POST"])
def update_settings():
    data = load_data()
    data["settings"] = request.get_json(force=True)
    save_data(data)
    return jsonify({"ok": True})

@app.route("/api/master-tests", methods=["POST"])
def update_master_tests():
    data = load_data()
    data["masterTests"] = request.get_json(force=True)
    save_data(data)
    return jsonify({"ok": True})

@app.route("/api/bills", methods=["GET"])
def get_bills():
    return jsonify(load_data().get("bills", []))

@app.route("/api/bills", methods=["POST"])
def save_bill():
    data = load_data()
    bill = request.get_json(force=True)
    bill["id"]      = int(datetime.now().timestamp() * 1000)
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
def get_pdf(bill_id):
    data = load_data()
    bill = next((b for b in data["bills"] if b.get("id") == bill_id), None)
    if not bill:
        return "Bill not found", 404
    pdf_bytes = build_pdf(bill, data["settings"])
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Invoice_{bill.get('invoiceNo', 'bill')}.pdf"
    )

@app.route("/api/pdf-preview", methods=["POST"])
def pdf_preview():
    payload = request.get_json(force=True)
    data    = load_data()
    s       = payload.get("settings") or data["settings"]
    pdf_bytes = build_pdf(payload["bill"], s)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        download_name=f"Invoice_{payload['bill'].get('invoiceNo','preview')}.pdf"
    )

# ── number to words ───────────────────────────────────────
def num_to_words(n):
    ones  = ['','ONE','TWO','THREE','FOUR','FIVE','SIX','SEVEN','EIGHT','NINE','TEN',
             'ELEVEN','TWELVE','THIRTEEN','FOURTEEN','FIFTEEN','SIXTEEN','SEVENTEEN',
             'EIGHTEEN','NINETEEN']
    tens_ = ['','','TWENTY','THIRTY','FORTY','FIFTY','SIXTY','SEVENTY','EIGHTY','NINETY']
    def h(x):
        if x == 0:   return ''
        if x < 20:   return ones[x] + ' '
        if x < 100:  return tens_[x//10] + (' ' + ones[x%10] if x%10 else '') + ' '
        return ones[x//100] + ' HUNDRED ' + h(x % 100)
    s, rem = '', int(round(n))
    if rem >= 10000000: s += h(rem // 10000000) + 'CRORE ';   rem %= 10000000
    if rem >= 100000:   s += h(rem // 100000)   + 'LAKH ';    rem %= 100000
    if rem >= 1000:     s += h(rem // 1000)     + 'THOUSAND '; rem %= 1000
    if rem >= 100:      s += h(rem // 100)      + 'HUNDRED '; rem %= 100
    if rem > 0:         s += h(rem)
    return (s.strip() or 'ZERO') + ' ONLY'

# ── PDF builder ───────────────────────────────────────────
def build_pdf(bill, s):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=10*mm, rightMargin=10*mm,
        topMargin=8*mm,   bottomMargin=8*mm
    )
    W = A4[0] - 20*mm
    story = []

    def P(text, align="left", bold=False, size=8):
        font = "Helvetica-Bold" if bold else "Helvetica"
        al   = TA_CENTER if align == "center" else (TA_RIGHT if align == "right" else 0)
        st   = ParagraphStyle("x", fontName=font, fontSize=size, leading=size+2, alignment=al)
        return Paragraph(text, st)

    def tblstyle(*extras):
        base = [
            ("BOX",            (0,0), (-1,-1), 0.5, colors.black),
            ("FONTSIZE",       (0,0), (-1,-1), 7),
            ("BOTTOMPADDING",  (0,0), (-1,-1), 2),
            ("TOPPADDING",     (0,0), (-1,-1), 2),
            ("LEFTPADDING",    (0,0), (-1,-1), 3),
            ("RIGHTPADDING",   (0,0), (-1,-1), 3),
        ]
        return TableStyle(base + list(extras))

    # ── HEADER ──────────────────────────────────────
    hdr = Table([
        [P("GST INVOICE", "center")],
        [P(f"<b>{s.get('labName','')}</b>", "center", size=14)],
        [P(f"Office Address : {s.get('labAddr','')}  &nbsp; Cell : {s.get('labPhone','')} , Email: {s.get('labEmail','')}", "center", size=7)],
    ], colWidths=[W])
    hdr.setStyle(tblstyle(("BOTTOMPADDING",(0,0),(-1,-1),3), ("TOPPADDING",(0,0),(-1,-1),3)))
    story.append(hdr)

    # ── META ────────────────────────────────────────
    ml = Table([
        [P(f"<b>PAn No :</b> {s.get('pan','')}")],
        [P("Tax is Payable on reverse Charges (Yes/No)")],
        [P(f"<b>Vendor Code :</b> &nbsp; <b>Order / Po No. :</b> {bill.get('poNo','')}")],
        [P(f"<b>Proposal No. :</b> &nbsp; <b>Order Date :</b> {bill.get('orderDate','')}")],
    ], colWidths=[W*0.6])
    mr = Table([
        [P(f"<b>Invoice No. :</b> {bill.get('invoiceNo','')}")],
        [P(f"<b>Date :</b> {bill.get('invDate','')}")],
        [P(f"<b>License key :</b> {s.get('license','')}")],
        [P("")],
    ], colWidths=[W*0.4])
    for t in (ml, mr):
        t.setStyle(TableStyle([("BOTTOMPADDING",(0,0),(-1,-1),1),("TOPPADDING",(0,0),(-1,-1),1)]))
    meta = Table([[ml, mr]], colWidths=[W*0.6, W*0.4])
    meta.setStyle(tblstyle(
        ("LINEBEFORE", (1,0),(1,-1), 0.5, colors.black),
        ("BOTTOMPADDING",(0,0),(-1,-1),3), ("TOPPADDING",(0,0),(-1,-1),3),
        ("LEFTPADDING",(0,0),(-1,-1),4),
    ))
    story.append(meta)

    # ── BILL TO / SHIP TO ───────────────────────────
    bt = P(f"<b>Bill to :</b><br/><b>{bill.get('clientName','')}</b><br/>"
           f"{bill.get('clientAddr1','')}<br/>{bill.get('clientCity','')} {bill.get('clientPin','')}<br/>"
           f"{('GSTIN: '+bill.get('clientGst','')) if bill.get('clientGst') else ''}")
    st_ = P(f"<b>Ship to :</b><br/>{bill.get('clientName','')}<br/>{bill.get('clientAddr1','')}")
    bs  = Table([[bt, st_]], colWidths=[W*0.5, W*0.5])
    bs.setStyle(tblstyle(
        ("LINEBEFORE",(1,0),(1,-1),0.5,colors.black),
        ("BOTTOMPADDING",(0,0),(-1,-1),5), ("TOPPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),4),
    ))
    story.append(bs)

    # ── ITEMS ───────────────────────────────────────
    tests = bill.get("tests", [])
    rows  = [[
        P("<b>Sr.</b>","center"), P("<b>Item Details</b>"),
        P("<b>HSN/SAC</b>","center"), P("<b>Unit</b>","center"),
        P("<b>Qty.</b>","center"), P("<b>Rate</b>","right"),
        P("<b>GST%</b>","center"), P("<b>Disc%</b>","center"),
        P("<b>Amount Rs.</b>","right"),
    ]]
    for i, t in enumerate(tests):
        qty  = float(t.get("qty",1)); rate = float(t.get("rate",0))
        gst  = float(t.get("gst",0)); disc = float(t.get("disc",0))
        base = qty * rate; da = base * disc / 100; tx = base - da
        amt  = tx + tx * gst / 100
        rows.append([
            P(str(i+1),"center"), P(str(t.get("desc",""))),
            P(str(t.get("hsn","None")),"center"), P(str(t.get("unit","NOS")),"center"),
            P(f"{qty:.2f}","center"), P(f"{rate:,.2f}","right"),
            P(str(gst),"center"), P(f"{disc:.2f}","center"),
            P(f"{amt:,.2f}","right"),
        ])
    for _ in range(max(0, 6-len(tests))):
        rows.append([P("&nbsp;")]*9)

    cw = [9*mm, W-9*mm-13*mm-10*mm-10*mm-18*mm-10*mm-10*mm-18*mm,
          13*mm,10*mm,10*mm,18*mm,10*mm,10*mm,18*mm]
    itbl = Table(rows, colWidths=cw, repeatRows=1)
    itbl.setStyle(tblstyle(
        ("INNERGRID",(0,0),(-1,-1),0.3,colors.grey),
        ("BACKGROUND",(0,0),(-1,0),colors.Color(0.93,0.93,0.93)),
    ))
    story.append(itbl)

    # ── TOTALS ──────────────────────────────────────
    grand = float(bill.get("grand",0))
    sub   = float(bill.get("subtotalNet",0)) - float(bill.get("totalCgst",0)) - float(bill.get("totalSgst",0))
    extra = float(bill.get("extraCharges",0))
    disc_ = float(bill.get("totalDisc",0)) + float(bill.get("extraDisc",0))
    cgst_ = float(bill.get("totalCgst",0))
    sgst_ = float(bill.get("totalSgst",0))
    igst_ = float(bill.get("totalIgst",0))
    roff  = float(bill.get("roundOff",0))
    words = num_to_words(grand)
    rem   = bill.get("remarks","")

    words_cell = P(f"<b>Amount in words :</b><br/><b>{words}</b>" + (f"<br/><i>{rem}</i>" if rem else ""))
    tot_rows = [
        [P("SubTotal"), P(f"{sub:,.2f}","right")],
        [P("Fright"),   P("0.00","right")],
        [P("Extra Charges"), P(f"{extra:,.2f}","right")],
        [P("Discount"), P(f"{disc_:,.2f}","right")],
        [P("CGST Amt"), P(f"{cgst_:,.2f}","right")],
        [P("SGST Amt"), P(f"{sgst_:,.2f}","right")],
        [P("IGST Amt"), P(f"{igst_:,.2f}","right")],
        [P("Round Off"),P(f"{roff:,.2f}","right")],
        [P("<b>Grandtotal</b>",bold=True), P(f"<b>{grand:,.2f}</b>","right",bold=True)],
    ]
    ttbl = Table(tot_rows, colWidths=[30*mm, 20*mm])
    ttbl.setStyle(tblstyle(
        ("INNERGRID",(0,0),(-1,-1),0.3,colors.lightgrey),
        ("LINEABOVE",(0,-1),(-1,-1),1,colors.black),
    ))
    trow = Table([[words_cell, ttbl]], colWidths=[W-50*mm, 50*mm])
    trow.setStyle(tblstyle(
        ("LINEBEFORE",(1,0),(1,-1),0.5,colors.black),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),4),
    ))
    story.append(trow)

    # ── GST BREAKDOWN ───────────────────────────────
    gmap = {}
    for t in tests:
        r  = float(t.get("gst",0))
        if r not in gmap: gmap[r] = {"tx":0,"cg":0,"sg":0}
        qty2=float(t.get("qty",1)); r2=float(t.get("rate",0)); d2=float(t.get("disc",0))
        b2=qty2*r2; da2=b2*d2/100; tx2=b2-da2
        gmap[r]["tx"]+=tx2; gmap[r]["cg"]+=tx2*r/2/100; gmap[r]["sg"]+=tx2*r/2/100

    gh = [[P(f"<b>{h}</b>","center") for h in ["GST(%)","Taxable Value","SGST AMT","CGST AMT","IGST AMT","Total AMT"]]]
    for rp in [0,5,12,18,28]:
        g  = gmap.get(rp,{})
        tx2=g.get("tx",0); cg2=g.get("cg",0); sg2=g.get("sg",0)
        gh.append([
            P(f"{rp}%","center"),
            P(f"{tx2:.2f}","center") if tx2 else P("","center"),
            P(f"{sg2:.2f}","center"),P(f"{cg2:.2f}","center"),
            P("0.00","center"),P(f"{cg2+sg2:.2f}","center"),
        ])
    gtbl = Table(gh, colWidths=[W/6]*6)
    gtbl.setStyle(tblstyle(
        ("INNERGRID",(0,0),(-1,-1),0.3,colors.grey),
        ("BACKGROUND",(0,0),(-1,0),colors.Color(0.93,0.93,0.93)),
    ))
    story.append(gtbl)

    # ── OUTSTANDING ─────────────────────────────────
    out = Table([[P(f"<b>Total Outstanding : {grand:,.2f}</b>")]], colWidths=[W])
    out.setStyle(tblstyle(("LEFTPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),3),("TOPPADDING",(0,0),(-1,-1),3)))
    story.append(out)

    # ── FOOTER ──────────────────────────────────────
    terms = (s.get("terms","") or "").replace("\n","<br/>")
    bank  = (f"Bank Name : {s.get('bankName','')}<br/>A/C Name : {s.get('bankAcName','')}<br/>"
             f"A/C No : {s.get('bankAc','')}<br/>({s.get('bankType','')})"
             + (f"<br/>IFSC : {s.get('bankIfsc','')}" if s.get("bankIfsc") else ""))
    sign  = f"<b>{s.get('labName','')}</b><br/><br/><br/><br/>Authorised Signatory"
    ftbl  = Table([
        [P(f"<b>Terms &amp; Conditions</b><br/>{terms}"),
         P(f"<b>Bank Details :</b><br/>{bank}"),
         P(sign,"center")]
    ], colWidths=[W/3, W/3, W/3])
    ftbl.setStyle(tblstyle(
        ("LINEBEFORE",(1,0),(1,-1),0.5,colors.black),
        ("LINEBEFORE",(2,0),(2,-1),0.5,colors.black),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),4),
    ))
    story.append(ftbl)

    doc.build(story)
    return buf.getvalue()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
