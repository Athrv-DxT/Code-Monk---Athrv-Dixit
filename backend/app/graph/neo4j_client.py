import logging
from typing import Optional, List, Dict, Any
from neo4j import GraphDatabase, Driver
from app.config import settings
from app.core.models import StructuredMeaningRepresentation, MeaningNode, MeaningRelationship

logger = logging.getLogger("meridian.neo4j")

_driver: Optional[Driver] = None
_connection_attempted: bool = False

def get_driver() -> Optional[Driver]:
    global _driver, _connection_attempted
    if _driver is None and not _connection_attempted:
        _connection_attempted = True
        try:
            logger.info(f"Connecting to Neo4j at {settings.NEO4J_URI}...")
            _driver = GraphDatabase.driver(
                settings.NEO4J_URI, 
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                connection_timeout=0.5
            )
            # Verify connectivity
            _driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j.")
        except Exception as e:
            logger.warning(f"Failed to connect to Neo4j: {e}. Graph operations will be bypassed.")
            _driver = None
    return _driver

def init_db():
    driver = get_driver()
    if not driver:
        return
        
    try:
        with driver.session() as session:
            # Create a constraint on MeaningNode id
            logger.info("Initializing Neo4j constraints and indices...")
            session.run("""
                CREATE CONSTRAINT FOR (m:MeaningNode) REQUIRE m.id IS UNIQUE
            """)
            session.run("""
                CREATE CONSTRAINT FOR (r:Run) REQUIRE r.id IS UNIQUE
            """)
            logger.info("Neo4j database constraints initialized successfully.")
    except Exception as e:
        # It's possible constraint already exists or syntax differs slightly in Neo4j version
        logger.info(f"Neo4j constraint creation skipped or already completed: {e}")

def save_meaning_representation(run_id: str, representation: StructuredMeaningRepresentation) -> bool:
    driver = get_driver()
    if not driver:
        logger.warning("Neo4j driver not available. Skipping save.")
        return False
        
    try:
        with driver.session() as session:
            session.execute_write(_save_tx, run_id, representation)
            logger.info(f"Successfully saved meaning representation for run {run_id} to Neo4j.")
            return True
    except Exception as e:
        logger.error(f"Failed to save meaning representation to Neo4j: {e}")
        return False

def _save_tx(tx, run_id: str, representation: StructuredMeaningRepresentation):
    # 1. Create the Run node
    tx.run("""
        MERGE (r:Run {id: $run_id})
        ON CREATE SET r.timestamp = datetime()
    """, run_id=run_id)
    
    # 2. Create meaning nodes
    for node in representation.nodes:
        # We sanitize the label to avoid cypher injection
        safe_label = "".join(c for c in node.type if c.isalnum())
        query = f"""
            MERGE (n:MeaningNode:{safe_label} {{id: $id, run_id: $run_id}})
            ON CREATE SET 
                n.text = $text, 
                n.source_span = $source_span,
                n.type = $type
            WITH n
            MATCH (r:Run {{id: $run_id}})
            MERGE (r)-[:EXTRACTED_NODE]->(n)
        """
        tx.run(
            query, 
            id=node.id, 
            run_id=run_id, 
            text=node.text, 
            source_span=node.source_span,
            type=node.type
        )
        
    # 3. Create relationships
    for rel in representation.relationships:
        safe_rel_type = "".join(c for c in rel.type if c.isalnum() or c == '_')
        query = f"""
            MATCH (s:MeaningNode {{id: $source_id, run_id: $run_id}})
            MATCH (t:MeaningNode {{id: $target_id, run_id: $run_id}})
            MERGE (s)-[r:{safe_rel_type}]->(t)
        """
        tx.run(
            query, 
            source_id=rel.source_id, 
            target_id=rel.target_id, 
            run_id=run_id
        )

def get_meaning_representation(run_id: str) -> StructuredMeaningRepresentation:
    """
    Retrieves the structured meaning representation from Neo4j for validation/visualization.
    If Neo4j is offline, returns an empty representation.
    """
    driver = get_driver()
    if not driver:
        logger.warning("Neo4j driver offline. Returning empty representation.")
        return StructuredMeaningRepresentation(nodes=[], relationships=[])
        
    try:
        with driver.session() as session:
            nodes_res = session.run("""
                MATCH (r:Run {id: $run_id})-[:EXTRACTED_NODE]->(n:MeaningNode)
                RETURN n.id as id, n.type as type, n.text as text, n.source_span as source_span
            """, run_id=run_id)
            
            nodes = []
            node_ids = set()
            for record in nodes_res:
                nodes.append(MeaningNode(
                    id=record["id"],
                    type=record["type"],
                    text=record["text"],
                    source_span=record["source_span"]
                ))
                node_ids.add(record["id"])
                
            rels_res = session.run("""
                MATCH (s:MeaningNode {run_id: $run_id})-[r]->(t:MeaningNode {run_id: $run_id})
                RETURN s.id as source_id, t.id as target_id, type(r) as type
            """, run_id=run_id)
            
            relationships = []
            for record in rels_res:
                relationships.append(MeaningRelationship(
                    source_id=record["source_id"],
                    target_id=record["target_id"],
                    type=record["type"]
                ))
                
            return StructuredMeaningRepresentation(nodes=nodes, relationships=relationships)
    except Exception as e:
        logger.error(f"Failed to fetch representation from Neo4j: {e}")
        return StructuredMeaningRepresentation(nodes=[], relationships=[])
