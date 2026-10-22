from datetime import date
import secrets

def random_patient():
    family=secrets.choice(('SYNTHETIC','PHANTOM','TESTPERSON','EXAMPLE'))
    given=secrets.choice(('ALEX','JAMIE','MORGAN','ROBIN','SAM'))
    return {'patient_name':family+'^'+given,'mrn':'SYN-'+secrets.token_hex(4).upper(),
            'birth_date':date(1950+secrets.randbelow(55),1+secrets.randbelow(12),1+secrets.randbelow(28)).isoformat(),
            'sex':secrets.choice(('M','F','O','U'))}

def defaults():
    return {**random_patient(),'accession':'ACC-'+secrets.token_hex(5).upper(),
            'description':'CT Head','slices':5}
