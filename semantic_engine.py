import os
import numpy as np

# მძიმე იმპორტები გადატანილია Lazy Loading რეჟიმში
faiss = None
SentenceTransformer = None

class SemanticEngine:
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2', index_path='legal_index.faiss'):
        self.model_name = model_name
        self.index_path = index_path
        self.model = None
        self.index = None
        self.dimension = 384 # MiniLM-L12-v2-ის განზომილება

    def preload(self):
        """მოდელის და ინდექსის წინასწარი ჩატვირთვა."""
        self._load_model()
        self.load_index()

    def _load_model(self):
        """მოდელის ჩატვირთვა (Lazy Loading)."""
        global SentenceTransformer
        if SentenceTransformer is None:
            print(f"Loading model: {self.model_name}...")
            from sentence_transformers import SentenceTransformer
            
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)
            print("Model loaded successfully.")
        return self.model

    def build_index(self, texts):
        """ახალი FAISS ინდექსის აგება ტექსტების სიიდან."""
        global faiss
        if faiss is None:
            import faiss
            
        model = self._load_model()
        if not model:
            raise ImportError("Sentence-transformers is not installed.")
            
        print(f"Generating embeddings for {len(texts)} articles...")
        embeddings = model.encode(texts, show_progress_bar=True)
        embeddings = np.array(embeddings).astype('float32')

        # FAISS ინდექსის შექმნა (L2 მანძილით ან Cosine Similarity)
        # Cosine-სთვის ვიყენებთ ნორმალიზებას და InnerProduct-ს
        faiss.normalize_L2(embeddings)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings)
        
        self.save_index()
        return len(texts)

    def save_index(self):
        """ინდექსის ფაილში შენახვა."""
        global faiss
        if faiss is None:
            import faiss
            
        if self.index:
            faiss.write_index(self.index, self.index_path)
            print(f"Index saved to {self.index_path}")

    def load_index(self):
        """ინდექსის ფაილიდან ჩატვირთვა."""
        global faiss
        if faiss is None:
            try:
                import faiss
            except ImportError:
                return False
                
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            print(f"Index loaded from {self.index_path}")
            return True
        return False

    def search(self, query, top_k=5):
        """სემანტიკური ძებნა."""
        if self.index is None:
            if not self.load_index():
                return []

        model = self._load_model()
        query_vector = model.encode([query])
        query_vector = np.array(query_vector).astype('float32')
        faiss.normalize_L2(query_vector)

        distances, indices = self.index.search(query_vector, top_k)
        
        # ვაბრუნებთ მხოლოდ ვალიდურ ინდექსებს და მათ ქულებს (scores)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1: # FAISS-მა შეიძლება დააბრუნოს -1 თუ შედეგი ცოტაა
                results.append({"vector_id": int(idx), "score": float(dist)})
        
        return results
