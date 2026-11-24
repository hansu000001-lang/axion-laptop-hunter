import re
from .models import Listing

CPU_RE = re.compile(r'\b(?:intel\s+)?(?:core\s+)?ultra\s+9\s*[- ]?275\s*hx\b', re.I)

def _num(pattern, text):
    m=re.search(pattern,text,re.I)
    if not m:
        return None
    value = float(m.group(1))
    return int(value) if value.is_integer() else value

def enrich_and_verify(item: Listing):
    text=' '.join([item.title or '', item.specs_text or ''])
    cpu=CPU_RE.search(text)
    ram=_num(r'\b(\d{2,3})\s*\s*(?:gb\s*)?(?:ddr[45]\s*)?ram\b',text)
    if ram is None: ram=_num(r'\b(\d{2,3})\s*gb\s*(?:ddr[45])?\b',text)
    ssd=_num(r'\b(\d(?:\.\d)?)\s*tb\s*(?:nvme\s*)?(?:ssd|solid state)',text)
    if ssd is not None: ssd=int(ssd*1024)
    if ssd is None: ssd=_num(r'\b(\d{3,5})\s*gb\s*(?:nvme\s*)?ssd\b',text)
    gpu_match=re.search(r'\b(RTX\s*\d{3,4}(?:\s*Ti)?|GeForce\s+RTX\s+\w+|Radeon\s+\w+)\b',text,re.I)
    item.cpu='Intel Core Ultra 9 275HX' if cpu else item.cpu
    item.ram_gb=ram or item.ram_gb
    item.ssd_gb=ssd or item.ssd_gb
    item.gpu=gpu_match.group(1) if gpu_match else item.gpu
    # Strict confidence: source must expose explicit specs, not just title keyword fragments.
    has_ram = bool(ram is not None and ram == 32 and re.search(r'\b(?:ram|memory|ddr[45])\b', text, re.I))
    has_ssd = bool(ssd is not None and ssd == 1024)
    item.confidence='verified' if cpu and has_ram and has_ssd else 'unverified'
    if not item.specs_text: item.specs_text=text
    return item

def is_candidate(item):
    return bool(CPU_RE.search((item.title or '')+' '+(item.specs_text or '')))
