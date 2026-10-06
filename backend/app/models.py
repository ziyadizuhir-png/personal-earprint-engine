from pydantic import BaseModel

class IEMSummary(BaseModel):
    name: str
    slug: str
    status: str
    path: str
    has_measurement: bool
    has_preferred: bool
    peq_source: str
    peq_valid: bool
    peq_filter_count: int
    peq_error: str | None = None
    ready: bool
    has_metadata: bool
