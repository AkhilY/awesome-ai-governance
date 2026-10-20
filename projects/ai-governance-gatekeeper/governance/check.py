"""Documentation gate inspired by NIST AI RMF, not a compliance certification."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

def nonempty(value):
    return isinstance(value, str) and bool(value.strip())

def evaluate(data):
    if not isinstance(data, dict):
        return [{"id":"SCHEMA","status":"fail","reason":"Root must be an object"}]
    checks = []
    def check(code, passed, reason):
        checks.append({"id":code,"status":"pass" if passed else "fail","reason":reason})
    check("GOV-OWNER",nonempty(data.get("owner")),"Named accountable owner is required")
    check("MAP-PURPOSE",nonempty(data.get("intended_purpose")),"Document the intended purpose")
    check("MAP-DATA",isinstance(data.get("data_sources"),list) and len(data["data_sources"])>0 and all(nonempty(x) for x in data["data_sources"]),"Declare at least one data source")
    check("GOV-PRIVACY",nonempty(data.get("privacy_review")),"Record privacy review reference")
    check("MEASURE-EVAL",nonempty(data.get("evaluation_report")),"Provide evaluation report reference")
    check("MEASURE-FAIRNESS",nonempty(data.get("fairness_assessment")),"Provide fairness assessment reference")
    check("MANAGE-INCIDENT",nonempty(data.get("incident_response_plan")),"Document incident response arrangements")
    risk=data.get("risk_level")
    check("MAP-RISK",risk in ("low","medium","high"),"risk_level must be low, medium or high")
    if risk=="high":
        check("MANAGE-HUMAN",data.get("human_oversight") is True,"High risk requires human oversight")
        check("MANAGE-APPROVAL",nonempty(data.get("approval_reference")),"High risk requires approval reference")
        check("MANAGE-MITIGATION",nonempty(data.get("mitigation_plan")),"High risk requires mitigation plan")
    return checks

def main():
    parser=argparse.ArgumentParser(description="AI governance documentation gate")
    parser.add_argument("manifest",type=Path)
    parser.add_argument("--output",type=Path,default=Path("governance-report.json"))
    args=parser.parse_args()
    try:
        data=json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as error:
        print(f"Unable to load manifest: {error}",file=sys.stderr)
        return 2
    checks=evaluate(data)
    failures=sum(c["status"]=="fail" for c in checks)
    report={"system":data.get("system_name","unknown") if isinstance(data,dict) else "unknown","checked_at":datetime.now(timezone.utc).isoformat(),"result":"fail" if failures else "pass","failures":failures,"checks":checks,"notice":"Documentation validation only; not evidence of actual safety or regulatory compliance."}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    for item in checks:
        print(f"[{item['status'].upper():4}] {item['id']}: {item['reason']}")
    print(f"Result: {report['result']} ({failures} failures); report: {args.output}")
    return 1 if failures else 0

if __name__=="__main__":
    sys.exit(main())
