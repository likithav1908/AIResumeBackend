import json
import hashlib
import random
from typing import List, Dict, Optional

class EmbeddingService:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model = None
        self.fallback_mode = True
        print("Embedding Service initialized in fallback mode (hash-based)")
    
    def load_model(self):
        """Load sentence transformer model - disabled due to compatibility issues"""
        pass
    
    def generate_embedding(self, text: str) -> Dict:
        """Generate embedding for text using fallback method"""
        if not text or not text.strip():
            return {
                "embedding": [],
                "dimension": 0,
                "model": self.model_name,
                "note": "Empty text provided"
            }
        
        # Fallback embedding using hash-based approach
        try:
            # Create deterministic embedding based on text hash
            embedding = self._create_fallback_embedding(text)
            
            return {
                "embedding": embedding,
                "dimension": len(embedding),
                "model": f"{self.model_name}_fallback",
                "note": "Using fallback hash-based embedding"
            }
            
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            return {
                "embedding": [],
                "dimension": 0,
                "model": self.model_name,
                "error": str(e)
            }
    
    def _create_fallback_embedding(self, text: str) -> List[float]:
        """Create fallback embedding using text features"""
        # Clean and normalize text
        text = text.lower().strip()
        
        # Create features from text
        features = []
        
        # 1. Text length features
        features.append(len(text) / 10000.0)  # Normalized length
        features.append(len(text.split()) / 1000.0)  # Word count
        
        # 2. Character distribution features
        char_counts = {
            'a': text.count('a'), 'e': text.count('e'), 'i': text.count('i'),
            'o': text.count('o'), 'u': text.count('u'), ' ': text.count(' '),
            '.': text.count('.'), ',': text.count(','), '\n': text.count('\n')
        }
        
        for char, count in char_counts.items():
            features.append(count / 1000.0)
        
        # 3. Word-level features
        words = text.split()
        common_words = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had']
        word_features = [words.count(word) / 100.0 for word in common_words[:20]]
        features.extend(word_features)
        
        # 4. Hash-based features for uniqueness
        text_hash = hashlib.md5(text.encode()).hexdigest()
        hash_features = [int(text_hash[i:i+2], 16) / 255.0 for i in range(0, min(32, len(text_hash)), 2)]
        features.extend(hash_features)
        
        # 5. Technical skill indicators
        tech_skills = ['python', 'java', 'javascript', 'react', 'node', 'sql', 'aws', 'docker', 'kubernetes', 'git', 'linux', 'html', 'css', 'angular', 'vue', 'mongodb', 'postgresql', 'mysql', 'redis', 'api', 'devops']
        skill_features = [1.0 if skill in text else 0.0 for skill in tech_skills]
        features.extend(skill_features)
        
        # 6. Random seed based on text for consistency
        random.seed(hash(text))
        random_features = [random.random() for _ in range(50)]
        features.extend(random_features)
        
        # Ensure we have exactly 384 dimensions (like the original model)
        target_dim = 384
        if len(features) < target_dim:
            # Pad with zeros
            features.extend([0.0] * (target_dim - len(features)))
        elif len(features) > target_dim:
            # Truncate
            features = features[:target_dim]
        
        # Normalize the embedding
        total = sum(abs(x) for x in features)
        if total > 0:
            features = [x / total for x in features]
        
        return features
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        if not embedding1 or not embedding2 or len(embedding1) != len(embedding2):
            return 0.0
        
        try:
            # Simple dot product for fallback embeddings
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
            
            # Calculate magnitudes
            mag1 = sum(a * a for a in embedding1) ** 0.5
            mag2 = sum(b * b for b in embedding2) ** 0.5
            
            if mag1 == 0 or mag2 == 0:
                return 0.0
            
            return dot_product / (mag1 * mag2)
            
        except Exception as e:
            print(f"Error calculating similarity: {str(e)}")
            return 0.0
    
    def batch_generate_embeddings(self, texts: List[str]) -> List[Dict]:
        """Generate embeddings for multiple texts"""
        results = []
        for text in texts:
            result = self.generate_embedding(text)
            results.append(result)
        return results
