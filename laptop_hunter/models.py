from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Listing:
    source: str
    source_id: str
    title: str
    url: str
    price: Optional[float] = None
    shipping: float = 0.0
    currency: str = "USD"
    condition: str = "unknown"
    seller: str = ""
    availability: str = "unknown"
    cpu: str = ""
    ram_gb: Optional[int] = None
    ssd_gb: Optional[int] = None
    gpu: str = ""
    specs_text: str = ""
    observed_at: str = ""
    confidence: str = "unverified"

    @property
    def total_price(self):
        return (self.price or 0) + (self.shipping or 0)

    def to_dict(self):
        return asdict(self)
