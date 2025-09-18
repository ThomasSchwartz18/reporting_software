from app.db import SessionLocal
from app import models as m
from sqlalchemy import select

ops = ["SMT AOI","TH AOI","Rework","Test","Final Inspect"]
lines = ["Line 1","Line 2","Offline"]
defects = [
    {"code":"S-BRIDGE","name":"Solder bridge","description":"Unwanted solder connection","default_operation":"SMT AOI","component_class":"IC","category":"Solder"},
    {"code":"MIS-POL","name":"Polarity mismatch","description":"Polarity reversed or misaligned","default_operation":"SMT AOI","component_class":"DIODE","category":"Polarity"},
    {"code":"LIFT-LEAD","name":"Lifted lead","description":"Lead lifted from pad","default_operation":"SMT AOI","component_class":"IC","category":"Placement"},
    {"code":"TH-INSUF","name":"Insufficient solder (TH)","description":"Fillet not meeting criteria","default_operation":"TH AOI","component_class":"TH","category":"Solder"}
]

with SessionLocal() as s:
    # operations
    existing_ops = set(x[0] for x in s.execute(select(m.Operation.name)).all())
    for o in ops:
        if o not in existing_ops:
            s.add(m.Operation(name=o))
    # lines
    existing_lines = set(x[0] for x in s.execute(select(m.Line.name)).all())
    for l in lines:
        if l not in existing_lines:
            s.add(m.Line(name=l))
    # defects
    existing_def = set(x[0] for x in s.execute(select(m.DefectCode.code)).all())
    for d in defects:
        if d["code"] not in existing_def:
            s.add(m.DefectCode(**d))
    s.commit()
print("Seeded operations, lines, and defect codes.")
