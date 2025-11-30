import sqlite3
import json
import math
from datetime import datetime
from typing import List, Dict, Optional

class DatabaseService:
    def __init__(self, db_path='database/resume_database.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database with user-centric schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ============================================
        #  USERS TABLE
        # ============================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ============================================
        #  RESUMES TABLE
        # ============================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                file_name TEXT,
                extracted_text TEXT,
                skills TEXT,                 -- JSON list of skills
                embedding TEXT,              -- JSON embedding vector
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # ============================================
        #  JOB DESCRIPTIONS TABLE
        # ============================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_descriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                job_title TEXT,
                job_text TEXT,
                required_skills TEXT,        -- JSON list
                embedding TEXT,              -- JSON vector
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # ============================================
        #  MATCH SCORES TABLE
        # ============================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS match_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER,
                job_id INTEGER,
                similarity_score REAL,
                missing_skills TEXT,         -- JSON list
                ats_score INTEGER,           -- ATS score (0–100)
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes(id),
                FOREIGN KEY (job_id) REFERENCES job_descriptions(id)
            )
        ''')
        
        # ============================================
        #  ATS SUGGESTIONS TABLE
        # ============================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ats_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER,
                suggestion TEXT,
                category TEXT,               -- e.g., 'skills', 'format', 'keywords'
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes(id)
            )
        ''')
        
        # ============================================
        #  SKILLS MASTER TABLE
        # ============================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skills_master (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT UNIQUE
            )
        ''')
        
        # ============================================
        #  RESUME SKILL MAP TABLE
        # ============================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resume_skill_map (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER,
                skill_name TEXT,
                FOREIGN KEY (resume_id) REFERENCES resumes(id)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_descriptions_user_id ON job_descriptions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_match_scores_resume_id ON match_scores(resume_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_match_scores_job_id ON match_scores(job_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ats_suggestions_resume_id ON ats_suggestions(resume_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_resume_skill_map_resume_id ON resume_skill_map(resume_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_skills_master_name ON skills_master(skill_name)')
        
        conn.commit()
        conn.close()
        print(f"Database initialized with user-centric schema: {self.db_path}")
    
    # ============================================
    #  USER MANAGEMENT
    # ============================================
    
    def create_user(self, name: str, email: str) -> int:
        """Create a new user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO users (name, email) VALUES (?, ?)', (name, email))
            user_id = cursor.lastrowid
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            # User with email already exists
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            return user[0] if user else None
        finally:
            conn.close()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
        finally:
            conn.close()
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
        finally:
            conn.close()
    
    # ============================================
    #  RESUME MANAGEMENT
    # ============================================
    
    def store_resume(self, user_id: int, resume_data: Dict) -> int:
        """Store resume for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Convert skills and embedding to JSON
            skills_json = json.dumps(resume_data.get('skills', []))
            embedding_json = json.dumps(resume_data.get('embedding', []))
            
            cursor.execute('''
                INSERT INTO resumes (user_id, file_name, extracted_text, skills, embedding)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                resume_data.get('file_name', ''),
                resume_data.get('extracted_text', ''),
                skills_json,
                embedding_json
            ))
            
            resume_id = cursor.lastrowid
            
            # Store skills in master table and mapping
            self._store_resume_skills(resume_id, resume_data.get('skills', []))
            
            conn.commit()
            return resume_id
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to store resume: {str(e)}")
        finally:
            conn.close()
    
    def get_user_resumes(self, user_id: int) -> List[Dict]:
        """Get all resumes for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC', (user_id,))
            rows = cursor.fetchall()
            
            resumes = []
            for row in rows:
                columns = [description[0] for description in cursor.description]
                resume_dict = dict(zip(columns, row))
                
                # Parse JSON fields
                resume_dict['skills'] = json.loads(resume_dict['skills'] or '[]')
                resume_dict['embedding'] = json.loads(resume_dict['embedding'] or '[]')
                
                resumes.append(resume_dict)
            
            return resumes
            
        finally:
            conn.close()
    
    def get_resume(self, resume_id: int) -> Optional[Dict]:
        """Get resume by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM resumes WHERE id = ?', (resume_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                resume_dict = dict(zip(columns, row))
                
                # Parse JSON fields
                resume_dict['skills'] = json.loads(resume_dict['skills'] or '[]')
                resume_dict['embedding'] = json.loads(resume_dict['embedding'] or '[]')
                
                return resume_dict
            return None
            
        finally:
            conn.close()
    
    # ============================================
    #  JOB DESCRIPTION MANAGEMENT
    # ============================================
    
    def store_job_description(self, user_id: int, job_data: Dict) -> int:
        """Store job description for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Convert skills and embedding to JSON
            skills_json = json.dumps(job_data.get('required_skills', []))
            embedding_json = json.dumps(job_data.get('embedding', []))
            
            cursor.execute('''
                INSERT INTO job_descriptions (user_id, job_title, job_text, required_skills, embedding)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                job_data.get('job_title', ''),
                job_data.get('job_text', ''),
                skills_json,
                embedding_json
            ))
            
            job_id = cursor.lastrowid
            conn.commit()
            return job_id
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to store job description: {str(e)}")
        finally:
            conn.close()
    
    def get_user_job_descriptions(self, user_id: int) -> List[Dict]:
        """Get all job descriptions for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM job_descriptions WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
            rows = cursor.fetchall()
            
            jobs = []
            for row in rows:
                columns = [description[0] for description in cursor.description]
                job_dict = dict(zip(columns, row))
                
                # Parse JSON fields
                job_dict['required_skills'] = json.loads(job_dict['required_skills'] or '[]')
                job_dict['embedding'] = json.loads(job_dict['embedding'] or '[]')
                
                jobs.append(job_dict)
            
            return jobs
            
        finally:
            conn.close()
    
    # ============================================
    #  MATCH SCORES MANAGEMENT
    # ============================================
    
    def store_match_score(self, resume_id: int, job_id: int, match_data: Dict) -> int:
        """Store match score between resume and job"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Convert missing skills to JSON
            missing_skills_json = json.dumps(match_data.get('missing_skills', []))
            
            cursor.execute('''
                INSERT INTO match_scores (resume_id, job_id, similarity_score, missing_skills, ats_score)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                resume_id,
                job_id,
                match_data.get('similarity_score', 0.0),
                missing_skills_json,
                match_data.get('ats_score', 0)
            ))
            
            match_id = cursor.lastrowid
            conn.commit()
            return match_id
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to store match score: {str(e)}")
        finally:
            conn.close()
    
    def get_resume_matches(self, resume_id: int) -> List[Dict]:
        """Get all matches for a resume"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT ms.*, jd.job_title 
                FROM match_scores ms
                JOIN job_descriptions jd ON ms.job_id = jd.id
                WHERE ms.resume_id = ?
                ORDER BY ms.similarity_score DESC
            ''', (resume_id,))
            
            rows = cursor.fetchall()
            matches = []
            
            for row in rows:
                columns = [description[0] for description in cursor.description]
                match_dict = dict(zip(columns, row))
                
                # Parse JSON fields
                match_dict['missing_skills'] = json.loads(match_dict['missing_skills'] or '[]')
                
                matches.append(match_dict)
            
            return matches
            
        finally:
            conn.close()
    
    # ============================================
    #  ATS SUGGESTIONS MANAGEMENT
    # ============================================
    
    def store_ats_suggestions(self, resume_id: int, suggestions: List[Dict]) -> bool:
        """Store ATS suggestions for a resume"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            for suggestion in suggestions:
                cursor.execute('''
                    INSERT INTO ats_suggestions (resume_id, suggestion, category)
                    VALUES (?, ?, ?)
                ''', (
                    resume_id,
                    suggestion.get('suggestion', ''),
                    suggestion.get('category', 'general')
                ))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to store ATS suggestions: {str(e)}")
        finally:
            conn.close()
    
    def get_ats_suggestions(self, resume_id: int) -> List[Dict]:
        """Get ATS suggestions for a resume"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM ats_suggestions WHERE resume_id = ? ORDER BY created_at', (resume_id,))
            rows = cursor.fetchall()
            
            suggestions = []
            for row in rows:
                columns = [description[0] for description in cursor.description]
                suggestion_dict = dict(zip(columns, row))
                suggestions.append(suggestion_dict)
            
            return suggestions
            
        finally:
            conn.close()
    
    # ============================================
    #  SKILLS MANAGEMENT
    # ============================================
    
    def _store_resume_skills(self, resume_id: int, skills: List[str]):
        """Store skills in master table and create mappings"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            for skill in skills:
                # Add to master table if not exists
                cursor.execute('INSERT OR IGNORE INTO skills_master (skill_name) VALUES (?)', (skill,))
                
                # Create mapping
                cursor.execute('INSERT INTO resume_skill_map (resume_id, skill_name) VALUES (?, ?)', (resume_id, skill))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to store resume skills: {str(e)}")
        finally:
            conn.close()
    
    def get_all_skills(self) -> List[str]:
        """Get all unique skills from master table"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT skill_name FROM skills_master ORDER BY skill_name')
            rows = cursor.fetchall()
            return [row[0] for row in rows]
            
        finally:
            conn.close()
    
    def get_skill_analytics(self) -> Dict:
        """Get skill usage analytics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Most common skills
            cursor.execute('''
                SELECT skill_name, COUNT(*) as usage_count
                FROM resume_skill_map
                GROUP BY skill_name
                ORDER BY usage_count DESC
                LIMIT 20
            ''')
            
            top_skills = [{'skill': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            return {
                'total_unique_skills': len(self.get_all_skills()),
                'top_skills': top_skills
            }
            
        finally:
            conn.close()
    
    # ============================================
    #  STATISTICS AND ANALYTICS
    # ============================================
    
    def get_statistics(self) -> Dict:
        """Get comprehensive database statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # User stats
            cursor.execute('SELECT COUNT(*) FROM users')
            stats['total_users'] = cursor.fetchone()[0]
            
            # Resume stats
            cursor.execute('SELECT COUNT(*) FROM resumes')
            stats['total_resumes'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM resumes WHERE embedding != "[]"')
            stats['resumes_with_embeddings'] = cursor.fetchone()[0]
            
            # Job description stats
            cursor.execute('SELECT COUNT(*) FROM job_descriptions')
            stats['total_job_descriptions'] = cursor.fetchone()[0]
            
            # Match stats
            cursor.execute('SELECT COUNT(*) FROM match_scores')
            stats['total_matches'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT AVG(similarity_score) FROM match_scores')
            avg_similarity = cursor.fetchone()[0]
            stats['average_similarity_score'] = round(avg_similarity, 3) if avg_similarity else 0.0
            
            cursor.execute('SELECT AVG(ats_score) FROM match_scores')
            avg_ats = cursor.fetchone()[0]
            stats['average_ats_score'] = round(avg_ats, 1) if avg_ats else 0.0
            
            # ATS suggestions stats
            cursor.execute('SELECT COUNT(*) FROM ats_suggestions')
            stats['total_ats_suggestions'] = cursor.fetchone()[0]
            
            # Skills analytics
            skill_analytics = self.get_skill_analytics()
            stats.update(skill_analytics)
            
            stats['database_path'] = self.db_path
            
            return stats
            
        finally:
            conn.close()
    
    # ============================================
    #  LEGACY COMPATIBILITY (for existing code)
    # ============================================
    
    def get_all_resumes(self) -> List[Dict]:
        """Legacy method - get all resumes (for compatibility)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM resumes ORDER BY uploaded_at DESC')
            rows = cursor.fetchall()
            
            resumes = []
            for row in rows:
                columns = [description[0] for description in cursor.description]
                resume_dict = dict(zip(columns, row))
                
                # Parse JSON fields
                resume_dict['skills'] = json.loads(resume_dict['skills'] or '[]')
                resume_dict['embedding'] = json.loads(resume_dict['embedding'] or '[]')
                
                resumes.append(resume_dict)
            
            return resumes
            
        finally:
            conn.close()
    
    def search_by_skills(self, skills: List[str]) -> List[Dict]:
        """Legacy method - search resumes by skills"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            results = []
            cursor.execute('SELECT * FROM resumes')
            rows = cursor.fetchall()
            
            for row in rows:
                columns = [description[0] for description in cursor.description]
                resume_dict = dict(zip(columns, row))
                
                # Parse skills
                resume_skills = json.loads(resume_dict['skills'] or '[]')
                
                # Check for matches
                matching_skills = set(skills) & set(resume_skills)
                if matching_skills:
                    resume_dict['matching_skills'] = list(matching_skills)
                    resume_dict['match_score'] = len(matching_skills) / len(skills)
                    results.append(resume_dict)
            
            # Sort by match score
            results.sort(key=lambda x: x['match_score'], reverse=True)
            return results
            
        finally:
            conn.close()
    
    def find_similar_resumes(self, embedding: List[float], limit: int = 10) -> List[Dict]:
        """Legacy method - find similar resumes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM resumes WHERE embedding != "[]"')
            rows = cursor.fetchall()
            
            similarities = []
            
            for row in rows:
                columns = [description[0] for description in cursor.description]
                resume_dict = dict(zip(columns, row))
                
                # Parse embedding
                stored_embedding = json.loads(resume_dict['embedding'] or '[]')
                
                if stored_embedding:
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(embedding, stored_embedding)
                    resume_dict['similarity_score'] = float(similarity)
                    similarities.append(resume_dict)
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similarities[:limit]
            
        finally:
            conn.close()
    
    def _cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors"""
        try:
            # Convert to lists if needed
            if not isinstance(vec1, list):
                vec1 = list(vec1)
            if not isinstance(vec2, list):
                vec2 = list(vec2)
            
            if not vec1 or not vec2 or len(vec1) != len(vec2):
                return 0.0
            
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # Calculate magnitudes
            mag1 = math.sqrt(sum(a * a for a in vec1))
            mag2 = math.sqrt(sum(b * b for b in vec2))
            
            if mag1 == 0 or mag2 == 0:
                return 0.0
            
            return dot_product / (mag1 * mag2)
            
        except Exception as e:
            print(f"Error calculating cosine similarity: {str(e)}")
            return 0.0
