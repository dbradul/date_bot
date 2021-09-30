from pydantic import BaseModel
from typing import List, Optional


class GentlemanInfo(BaseModel):
    # id: Optional[int] = 0
    profile_id: Optional[int] = 0
    age_from: Optional[int] = 0
    age_to: Optional[int] = 0
    priority: Optional[int] = 0


# class RunStats(BaseModel):
#     is_online: int = 0
#     rejected_age_mismatch: int = 0
#     letters_sent: int = 0
#     country: str
