#!/usr/bin/env python3
"""Independent arithmetic recomputation of selected Bering financial outputs.

Reads source hard-coded inputs and independently computes scenario cash flows.
Does not evaluate Excel formulas or verify commercial demand / contractual claims.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from openpyxl import load_workbook

SHEETS = {"rate":39,"project":42,"scenario":43,"dcf":44,"d2d":61,"margin":63,"change":65,"gates":67,"synthetic":69}

def numeric(v):
    if isinstance(v, bool) or not isinstance(v,(int,float)):
        raise ValueError(f"Non-numeric numeric input: {v!r}")
    return float(v)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--book",required=True,type=Path)
    ap.add_argument("--expected-sha256",type=str,default=None)
    ap.add_argument("--manifest",type=Path)
    ap.add_argument("--root",type=Path)
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    if bool(args.manifest) != bool(args.root):
        ap.error("--manifest and --root must be provided together")
    actual_sha=hashlib.sha256(args.book.read_bytes()).hexdigest()
    if args.expected_sha256 and actual_sha != args.expected_sha256.lower():
        ap.error("Workbook SHA-256 does not match pinned source")
    wf=load_workbook(args.book,data_only=False,read_only=True)
    wc=load_workbook(args.book,data_only=True,read_only=True)
    assert len(wf.sheetnames)==72
    tests=[]
    def verify(group,sheet,cell,expected,notes=""):
        actual=wc.worksheets[SHEETS[sheet]][cell].value
        if isinstance(expected,(int,float)):
            ok=isinstance(actual,(int,float)) and abs(float(actual)-expected)<=max(0.05,abs(expected)*1e-10)
        else:ok=actual==expected
        tests.append({"group":group,"sheet":wf.worksheets[SHEETS[sheet]].title,"cell":cell,"expected":expected,"cached":actual,"pass":ok,"notes":notes})
    scenario=wf.worksheets[SHEETS["scenario"]]
    inputs=[]
    for row in range(5,10):
        vals=[numeric(scenario.cell(row,col).value) for col in range(2,12)]
        capex,teu,mteu,gen,mgen,fish,mfish,ofrac,r,years=vals
        contribution=teu*mteu+gen*mgen+fish*mfish-capex*ofrac
        annuity=(1-(1+r)**(-years))/r
        npv=-capex+contribution*annuity
        verify("scenario","scenario",f"L{row}",contribution,"Independent sum of category contributions less fixed OPEX")
        verify("scenario","scenario",f"M{row}",npv,"Independent annuity NPV; simplified hypothetical")
        inputs.append({"row":row,"name":scenario.cell(row,1).value,"capex_rub":capex,"teu_annual":teu,"general_tonnes":gen,"fish_tonnes":fish,"contribution_rub":contribution,"npv_rub":npv,"discount_rate":r,"years":years,"assumptions_not_contracts":True})
    capex,teu,mteu,gen,mgen,fish,mfish,ofrac,r,years=[numeric(scenario.cell(8,col).value) for col in range(2,12)]
    fixed=capex*ofrac
    annuity=(1-(1+r)**(-years))/r
    required=(capex/annuity+fixed)
    break_even_teu=(required-gen*mgen-fish*mfish)/teu
    verify("break_even","scenario","B12",required,"Required annual contribution for zero NPV, fixed load")
    verify("break_even","scenario","B13",break_even_teu,"Simplified no-ramp break-even contribution per TEU")
    sdcf=wf.worksheets[SHEETS["dcf"]]
    npv_dcf=0.0
    ramp_pv=0.0
    noncontainer_rev=(gen*mgen+fish*mfish)
    for row in range(5,26):
        year=numeric(sdcf.cell(row,1).value)
        ramp=numeric(sdcf.cell(row,2).value)
        vols=(ramp*teu,ramp*gen,ramp*fish)
        variable=vols[0]*mteu+vols[1]*mgen+vols[2]*mfish
        cost=0 if year==0 else fixed
        investment=capex if year==0 else 0
        cashflow=variable-cost-investment
        df=1/(1+r)**year
        pv=cashflow*df
        npv_dcf+=pv
        if year>0:ramp_pv+=ramp*df
        for col,value in {"C":vols[0],"D":vols[1],"E":vols[2],"F":variable,"G":cost,"H":investment,"I":cashflow,"J":df,"K":pv}.items():
            verify("20y_dcf","dcf",f"{col}{row}",value,"Independent 20-year DCF rebuild")
    verify("20y_dcf","dcf","K27",npv_dcf,"Sum of independently computed PV values")
    for row in range(5,8):
        ss=wf.worksheets[SHEETS["rate"]]
        val=numeric(ss.cell(row,2).value)*numeric(ss.cell(row,3).value)*numeric(ss.cell(row,4).value)/365
        verify("inventory_time","rate",f"E{row}",val,"Product-value carrying cost, NOT project revenue")
    pj=wf.worksheets[SHEETS["project"]]
    verify("investor_claim_arithmetic","project","B15",numeric(pj["B11"].value)/numeric(wf.worksheets[33]["C6"].value),"30k vs observed historic 84k TEU ratio; no added demand")
    verify("investor_claim_arithmetic","project","B16",numeric(pj["B5"].value)-numeric(pj["B6"].value),"CAPEX less sponsor external financing claim")
    verify("investor_claim_arithmetic","project","B17",numeric(pj["B9"].value)/numeric(pj["B5"].value),"Claimed NPV relative to claimed capex")
    sh=wf.worksheets[SHEETS["change"]]
    verify("project_scope","change","D5",numeric(sh["C5"].value)/numeric(sh["B5"].value),"Capacity ratio is NOT increased paid demand")
    verify("project_scope","change","D6",numeric(sh["C6"].value)-numeric(sh["B6"].value),"Capacity difference not spare capacity")
    s=wf.worksheets[SHEETS["synthetic"]]
    for row in (5,6):
        contract,diverted,duplicate=[numeric(s.cell(row,j).value) for j in (2,3,4)]
        net=max(0,contract-diverted-duplicate)
        cm=net*numeric(s.cell(row,6).value)+diverted*(numeric(s.cell(row,6).value)-numeric(s.cell(row,7).value))-numeric(s.cell(row,8).value)
        verify("synthetic_only","synthetic",f"E{row}",net,"Synthetic TEST, not actual contract")
        verify("synthetic_only","synthetic",f"I{row}",cm,"Synthetic TEST, not forecast")
    for i in (5,6,7):
        verify("pilot_gate","margin",f"N{i}","HOLD","No documentary evidence accepted")
        verify("pilot_gate","d2d",f"F{i}","HOLD","Incomplete D2D pricing")
        verify("pilot_gate","gates",f"H{i}","HOLD","No accepted actual contracts/waybills/invoices")
    risk_synthetic={"contracted":100,"diverted":20,"duplicated":10,"new_unit_margin":9000,"old_unit_margin":5000,"fixed":100000,"risk":20000}
    net_new=risk_synthetic["contracted"]-risk_synthetic["diverted"]-risk_synthetic["duplicated"]
    risk_margin=net_new*risk_synthetic["new_unit_margin"]+risk_synthetic["diverted"]*(risk_synthetic["new_unit_margin"]-risk_synthetic["old_unit_margin"])-risk_synthetic["fixed"]-risk_synthetic["risk"]
    assert net_new==70 and risk_margin==590000
    ramp_break_even_unit_teu=(capex+fixed*annuity-noncontainer_rev*ramp_pv)/(teu*ramp_pv)
    archive=None
    if args.manifest and args.root:
        records=json.loads(args.manifest.read_text(encoding="utf-8"))["files"]
        items=[]
        for row in records:
            path=args.root/row["relative_path"]
            if not path.exists():
                lookup=list(args.root.rglob(row["original_filename"]))
                path=lookup[0] if len(lookup)==1 else path
            valid=path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
            items.append({"filename":row["original_filename"],"sha256":row["sha256"],"pass":valid})
        archive={"files":len(items),"passed":sum(x["pass"] for x in items),"items":items,"all_pass":all(x["pass"] for x in items)}
    totals={"tests":len(tests),"passed":sum(x["pass"] for x in tests),"failed":sum(not x["pass"] for x in tests)}
    result={"source_workbook":args.book.name,"source_sha256":actual_sha,"source_hash_gate":"MATCH" if args.expected_sha256 else "NOT_PINNED","source_sheet_count":len(wf.sheetnames),
            "tests":tests,"summary":totals,"scenarios":inputs,"dcf":{"npv_rub":npv_dcf,"presented_source_cached":wc.worksheets[44]["K27"].value,
            "zero_npv_teu_margin_no_ramp_rub_per_teu":break_even_teu,
            "zero_npv_teu_margin_with_ramp_rub_per_teu":ramp_break_even_unit_teu,"interpretation":"Audit diagnostic; no evidenced new cargo or contractual margin"},
            "risk_synthetic":{"net_new_containers":net_new,"incremental_cm_rub":risk_margin,"real_volume":False},
            "source_archive":archive,"formula_recalculation":"INDEPENDENT CALCULATIONS FOR LISTED CELLS ONLY; NOT FULL EXCEL RECALC",
            "bankable_forecast":False,"ready_for_investment_decision":False}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"source":result["source_sha256"],"summary":totals,"archive":None if not archive else [archive["passed"],archive["files"]],
                      "dcf_npv_rub":npv_dcf,"no_ramp_break_even_teu_cm_rub":break_even_teu,"ramp_break_even_teu_cm_rub":ramp_break_even_unit_teu},indent=2))
    return 1 if totals["failed"] or (archive and not archive["all_pass"]) else 0

if __name__=="__main__":
    raise SystemExit(main())
