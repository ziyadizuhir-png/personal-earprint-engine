from pydantic import BaseModel

class IEMSummary(BaseModel):
    name: str
    slug: str
    status: str
    path: str
    has_measurement: bool
    has_preferred: bool
    has_metadata: bool
