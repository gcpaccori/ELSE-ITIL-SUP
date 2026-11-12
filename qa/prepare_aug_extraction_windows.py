"""Prepare isolated August 2026 QA exporter from previously reviewed February C#.

On ELSE62 only. Use fixed SELECT; split request and gold. Never change
production code and do not overwrite previous QA exports.
"""
from pathlib import Path
ROOT=Path(r"C:\Temp\ELSE_ITIL_AUG2026_QA_20261110")
OLD=Path(r"C:\Temp\ELSE_ITIL_FEB100_QA_20261110")
if ROOT.exists():
    raise SystemExit("AUG_QA_OUTPUT_ALREADY_EXISTS")
ROOT.mkdir()
src=(OLD/"FebExporter.cs").read_text(encoding="utf-8")
patterns=[
    ("FebExporter","AugExporter"),
    (r"C:\Temp\ELSE_ITIL_FEB100_QA_20261110",r"C:\Temp\ELSE_ITIL_AUG2026_QA_20261110"),
    ("new DateTime(2026,2,1)","new DateTime(2026,8,1)"),
    ("new DateTime(2026,3,1)","new DateTime(2026,9,1)"),
    ("opened.Month!=2","opened.Month!=8"),
    ("OUT_OF_FEBRUARY_SCOPE","OUT_OF_AUGUST_SCOPE"),
    ("feb2026","aug2026"),
    ('month="2026-02"','month="2026-08"'),
    ("month=2,","month=8,"),
    ("FEB_QA_","AUG_QA_"),
]
for a,b in patterns:
    if a not in src:raise SystemExit("EXPECTED_SOURCE_FRAGMENT_MISSING_"+a)
    src=src.replace(a,b)
assert 'new DateTime(2026,2,1)' not in src
needle='''     var records=Path.Combine(root,"aug2026_requests.private.jsonl");'''
assert needle in src
src=src.replace(needle,'''
     if(data.Rows.Count!=1819)throw new Exception("AUG2026_COUNT_DRIFT");
'''+needle)
(ROOT/"AugExporter.cs").write_text(src,encoding="utf-8")
proj=(OLD/"FebExporter.csproj").read_text(encoding="utf-8")
assert 'FebExporter.cs' in proj
(ROOT/"AugExporter.csproj").write_text(
    proj.replace("FebExporter.cs","AugExporter.cs"),encoding="utf-8")
print("AUG_MONTH_CSHARP_PREPARED")
print("AUG_EXACT_EXPECTED_COUNT=1819")
