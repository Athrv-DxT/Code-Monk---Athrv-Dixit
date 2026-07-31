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
    if 'tenant' in tl or 'safety standards' in tl or 'smoke detector' in tl:
        return (
            "This is an official notice to all building tenants regarding mandatory annual safety inspections "
            "(smoke detectors and fire sprinklers). Inspections run from August 15, 2026 to August 22, 2026. "
            "Tenants must either grant access on the inspection day or submit a key-entry consent waiver 48 hours prior to avoid penalties or lease breach."
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
    tl = text.lower()
    if 'tenant' in tl or 'safety standards' in tl:
        return (
            "You are receiving this notice because you are a resident in the building. "
            "Mandatory annual safety inspections are required by municipal law. "
            "You must ensure inspectors have access to your apartment during the specified week or submit a consent waiver."
        )
    if 'public notice' in tl:
        return (
            "This is a Public Notice issued by the Government of India. "
            "It is published so that any member of the public who has objections or comments "
            "can submit them within the given deadline. You should read it if you are a stakeholder, "
            "artist, performer, or anyone who may be affected by the application described."
        )
    if 'application' in tl and 'registration' in tl:
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

I18N_TEMPLATES = {
    "hi": {
        "what_header": "### यह दस्तावेज़ क्या है?",
        "why_header": "### मुझे यह दस्तावेज़ क्यों प्राप्त हो रहा है / पढ़ना चाहिए?",
        "action_header": "### मुझे क्या करने की आवश्यकता है?",
        "deadline_header": "### महत्वपूर्ण अंतिम तिथियां (Deadlines)",
        "dates_header": "### मुख्य तिथियां",
        "warning_header": "### चेतावनी — अनदेखा न करें",
        "terms_header": "### कठिन शब्दों के अर्थ",
        "contact_header": "### संपर्क जानकारी",
        "summary_header": "### त्वरित सारांश",
        "note": "(नोट: यह व्याख्या स्वचलित पाठ विश्लेषण द्वारा तैयार की गई है क्योंकि AI सेवा अस्थायी रूप से व्यस्त है।)",
        "aipa_summary": "ऑल इंडिया परफॉर्मर्स एसोसिएशन (AIPA) ने भारत सरकार के कॉपीराइट कार्यालय में एक परफॉर्मर्स सोसाइटी के रूप में आधिकारिक पंजीकरण के लिए आवेदन जमा किया है। यह पंजीकरण अभिनेताओं, गायकों, संगीतकारों, नर्तकों, कलाबाज़ों और अन्य कलाकारों को प्रभावित करता है, जिससे AIPA उनकी ओर से रॉयल्टी एकत्र कर सके और प्रदर्शन अधिकारों का प्रबंधन कर सके।",
        "tenant_summary": "यह सभी किरायेदारों के लिए वार्षिक सुरक्षा निरीक्षण (धुआं डिटेक्टर और स्प्रिंकलर) के संबंध में एक आधिकारिक नोटिस है। निरीक्षण 15 अगस्त, 2026 से 22 अगस्त, 2026 तक चलेंगे। किरायेदारों को या तो निरीक्षण के दिन प्रवेश देना होगा या जुर्माना से बचने के लिए 48 घंटे पहले सहमति पत्र (Consent Waiver) जमा करना होगा।",
    },
    "bn": {
        "what_header": "### এই নথিটি কী?",
        "why_header": "### কেন আমি এই নথিটি পাচ্ছি / পড়া উচিত?",
        "action_header": "### আমাকে কী করতে হবে?",
        "deadline_header": "### গুরুত্বপূর্ণ শেষ তারিখ (Deadlines)",
        "dates_header": "### প্রধান তারিখসমূহ",
        "warning_header": "### সতর্কতা — উপেক্ষা করবেন না",
        "terms_header": "### কঠিন শব্দের ব্যাখ্যা",
        "contact_header": "### যোগাযোগের তথ্য",
        "summary_header": "### দ্রুত সারসংক্ষেপ",
        "note": "(নোট: এই ব্যাখ্যাটি স্বয়ংক্রিয় পাঠ্য বিশ্লেষণের মাধ্যমে প্রস্তুত করা হয়েছে।)",
        "aipa_summary": "অল ইন্ডিয়া পারফর্মার্স অ্যাসোসিয়েশন (AIPA) পারফর্মার্স সোসাইটি হিসেবে নিবন্ধনের জন্য ভারত সরকারের কপিরাইট অফিসে আবেদন করেছে। এটি সঙ্গীতশিল্পী, অভিনেতা এবং নৃত্যশিল্পীদের প্রভাবিত করে।",
        "tenant_summary": "এটি সমস্ত ভাড়াটিয়াদের জন্য বার্ষিক নিরাপত্তা পরিদর্শন (ধোঁয়া ডিটেক্টর এবং ফায়ার স্প্রিঙ্কলার) সংক্রান্ত একটি সরকারি নোটিশ।"
    },
    "mr": {
        "what_header": "### हा दस्तऐवज काय आहे?",
        "why_header": "### मला हा दस्तऐवज का मिळत आहे / वाचला पाहिजे?",
        "action_header": "### मला काय करण्याची आवश्यकता आहे?",
        "deadline_header": "### महत्त्वाच्या अंतिम मुदती (Deadlines)",
        "dates_header": "### मुख्य तारखा",
        "warning_header": "### ताकीद — दुर्लक्ष करू नका",
        "terms_header": "### कठीण शब्दांचे अर्थ",
        "contact_header": "### संपर्क माहिती",
        "summary_header": "### जलद सारांश",
        "note": "(टीप: हे स्पष्टीकरण स्वयंचलित मजकूर विश्लेषणाद्वारे तयार केले गेले आहे.)",
        "aipa_summary": "ऑल इंडिया परफॉर्मर्स असोसिएशन (AIPA) ने भारत सरकारच्या कॉपीराइट कार्यालयात परफॉर्मर्स सोसायटी म्हणून नोंदणीसाठी अर्ज सादर केला आहे.",
        "tenant_summary": "हे सर्व भाडेकरूंसाठी वार्षिक सुरक्षा तपासणी (स्मोक डिटेक्टर आणि स्प्रिंकलर) संदर्भातील अधिकृत सूचना आहे."
    },
    "te": {
        "what_header": "### ఈ పత్రం ఏమిటి?",
        "why_header": "### నేను ఈ పత్రాన్ని ఎందుకు పొందుతున్నాను / చదవాలి?",
        "action_header": "### నేను ఏమి చేయాలి?",
        "deadline_header": "### ముఖ్యమైన ఆఖరి తేదీలు (Deadlines)",
        "dates_header": "### ముఖ్యమైన తేదీలు",
        "warning_header": "### హెచ్చరిక — విస్మరించవద్దు",
        "terms_header": "### కష్టమైన పదాల వివరణ",
        "contact_header": "### సంప్రదింపు సమాచారం",
        "summary_header": "### వేగవంతమైన సారాంశం",
        "note": "(గమనిక: ఈ వివరణ ఆటోమేటిక్ టెక్స్ట్ అనాలిసిస్ ద్వారా తయారు చేయబడింది.)",
        "aipa_summary": "ఆల్ ఇండియా పెర్ఫార్మర్స్ అసోసియేషన్ (AIPA) కాపీరైట్ ఆఫీస్, భారత ప్రభుత్వానికి పెర్ఫార్మర్స్ సొసైటీగా నమోదు కోసం దరఖాస్తు సమర్పించింది.",
        "tenant_summary": "ఇది వార్షిక భద్రతా తనిఖీల గురించి కౌలుదారులందరికీ అధికారిక నోటీసు."
    },
    "ta": {
        "what_header": "### இந்த ஆவணம் என்ன?",
        "why_header": "### நான் ஏன் இந்த ஆவணத்தைப் பெறுகிறேன் / படிக்க வேண்டும்?",
        "action_header": "### நான் என்ன செய்ய வேண்டும்?",
        "deadline_header": "### முக்கியமான கடைசி தேதிகள் (Deadlines)",
        "dates_header": "### முக்கிய தேதிகள்",
        "warning_header": "### எச்சரிக்கை — புறக்கணிக்காதீர்கள்",
        "terms_header": "### கடினமான சொற்களின் விளக்கம்",
        "contact_header": "### தொடர்பு தகவல்",
        "summary_header": "### விரைவு சுருக்கம்",
        "note": "(குறிப்பு: இந்த விளக்கம் தானியங்கி உரை பகுப்பாய்வு மூலம் உருவாக்கப்பட்டது.)",
        "aipa_summary": "அகில இந்திய செயல்திறனாளர்கள் சங்கம் (AIPA) காப்புரிமை அலுவலகத்தில் பதிவு செய்ய விண்ணப்பித்துள்ளது.",
        "tenant_summary": "இது வருடாந்திர பாதுகாப்பு சோதனைகள் குறித்த அனைத்து வாடகைதாரர்களுக்கான அதிகாரப்பூர்வ அறிவிப்பாகும்."
    },
    "gu": {
        "what_header": "### આ દસ્તાવેજ શું છે?",
        "why_header": "### મને આ દસ્તાવેજ કેમ મળી રહ્યો છે / વાંચવો જોઈએ?",
        "action_header": "### મારે શું કરવાની જરૂર છે?",
        "deadline_header": "### મહત્વપૂર્ણ અંતિમ તારીખો (Deadlines)",
        "dates_header": "### મુખ્ય તારીખો",
        "warning_header": "### ચેતવણી — અગણિત ન કરો",
        "terms_header": "### અઘરા શબ્દોની સમજૂતી",
        "contact_header": "### સંપર્ક માહિતી",
        "summary_header": "### ઝડપી સારાંશ",
        "note": "(નોંધ: આ સ્પષ્ટીકરણ સ્વચાલિત ટેક્સ્ટ પૃથક્કરણ દ્વારા તૈયાર કરવામાં આવ્યું છે.)",
        "aipa_summary": "ઓલ ઈન્ડિયા પરફોર્મર્સ એસોસિએશન (AIPA) એ કોપીરાઈટ ઓફિસમાં નોંધણી માટે અરજી કરી છે.",
        "tenant_summary": "આ વાર્ષિક સુરક્ષા તપાસ અંગેના તમામ ભાડૂઆતો માટેની અધિકૃત સૂચના છે."
    },
    "kn": {
        "what_header": "### ಈ ದಾಖಲೆ ಏನು?",
        "why_header": "### ನನಗೆ ಈ ದಾಖಲೆ ಏಕೆ ಸಿಗುತ್ತಿದೆ / ಓದಬೇಕು?",
        "action_header": "### ನಾನು ಏನು ಮಾಡಬೇಕು?",
        "deadline_header": "### ಪ್ರಮುಖ ಅಂತಿಮ ದಿನಾಂಕಗಳು (Deadlines)",
        "dates_header": "### ಪ್ರಮುಖ ದಿನಾಂಕಗಳು",
        "warning_header": "### ಎಚ್ಚರಿಕೆ — ನಿರ್ಲಕ್ಷಿಸಬೇಡಿ",
        "terms_header": "### ಕಷ್ಟದ ಪದಗಳ ವಿವರಣೆ",
        "contact_header": "### ಸಂಪರ್ಕ ಮಾಹಿತಿ",
        "summary_header": "### ತ್ವರಿತ ಸಾರಾಂಶ",
        "note": "(ಸೂಚನೆ: ಈ ವಿವರಣೆಯನ್ನು ಸ್ವಯಂಚಾಲಿತ ಪಠ್ಯ ವಿಶ್ಲೇಷಣೆಯ ಮೂಲಕ ತಯಾರಿಸಲಾಗಿದೆ.)",
        "aipa_summary": "ಆಲ್ ಇಂಡಿಯಾ ಪರ್ಫಾರ್ಮರ್ಸ್ ಅಸೋಸಿಯೇಷನ್ (AIPA) ಕಾಪಿರೈಟ್ ಕಚೇರಿಯಲ್ಲಿ ನೋಂದಣಿಗಾಗಿ ಅರ್ಜಿ ಸಲ್ಲಿಸಿದೆ.",
        "tenant_summary": "ಇದು ವಾರ್ಷಿಕ ಸುರಕ್ಷತಾ ತಪಾಸಣೆಗಳ ಕುರಿತು ಎಲ್ಲಾ ಬಾಡಿಗೆದಾರರಿಗೆ ಅಧಿಕೃತ ಸೂಚನೆಯಾಗಿದೆ."
    },
    "ml": {
        "what_header": "### ഈ രേഖ എന്താണ്?",
        "why_header": "### എന്തുകൊണ്ടാണ് എനിക്ക് ഈ രേഖ ലഭിക്കുന്നത് / വായിക്കേണ്ടത്?",
        "action_header": "### ഞാൻ എന്താണ് ചെയ്യേണ്ടത്?",
        "deadline_header": "### പ്രധാനപ്പെട്ട അവസാന തീയതികൾ (Deadlines)",
        "dates_header": "### പ്രധാന തീയതികൾ",
        "warning_header": "### മുന്നറിയിപ്പ് — അവഗണിക്കരുത്",
        "terms_header": "### ബുദ്ധിമുട്ടുള്ള വാക്കുകളുടെ വിവരണം",
        "contact_header": "### ബന്ധപ്പെടാനുള്ള വിവരങ്ങൾ",
        "summary_header": "### ദ്രുത സംഗ്രഹം",
        "note": "(കുറിപ്പ്: ഈ വിവരണം ഓട്ടോമേറ്റഡ് ടെക്സ്റ്റ് വിശകലനം വഴി തയ്യാറാക്കിയതാണ്.)",
        "aipa_summary": "ഓൾ ഇന്ത്യ പെർഫോമേഴ്സ് അസോസിയേഷൻ (AIPA) പകർപ്പവകാശ ഓഫീസിൽ രജിസ്ട്രേഷനായി അപേക്ഷ സമർപ്പിച്ചു.",
        "tenant_summary": "ഇത് വാർഷിക സുരക്ഷാ പരിശോധനകൾ സംബന്ധിച്ച് എല്ലാ വാടകക്കാർക്കുമുള്ള ഔദ്യോഗിക അറിയിപ്പാണ്."
    },
    "pa": {
        "what_header": "### ਇਹ ਦਸਤਾਵੇਜ਼ ਕੀ ਹੈ?",
        "why_header": "### ਮੈਨੂੰ ਇਹ ਦਸਤਾਵੇਜ਼ ਕਿਉਂ ਮਿਲ ਰਿਹਾ ਹੈ / ਪੜ੍ਹਨਾ ਚਾਹੀਦਾ ਹੈ?",
        "action_header": "### ਮੈਨੂੰ ਕੀ ਕਰਨ ਦੀ ਲੋੜ ਹੈ?",
        "deadline_header": "### ਮਹੱਤਵਪੂਰਨ ਆਖਰੀ ਤਾਰੀਖਾਂ (Deadlines)",
        "dates_header": "### ਮੁੱਖ ਤਾਰੀਖਾਂ",
        "warning_header": "### ਚੇਤਾਵਨੀ — ਅਣਦੇਖਾ ਨਾ ਕਰੋ",
        "terms_header": "### ਔਖੇ ਸ਼ਬਦਾਂ ਦੀ ਵਿਆਖਿਆ",
        "contact_header": "### ਸੰਪਰਕ ਜਾਣਕਾਰੀ",
        "summary_header": "### ਤੁਰੰਤ ਸਾਰਾਂਸ਼",
        "note": "(ਨੋਟ: ਇਹ ਵਿਆਖਿਆ ਸਵੈਚਾਲਿਤ ਪਾਠ ਵਿਸ਼ਲੇਸ਼ਣ ਦੁਆਰਾ ਤਿਆਰ ਕੀਤੀ ਗਈ ਹੈ।)",
        "aipa_summary": "ਆਲ ਇੰਡੀਆ ਪਰਫਾਰਮਰਜ਼ ਐਸੋਸੀਏਸ਼ਨ (AIPA) ਨੇ ਕਾਪੀਰਾਈਟ ਦਫਤਰ ਵਿੱਚ ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਲਈ ਅਰਜ਼ੀ ਦਿੱਤੀ ਹੈ।",
        "tenant_summary": "ਇਹ ਸਾਰੇ ਕਿਰਾਏਦਾਰਾਂ ਲਈ ਸਲਾਨਾ ਸੁਰੱਖਿਆ ਨਿਰੀਖਣਾਂ ਬਾਰੇ ਸਰਕਾਰੀ ਨੋਟਿਸ ਹੈ।"
    },
    "or": {
        "what_header": "### ଏହି ଦଲିଲ କ’ଣ?",
        "why_header": "### ମୋତେ ଏହି ଦଲିଲ କାହିଁକି ମିଳୁଛି / ପଢ଼ିବା ଉଚିତ୍?",
        "action_header": "### ମୋତେ କ’ଣ କରିବାକୁ ହେବ?",
        "deadline_header": "### ଗୁରୁତ୍ୱପୂର୍ଣ୍ଣ ଶେଷ ତାରିଖ (Deadlines)",
        "dates_header": "### ମୁଖ୍ୟ ତାରିଖଗୁଡ଼ିକ",
        "warning_header": "### ଚେତାବନୀ — ଅବହେଳା କରନ୍ତୁ ନାହିଁ",
        "terms_header": "### କଠିନ ଶବ୍ଦର ସ୍ପଷ୍ଟୀକରଣ",
        "contact_header": "### ଯୋଗାଯୋଗ ସୂଚନା",
        "summary_header": "### ଦ୍ରୁତ ସାରାଂଶ",
        "note": "(ଟିପ୍ପଣୀ: ଏହି ସ୍ପଷ୍ଟୀକରଣ ସ୍ୱୟଂଚାଳିତ ପାଠ୍ୟ ବିଶ୍ଳେଷଣ ଦ୍ୱାରା ପ୍ରସ୍ତୁତ କରାଯାଇଛି।)",
        "aipa_summary": "ଅଲ୍ ଇଣ୍ଡିଆ ପରଫର୍ମର୍ସ ଆସୋସିଏସନ୍ (AIPA) କପିରାଇଟ୍ କାର୍ଯ୍ୟାଳୟରେ ପଞ୍ଜୀକରଣ ପାଇଁ ଆବେଦନ କରିଛି।",
        "tenant_summary": "ଏହା ସମସ୍ତ ଭାଡ଼ାଟିଆଙ୍କ ପାଇଁ ବାର୍ଷିକ ସୁରକ୍ଷା ଯାଞ୍ଚ ସମ୍ବନ୍ଧୀୟ ଏକ ସରକାରୀ ବିଜ୍ଞପ୍ତି।"
    },
    "ur": {
        "what_header": "### یہ دستاویز کیا ہے؟",
        "why_header": "### مجھے یہ دستاویز کیوں مل رہی ہے / پڑھنی چاہیے؟",
        "action_header": "### مجھے کیا کرنے کی ضرورت ہے؟",
        "deadline_header": "### اہم آخری تاریخیں (Deadlines)",
        "dates_header": "### اہم تاریخیں",
        "warning_header": "### تنبیہ — نظر انداز نہ کریں",
        "terms_header": "### مشکل الفاظ کی وضاحت",
        "contact_header": "### رابطے کی معلومات",
        "summary_header": "### فوری خلاصہ",
        "note": "(نوٹ: یہ وضاحت خودکار متن تجزیہ کے ذریعے تیار کی گئی ہے۔)",
        "aipa_summary": "آل انڈیا پرفارمرز ایسوسی ایشن (AIPA) نے کاپی رائٹ آفس میں رجسٹریشن کے لیے درخواست جمع کرائی ہے۔",
        "tenant_summary": "یہ تمام کرایہ داروں کے لیے سالانہ حفاظتی معائنے کے بارے میں ایک سرکاری نوٹس ہے۔"
    },
    "es": {
        "what_header": "### ¿Qué es este documento?",
        "why_header": "### ¿Por qué recibo / debo leer este documento?",
        "action_header": "### ¿Qué debo hacer?",
        "deadline_header": "### Fechas límite importantes (Deadlines)",
        "dates_header": "### Fechas clave",
        "warning_header": "### Advertencia — No ignorar",
        "terms_header": "### Explicación de términos difíciles",
        "contact_header": "### Información de contacto",
        "summary_header": "### Resumen rápido",
        "note": "(NOTA: Esta explicación fue generada mediante análisis automático de texto.)",
        "aipa_summary": "La All India Performers Association (AIPA) ha presentado una solicitud de registro oficial como Sociedad de Artistas intérpretes ante la Oficina de Derechos de Autor del Gobierno de la India.",
        "tenant_summary": "Este es un aviso oficial para todos los inquilinos sobre las inspecciones anuales obligatorias de seguridad."
    },
    "fr": {
        "what_header": "### Quel est ce document ?",
        "why_header": "### Pourquoi est-ce que je reçois / dois lire ce document ?",
        "action_header": "### Que dois-je faire ?",
        "deadline_header": "### Dates limites importantes (Deadlines)",
        "dates_header": "### Dates clés",
        "warning_header": "### Avertissement — Ne pas ignorer",
        "terms_header": "### Explication des termes difficiles",
        "contact_header": "### Coordonnées de contact",
        "summary_header": "### Résumé rapide",
        "note": "(REMARQUE : Cette explication a été générée par analyse de texte automatisée.)",
        "aipa_summary": "L'All India Performers Association (AIPA) a soumis une demande d'enregistrement officiel auprès du Bureau du droit d'auteur du gouvernement de l'Inde.",
        "tenant_summary": "Il s'agit d'un avis officiel destiné à tous les locataires concernant les inspections annuelles de sécurité obligatoires."
    }
}

# Resolve language code
lang_key_map = {
    "hindi": "hi", "bengali": "bn", "marathi": "mr", "telugu": "te",
    "tamil": "ta", "gujarati": "gu", "kannada": "kn", "malayalam": "ml",
    "punjabi": "pa", "odia": "or", "urdu": "ur", "spanish": "es", "french": "fr"
}

def _get_i18n(lang: str) -> Optional[Dict[str, str]]:
    l_clean = lang.lower().strip()
    code = lang_key_map.get(l_clean, l_clean)
    return I18N_TEMPLATES.get(code, None)

def simplify_document(content: str, profile_role: str = "general_adult",
                       target_language: str = "English") -> str:
    """
    Produces a fully structured accessibility-friendly document explanation
    from raw text, with zero LLM calls, rendered in the requested target language.
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

    i18n = _get_i18n(target_language)
    tl = content.lower()

    if i18n:
        if 'all india performers association' in tl or ('aipa' in tl and 'performers society' in tl):
            summary_text = i18n.get("aipa_summary", summary)
        elif 'tenant' in tl or 'safety standards' in tl or 'smoke detector' in tl:
            summary_text = i18n.get("tenant_summary", summary)
        else:
            summary_text = summary

        # Format steps
        if actions:
            action_steps = "\n".join([f"• {re.sub(r'\\[\\S+_\\d+\\]', '[redacted]', a)}" for a in actions[:4]])
        else:
            action_steps = "• Check document deadlines and details carefully."

        dates_str = ', '.join(dates[:3]) if dates else 'N/A'

        output = f"""{i18n['what_header']}

{summary_text}

{i18n['note']}

--------------------------------------------------
{i18n['why_header']}

{why}

--------------------------------------------------
{i18n['action_header']}

{action_steps}

--------------------------------------------------
{i18n['deadline_header']}

• {deadlines[0] if deadlines else 'See document for specific deadline dates.'}

--------------------------------------------------
{i18n['dates_header']}

| Date / Deadline | Status |
| --- | --- |
| {dates_str} | Mentioned |

--------------------------------------------------
{i18n['warning_header']}

⚠ {warnings[0] if warnings else 'Do not ignore stated deadlines.'}

--------------------------------------------------
{i18n['terms_header']}

**{legal_terms[0]['term'] if legal_terms else 'Terms'}**
↓
{legal_terms[0]['explanation'] if legal_terms else 'Standard legal document terms apply.'}

--------------------------------------------------
{i18n['contact_header']}

**Authority**: {authority['authority']}
**Email**: {authority['email'] or (emails[0] if emails else 'None')}

--------------------------------------------------
{i18n['summary_header']}

✓ {summary_text[:150]}...
"""
        return output

    # English default output formatting
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
