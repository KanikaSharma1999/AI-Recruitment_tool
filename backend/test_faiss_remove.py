import numpy as np
import faiss

def test_remove():
    dim = 4
    index = faiss.IndexFlatIP(dim)
    
    # Add 3 vectors
    v1 = np.array([1, 0, 0, 0], dtype='float32').reshape(1, -1)
    v2 = np.array([0, 1, 0, 0], dtype='float32').reshape(1, -1)
    v3 = np.array([0, 0, 1, 0], dtype='float32').reshape(1, -1)
    
    index.add(v1)
    index.add(v2)
    index.add(v3)
    
    print(f"Initial total: {index.ntotal}")
    
    # Try removing the 2nd vector (index 1)
    # Note: flat index requires ID Selector for remove_ids
    try:
        # In FAISS, remove_ids takes an IDSelector. 
        # A simple array of IDs can be passed which will be converted automatically by SWIG.
        ids_to_remove = np.array([1], dtype='int64')
        removed = index.remove_ids(ids_to_remove)
        print(f"Removed count: {removed}")
        print(f"New total: {index.ntotal}")
        
        # Verify remaining vectors
        # If we search, we should find them
        # Let's search with v2 (should be low similarity now) and v3 (should be high similarity)
        scores, indices = index.search(v3, 1)
        print(f"Search for v3 result: score={scores[0][0]}, index={indices[0][0]}")
    except Exception as e:
        print(f"Error during remove_ids: {e}")

if __name__ == "__main__":
    test_remove()
