import logging
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi

logger = logging.getLogger("meridian.bm25")

# Curated corpus of domain-specific glossary items
GLOSSARY_CORPUS = [
    {
        "term": "Force Majeure",
        "domain": "legal",
        "definition": "An unexpected event (like a natural disaster, war, or strike) that prevents a party from fulfilling a contract, freeing them from liability for non-performance."
    },
    {
        "term": "Indemnify",
        "domain": "legal",
        "definition": "To promise to protect someone from legal responsibility, or to compensate them for any losses, damages, or expenses they might incur."
    },
    {
        "term": "HIPAA",
        "domain": "medical",
        "definition": "Health Insurance Portability and Accountability Act. A federal US law protecting sensitive patient health details from being shared without consent."
    },
    {
        "term": "Prior Authorization",
        "domain": "medical",
        "definition": "An official decision by a health insurance plan that a medical service, treatment, or drug is medically necessary before it is received."
    },
    {
        "term": "Co-pay",
        "domain": "medical",
        "definition": "A set, flat fee (e.g. $20) you pay for a medical service or prescription, with your insurance company covering the remaining balance."
    },
    {
        "term": "Statute of Limitations",
        "domain": "legal",
        "definition": "A law setting the maximum time period that parties have from the date of an incident to start legal proceedings or file a lawsuit."
    },
    {
        "term": "Severability",
        "domain": "legal",
        "definition": "A contract clause stating that if any specific part of the agreement is found to be illegal or invalid, the remaining parts stay in effect."
    },
    {
        "term": "Arbitration",
        "domain": "legal",
        "definition": "A method of resolving a legal dispute outside of the court system, where an independent third party (the arbitrator) makes a binding decision."
    },
    {
        "term": "Deductible",
        "domain": "medical",
        "definition": "The specific out-of-pocket money you must spend on healthcare services before your health insurance begins to pay for covered services."
    },
    {
        "term": "Out-of-Pocket Maximum",
        "domain": "medical",
        "definition": "The maximum amount of money you are required to pay for health services in a year. Once reached, your insurance covers 100% of costs."
    },
    {
        "term": "Lien",
        "domain": "legal",
        "definition": "A legal claim or right against an asset/property, used as collateral or security to ensure payment of a debt or legal obligation."
    },
    {
        "term": "Notice Period",
        "domain": "administrative",
        "definition": "The official amount of time in advance (e.g. 30 days) that a party must inform the other before ending or altering an agreement."
    }
]

class BM25Searcher:
    def __init__(self):
        # Tokenize by converting to lowercase and splitting on whitespace
        self.corpus = GLOSSARY_CORPUS
        self.tokenized_corpus = [
            (doc["term"].lower() + " " + doc["definition"].lower()).split()
            for doc in self.corpus
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        logger.info(f"Initialized BM25 index with {len(self.corpus)} terms.")

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not query:
            return []
            
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        
        # Sort indices by score descending
        ranked_indices = sorted(
            range(len(scores)), 
            key=lambda i: scores[i], 
            reverse=True
        )
        
        results = []
        for idx in ranked_indices[:top_k]:
            if scores[idx] > 0.0:  # Only return documents with some match
                results.append({
                    "term": self.corpus[idx]["term"],
                    "definition": self.corpus[idx]["definition"],
                    "domain": self.corpus[idx]["domain"],
                    "score": float(scores[idx])
                })
        return results

bm25_searcher = BM25Searcher()
