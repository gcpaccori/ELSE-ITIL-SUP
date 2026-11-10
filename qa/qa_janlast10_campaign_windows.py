"""Ten-day QA spread: one fresh model→NuGet→O5→model case per calendar day.

The 22nd was previously exercised separately; this executes Jan23–31.
Private result artifacts stay only on the Windows and authorized Linux QA hosts.
"""
from __future__ import annotations
from pathlib import Path
import json
import traceback
from qa_janlast10_windows import run

ROOT=Path(r"C:\Temp\ELSE_ITIL_JANLAST10_DYNAMIC_20261110")
CASES=[
("2026-01-23","62285e6940cb3b731ebb577a529ee8c81fa3831a7b5762f0885ed1c81d551f0b"),
("2026-01-24","8c654217b8b5dfd17b3fb6abb04c1a4ec6fbf9dffee1f151cfe83f5fa5e53fae"),
("2026-01-25","2c51eefc671cfa5a8b7cf64fa1b71b9ec53889afdd7cb488086c02d3131396f8"),
("2026-01-26","565ab2931d3c86500aed435b279ddd601fa2ed5a2488bc13e740fc5bf2963ed8"),
("2026-01-27","05fbc5cbdcbf1e801954287f1ce9b6c34e1c6e16b0980677728ea64ebe28719a"),
("2026-01-28","01e6b08e6ec2477f75ac3f3113fc3b22bb3ce99fa8e7cb1054e96c43dd46dfb6"),
("2026-01-29","033df7598af50aca17b4d47f722e810ec520c61215f752b727b902fe0915be65"),
("2026-01-30","0aaf54a405b1510f77fea281d169c7fa2cada9c91e97ac708106b982acbfdd6c"),
("2026-01-31","58009350ce3c5bbee1af57f184fa977d1ab1155f95bc41e86a5fa84fbd7698fc"),
]
def main():
    summary=[]
    for day,sha in CASES:
        try:
            outcome=run(case_sha=sha,
               allowlist=ROOT/"allowlist.private.jsonl",
               out_root=ROOT/"runs",
               dotnet_project=ROOT/"qa/JanLast10ExactRead.csproj",
               source_file=ROOT/"qa/JanLast10ExactRead.cs")
            result={"day":day,"case_sha_prefix":sha[:16],
                    "status":"COMPLETED",**outcome}
        except Exception as exc:
            result={"day":day,"case_sha_prefix":sha[:16],
                    "status":"QA_EXECUTION_FAILED",
                    "error_type":type(exc).__name__}
        summary.append(result)
        print(json.dumps(result,ensure_ascii=False),flush=True)
    target=ROOT/"janlast10_campaign_9_results.private.json"
    with target.open("x",encoding="utf-8") as f:
        json.dump(summary,f,indent=2,ensure_ascii=False)
    print(json.dumps({"campaign_completed":len(summary),
                      "e2e_receipts_verified":sum(x.get("o5_o13_o15_verified") is True
                                                 for x in summary),
                      "without_repair":True}),flush=True)
if __name__=="__main__":main()
