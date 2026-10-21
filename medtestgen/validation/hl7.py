from hl7apy.validation import Validator

def validate_order_tree(message):
    """Resolve hl7apy 1.3.5 choice-cardinality defect for our OBR-only profile."""
    def narrow(reference):
        if reference[0] not in ('sequence','choice'):
            return reference
        children=reference[1]
        if reference[0]=='choice' and {c[0] for c in children} >= {'OBR','RQD'}:
            children=tuple(c for c in children if c[0]=='OBR')
        mapped=tuple((c[0],narrow(c[1]),*c[2:]) for c in children)
        return ('sequence',mapped,*reference[2:])
    return Validator.validate(message,reference=narrow(message.reference))
from hl7apy.parser import parse_message
from hl7apy.consts import VALIDATION_LEVEL

def extract_hl7(payload):
    text=payload.decode('utf-8')
    parts=[line.split('|') for line in text.rstrip('\r').split('\r')]
    return {row[0]:row for row in parts}

def unescape(value):
    import re
    codes={'F':'|','S':'^','R':'~','E':'\\','T':'&'}
    return re.sub(r'\\([FSRET])\\',lambda match:codes[match[1]],value)

def validate_hl7(payload):
    errors=[]
    try:
        text=payload.decode('utf-8')
        message=parse_message(text.rstrip('\r'),validation_level=VALIDATION_LEVEL.STRICT,
                              find_groups=True)
        validate_order_tree(message)
        rows=[line.split('|') for line in text.rstrip('\r').split('\r')]
        if [row[0] for row in rows]!=['MSH','PID','PV1','ORC','OBR']:
            raise ValueError('Expected one MSH, PID, PV1, ORC, OBR in order')
        m,p,v,o,b=rows
        for field,actual,expected in [('MSH-9',m[8],'ORM^O01^ORM_O01'),
            ('MSH-11',m[10],'T'),('MSH-12',m[11],'2.5.1'),
            ('MSH-18',m[17],'UNICODE UTF-8'),('PV1-2',v[2],'O'),('ORC-1',o[1],'NW')]:
            if actual!=expected: errors.append({'field':field,'reason':'Unexpected profile value'})
        for field,actual in [('PID-3',p[3]),('PID-5',p[5]),('ORC-2',o[2]),
            ('ORC-3',o[3]),('OBR-2',b[2]),('OBR-3',b[3]),('OBR-4',b[4]),('OBR-18',b[18])]:
            if not actual.split('^')[0]: errors.append({'field':field,'reason':'Required value missing'})
        if p[8] not in ('M','F','O','U'): errors.append({'field':'PID-8','reason':'Invalid sex'})
        if o[2]!=b[2] or o[3]!=b[3]: errors.append({'field':'ORC/OBR','reason':'Order identifiers differ'})
    except Exception as exc:
        errors.append({'field':'message','reason':str(exc)})
    return {'status':'FAILED' if errors else 'PASSED','findings':errors,
            'coverage':'HL7 v2.5.1 strict message structure and MedTestGen profile'}
