"""
Pathology Lab GST Invoice Generator
Single-file Flask app. No templates folder, no external file dependencies.
Deploy: gunicorn app:app
"""
from flask import Flask, request, jsonify, Response
import json, os
from datetime import datetime

app = Flask(__name__)

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")

DEFAULT_DATA = {
    "settings": {
        "labName": "Your Lab Name Pvt Ltd",
        "labAddr": "Office address line",
        "labPhone": "",
        "labEmail": "",
        "pan": "",
        "gst": "",
        "license": "",
        "invPrefix": "S",
        "bankName": "",
        "bankAcName": "",
        "bankAc": "",
        "bankType": "Current A/C",
        "bankIfsc": "",
        "terms": "Payment request by crossed a/c Payee cheque / NEFT / RTGS only."
    },
    "masterTests": [
        {"name": "Complete Blood Count (CBC)",  "rate": 350, "hsn": "999313"},
        {"name": "Blood Glucose (Fasting)",     "rate": 80,  "hsn": "999313"},
        {"name": "Lipid Profile",               "rate": 500, "hsn": "999313"},
        {"name": "Liver Function Test (LFT)",   "rate": 600, "hsn": "999313"},
        {"name": "Kidney Function Test (KFT)",  "rate": 500, "hsn": "999313"},
        {"name": "Thyroid Profile (T3/T4/TSH)", "rate": 700, "hsn": "999313"},
        {"name": "Urine Routine & Microscopy",  "rate": 150, "hsn": "999313"},
        {"name": "HbA1c",                       "rate": 400, "hsn": "999313"}
    ],
    "bills": []
}


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                d = json.load(f)
            for k in DEFAULT_DATA:
                d.setdefault(k, DEFAULT_DATA[k])
            return d
        except Exception as e:
            print("load_data error:", e)
    return json.loads(json.dumps(DEFAULT_DATA))


def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print("save_data error:", e)
        return False


# ── API ROUTES ───────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


@app.route("/api/data")
def api_data():
    return jsonify(load_data())


@app.route("/api/settings", methods=["POST"])
def api_settings():
    d = load_data()
    d["settings"] = request.get_json(force=True)
    save_data(d)
    return jsonify({"ok": True})


@app.route("/api/master-tests", methods=["POST"])
def api_master_tests():
    d = load_data()
    d["masterTests"] = request.get_json(force=True)
    save_data(d)
    return jsonify({"ok": True})


@app.route("/api/bills", methods=["GET"])
def api_get_bills():
    return jsonify(load_data().get("bills", []))


@app.route("/api/bills", methods=["POST"])
def api_save_bill():
    d = load_data()
    b = request.get_json(force=True)
    b["id"] = int(datetime.now().timestamp() * 1000)
    b["savedAt"] = datetime.now().isoformat()
    d["bills"].insert(0, b)
    save_data(d)
    return jsonify({"ok": True, "id": b["id"]})


@app.route("/api/bills/<int:bill_id>", methods=["DELETE"])
def api_delete_bill(bill_id):
    d = load_data()
    d["bills"] = [b for b in d["bills"] if b.get("id") != bill_id]
    save_data(d)
    return jsonify({"ok": True})


@app.route("/api/bills/clear", methods=["POST"])
def api_clear_bills():
    d = load_data()
    d["bills"] = []
    save_data(d)
    return jsonify({"ok": True})


@app.errorhandler(500)
def err500(e):
    return jsonify({"error": "server error", "detail": str(e)}), 500


@app.route("/")
def index():
    return Response(HTML_PAGE, mimetype="text/html")

# ═════════════════════════════════════════════════════════
#  EMBEDDED FRONTEND
# ═════════════════════════════════════════════════════════
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lab Invoice Generator</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#eef2f7;color:#1a202c}
.nav{background:#1a365d;color:#fff;display:flex;align-items:center;height:54px;padding:0 18px;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.3)}
.nav-brand{font-size:16px;font-weight:800;flex:1}
.nav-tab{padding:0 15px;height:54px;display:flex;align-items:center;cursor:pointer;font-size:13px;color:rgba(255,255,255,.65);border-bottom:3px solid transparent}
.nav-tab:hover,.nav-tab.active{color:#fff;border-bottom-color:#63b3ed}
.toast{position:fixed;top:64px;right:16px;z-index:999;padding:11px 18px;border-radius:8px;font-size:13px;font-weight:600;box-shadow:0 4px 16px rgba(0,0,0,.18);display:none;max-width:320px}
.toast.show{display:block}
.toast.success{background:#c6f6d5;color:#276749}
.toast.error{background:#fff5f5;color:#c53030}
.page{display:none;padding:18px;max-width:1060px;margin:0 auto}
.page.active{display:block}
.card{background:#fff;border-radius:10px;padding:18px 20px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.card-title{font-size:12px;font-weight:800;color:#2b6cb0;text-transform:uppercase;letter-spacing:.8px;margin-bottom:14px;padding-bottom:9px;border-bottom:2px solid #ebf4ff}
.fg{display:grid;grid-template-columns:1fr 1fr;gap:13px}
.full{grid-column:1/-1}
label{display:block;font-size:11px;font-weight:700;color:#4a5568;margin-bottom:3px;text-transform:uppercase}
input,select,textarea{width:100%;padding:8px 10px;border:1.5px solid #e2e8f0;border-radius:6px;font-size:13px;background:#fafafa}
input:focus,select:focus,textarea:focus{outline:none;border-color:#4299e1;background:#fff}
.btn{border:none;border-radius:7px;padding:9px 18px;font-size:13px;font-weight:700;cursor:pointer}
.btn-primary{background:#1a365d;color:#fff}.btn-primary:hover{background:#2a4a7f}
.btn-primary:disabled{background:#a0aec0;cursor:not-allowed}
.btn-blue{background:#2b6cb0;color:#fff}.btn-green{background:#276749;color:#fff}
.btn-sm{padding:6px 12px;font-size:12px}
.btn-full{width:100%;padding:13px;font-size:14px}
.btn-x{background:#fff5f5;color:#c53030;border:1.5px solid #fed7d7;border-radius:5px;padding:4px 10px;font-size:12px;cursor:pointer}
.tbl-wrap{overflow-x:auto}
table.itbl{width:100%;border-collapse:collapse;font-size:12px;min-width:700px}
table.itbl th{background:#ebf4ff;color:#2b6cb0;padding:7px 8px;border:1px solid #bee3f8;text-align:left;font-size:11px}
table.itbl td{padding:6px 8px;border:1px solid #e2e8f0}
table.itbl td input{border:none;background:transparent;padding:2px 4px;font-size:12px}
table.itbl td input:focus{background:#ebf4ff;outline:1px solid #4299e1}
.add-row{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap;align-items:flex-end}
.tot-table{width:100%;font-size:13px;border-collapse:collapse}
.tot-table td{padding:5px 8px;border-bottom:1px solid #f0f4f8}
.tot-table td:last-child{text-align:right;font-weight:600}
.tot-table tr.grand td{font-size:15px;font-weight:800;color:#1a365d;border-top:2px solid #1a365d;padding-top:9px}
.totals-split{display:grid;grid-template-columns:1fr 240px;gap:20px;align-items:start}
.bill-card{background:#fff;border-radius:8px;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 1px 3px rgba(0,0,0,.07);border-left:4px solid #2b6cb0;margin-bottom:10px;flex-wrap:wrap;gap:8px}
.bc-inv{font-weight:800;font-size:14px;color:#1a365d}
.bc-name{font-size:13px;color:#4a5568;margin-top:2px}
.bc-date{font-size:11px;color:#718096}
.bc-amt{font-size:20px;font-weight:900;color:#276749}
.empty{text-align:center;padding:50px;color:#a0aec0;font-size:14px}
.hist-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:10px}
.hist-hdr h2{font-size:17px;color:#1a365d}
.stab-row{display:flex;gap:4px;margin-bottom:16px;flex-wrap:wrap}
.stab{padding:7px 16px;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;background:#f0f4f8;color:#4a5568;border:none}
.stab.active{background:#2b6cb0;color:#fff}
.mtbl{width:100%;border-collapse:collapse;font-size:13px}
.mtbl th{background:#f7fafc;padding:7px 10px;border:1px solid #e2e8f0;text-align:left;font-size:11px;color:#4a5568}
.mtbl td{padding:7px 10px;border:1px solid #e2e8f0}
@media(max-width:640px){.fg,.totals-split{grid-template-columns:1fr}.nav-tab{padding:0 9px;font-size:11px}.add-row>*{width:100%!important;max-width:none!important}}
</style>
</head>
<body>
<div class="nav">
  <div class="nav-brand">&#128300; Lab Invoice</div>
  <div class="nav-tab active" id="tab-form" onclick="showPage('form')">New Bill</div>
  <div class="nav-tab" id="tab-history" onclick="showPage('history')">History</div>
  <div class="nav-tab" id="tab-settings" onclick="showPage('settings')">Settings</div>
</div>
<div class="toast" id="toast"></div>

<!-- NEW BILL -->
<div class="page active" id="page-form">
  <div class="card">
    <div class="card-title">Invoice Details</div>
    <div class="fg">
      <div><label>Invoice No.</label><input id="inv-number"></div>
      <div><label>Invoice Date</label><input type="date" id="inv-date"></div>
      <div><label>Order / PO No.</label><input id="po-number" placeholder="Optional"></div>
      <div><label>Order Date</label><input type="date" id="order-date"></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">Bill To</div>
    <div class="fg">
      <div class="full"><label>Client / Patient Name</label><input id="client-name" placeholder="DNA Pathology Lab"></div>
      <div class="full"><label>Address</label><input id="client-addr1" placeholder="Street, Area"></div>
      <div><label>City, State</label><input id="client-city" placeholder="Mumbai, Maharashtra"></div>
      <div><label>PIN</label><input id="client-pin" placeholder="400074"></div>
      <div><label>GSTIN (optional)</label><input id="client-gst"></div>
      <div><label>Phone (optional)</label><input id="client-phone"></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">Tests / Items</div>
    <div class="tbl-wrap"><table class="itbl">
      <thead><tr><th style="width:36px">Sr.</th><th>Description</th><th style="width:80px">HSN/SAC</th>
      <th style="width:52px">Unit</th><th style="width:56px">Qty</th><th style="width:80px">Rate</th>
      <th style="width:56px">GST%</th><th style="width:56px">Disc%</th><th style="width:88px">Amount</th><th style="width:36px"></th></tr></thead>
      <tbody id="test-body"><tr><td colspan="10" style="text-align:center;color:#a0aec0;padding:20px 0">No tests added yet</td></tr></tbody>
    </table></div>
    <div class="add-row">
      <select id="quick-test" style="flex:2;min-width:180px" onchange="quickAdd()"><option value="">&mdash; Quick add from master list &mdash;</option></select>
      <input id="new-desc" style="flex:2;min-width:150px" placeholder="Or type test name">
      <input id="new-hsn" style="max-width:80px" value="None" placeholder="HSN">
      <input id="new-unit" style="max-width:66px" value="NOS" placeholder="Unit">
      <input id="new-qty" type="number" style="max-width:58px" value="1" min="0.01" step="0.01" placeholder="Qty">
      <input id="new-rate" type="number" style="max-width:88px" min="0" step="0.01" placeholder="Rate">
      <input id="new-gst" type="number" style="max-width:64px" value="0" min="0" max="28" placeholder="GST%">
      <input id="new-disc" type="number" style="max-width:64px" value="0" min="0" max="100" placeholder="Disc%">
      <button class="btn btn-blue btn-sm" onclick="addTest()">+ Add</button>
    </div>
  </div>
  <div class="card">
    <div class="card-title">Summary</div>
    <div class="totals-split">
      <div>
        <div class="fg" style="margin-bottom:12px">
          <div><label>Extra Charges</label><input type="number" id="extra-charges" value="0" min="0" oninput="recalc()"></div>
          <div><label>Extra Discount</label><input type="number" id="extra-disc" value="0" min="0" oninput="recalc()"></div>
          <div><label>Round Off</label><input type="number" id="round-off" value="0" step="0.01" oninput="recalc()"></div>
          <div><label>Payment Status</label><select id="pay-status"><option>Paid</option><option>Unpaid</option><option>Partial</option></select></div>
        </div>
        <div><label>Remarks</label><textarea id="remarks" rows="2"></textarea></div>
      </div>
      <div><table class="tot-table">
        <tr><td>SubTotal</td><td id="t-sub">0.00</td></tr>
        <tr><td>Extra Charges</td><td id="t-extra">0.00</td></tr>
        <tr><td>Discount</td><td id="t-disc">0.00</td></tr>
        <tr><td>CGST</td><td id="t-cgst">0.00</td></tr>
        <tr><td>SGST</td><td id="t-sgst">0.00</td></tr>
        <tr><td>IGST</td><td id="t-igst">0.00</td></tr>
        <tr><td>Round Off</td><td id="t-round">0.00</td></tr>
        <tr class="grand"><td>Grand Total</td><td id="t-grand">0.00</td></tr>
      </table></div>
    </div>
  </div>
  <button class="btn btn-primary btn-full" id="gen-btn" onclick="generateBill()">&#11015; Generate Invoice &amp; Download PDF</button>
  <div style="height:36px"></div>
</div>

<!-- HISTORY -->
<div class="page" id="page-history">
  <div class="hist-hdr">
    <h2>Bill History</h2>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <input id="hist-search" placeholder="Search name or invoice..." style="width:210px" oninput="renderHistory()">
      <button class="btn-x" onclick="clearAll()">Clear All</button>
    </div>
  </div>
  <div id="bill-list"></div>
</div>

<!-- SETTINGS -->
<div class="page" id="page-settings">
  <div class="stab-row">
    <button class="stab active" onclick="sTab('lab')">Lab Details</button>
    <button class="stab" onclick="sTab('bank')">Bank &amp; Terms</button>
    <button class="stab" onclick="sTab('tests')">Test Master</button>
  </div>
  <div id="stab-lab">
    <div class="card">
      <div class="card-title">Lab / Company Info</div>
      <div class="fg">
        <div class="full"><label>Lab Name</label><input id="s-lab-name"></div>
        <div class="full"><label>Office Address</label><input id="s-lab-addr"></div>
        <div><label>Phone</label><input id="s-lab-phone"></div>
        <div><label>Email</label><input id="s-lab-email"></div>
        <div><label>PAN No.</label><input id="s-pan"></div>
        <div><label>GST No.</label><input id="s-gst"></div>
        <div><label>License No.</label><input id="s-license"></div>
        <div><label>Invoice Prefix</label><input id="s-inv-prefix" style="max-width:90px"></div>
      </div>
      <div style="margin-top:14px"><button class="btn btn-primary" onclick="saveSettings()">&#128190; Save</button></div>
    </div>
  </div>
  <div id="stab-bank" style="display:none">
    <div class="card">
      <div class="card-title">Bank Details</div>
      <div class="fg">
        <div><label>Bank Name</label><input id="s-bank-name"></div>
        <div><label>A/C Name</label><input id="s-bank-ac-name"></div>
        <div><label>A/C No.</label><input id="s-bank-ac"></div>
        <div><label>A/C Type</label><input id="s-bank-type"></div>
        <div><label>IFSC</label><input id="s-bank-ifsc"></div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Terms &amp; Conditions</div>
      <textarea id="s-terms" rows="4"></textarea>
    </div>
    <button class="btn btn-primary" onclick="saveSettings()">&#128190; Save</button>
    <div style="height:20px"></div>
  </div>
  <div id="stab-tests" style="display:none">
    <div class="card">
      <div class="card-title">Test Master List</div>
      <p style="font-size:12px;color:#718096;margin-bottom:12px">These appear in the Quick Add dropdown.</p>
      <div id="master-wrap"></div>
      <div class="add-row" style="margin-top:14px">
        <input id="m-name" style="flex:2;min-width:150px" placeholder="Test name">
        <input id="m-rate" type="number" style="max-width:110px" min="0" placeholder="Rate">
        <input id="m-hsn" style="max-width:100px" value="None" placeholder="HSN">
        <button class="btn btn-blue btn-sm" onclick="addMasterTest()">+ Add Test</button>
      </div>
    </div>
  </div>
  <div style="height:40px"></div>
</div>
<script>
// ══════════════════ STATE ══════════════════
let tests=[], allData={settings:{},masterTests:[],bills:[]}, histBills=[];

// ══════════════════ BOOT ══════════════════
async function boot(){
  try{
    const r=await fetch('/api/data');
    allData=await r.json();
    fillSettings(); fillQuickAdd(); defaultDates(); nextInvNo(); renderTests();
  }catch(e){ toast('Could not load data','error'); }
}

function defaultDates(){
  const t=new Date().toISOString().split('T')[0];
  document.getElementById('inv-date').value=t;
  document.getElementById('order-date').value=t;
}
function nextInvNo(){
  const p=allData.settings.invPrefix||'S';
  const nums=(allData.bills||[]).map(b=>parseInt((b.invoiceNo||'').replace(/\D/g,''))||0);
  const n=nums.length?Math.max.apply(null,nums)+1:1;
  document.getElementById('inv-number').value=p+String(n).padStart(8,'0');
}

// ══════════════════ NAV ══════════════════
function showPage(id){
  ['form','history','settings'].forEach(p=>{
    document.getElementById('page-'+p).classList.remove('active');
    document.getElementById('tab-'+p).classList.remove('active');
  });
  document.getElementById('page-'+id).classList.add('active');
  document.getElementById('tab-'+id).classList.add('active');
  if(id==='history') loadHistory();
  if(id==='settings'){ fillSettings(); renderMaster(); }
}
function sTab(t){
  ['lab','bank','tests'].forEach(x=>document.getElementById('stab-'+x).style.display = x===t?'block':'none');
  document.querySelectorAll('.stab').forEach((b,i)=>b.classList.toggle('active',['lab','bank','tests'][i]===t));
  if(t==='tests') renderMaster();
}

// ══════════════════ SETTINGS ══════════════════
const SMAP={'s-lab-name':'labName','s-lab-addr':'labAddr','s-lab-phone':'labPhone','s-lab-email':'labEmail',
 's-pan':'pan','s-gst':'gst','s-license':'license','s-inv-prefix':'invPrefix','s-bank-name':'bankName',
 's-bank-ac-name':'bankAcName','s-bank-ac':'bankAc','s-bank-type':'bankType','s-bank-ifsc':'bankIfsc','s-terms':'terms'};

function fillSettings(){
  const s=allData.settings||{};
  Object.keys(SMAP).forEach(id=>{ const el=document.getElementById(id); if(el&&s[SMAP[id]]!=null) el.value=s[SMAP[id]]; });
}
async function saveSettings(){
  const s={};
  Object.keys(SMAP).forEach(id=>{ s[SMAP[id]]=v(id); });
  s.invPrefix=s.invPrefix||'S';
  try{
    await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(s)});
    allData.settings=s; toast('Settings saved'); nextInvNo();
  }catch(e){ toast('Save failed','error'); }
}

// ══════════════════ MASTER TESTS ══════════════════
function fillQuickAdd(){
  const sel=document.getElementById('quick-test');
  sel.innerHTML='<option value="">&mdash; Quick add from master list &mdash;</option>'+
    (allData.masterTests||[]).map((t,i)=>'<option value="'+i+'">'+esc(t.name)+' &mdash; Rs.'+t.rate+'</option>').join('');
}
function quickAdd(){
  const sel=document.getElementById('quick-test'); if(sel.value==='') return;
  const t=allData.masterTests[+sel.value];
  tests.push({desc:t.name,hsn:t.hsn||'None',unit:'NOS',qty:1,rate:+t.rate,gst:0,disc:0});
  renderTests(); sel.value='';
}
function renderMaster(){
  const w=document.getElementById('master-wrap'); const L=allData.masterTests||[];
  if(!L.length){ w.innerHTML='<p style="color:#a0aec0;font-size:13px">No tests yet.</p>'; return; }
  w.innerHTML='<table class="mtbl"><thead><tr><th>Test Name</th><th>Rate</th><th>HSN</th><th></th></tr></thead><tbody>'+
    L.map((t,i)=>'<tr><td>'+esc(t.name)+'</td><td>Rs.'+Number(t.rate).toFixed(2)+'</td><td>'+esc(t.hsn)+
    '</td><td><button class="btn-x" onclick="delMaster('+i+')">&times;</button></td></tr>').join('')+'</tbody></table>';
}
async function addMasterTest(){
  const n=v('m-name').trim(); if(!n){ toast('Enter test name','error'); return; }
  allData.masterTests.push({name:n,rate:parseFloat(v('m-rate'))||0,hsn:v('m-hsn')||'None'});
  await pushMaster(); document.getElementById('m-name').value=''; document.getElementById('m-rate').value='';
  renderMaster(); fillQuickAdd(); toast('Test added');
}
async function delMaster(i){ allData.masterTests.splice(i,1); await pushMaster(); renderMaster(); fillQuickAdd(); }
async function pushMaster(){
  await fetch('/api/master-tests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(allData.masterTests)});
}

// ══════════════════ TEST ROWS ══════════════════
function addTest(){
  const d=v('new-desc').trim(); if(!d){ toast('Enter test description','error'); return; }
  tests.push({desc:d,hsn:v('new-hsn')||'None',unit:v('new-unit')||'NOS',
    qty:parseFloat(v('new-qty'))||1,rate:parseFloat(v('new-rate'))||0,
    gst:parseFloat(v('new-gst'))||0,disc:parseFloat(v('new-disc'))||0});
  renderTests();
  ['new-desc','new-rate'].forEach(i=>document.getElementById(i).value='');
  document.getElementById('new-qty').value='1';
  document.getElementById('new-gst').value='0';
  document.getElementById('new-disc').value='0';
}
function delTest(i){ tests.splice(i,1); renderTests(); }
function renderTests(){
  const b=document.getElementById('test-body');
  if(!tests.length){ b.innerHTML='<tr><td colspan="10" style="text-align:center;color:#a0aec0;padding:20px 0">No tests added yet</td></tr>'; recalc(); return; }
  b.innerHTML=tests.map(function(t,i){
    const base=t.qty*t.rate, da=base*t.disc/100, tx=base-da, amt=tx+tx*t.gst/100;
    return '<tr><td style="text-align:center">'+(i+1)+'</td><td>'+esc(t.desc)+'</td>'+
    '<td><input value="'+esc(t.hsn)+'" onchange="tests['+i+'].hsn=this.value"></td>'+
    '<td><input value="'+esc(t.unit)+'" onchange="tests['+i+'].unit=this.value" style="width:46px"></td>'+
    '<td><input type="number" value="'+t.qty+'" min="0.01" step="0.01" onchange="tests['+i+'].qty=parseFloat(this.value)||1;renderTests()" style="width:48px"></td>'+
    '<td><input type="number" value="'+t.rate+'" min="0" step="0.01" onchange="tests['+i+'].rate=parseFloat(this.value)||0;renderTests()" style="width:70px"></td>'+
    '<td><input type="number" value="'+t.gst+'" min="0" max="28" onchange="tests['+i+'].gst=parseFloat(this.value)||0;renderTests()" style="width:46px"></td>'+
    '<td><input type="number" value="'+t.disc+'" min="0" max="100" onchange="tests['+i+'].disc=parseFloat(this.value)||0;renderTests()" style="width:46px"></td>'+
    '<td style="text-align:right;font-weight:600">'+money(amt)+'</td>'+
    '<td><button class="btn-x" onclick="delTest('+i+')">&times;</button></td></tr>';
  }).join('');
  recalc();
}

// ══════════════════ CALC ══════════════════
function calcTotals(){
  let net=0,disc=0,cg=0,sg=0;
  tests.forEach(function(t){
    const base=t.qty*t.rate, da=base*t.disc/100, tx=base-da;
    disc+=da; cg+=tx*t.gst/2/100; sg+=tx*t.gst/2/100; net+=tx;
  });
  const extra=parseFloat(v('extra-charges'))||0, xd=parseFloat(v('extra-disc'))||0, ro=parseFloat(v('round-off'))||0;
  return {net:net,disc:disc,cg:cg,sg:sg,extra:extra,xd:xd,ro:ro,grand:net+cg+sg+extra-xd+ro};
}
function recalc(){
  const c=calcTotals();
  set('t-sub',money(c.net)); set('t-extra',money(c.extra)); set('t-disc',money(c.disc+c.xd));
  set('t-cgst',money(c.cg)); set('t-sgst',money(c.sg)); set('t-igst','0.00');
  set('t-round',money(c.ro)); set('t-grand',money(c.grand));
}

// ══════════════════ GENERATE ══════════════════
async function generateBill(){
  if(!tests.length){ toast('Add at least one test','error'); return; }
  const btn=document.getElementById('gen-btn');
  btn.disabled=true; btn.innerHTML='&#9203; Generating...';
  try{
    const c=calcTotals();
    const bill={invoiceNo:v('inv-number'),invDate:v('inv-date'),poNo:v('po-number'),orderDate:v('order-date'),
      clientName:v('client-name'),clientAddr1:v('client-addr1'),clientCity:v('client-city'),
      clientPin:v('client-pin'),clientGst:v('client-gst'),clientPhone:v('client-phone'),
      tests:JSON.parse(JSON.stringify(tests)),
      extraCharges:c.extra,extraDisc:c.xd,roundOff:c.ro,
      subtotalNet:c.net+c.cg+c.sg,totalDisc:c.disc,totalCgst:c.cg,totalSgst:c.sg,totalIgst:0,
      grand:c.grand,payStatus:v('pay-status'),remarks:v('remarks')};

    const res=await fetch('/api/bills',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(bill)});
    const saved=await res.json();
    bill.id=saved.id;
    allData.bills=allData.bills||[]; allData.bills.unshift(bill);

    downloadPDF(bill, allData.settings);
    toast('Invoice saved & PDF downloaded');
    nextInvNo(); resetForm();
  }catch(e){ console.error(e); toast('Error: '+e.message,'error'); }
  finally{ btn.disabled=false; btn.innerHTML='&#11015; Generate Invoice &amp; Download PDF'; }
}

function resetForm(){
  tests=[]; renderTests();
  ['client-name','client-addr1','client-city','client-pin','client-gst','client-phone','po-number','remarks'].forEach(function(i){
    const e=document.getElementById(i); if(e) e.value='';
  });
  document.getElementById('extra-charges').value='0';
  document.getElementById('extra-disc').value='0';
  document.getElementById('round-off').value='0';
  defaultDates(); recalc();
}

// ══════════════════ HISTORY ══════════════════
async function loadHistory(){
  try{ const r=await fetch('/api/bills'); histBills=await r.json(); renderHistory(); }
  catch(e){ toast('Could not load history','error'); }
}
function renderHistory(){
  const list=document.getElementById('bill-list');
  const q=(v('hist-search')||'').toLowerCase();
  const f=histBills.filter(function(b){
    return (b.clientName||'').toLowerCase().indexOf(q)>-1 || (b.invoiceNo||'').toLowerCase().indexOf(q)>-1;
  });
  if(!f.length){ list.innerHTML='<div class="empty">No bills found.</div>'; return; }
  list.innerHTML=f.map(function(b){
    return '<div class="bill-card"><div><div class="bc-inv">'+esc(b.invoiceNo)+'</div>'+
    '<div class="bc-name">'+esc(b.clientName||'-')+'</div>'+
    '<div class="bc-date">'+esc(b.invDate)+' &middot; '+esc(b.payStatus||'')+'</div></div>'+
    '<div style="text-align:right"><div class="bc-amt">'+money(b.grand)+'</div>'+
    '<div style="display:flex;gap:6px;margin-top:6px">'+
    '<button class="btn btn-green btn-sm" onclick="rePDF('+b.id+')">&#11015; PDF</button>'+
    '<button class="btn-x" onclick="delBill('+b.id+')">&times; Delete</button></div></div></div>';
  }).join('');
}
function rePDF(id){
  const b=histBills.filter(function(x){return x.id===id;})[0];
  if(b) downloadPDF(b, allData.settings);
}
async function delBill(id){
  if(!confirm('Delete this bill?')) return;
  await fetch('/api/bills/'+id,{method:'DELETE'});
  histBills=histBills.filter(function(b){return b.id!==id;});
  allData.bills=(allData.bills||[]).filter(function(b){return b.id!==id;});
  renderHistory(); toast('Bill deleted');
}
async function clearAll(){
  if(!confirm('Delete ALL bill history? Cannot be undone.')) return;
  await fetch('/api/bills/clear',{method:'POST'});
  histBills=[]; allData.bills=[]; renderHistory(); toast('History cleared');
}

// ══════════════════ HELPERS ══════════════════
function v(id){ const e=document.getElementById(id); return e?e.value:''; }
function set(id,t){ const e=document.getElementById(id); if(e) e.textContent=t; }
function money(n){ return Number(n||0).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2}); }
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }
function toast(m,t){
  const e=document.getElementById('toast');
  e.textContent=m; e.className='toast show '+(t||'success');
  clearTimeout(e._t); e._t=setTimeout(function(){ e.classList.remove('show'); },3000);
}
function numToWords(n){
  const o=['','ONE','TWO','THREE','FOUR','FIVE','SIX','SEVEN','EIGHT','NINE','TEN','ELEVEN','TWELVE',
    'THIRTEEN','FOURTEEN','FIFTEEN','SIXTEEN','SEVENTEEN','EIGHTEEN','NINETEEN'];
  const t=['','','TWENTY','THIRTY','FORTY','FIFTY','SIXTY','SEVENTY','EIGHTY','NINETY'];
  function h(x){
    if(x===0) return '';
    if(x<20) return o[x]+' ';
    if(x<100) return t[Math.floor(x/10)]+(x%10?' '+o[x%10]:'')+' ';
    return o[Math.floor(x/100)]+' HUNDRED '+h(x%100);
  }
  let s='',r=Math.round(n);
  if(r===0) return 'ZERO ONLY';
  if(r>=10000000){ s+=h(Math.floor(r/10000000))+'CRORE '; r%=10000000; }
  if(r>=100000){ s+=h(Math.floor(r/100000))+'LAKH '; r%=100000; }
  if(r>=1000){ s+=h(Math.floor(r/1000))+'THOUSAND '; r%=1000; }
  if(r>=100){ s+=h(Math.floor(r/100))+'HUNDRED '; r%=100; }
  if(r>0) s+=h(r);
  return s.trim()+' ONLY';
}

// ═══════════════════════════════════════════════════════
//  PDF ENGINE  (jsPDF + autoTable)
// ═══════════════════════════════════════════════════════
function downloadPDF(bill, s){
  if(!window.jspdf || !window.jspdf.jsPDF){
    toast('PDF library not loaded. Check your internet connection.','error');
    return;
  }
  const jsPDFCtor = window.jspdf.jsPDF;
  const doc = new jsPDFCtor({unit:'mm',format:'a4'});
  s = s || {};

  const M=8, PW=210, W=PW-M*2;
  let y=M;
  const GREY=[235,235,235], LINE=[40,40,40];

  // HEADER
  doc.setDrawColor(40,40,40); doc.setLineWidth(0.3);
  const hdrH=20;
  doc.rect(M,y,W,hdrH);
  doc.setFont('helvetica','bold'); doc.setFontSize(7);
  doc.text('GST INVOICE', PW/2, y+4, {align:'center'});
  doc.setFontSize(15);
  doc.text(String(s.labName||'Lab Name'), PW/2, y+10.5, {align:'center'});
  doc.setFont('helvetica','normal'); doc.setFontSize(7);
  doc.text('Office Address : '+(s.labAddr||''), PW/2, y+14.5, {align:'center'});
  doc.text('Cell : '+(s.labPhone||'')+' , Email: '+(s.labEmail||''), PW/2, y+18, {align:'center'});
  y+=hdrH;

  // META
  const metaH=18, splitX=M+W*0.60, lx=M+2, rx=splitX+2;
  doc.rect(M,y,W,metaH); doc.line(splitX,y,splitX,y+metaH);
  doc.setFontSize(7.5);
  let ly=y+4;
  doc.setFont('helvetica','bold'); doc.text('PAn No :',lx,ly);
  doc.setFont('helvetica','normal'); doc.text(String(s.pan||''),lx+14,ly);
  ly+=4; doc.text('Tax is Payable on reverse Charges (Yes/No)',lx,ly);
  ly+=4;
  doc.setFont('helvetica','bold'); doc.text('Vendor Code :',lx,ly); doc.text('Order / Po No. :',lx+40,ly);
  doc.setFont('helvetica','normal'); doc.text(String(bill.poNo||''),lx+70,ly);
  ly+=4;
  doc.setFont('helvetica','bold'); doc.text('Proposal No. :',lx,ly); doc.text('Order Date :',lx+40,ly);
  doc.setFont('helvetica','normal'); doc.text(String(bill.orderDate||''),lx+65,ly);
  let ry=y+4;
  doc.setFont('helvetica','bold'); doc.text('Invoice No. :',rx,ry);
  doc.setFont('helvetica','normal'); doc.text(String(bill.invoiceNo||''),rx+22,ry);
  ry+=4.5;
  doc.setFont('helvetica','bold'); doc.text('Date :',rx,ry);
  doc.setFont('helvetica','normal'); doc.text(String(bill.invDate||''),rx+22,ry);
  ry+=4.5;
  doc.setFont('helvetica','bold'); doc.text('License key :',rx,ry);
  doc.setFont('helvetica','normal'); doc.text(String(s.license||''),rx+22,ry);
  y+=metaH;

  // BILL TO / SHIP TO
  const bsH=24, midX=M+W*0.5;
  doc.rect(M,y,W,bsH); doc.line(midX,y,midX,y+bsH);
  doc.setFontSize(7.5);
  let by=y+4;
  doc.setFont('helvetica','bold'); doc.text('Bill to :',lx,by);
  by+=4; doc.text(String(bill.clientName||''),lx,by);
  doc.setFont('helvetica','normal');
  by+=4; doc.text(String(bill.clientAddr1||''),lx,by,{maxWidth:W*0.5-6});
  by+=4; doc.text(String(bill.clientCity||'')+' '+String(bill.clientPin||''),lx,by);
  if(bill.clientGst){ by+=4; doc.text('GSTIN: '+bill.clientGst,lx,by); }
  let sy=y+4;
  doc.setFont('helvetica','bold'); doc.text('Ship to :',midX+2,sy);
  sy+=4; doc.text(String(bill.clientName||''),midX+2,sy);
  doc.setFont('helvetica','normal');
  sy+=4; doc.text(String(bill.clientAddr1||''),midX+2,sy,{maxWidth:W*0.5-6});
  y+=bsH;

  // ITEMS
  const T=bill.tests||[];
  const body=T.map(function(t,i){
    const qty=+t.qty||0, rate=+t.rate||0, gst=+t.gst||0, disc=+t.disc||0;
    const base=qty*rate, da=base*disc/100, tx=base-da, amt=tx+tx*gst/100;
    return [String(i+1),String(t.desc||''),String(t.hsn||'None'),String(t.unit||'NOS'),
            qty.toFixed(2),money(rate),String(gst),disc.toFixed(2),money(amt)];
  });
  for(let i=0;i<Math.max(0,6-T.length);i++) body.push(['','','','','','','','','']);

  doc.autoTable({
    startY:y, margin:{left:M,right:M}, tableWidth:W,
    head:[['Sr.No.','Item Details','HSN/SAC\nCode','Unit','Qty.','Rate','GST\n%','Disc\n%','Amount\nRs.']],
    body:body, theme:'grid',
    styles:{fontSize:7,cellPadding:1.4,lineColor:[120,120,120],lineWidth:0.15,textColor:[0,0,0],overflow:'linebreak',valign:'middle'},
    headStyles:{fillColor:GREY,textColor:[0,0,0],fontStyle:'bold',halign:'center',lineColor:LINE,lineWidth:0.25,fontSize:6.5},
    columnStyles:{0:{cellWidth:10,halign:'center'},1:{cellWidth:'auto'},2:{cellWidth:15,halign:'center'},
      3:{cellWidth:11,halign:'center'},4:{cellWidth:11,halign:'center'},5:{cellWidth:20,halign:'right'},
      6:{cellWidth:11,halign:'center'},7:{cellWidth:11,halign:'right'},8:{cellWidth:22,halign:'right'}},
    didParseCell:function(d){ if(d.section==='body') d.cell.styles.minCellHeight=5.5; }
  });
  y=doc.lastAutoTable.finalY;

  // TOTALS
  const grand=+bill.grand||0, cgst=+bill.totalCgst||0, sgst=+bill.totalSgst||0, igst=+bill.totalIgst||0;
  const sub=(+bill.subtotalNet||0)-cgst-sgst;
  const extra=+bill.extraCharges||0;
  const disc=(+bill.totalDisc||0)+(+bill.extraDisc||0);
  const roff=+bill.roundOff||0;
  const totRows=[['SubTotal',money(sub)],['Fright','0.00'],['Extra Charges',money(extra)],
    ['Discount',money(disc)],['CGST Amt',money(cgst)],['SGST Amt',money(sgst)],
    ['IGST Amt',money(igst)],['Round Off',money(roff)],['Grandtotal',money(grand)]];
  const TOTW=58;
  doc.autoTable({
    startY:y, margin:{left:M+W-TOTW,right:M}, tableWidth:TOTW,
    body:totRows, theme:'grid',
    styles:{fontSize:7,cellPadding:1.3,lineColor:[150,150,150],lineWidth:0.15,textColor:[0,0,0]},
    columnStyles:{0:{cellWidth:34},1:{cellWidth:24,halign:'right'}},
    didParseCell:function(d){
      if(d.row.index===totRows.length-1){
        d.cell.styles.fontStyle='bold'; d.cell.styles.fontSize=8;
        d.cell.styles.lineWidth={top:0.5,right:0.15,bottom:0.15,left:0.15};
      }
    }
  });
  const totEnd=doc.lastAutoTable.finalY;

  doc.setDrawColor(40,40,40); doc.setLineWidth(0.3);
  doc.rect(M,y,W-TOTW,totEnd-y);
  doc.setFontSize(7.5); doc.setFont('helvetica','bold');
  doc.text('Amount in words :',M+2,y+4);
  const wl=doc.splitTextToSize(numToWords(grand),W-TOTW-6);
  doc.text(wl,M+2,y+8);
  if(bill.remarks){
    doc.setFont('helvetica','italic'); doc.setFontSize(7);
    doc.text(doc.splitTextToSize(String(bill.remarks),W-TOTW-6),M+2,y+8+wl.length*3.6+2);
  }
  y=totEnd;

  // GST BREAKDOWN
  const gmap={};
  T.forEach(function(t){
    const r=+t.gst||0;
    if(!gmap[r]) gmap[r]={tx:0,cg:0,sg:0};
    const base=(+t.qty||0)*(+t.rate||0), da=base*(+t.disc||0)/100, tx=base-da;
    gmap[r].tx+=tx; gmap[r].cg+=tx*r/2/100; gmap[r].sg+=tx*r/2/100;
  });
  const gstBody=[0,5,12,18,28].map(function(r){
    const g=gmap[r]||{tx:0,cg:0,sg:0};
    return [r+' (%)', g.tx?money(g.tx):'0.00', money(g.sg), money(g.cg), '0.00', money(g.cg+g.sg)];
  });
  doc.autoTable({
    startY:y, margin:{left:M,right:M}, tableWidth:W,
    head:[['GST(%)','Taxable Value','SGST AMT','CGST AMT','IGST AMT','Total AMT']],
    body:gstBody, theme:'grid',
    styles:{fontSize:7,cellPadding:1.3,halign:'center',lineColor:[150,150,150],lineWidth:0.15,textColor:[0,0,0]},
    headStyles:{fillColor:GREY,textColor:[0,0,0],fontStyle:'bold',lineColor:LINE,lineWidth:0.25},
    columnStyles:{0:{cellWidth:W/6,fontStyle:'bold',halign:'left'}}
  });
  y=doc.lastAutoTable.finalY;

  // OUTSTANDING
  doc.setDrawColor(40,40,40); doc.setLineWidth(0.3);
  doc.rect(M,y,W,6);
  doc.setFont('helvetica','bold'); doc.setFontSize(8);
  doc.text('Total Outstanding : '+money(grand),M+2,y+4);
  y+=6;

  // FOOTER
  const fH=30, c1=M+W/3, c2=M+2*W/3;
  doc.rect(M,y,W,fH); doc.line(c1,y,c1,y+fH); doc.line(c2,y,c2,y+fH);
  doc.setFontSize(7); doc.setFont('helvetica','bold');
  doc.text('Terms & Conditions',M+2,y+4);
  doc.setFont('helvetica','normal'); doc.setFontSize(6.2);
  doc.text(doc.splitTextToSize(String(s.terms||''),W/3-5),M+2,y+7.5);
  doc.setFontSize(7); doc.setFont('helvetica','bold');
  doc.text('Bank Details :',c1+2,y+4);
  doc.setFont('helvetica','normal'); doc.setFontSize(6.5);
  let bky=y+7.5;
  ['Bank Name : '+(s.bankName||''),'A/C Name : '+(s.bankAcName||''),
   'A/C No : '+(s.bankAc||''),'('+(s.bankType||'')+')',
   s.bankIfsc?('IFSC : '+s.bankIfsc):''
  ].filter(Boolean).forEach(function(t){ doc.text(t,c1+2,bky,{maxWidth:W/3-5}); bky+=3.4; });
  doc.setFontSize(7); doc.setFont('helvetica','bold');
  doc.text(doc.splitTextToSize(String(s.labName||''),W/3-6),c2+W/6,y+4,{align:'center'});
  doc.setFont('helvetica','normal');
  doc.text('Authorised Signatory',c2+W/6,y+fH-3,{align:'center'});

  doc.save('Invoice_'+(bill.invoiceNo||'bill')+'.pdf');
}

boot();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
