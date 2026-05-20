import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.vector_store import get_embedding_model
print("Loading embedding model...")
model = get_embedding_model()
print("Model loaded successfully:", model)
