import csv
import os
from typing import List, Dict, Optional
from datetime import datetime
import logging
from database.database_service import DatabaseService
from embedding_service import EmbeddingService
from nlp_service import NLPService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobService:
    def __init__(self):
        self.db_service = DatabaseService()
        self.embedding_service = EmbeddingService()
        self.nlp_service = NLPService()
        self.init_job_database()
    
    def init_job_database(self):
        """Initialize job postings table"""
        conn = self.db_service.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_postings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                description TEXT,
                requirements TEXT,
                skills_json TEXT,
                keywords_json TEXT,
                embedding_blob BLOB,
                embedding_dimension INTEGER,
                embedding_model TEXT,
                salary_min REAL,
                salary_max REAL,
                job_type TEXT,
                experience_level TEXT,
                posted_date DATE,
                source_file TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_job_skills 
            ON job_postings(skills_json)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_job_location 
            ON job_postings(location)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Job database initialized")
    
    def feed_jobs_from_csv(self, csv_file_path: str, source_name: str = None) -> Dict:
        """Feed jobs from CSV file into database"""
        try:
            if not os.path.exists(csv_file_path):
                return {"error": f"CSV file not found: {csv_file_path}"}
            
            source_name = source_name or os.path.basename(csv_file_path)
            jobs_processed = 0
            jobs_failed = 0
            errors = []
            
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                # Detect CSV dialect
                sample = file.read(1024)
                file.seek(0)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample)
                
                reader = csv.DictReader(file, dialect=dialect)
                
                for row_num, row in enumerate(reader, 1):
                    try:
                        job_data = self._parse_csv_row(row, source_name)
                        if job_data:
                            self._store_job(job_data)
                            jobs_processed += 1
                        else:
                            jobs_failed += 1
                            errors.append(f"Row {row_num}: Failed to parse job data")
                    except Exception as e:
                        jobs_failed += 1
                        errors.append(f"Row {row_num}: {str(e)}")
                        logger.error(f"Error processing row {row_num}: {str(e)}")
            
            logger.info(f"CSV processing completed: {jobs_processed} processed, {jobs_failed} failed")
            
            return {
                "status": "completed",
                "source_file": source_name,
                "jobs_processed": jobs_processed,
                "jobs_failed": jobs_failed,
                "errors": errors[:10]  # Limit errors to prevent large responses
            }
            
        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
            return {"error": f"CSV processing failed: {str(e)}"}
    
    def _parse_csv_row(self, row: Dict, source_file: str) -> Optional[Dict]:
        """Parse CSV row into job data"""
        try:
            # Map common CSV column names to standard fields
            field_mapping = {
                'title': ['title', 'job_title', 'position', 'role'],
                'company': ['company', 'company_name', 'employer'],
                'location': ['location', 'city', 'city_state', 'place'],
                'description': ['description', 'job_description', 'details', 'summary'],
                'requirements': ['requirements', 'qualifications', 'skills_required', 'must_have'],
                'salary_min': ['salary_min', 'min_salary', 'salary_low'],
                'salary_max': ['salary_max', 'max_salary', 'salary_high'],
                'job_type': ['job_type', 'employment_type', 'type'],
                'experience_level': ['experience_level', 'seniority', 'level'],
                'posted_date': ['posted_date', 'date_posted', 'posted', 'date']
            }
            
            job_data = {}
            
            # Extract data using field mapping
            for standard_field, csv_fields in field_mapping.items():
                for csv_field in csv_fields:
                    if csv_field in row and row[csv_field].strip():
                        job_data[standard_field] = row[csv_field].strip()
                        break
            
            # Generate unique job ID
            job_id = self._generate_job_id(job_data.get('title', ''), job_data.get('company', ''))
            job_data['job_id'] = job_id
            job_data['source_file'] = source_file
            
            # Validate required fields
            if not job_data.get('title'):
                return None
            
            # Combine description and requirements for full text
            full_text = f"{job_data.get('description', '')} {job_data.get('requirements', '')}"
            job_data['full_text'] = full_text.strip()
            
            return job_data
            
        except Exception as e:
            logger.error(f"Error parsing CSV row: {str(e)}")
            return None
    
    def _generate_job_id(self, title: str, company: str) -> str:
        """Generate unique job ID"""
        import re
        # Clean and create ID
        title_clean = re.sub(r'[^a-zA-Z0-9]', '', title.lower())[:20]
        company_clean = re.sub(r'[^a-zA-Z0-9]', '', company.lower())[:15]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"{company_clean}_{title_clean}_{timestamp}"
    
    def _store_job(self, job_data: Dict):
        """Store job in database with NLP processing"""
        conn = self.db_service.get_connection()
        cursor = conn.cursor()
        
        try:
            # Process with NLP
            nlp_results = self.nlp_service.extract_skills_and_keywords(job_data.get('full_text', ''))
            
            # Generate embedding
            embedding_result = self.embedding_service.generate_embedding(job_data.get('full_text', ''))
            
            # Convert embedding to bytes
            embedding_blob = None
            embedding_dimension = None
            embedding_model = None
            
            if embedding_result and 'embedding' in embedding_result:
                import numpy as np
                embedding_array = np.array(embedding_result['embedding'], dtype=np.float32)
                embedding_blob = embedding_array.tobytes()
                embedding_dimension = embedding_result.get('dimension', len(embedding_result['embedding']))
                embedding_model = embedding_result.get('model', 'unknown')
            
            # Store in database
            cursor.execute('''
                INSERT OR REPLACE INTO job_postings (
                    job_id, title, company, location, description, requirements,
                    skills_json, keywords_json, embedding_blob, embedding_dimension,
                    embedding_model, salary_min, salary_max, job_type, experience_level,
                    posted_date, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_data['job_id'],
                job_data.get('title', ''),
                job_data.get('company', ''),
                job_data.get('location', ''),
                job_data.get('description', ''),
                job_data.get('requirements', ''),
                str(nlp_results.get('SKILL', [])),
                str(nlp_results.get('KEYWORDS', [])),
                embedding_blob,
                embedding_dimension,
                embedding_model,
                job_data.get('salary_min'),
                job_data.get('salary_max'),
                job_data.get('job_type'),
                job_data.get('experience_level'),
                job_data.get('posted_date'),
                job_data.get('source_file')
            ))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job by ID"""
        conn = self.db_service.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM job_postings WHERE job_id = ?', (job_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_job_dict(cursor, row)
            return None
            
        finally:
            conn.close()
    
    def get_all_jobs(self, limit: int = 100) -> List[Dict]:
        """Get all jobs with optional limit"""
        conn = self.db_service.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM job_postings ORDER BY created_at DESC LIMIT ?', (limit,))
            rows = cursor.fetchall()
            return [self._row_to_job_dict(cursor, row) for row in rows]
            
        finally:
            conn.close()
    
    def search_jobs_by_skills(self, skills: List[str], limit: int = 50) -> List[Dict]:
        """Search jobs by required skills"""
        conn = self.db_service.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM job_postings')
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                job_dict = self._row_to_job_dict(cursor, row)
                job_skills = job_dict.get('skills', [])
                
                # Check if any search skills match job skills
                matching_skills = set(skills) & set(job_skills)
                if matching_skills:
                    job_dict['matching_skills'] = list(matching_skills)
                    job_dict['match_score'] = len(matching_skills) / len(skills)
                    results.append(job_dict)
            
            # Sort by match score
            results.sort(key=lambda x: x['match_score'], reverse=True)
            return results[:limit]
            
        finally:
            conn.close()
    
    def find_similar_jobs(self, embedding: List[float], limit: int = 10) -> List[Dict]:
        """Find similar jobs using embedding similarity"""
        conn = self.db_service.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM job_postings WHERE embedding_blob IS NOT NULL')
            rows = cursor.fetchall()
            
            target_embedding = np.array(embedding)
            similarities = []
            
            for row in rows:
                job_dict = self._row_to_job_dict(cursor, row)
                stored_embedding = np.array(job_dict.get('embedding', []))
                
                if len(stored_embedding) > 0:
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(target_embedding, stored_embedding)
                    job_dict['similarity_score'] = float(similarity)
                    similarities.append(job_dict)
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similarities[:limit]
            
        finally:
            conn.close()
    
    def get_job_statistics(self) -> Dict:
        """Get job database statistics"""
        conn = self.db_service.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM job_postings')
            total_jobs = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM job_postings WHERE embedding_blob IS NOT NULL')
            jobs_with_embeddings = cursor.fetchone()[0]
            
            cursor.execute('SELECT DISTINCT location FROM job_postings WHERE location != ""')
            locations = [row[0] for row in cursor.fetchall()]
            
            cursor.execute('SELECT DISTINCT job_type FROM job_postings WHERE job_type != ""')
            job_types = [row[0] for row in cursor.fetchall()]
            
            return {
                'total_jobs': total_jobs,
                'jobs_with_embeddings': jobs_with_embeddings,
                'locations': locations,
                'job_types': job_types
            }
            
        finally:
            conn.close()
    
    def _row_to_job_dict(self, cursor, row) -> Dict:
        """Convert database row to job dictionary"""
        import numpy as np
        import json
        
        columns = [description[0] for description in cursor.description]
        job_dict = dict(zip(columns, row))
        
        # Parse JSON fields
        try:
            job_dict['skills'] = json.loads(job_dict['skills_json'] or '[]')
        except:
            job_dict['skills'] = []
        
        try:
            job_dict['keywords'] = json.loads(job_dict['keywords_json'] or '[]')
        except:
            job_dict['keywords'] = []
        
        # Convert embedding back from bytes
        if job_dict['embedding_blob']:
            embedding_bytes = job_dict['embedding_blob']
            embedding_array = np.frombuffer(embedding_bytes, dtype=np.float32)
            job_dict['embedding'] = embedding_array.tolist()
        else:
            job_dict['embedding'] = []
        
        # Remove raw fields
        for field in ['skills_json', 'keywords_json', 'embedding_blob']:
            if field in job_dict:
                del job_dict[field]
        
        return job_dict
    
    def _cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors"""
        import numpy as np
        
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
