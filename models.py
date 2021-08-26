from pydantic import BaseModel
from typing import List, Optional


class GentlemanInfo(BaseModel):
    # id: Optional[int] = 0
    profile_id: Optional[int] = 0
    age_from: Optional[int] = 0
    age_to: Optional[int] = 0
