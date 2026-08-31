"""Break-glass request payload (#406)."""

from pydantic import BaseModel, Field


class BreakGlassRequest(BaseModel):
    """Why an admin needs to read one private record.

    Mandatory and non-empty: the reason is the whole point. An access with no
    stated cause is a standing permission with extra steps, and the record this
    writes is shown to the person whose record was read.
    """

    #: Long enough to be a sentence. A cause that fits in a handful of
    #: characters is a formality, and this is shown to the person whose
    #: record was read — "debug" would insult them.
    reason: str = Field(..., min_length=20, max_length=500)
