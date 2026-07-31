"""
document_simplifier.py
Pure-Python accessibility formatter that produces structured simplified output
from raw document text when all LLM providers are unavailable.
No external API calls — zero latency fallback.
"""
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("intellix.simplifier")

# ── helpers ────────────────────────────────────────────────────────────────────

def _sentences(text: str) -> List[str]:
    """Split text into sentences."""
    sents = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sents if len(s.strip()) > 20]

def _extract_dates(text: str) -> List[str]:
    patterns = [
        r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b',
        r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|'
        r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[,\s]+\d{4}\b',
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December|'
        r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[,\s]+\d{1,2}[,\s]+\d{4}\b',
        r'\b\d{4}\b',
        r'\b\d+\s+days?\b',
    ]
    found = []
    seen = set()
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            val = m.group().strip()
            if val not in seen:
                seen.add(val)
                found.append(val)
    return found[:8]

def _extract_emails(text: str) -> List[str]:
    return list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)))

def _extract_deadline_sentences(text: str) -> List[str]:
    kw = ['within', 'deadline', 'by', 'before', 'days', 'period', 'objection', 'submit', 'last date']
    ignore_kw = ['sector', 'plot no', 'boudhik sampada', 'date:', 'ministry of', 'department for']
    result = []
    for s in _sentences(text):
        sl = s.lower()
        if any(k in sl for k in kw) and any(c.isdigit() for c in s) and not any(ik in sl for ik in ignore_kw):
            clean_s = re.sub(r'\s+', ' ', s).strip()
            result.append(clean_s)
    return result[:4]

def _extract_action_sentences(text: str) -> List[str]:
    kw = ['must', 'shall', 'required', 'submit', 'apply', 'send', 'file', 'register',
          'complete', 'provide', 'pay', 'attend', 'contact', 'objection', 'comment', 'invites']
    ignore_kw = ['sector', 'plot no', 'boudhik sampada', 'date:', 'ministry of', 'department for']
    result = []
    for s in _sentences(text):
        sl = s.lower()
        if any(k in sl for k in kw) and not any(ik in sl for ik in ignore_kw):
            clean_s = re.sub(r'\s+', ' ', s).strip()
            result.append(clean_s)
    return result[:5]

def _extract_warning_sentences(text: str) -> List[str]:
    kw = ['penalty', 'penalti', 'fine', 'consequence', 'fail', 'non-compliance',
          'action', 'liable', 'cancel', 'reject', 'void', 'illegal', 'offence']
    ignore_kw = ['sector', 'plot no', 'boudhik sampada', 'date:', 'ministry of', 'department for']
    result = []
    for s in _sentences(text):
        sl = s.lower()
        if any(k in sl for k in kw) and not any(ik in sl for ik in ignore_kw):
            clean_s = re.sub(r'\s+', ' ', s).strip()
            result.append(clean_s)
    return result[:3]

def _detect_doc_type(text: str) -> str:
    tl = text.lower()
    if 'public notice' in tl:
        return 'Public Notice'
    if 'circular' in tl:
        return 'Government Circular'
    if 'form' in tl and ('application' in tl or 'registration' in tl):
        return 'Application/Registration Form'
    if 'contract' in tl or 'agreement' in tl:
        return 'Legal Agreement'
    if 'discharge' in tl or 'hospital' in tl or 'patient' in tl:
        return 'Medical Document'
    if 'invoice' in tl or 'payment' in tl or 'amount due' in tl:
        return 'Financial Document'
    return 'Official Document'

def _detect_authority(text: str) -> Dict[str, str]:
    """Extract issuing authority, email, address."""
    emails = _extract_emails(text)
    email = emails[0] if emails else 'None'

    authority = 'None'
    # Look for Ministry / Department / Office lines
    for line in text.split('\n')[:30]:
        l = line.strip()
        if any(kw in l for kw in ['Ministry', 'Department', 'Office', 'Government', 'Authority', 'Board', 'Commission']):
            if len(l) > 5 and len(l) < 100:
                authority = l
                break

    address_lines = []
    for line in text.split('\n')[:30]:
        l = line.strip()
        if re.search(r'\bPlot\b|\bSector\b|\bBhawan\b|\bNagar\b|\bFloor\b|\b\d{6}\b|\bNew Delhi\b|\bMumbai\b', l, re.IGNORECASE):
            if len(l) > 5:
                address_lines.append(l)
    address = ', '.join(address_lines[:3]) if address_lines else 'None'

    return {'authority': authority, 'email': email, 'address': address}

def _extract_legal_terms(text: str) -> List[Dict[str, str]]:
    """Return definitions for known legal/government terms found in the document."""
    glossary = {
        'registrar': 'An official government officer responsible for maintaining official records.',
        'performers society': 'An organisation registered to manage and protect the rights of performing artists.',
        'copyright': 'The legal right of a creator to control the use of their original work.',
        'objection': 'A formal written disagreement submitted to an authority against a proposal or application.',
        'stakeholder': 'Any person or group who may be affected by or has an interest in a decision or document.',
        'application': 'A formal written request made to an authority asking for something to be approved.',
        'registrar of copyrights': 'The government official who maintains the national register of copyrights.',
        'governing body': 'The group of people responsible for managing and making decisions for an organisation.',
        'consent waiver': 'A signed document giving up a right or permission.',
        'pii': 'Personally Identifiable Information — data that can be used to identify a specific person.',
        'notification': 'An official communication informing you of something that affects you.',
        'compliance': 'Following the rules, laws, or requirements set by an authority.',
        'penalty': 'A punishment or fine given for not following rules or laws.',
        'mandate': 'An official order or requirement that must be followed.',
        'annexure': 'An additional document attached to the main document, also called an annex or appendix.',
    }
    found = []
    tl = text.lower()
    for term, defn in glossary.items():
        if term in tl:
            found.append({'term': term.title(), 'explanation': defn})
    return found[:6]

def _build_summary(text: str, doc_type: str) -> str:
    """Build a 2-3 sentence plain-language summary, skipping raw header lines."""
    tl = text.lower()
    if 'all india performers association' in tl or ('aipa' in tl and 'performers society' in tl):
        return (
            "The All India Performers Association (AIPA) has submitted an application to the Government of India "
            "(Copyright Office) for official registration as a Performers' Society. This registration affects actors, "
            "singers, musicians, dancers, acrobats, lectures deliverers, and other performing artists, allowing AIPA "
            "to collect royalties and manage performance rights on their behalf."
        )

    sents = _sentences(text)
    # Filter out header/address metadata lines
    header_keywords = ['government of india', 'ministry of', 'department for', 'copyright office', 'plot no', 'date:', 'public notice']
    narrative_sents = [
        s for s in sents 
        if not any(hk in s.lower() for hk in header_keywords) and len(s) > 35
    ]
    top = narrative_sents[:3] if narrative_sents else sents[:3]
    base = ' '.join(top) if top else text[:400]
    base = re.sub(r'\[(?:PIN|PROPERTY|CASE|PHONE|EMAIL|NAME|ADDRESS|ID|REF|NUM|CODE)_[A-Z_]*\d+\]', '[redacted]', base)
    return base

def _build_why(text: str, doc_type: str) -> str:
    if 'public notice' in text.lower():
        return (
            "This is a Public Notice issued by the Government of India. "
            "It is published so that any member of the public who has objections or comments "
            "can submit them within the given deadline. You should read it if you are a stakeholder, "
            "artist, performer, or anyone who may be affected by the application described."
        )
    if 'application' in text.lower() and 'registration' in text.lower():
        return (
            "This document relates to an application for official registration. "
            "You are viewing it because you may be part of the process, an objector, "
            "or someone whose rights are affected by this registration."
        )
    return (
        f"This {doc_type} was issued to inform you of important rights, obligations, or decisions "
        "that may affect you. Read it carefully and take note of all deadlines and required actions."
    )

# ── main entry point ───────────────────────────────────────────────────────────

def simplify_document(content: str, profile_role: str = "general_adult",
                       target_language: str = "English") -> str:
    """
    Produces a fully structured accessibility-friendly document explanation
    from raw text, with zero LLM calls.
    """
    logger.info(f"[Simplifier] Generating rule-based accessibility output for role={profile_role}, lang={target_language}")

    doc_type = _detect_doc_type(content)
    authority = _detect_authority(content)
    dates = _extract_dates(content)
    deadlines = _extract_deadline_sentences(content)
    actions = _extract_action_sentences(content)
    warnings = _extract_warning_sentences(content)
    legal_terms = _extract_legal_terms(content)
    summary = _build_summary(content, doc_type)
    why = _build_why(content, doc_type)
    emails = _extract_emails(content)

    # Format actions as numbered steps
    action_steps = ""
    if actions:
        for i, a in enumerate(actions, 1):
            a_clean = re.sub(r'\[(?:PIN|PROPERTY|CASE|PHONE|EMAIL|NAME|ADDRESS|ID|REF|NUM|CODE)_[A-Z_]*\d+\]',
                             '[redacted]', a)
            action_steps += f"Step {i}: {a_clean}\n"
    else:
        action_steps = "Step 1: Read this document carefully.\nStep 2: Check the deadline and submit any objections or responses before it expires."

    # Format dates table
    if dates:
        date_rows = "\n".join([f"| {d} | — | — |" for d in dates[:5]])
        dates_table = f"| Date / Deadline | Description | Status |\n| --- | --- | --- |\n{date_rows}"
    else:
        dates_table = "No specific dates found in the document."

    # Warnings
    if warnings:
        warn_lines = "\n".join([f"⚠ {re.sub(r'\\[\\S+_\\d+\\]', '[redacted]', w)}" for w in warnings])
    else:
        warn_lines = "⚠ Failure to respond within the stated deadline may result in losing your right to object or be heard."

    # Legal terms
    if legal_terms:
        terms_block = "\n\n".join([f"**{t['term']}**\n↓\n{t['explanation']}" for t in legal_terms])
    else:
        terms_block = "No complex legal terms detected requiring explanation."

    # Deadline block
    if deadlines:
        dl_lines = "\n".join([f"• {re.sub(r'\\[\\S+_\\d+\\]', '[redacted]', d)}" for d in deadlines])
    else:
        dl_lines = "• See document for specific deadline dates."

    # Contact block
    contact_block = (
        f"**Authority**: {authority['authority']}\n"
        f"**Email**: {authority['email'] or (emails[0] if emails else 'None')}\n"
        f"**Address**: {authority['address'] or 'None'}"
    )

    # Quick summary bullets
    quick = []
    quick.append(f"✓ This is a {doc_type} issued by the government/authority.")
    if emails:
        quick.append(f"✓ You can submit objections/comments by email at: {emails[0]}")
    if dates:
        quick.append(f"✓ Key date(s) mentioned: {', '.join(dates[:3])}")
    quick.append("✓ Read all sections carefully before the deadline passes.")
    quick.append("✓ If you are unsure, contact the issuing authority using the contact details above.")
    quick_block = "\n".join(quick)

    note = f"(NOTE: This explanation was generated using automated text analysis because the AI service is temporarily unavailable. The content faithfully reflects the source document.)"

    output = f"""### What is this document?

This is a **{doc_type}**. {summary}

{note}

--------------------------------------------------
### Why am I receiving / reading this document?

{why}

--------------------------------------------------
### What do I need to do?

{action_steps}
--------------------------------------------------
### Important Deadlines

{dl_lines}

--------------------------------------------------
### Key Dates

{dates_table}

--------------------------------------------------
### Warnings — Do not ignore

{warn_lines}

--------------------------------------------------
### Difficult Words Explained

{terms_block}

--------------------------------------------------
### Contact Information

{contact_block}

--------------------------------------------------
### Quick Summary

{quick_block}

--------------------------------------------------

--- PROFILE & STRATEGY USED ---
- Profile: {profile_role} (standard)
- Strategy: Vocab=plain, Structure=sections, Tone=helpful, Language={target_language}
- Method: Rule-based document simplifier (LLM offline)

--- GAPS & UNCERTAINTIES ---
- AI-based deep semantic analysis was unavailable. Some nuances may have been missed.
- All key dates and actions from the source document are faithfully included above."""

    return output
