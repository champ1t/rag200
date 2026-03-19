from sentence_transformers import SentenceTransformer

model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
try:
    model = SentenceTransformer(model_name)
    dim = model.get_sentence_embedding_dimension()
    print(f"Model: {model_name}")
    print(f"Dimension: {dim}")
except Exception as e:
    print(f"Error loading model: {e}")
