import logging
import numpy as np
from typing import List, Dict, Any
from app.retrieval.embeddings import get_embedding, get_embeddings
from app.retrieval.bm25_index import bm25_searcher, GLOSSARY_CORPUS

logger = logging.getLogger("intellix.hybrid_search")

# Globals to cache corpus embeddings
_corpus_embeddings = None

def init_dense_index():
    global _corpus_embeddings
    if _corpus_embeddings is None:
        try:
            logger.info("Pre-computing dense embeddings for glossary corpus...")
            texts = [f"{item['term']}: {item['definition']}" for item in GLOSSARY_CORPUS]
            _corpus_embeddings = get_embeddings(texts)
            logger.info("Dense glossary index ready.")
        except Exception as e:
            logger.error(f"Failed to precompute glossary embeddings: {e}")
            _corpus_embeddings = []

def hybrid_search(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Executes hybrid search combining dense (BGE) and sparse (BM25) search
    using Reciprocal Rank Fusion (RRF).
    """
    if not query:
        return []
        
    init_dense_index()
    
    # 1. Sparse search (BM25)
    bm25_results = bm25_searcher.search(query, top_k=len(GLOSSARY_CORPUS))
    bm25_ranks = {res["term"]: rank for rank, res in enumerate(bm25_results)}
    
    # 2. Dense search (BGE Cosine Similarity)
    dense_ranks = {}
    if len(_corpus_embeddings) > 0:
        try:
            q_emb = np.array(get_embedding(query))
            similarities = []
            for idx, item_emb in enumerate(_corpus_embeddings):
                sim = np.dot(q_emb, np.array(item_emb))  # Dot product on normalized vectors
                similarities.append((GLOSSARY_CORPUS[idx]["term"], float(sim)))
                
            # Sort by similarity descending
            sorted_similarities = sorted(similarities, key=lambda x: x[1], reverse=True)
            dense_ranks = {item[0]: rank for rank, item in enumerate(sorted_similarities)}
        except Exception as e:
            logger.warning(f"Dense search failed, falling back to sparse: {e}")
            
    # 3. Reciprocal Rank Fusion (RRF)
    # RRF formula: score = 1 / (60 + rank_dense) + 1 / (60 + rank_sparse)
    rrf_constant = 60
    rrf_scores = {}
    
    for item in GLOSSARY_CORPUS:
        term = item["term"]
        score = 0.0
        
        # Add dense score
        if term in dense_ranks:
            score += 1.0 / (rrf_constant + dense_ranks[term])
            
        # Add sparse score
        if term in bm25_ranks:
            score += 1.0 / (rrf_constant + bm25_ranks[term])
            
        if score > 0:
            rrf_scores[term] = score
            
    # Sort terms by RRF score descending
    sorted_terms = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Build final results
    results = []
    term_to_corpus = {item["term"]: item for item in GLOSSARY_CORPUS}
    
    for term, score in sorted_terms[:top_k]:
        corpus_item = term_to_corpus[term]
        results.append({
            "term": corpus_item["term"],
            "definition": corpus_item["definition"],
            "domain": corpus_item["domain"],
            "rrf_score": score
        })
        
    logger.info(f"Hybrid search returned {len(results)} results for query: '{query}'")
    return results
