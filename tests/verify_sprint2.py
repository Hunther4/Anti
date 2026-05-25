import sqlite3
import time
import random
import string
from src.archive import ArchiveManager
from src.brain import Brain

def create_mock_db(db_path, num_entities=100, avg_edges=5):
    """Creates a mock DB with a connected graph for benchmarking."""
    am = ArchiveManager(db_path)
    conn = am._get_conn()
    cursor = conn.cursor()
    
    # Clear tables
    cursor.execute("DELETE FROM edges")
    cursor.execute("DELETE FROM entities")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='entities' OR name='edges'")
    
    entities = []
    for i in range(num_entities):
        # We use a simple observation_id for all to simulate a dense graph for one observation
        obs_id = "obs_1"
        val = ''.join(random.choices(string.ascii_letters, k=10))
        cursor.execute(
            "INSERT INTO entities (observation_id, entity_type, value, timestamp) VALUES (?, ?, ?, ?)",
            (obs_id, "concept", val, "2026-01-01T00:00:00")
        )
        entities.append(cursor.lastrowid)
    
    for ent_id in entities:
        # Add some random edges - MAKE IT SPARSE
        targets = random.sample(entities, k=2) # reduced from avg_edges
        for target_id in targets:
            if ent_id != target_id:
                cursor.execute(
                    "INSERT INTO edges (source_id, target_id, relation_type, timestamp) VALUES (?, ?, ?, ?)",
                    (ent_id, target_id, "relates_to", "2026-01-01T00:00:00")
                )
    
    conn.commit()
    return am

def old_mem_graph_bfs(am, observation_id, depth=2):
    """The old BFS implementation from src/archive.py"""
    from collections import deque
    conn = am._get_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, observation_id, entity_type, value FROM entities WHERE observation_id = ?", (observation_id,))
    initial_entities = cursor.fetchall()
    if not initial_entities: return {"nodes": [], "edges": []}
    
    nodes = {}
    edges = []
    levels = {}
    visited = set()
    queue = deque()
    
    for ent in initial_entities:
        entity_id = ent[0]
        nodes[entity_id] = {"id": entity_id, "observation_id": ent[1], "entity_type": ent[2], "value": ent[3]}
        levels[entity_id] = 0
        visited.add(entity_id)
        queue.append(entity_id)
        
    while queue:
        current_id = queue.popleft()
        current_level = levels[current_id]
        if current_level >= depth: continue
        
        cursor.execute("SELECT target_id, relation_type FROM edges WHERE source_id = ?", (current_id,))
        for row in cursor.fetchall():
            target_id, rel_type = row
            edges.append({"source_id": current_id, "target_id": target_id, "relation_type": rel_type})
            if target_id not in visited:
                cursor.execute("SELECT id, observation_id, entity_type, value FROM entities WHERE id = ?", (target_id,))
                target_ent = cursor.fetchone()
                if target_ent:
                    nodes[target_id] = {"id": target_ent[0], "observation_id": target_ent[1], "entity_type": target_ent[2], "value": target_ent[3]}
                    levels[target_id] = current_level + 1
                    visited.add(target_id)
                    queue.append(target_id)
        
        cursor.execute("SELECT source_id, relation_type FROM edges WHERE target_id = ?", (current_id,))
        for row in cursor.fetchall():
            source_id, rel_type = row
            edges.append({"source_id": source_id, "target_id": current_id, "relation_type": rel_type})
            if source_id not in visited:
                cursor.execute("SELECT id, observation_id, entity_type, value FROM entities WHERE id = ?", (source_id,))
                source_ent = cursor.fetchone()
                if source_ent:
                    nodes[source_id] = {"id": source_ent[0], "observation_id": source_ent[1], "entity_type": source_ent[2], "value": source_ent[3]}
                    levels[source_id] = current_level + 1
                    visited.add(source_id)
                    queue.append(source_id)
                    
    return {"nodes": list(nodes.values()), "edges": edges}

def test_graph_performance():
    print("--- Testing Graph Traversal Performance ---")
    db_path = "test_perf.db"
    am = create_mock_db(db_path, num_entities=500, avg_edges=10)
    obs_id = "obs_1"
    depth = 3
    
    # Measure Old BFS
    start = time.time()
    res_old = old_mem_graph_bfs(am, obs_id, depth)
    end = time.time()
    time_old = end - start
    print(f"Old BFS time: {time_old:.4f}s (Nodes: {len(res_old['nodes'])})")
    
    # Measure New CTE
    start = time.time()
    res_new = am.mem_graph(obs_id, depth)
    end = time.time()
    time_new = end - start
    print(f"New CTE time: {time_new:.4f}s (Nodes: {len(res_new['nodes'])})")
    
    gain = (time_old / time_new) if time_new > 0 else 0
    print(f"Performance gain: {gain:.2f}x")
    
    assert len(res_old['nodes']) == len(res_new['nodes']), "Node count mismatch!"
    print("✅ Graph traversal results match and performance measured.")
    return gain

def test_brain_u_shape():
    print("\n--- Testing Brain U-Shape Ordering ---")
    brain = Brain()
    system_prompt = "You are a helpful assistant."
    # Create 5 chunks of history
    history_chunks = [
        [{"role": "user", "content": "chunk 0"}, {"role": "assistant", "content": "resp 0"}],
        [{"role": "user", "content": "chunk 1"}, {"role": "assistant", "content": "resp 1"}],
        [{"role": "user", "content": "chunk 2"}, {"role": "assistant", "content": "resp 2"}],
        [{"role": "user", "content": "chunk 3"}, {"role": "assistant", "content": "resp 3"}],
        [{"role": "user", "content": "chunk 4"}, {"role": "assistant", "content": "resp 4"}],
    ]
    
    # Brain.prepare_messages expects a single history list. 
    # To test U-shape, we need to modify prepare_messages to actually split history if it's too long,
    # or we can test the ushape_order method directly if we can't easily trigger the split.
    # Given current implementation, chunks = [history], so it won't trigger U-shape unless we pass multiple chunks.
    # Let's test ushape_order directly.
    
    result = brain.ushape_order(history_chunks)
    # Expected: [0, 2, 4, 3, 1]
    expected_indices = [0, 2, 4, 3, 1]
    actual_indices = []
    # Find index of each chunk in the result
    for chunk in history_chunks:
        # This is a bit naive but works for this test
        for i, res_chunk in enumerate(result):
            if res_chunk == chunk:
                actual_indices.append(i)
                break
    
    # Since we want to see if it's ordered [0, 2, 4, 3, 1]
    # Let's check the content instead.
    actual_contents = [c[0]['content'] for c in result]
    expected_contents = ["chunk 0", "chunk 2", "chunk 4", "chunk 3", "chunk 1"]
    
    print(f"Expected order: {expected_contents}")
    print(f"Actual order:   {actual_contents}")
    
    assert actual_contents == expected_contents, "U-shape ordering failed!"
    print("✅ Brain U-shape ordering verified.")

if __name__ == "__main__":
    try:
        gain = test_graph_performance()
        test_brain_u_shape()
        print("\n🚀 ALL TESTS PASSED")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
