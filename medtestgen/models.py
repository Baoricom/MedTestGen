from datetime import date, datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, validator
from pydicom.uid import generate_uid
from uuid import uuid4

class GenerateRequest(BaseModel):
    patient_name: str = 'SYNTHETIC^ALEX'
    mrn: str = 'SYN-001'
    birth_date: date = date(1980, 1, 1)
    sex: Literal['M', 'F', 'O', 'U'] = 'U'
    description: str = 'CT Head'
    accession: str = 'SYN-ACC-001'
    slices: int = Field(5, ge=1, le=10)

    @validator('slices', pre=True)
    def integer_count(cls, value):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError('Slice count must be an integer')
        return value

    @validator('patient_name', 'mrn', 'description', 'accession')
    def safe_text(cls, value, field):
        limit = 16 if field.name == 'accession' else 64
        if not value or len(value) > limit or value != value.strip():
            raise ValueError(f'Expected 1–{limit} characters without outer whitespace')
        if any(ord(c) < 32 or ord(c) == 127 for c in value) or '\\' in value:
            raise ValueError('Control characters and DICOM separators are not allowed')
        if field.name == 'patient_name':
            if value.count('^') > 1 or '=' in value or not value.split('^')[0]:
                raise ValueError('Use Family^Given notation')
        elif field.name in ('mrn', 'accession') and any(c in value for c in '|^~&'):
            raise ValueError('Identifier contains structural separators')
        return value

    @validator('birth_date')
    def past_date(cls, value):
        if value > date.today():
            raise ValueError('Birth date cannot be in the future')
        return value

    class Config:
        extra = 'forbid'
        allow_mutation = False

class Scenario(BaseModel):
    request: GenerateRequest
    created_at: datetime
    study_uid: str
    series_uid: str
    frame_uid: str
    sop_uids: tuple[str, ...]
    order_id: str
    message_id: str
    patient_uuid: str
    order_uuid: str
    study_uuid: str

    class Config:
        allow_mutation = False

def make_scenario(request: GenerateRequest) -> Scenario:
    return Scenario(request=request, created_at=datetime.now(timezone.utc),
        study_uid=generate_uid(), series_uid=generate_uid(), frame_uid=generate_uid(),
        sop_uids=tuple(generate_uid() for _ in range(request.slices)),
        order_id=uuid4().hex[:16], message_id=uuid4().hex[:20],
        patient_uuid=str(uuid4()), order_uuid=str(uuid4()), study_uuid=str(uuid4()))
