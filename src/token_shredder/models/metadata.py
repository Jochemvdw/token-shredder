from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Metadata:
    file_path: str
    file_size: int
    file_type: str
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    converter_used: Optional[str] = None
    processors_applied: list = field(default_factory=list)
