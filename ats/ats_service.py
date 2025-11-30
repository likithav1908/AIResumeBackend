import json
import math
import re
import logging
from typing import Dict, List, Tuple
from database.database_service import DatabaseService
from nlp.nlp_service import NLPService
from nlp.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class ATSService:
    def __init__(self, db_service: DatabaseService = None, nlp_service: NLPService = None, embedding_service: EmbeddingService = None):
        self.db_service = db_service or DatabaseService()
        self.nlp_service = nlp_service or NLPService()
        self.embedding_service = embedding_service or EmbeddingService()
    
    def calculate_ats_score(self, resume_data: Dict) -> Dict:
        """Calculate comprehensive ATS score for resume"""
        try:
            scores = {}
            
            # 1. Format and Structure Score (25%)
            scores['format_score'] = self._calculate_format_score(resume_data)
            
            # 2. Skills Match Score (30%)
            scores['skills_score'] = self._calculate_skills_score(resume_data)
            
            # 3. Experience Score (25%)
            scores['experience_score'] = self._calculate_experience_score(resume_data)
            
            # 4. Education Score (10%)
            scores['education_score'] = self._calculate_education_score(resume_data)
            
            # 5. Keyword Density Score (10%)
            scores['keyword_score'] = self._calculate_keyword_score(resume_data)
            
            # Calculate weighted overall score - rebalanced to prioritize skills
            weights = {
                'format_score': 0.15,      # Reduced from 25% - less important
                'skills_score': 0.45,      # Increased from 30% - most important
                'experience_score': 0.20,  # Reduced from 25% - moderate importance
                'education_score': 0.10,   # Unchanged
                'keyword_score': 0.10      # Unchanged
            }
            
            overall_score = sum(
                scores[category] * weights[category] 
                for category in scores
            )
            
            scores['overall_score'] = overall_score
            scores['ats_grade'] = self._get_ats_grade(overall_score)
            
            return scores
            
        except Exception as e:
            logger.error(f"Error calculating ATS score: {str(e)}")
            return {
                'overall_score': 0.0,
                'ats_grade': 'F',
                'error': str(e)
            }
    
    def find_matching_jobs(self, resume_data: Dict, limit: int = None) -> List[Dict]:
        """Find best matching jobs for resume"""
        try:
            # Get resume embedding
            resume_embedding = resume_data.get('embedding', [])
            if not resume_embedding:
                logger.warning("No embedding found for resume")
                return []
            
            # Get ATS score first to check if candidate is qualified
            ats_scores = self.calculate_ats_score(resume_data)
            overall_score = ats_scores.get('overall_score', 0)
            ats_grade = ats_scores.get('ats_grade', 'F')
            
            # If ATS score is too low, return empty matches
            if overall_score < 0.2:
                logger.warning(f"Candidate not qualified for job matching - ATS Score: {overall_score:.3f}, Grade: {ats_grade}")
                return []
            
            # Get all jobs with embeddings from database directly
            conn = self.db_service.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT job_title, job_text, required_skills, embedding 
                FROM job_descriptions 
                WHERE embedding IS NOT NULL 
                LIMIT 100
            """)
            rows = cursor.fetchall()
            conn.close()
            
            print(f"🔍 ATS Debug: Found {len(rows)} jobs with embeddings in database")
            
            # Convert to job objects
            all_jobs = []
            for row in rows:
                try:
                    job = {
                        'job_title': row[0],
                        'job_text': row[1],
                        'required_skills': json.loads(row[2]) if row[2] else [],
                        'embedding': json.loads(row[3]) if row[3] else []
                    }
                    all_jobs.append(job)
                    print(f"  📋 Job: {job['job_title']} - Skills: {len(job['required_skills'])} - Embedding: {len(job['embedding'])}")
                except Exception as e:
                    print(f"  ❌ Error parsing job {row[0]}: {str(e)}")
                    continue
            
            # Calculate match scores for each job
            job_matches = []
            
            print(f"🔍 ATS Debug: Resume embedding length: {len(resume_embedding)}")
            print(f"🔍 ATS Debug: Processing {len(all_jobs)} jobs for matching")
            
            for i, job in enumerate(all_jobs):
                job_embedding = job.get('embedding', [])
                if not job_embedding:
                    print(f"  ⚠️  Job {i+1} {job['job_title']} - No embedding, skipping")
                    continue
                
                print(f"  🔍 Processing job {i+1}: {job['job_title']}")
                print(f"    Resume skills: {resume_data.get('nlp_analysis', {}).get('SKILL', [])[:5]}")
                print(f"    Job skills: {job['required_skills'][:5]}")
                
                # Calculate similarity score with enhanced semantic matching
                similarity = self._enhanced_semantic_similarity(
                    resume_embedding, 
                    job_embedding,
                    resume_data.get('full_text', ''),
                    job.get('job_text', '')
                )
                
                # Calculate skills match score
                skills_match = self._calculate_job_skills_match(resume_data, job)
                
                # Calculate experience match
                experience_match = self._calculate_job_experience_match(resume_data, job)
                
                print(f"    Similarity: {similarity:.3f}, Skills: {skills_match:.3f}, Experience: {experience_match:.3f}")
                
                # Calculate overall job match score with optimized weights
                job_match_score = (
                    similarity * 0.3 +      # 30% semantic similarity (reduced from 40%)
                    skills_match * 0.5 +     # 50% skills compatibility (increased from 40%)
                    experience_match * 0.2    # 20% experience level (unchanged)
                )
                
                print(f"    Overall score: {job_match_score:.3f}")
                
                job_match = {
                    'job': job,
                    'match_score': job_match_score,
                    'similarity_score': similarity,
                    'skills_match_score': skills_match,
                    'experience_match_score': experience_match,
                    'match_percentage': round(job_match_score * 100, 1),
                    'match_level': self._get_match_level(job_match_score)
                }
                
                job_matches.append(job_match)
            
            # Sort by match score and return top results
            job_matches.sort(key=lambda x: x['match_score'], reverse=True)
            
            # Filter out matches with very low scores (below 40% - increased from 30% for better quality)
            quality_matches = [match for match in job_matches if match['match_score'] >= 0.4]
            
            # Return all matches that meet quality threshold if no limit specified, otherwise return top matches
            if limit is None:
                top_matches = quality_matches
            else:
                top_matches = quality_matches[:limit]
            
            if not top_matches:
                logger.info("No job matches met the minimum quality threshold (40%)")
                return []
            
            # Console log the matching jobs
            logger.info(f"Found {len(top_matches)} matching jobs for resume")
            for i, match in enumerate(top_matches, 1):
                job = match['job']
                logger.info(f"  Match {i}: {job.get('job_title', 'Unknown')} - {match['match_percentage']}% ({match['match_level']})")
                logger.info(f"    Skills Match: {match['skills_match_score']:.2f}")
                logger.info(f"    Similarity: {match['similarity_score']:.2f}")
                logger.info(f"    Experience Match: {match['experience_match_score']:.2f}")
            
            return top_matches
            
        except Exception as e:
            logger.error(f"Error finding matching jobs: {str(e)}")
            return []
    
    def process_resume_with_ats(self, resume_data: Dict) -> Dict:
        """Complete ATS processing with job matching"""
        try:
            # Calculate ATS score
            ats_scores = self.calculate_ats_score(resume_data)
            
            # Find matching jobs - get all matching jobs without limit
            matching_jobs = self.find_matching_jobs(resume_data, limit=None)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(resume_data, ats_scores, matching_jobs)
            
            return {
                'ats_scores': ats_scores,
                'matching_jobs': matching_jobs,
                'recommendations': recommendations,
                'summary': {
                    'ats_score': ats_scores.get('overall_score', 0),
                    'ats_grade': ats_scores.get('ats_grade', 'F'),
                    'total_matching_jobs': len(matching_jobs),
                    'top_match_score': matching_jobs[0]['match_percentage'] if matching_jobs else 0,
                    'top_job_title': matching_jobs[0]['job']['job_title'] if matching_jobs else None
                }
            }
            
        except Exception as e:
            import traceback
            logger.error(f"Error in ATS processing: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                'error': str(e),
                'ats_scores': {'overall_score': 0, 'ats_grade': 'F'},
                'matching_jobs': [],
                'recommendations': []
            }
    
    def _calculate_format_score(self, resume_data: Dict) -> float:
        """Calculate resume format and structure score - more lenient"""
        try:
            text = resume_data.get('full_text', '')
            score = 0.0
            
            # Check for standard sections (30 points) - more flexible section detection
            sections = ['summary', 'experience', 'education', 'skills', 'work', 'project', 'qualification']
            found_sections = sum(1 for section in sections if section in text.lower())
            score += min((found_sections / 4) * 0.3, 0.3)  # Cap at 4 sections for full points
            
            # Check text length (20 points) - more flexible range
            word_count = len(text.split())
            if 200 <= word_count <= 2500:  # Expanded range
                score += 0.2
            elif 100 <= word_count < 200 or 2500 < word_count <= 3500:
                score += 0.15
            elif word_count >= 50:  # Give some credit for minimal content
                score += 0.1
            
            # Check for contact information (20 points) - more lenient
            contact_patterns = [
                r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
                r'\blinkedin\.com|github\.com|portfolio|website\b'  # Social profiles
            ]
            contact_found = sum(1 for pattern in contact_patterns if re.search(pattern, text, re.IGNORECASE))
            score += min((contact_found / 2) * 0.2, 0.2)  # Only need 2 out of 3 for full points
            
            # Check for bullet points and formatting (20 points) - more lenient
            bullet_indicators = ['•', '-', '*', '·', '▪', '▸', '▬', '→']
            bullet_count = sum(text.count(indicator) for indicator in bullet_indicators)
            if bullet_count >= 5:  # Reduced from 10
                score += 0.2
            elif bullet_count >= 2:  # Give partial credit
                score += 0.1
            
            # Check for professional language (10 points) - more lenient
            professional_words = ['developed', 'managed', 'implemented', 'created', 'led', 'coordinated', 'designed', 'built', 'worked']
            prof_word_count = sum(1 for word in professional_words if word in text.lower())
            if prof_word_count >= 3:  # Reduced from 5
                score += 0.1
            elif prof_word_count >= 1:  # Give partial credit
                score += 0.05
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating format score: {str(e)}")
            return 0.3  # Better fallback score
    
    def _calculate_skills_score(self, resume_data: Dict) -> float:
        """Calculate skills relevance score"""
        try:
            skills = resume_data.get('nlp_analysis', {}).get('SKILL', [])
            if not skills:
                return 0.0
            
            # Categorize skills
            technical_skills = [s for s in skills if self._is_technical_skill(s)]
            soft_skills = [s for s in skills if self._is_soft_skill(s)]
            
            # Score based on skill diversity and relevance
            score = 0.0
            
            # Technical skills (60% of skills score)
            if len(technical_skills) >= 8:
                score += 0.6
            elif len(technical_skills) >= 5:
                score += 0.4
            elif len(technical_skills) >= 3:
                score += 0.2
            
            # High-demand technical skills bonus
            high_demand_skills = ['python', 'java', 'javascript', 'aws', 'docker', 'kubernetes', 'react', 'node.js']
            high_demand_count = sum(1 for skill in technical_skills if skill.lower() in high_demand_skills)
            score += min(high_demand_count * 0.05, 0.2)
            
            # Soft skills (20% of skills score)
            if len(soft_skills) >= 5:
                score += 0.2
            elif len(soft_skills) >= 3:
                score += 0.1
            
            # Skill variety (20% of skills score)
            unique_skill_categories = len(set(self._get_skill_category(skill) for skill in technical_skills))
            if unique_skill_categories >= 4:
                score += 0.2
            elif unique_skill_categories >= 2:
                score += 0.1
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating skills score: {str(e)}")
            return 0.0
    
    def _calculate_experience_score(self, resume_data: Dict) -> float:
        """Calculate experience level score"""
        try:
            text = resume_data.get('full_text', '').lower()
            
            # Extract years of experience
            year_patterns = [
                r'(\d+)\+?\s*(?:years?|yrs?)',
                r'(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)',
                r'(?:experience|exp)\s*(?:of\s*)?(\d+)\s*(?:years?|yrs?)'
            ]
            
            max_years = 0
            for pattern in year_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    if isinstance(match, tuple):
                        years = max(int(match[0]), int(match[1]) if len(match) > 1 else 0)
                    else:
                        years = int(match)
                    max_years = max(max_years, years)
            
            # Score based on years of experience
            if max_years >= 10:
                return 1.0
            elif max_years >= 7:
                return 0.8
            elif max_years >= 5:
                return 0.6
            elif max_years >= 3:
                return 0.4
            elif max_years >= 1:
                return 0.2
            else:
                return 0.1
                
        except Exception as e:
            logger.error(f"Error calculating experience score: {str(e)}")
            return 0.0
    
    def _calculate_education_score(self, resume_data: Dict) -> float:
        """Calculate education level score"""
        try:
            text = resume_data.get('full_text', '').lower()
            
            # Education level indicators
            education_keywords = {
                'phd': 1.0,
                'doctorate': 1.0,
                'master': 0.8,
                'mba': 0.8,
                'bachelor': 0.6,
                'degree': 0.5,
                'associate': 0.3,
                'certificate': 0.2
            }
            
            max_score = 0.0
            for keyword, score in education_keywords.items():
                if keyword in text:
                    max_score = max(max_score, score)
            
            return max_score
            
        except Exception as e:
            logger.error(f"Error calculating education score: {str(e)}")
            return 0.0
    
    def _calculate_keyword_score(self, resume_data: Dict) -> float:
        """Calculate keyword density and relevance score - more lenient"""
        try:
            keywords = resume_data.get('nlp_analysis', {}).get('KEYWORDS', [])
            text = resume_data.get('full_text', '')
            
            if not keywords or not text:
                # If no keywords found, still give some credit for having content
                return 0.3 if len(text.split()) > 100 else 0.1
            
            # Calculate keyword density
            total_words = len(text.split())
            keyword_count = sum(1 for keyword in keywords if keyword.lower() in text.lower())
            
            density = keyword_count / total_words if total_words > 0 else 0
            
            # More lenient scoring - expanded optimal ranges
            if 0.01 <= density <= 0.08:  # Expanded from 2-5% to 1-8%
                return 1.0
            elif 0.005 <= density < 0.01 or 0.08 < density <= 0.12:  # Expanded ranges
                return 0.8
            elif density < 0.005 or density > 0.12:
                return 0.6  # Better minimum score
            else:
                return 0.7  # Default decent score
                
        except Exception as e:
            logger.error(f"Error calculating keyword score: {str(e)}")
            return 0.3  # Better fallback score
    
    def _calculate_job_skills_match(self, resume_data: Dict, job: Dict) -> float:
        """Calculate skills compatibility between resume and job"""
        try:
            resume_skills = set(resume_data.get('nlp_analysis', {}).get('SKILL', []))
            job_skills = set(job.get('required_skills', []))
            
            if not job_skills:
                return 0.0
            
            # Enhanced skill matching with synonyms and variations
            skill_synonyms = {
                # Programming languages
                'js': 'javascript', 'typescript': 'javascript', 'ts': 'typescript',
                'py': 'python', 'python3': 'python',
                'c++': 'cpp', 'c#': 'csharp', '.net': 'csharp',
                # Web technologies
                'html5': 'html', 'css3': 'css', 'sass': 'css', 'scss': 'css',
                'reactjs': 'react', 'react.js': 'react', 'nextjs': 'react',
                'vuejs': 'vue', 'vue.js': 'vue', 'angularjs': 'angular',
                'nodejs': 'node', 'node.js': 'node', 'expressjs': 'express',
                # Databases
                'postgres': 'postgresql', 'postgre': 'postgresql', 'mysql': 'mysql',
                'mongo': 'mongodb', 'nosql': 'mongodb',
                # Cloud & DevOps
                'aws': 'amazon web services', 'azure': 'microsoft azure', 'gcp': 'google cloud',
                'k8s': 'kubernetes', 'docker': 'docker', 'jenkins': 'jenkins',
                'ci/cd': 'cicd', 'devops': 'devops',
                # Tools & frameworks
                'git': 'git', 'github': 'git', 'gitlab': 'git',
                'linux': 'linux', 'ubuntu': 'linux', 'unix': 'linux',
                'api': 'api', 'rest': 'api', 'graphql': 'api', 'soap': 'api'
            }
            
            # Normalize skills by applying synonyms
            normalized_resume_skills = set()
            for skill in resume_skills:
                skill_lower = skill.lower().strip()
                normalized = skill_synonyms.get(skill_lower, skill_lower)
                normalized_resume_skills.add(normalized)
            
            normalized_job_skills = set()
            for skill in job_skills:
                skill_lower = skill.lower().strip()
                normalized = skill_synonyms.get(skill_lower, skill_lower)
                normalized_job_skills.add(normalized)
            
            # Calculate exact matches
            exact_matches = normalized_resume_skills & normalized_job_skills
            
            # Calculate partial matches (skills that contain each other)
            partial_matches = set()
            for resume_skill in normalized_resume_skills:
                for job_skill in normalized_job_skills:
                    if (resume_skill in job_skill or job_skill in resume_skill) and len(resume_skill) > 2:
                        partial_matches.add(resume_skill)
            
            # Combine matches
            all_matches = exact_matches | partial_matches
            
            # Calculate base match ratio
            match_ratio = len(all_matches) / len(normalized_job_skills)
            
            # Enhanced scoring with skill importance weighting
            critical_skills = {
                'python', 'java', 'javascript', 'react', 'node', 'sql', 'aws', 
                'docker', 'kubernetes', 'git', 'linux', 'api', 'devops'
            }
            
            # Calculate weighted score
            weighted_score = 0.0
            for job_skill in normalized_job_skills:
                if job_skill in exact_matches:
                    # Critical skills get higher weight
                    if job_skill in critical_skills:
                        weighted_score += 1.2  # 20% bonus for critical skills
                    else:
                        weighted_score += 1.0
                elif job_skill in partial_matches:
                    weighted_score += 0.7  # Partial matches get 70% credit
            
            # Normalize by total job skills and add critical skills bonus
            final_score = min(weighted_score / len(normalized_job_skills), 1.0)
            
            # Add bonus for skill diversity
            skill_categories = self._count_skill_categories(normalized_resume_skills)
            diversity_bonus = min(skill_categories / 5, 0.1)  # Max 10% bonus for diversity
            
            return min(final_score + diversity_bonus, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating job skills match: {str(e)}")
            return 0.0
    
    def _calculate_job_experience_match(self, resume_data: Dict, job: Dict) -> float:
        """Calculate experience level compatibility with enhanced parsing"""
        try:
            job_text = job.get('job_text', '').lower()
            job_title = job.get('job_title', '').lower()
            resume_text = resume_data.get('full_text', '').lower()
            
            # Extract experience requirements from job
            job_experience_req = self._extract_job_experience_requirements(job_text, job_title)
            
            # Extract candidate's experience from resume
            candidate_experience = self._extract_candidate_experience(resume_text)
            
            # Calculate match based on multiple factors
            if not job_experience_req:
                return 0.8  # Default score if no clear requirements
            
            # Years of experience matching
            years_match = self._calculate_years_experience_match(candidate_experience['total_years'], job_experience_req['required_years'])
            
            # Seniority level matching
            seniority_match = self._calculate_seniority_match(candidate_experience['seniority_level'], job_experience_req['seniority_level'])
            
            # Domain experience matching
            domain_match = self._calculate_domain_experience_match(candidate_experience['domains'], job_experience_req['required_domains'])
            
            # Leadership experience matching
            leadership_match = self._calculate_leadership_match(candidate_experience['leadership_indicators'], job_experience_req['leadership_required'])
            
            # Weighted combination
            final_score = (
                years_match * 0.4 +      # 40% weight for years of experience
                seniority_match * 0.3 +  # 30% weight for seniority level
                domain_match * 0.2 +     # 20% weight for domain experience
                leadership_match * 0.1    # 10% weight for leadership
            )
            
            return min(final_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating job experience match: {str(e)}")
            return 0.5
    
    def _enhanced_semantic_similarity(self, resume_embedding: List[float], job_embedding: List[float], 
                                     resume_text: str, job_text: str) -> float:
        """Enhanced semantic similarity combining embeddings with keyword matching"""
        try:
            # Base cosine similarity
            base_similarity = self._cosine_similarity(resume_embedding, job_embedding)
            
            # Keyword-based similarity boost
            keyword_boost = self._calculate_keyword_similarity_boost(resume_text, job_text)
            
            # Title-based similarity boost
            title_boost = self._calculate_title_similarity_boost(resume_text, job_text)
            
            # Industry/Domain matching boost
            domain_boost = self._calculate_domain_similarity_boost(resume_text, job_text)
            
            # Combine all similarity measures with weights
            enhanced_similarity = (
                base_similarity * 0.6 +      # 60% weight for embedding similarity
                keyword_boost * 0.2 +        # 20% weight for keyword matching
                title_boost * 0.1 +          # 10% weight for title matching
                domain_boost * 0.1            # 10% weight for domain matching
            )
            
            return min(enhanced_similarity, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating enhanced semantic similarity: {str(e)}")
            return self._cosine_similarity(resume_embedding, job_embedding)
    
    def _calculate_keyword_similarity_boost(self, resume_text: str, job_text: str) -> float:
        """Calculate keyword-based similarity boost"""
        try:
            # Extract important keywords from both texts
            resume_keywords = set(self._extract_important_keywords(resume_text))
            job_keywords = set(self._extract_important_keywords(job_text))
            
            if not job_keywords:
                return 0.0
            
            # Calculate Jaccard similarity
            intersection = resume_keywords & job_keywords
            union = resume_keywords | job_keywords
            
            if not union:
                return 0.0
            
            jaccard_similarity = len(intersection) / len(union)
            
            # Bonus for matching critical keywords
            critical_keywords = {'senior', 'lead', 'manager', 'architect', 'principal', 'director'}
            critical_matches = len(intersection & critical_keywords)
            critical_bonus = min(critical_matches * 0.1, 0.2)
            
            return min(jaccard_similarity + critical_bonus, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating keyword similarity boost: {str(e)}")
            return 0.0
    
    def _calculate_title_similarity_boost(self, resume_text: str, job_text: str) -> float:
        """Calculate title-based similarity boost"""
        try:
            # Extract job titles from resume
            resume_titles = self._extract_job_titles(resume_text)
            job_title = self._extract_job_title_from_text(job_text)
            
            if not job_title or not resume_titles:
                return 0.0
            
            # Find best matching title
            best_match = 0.0
            for resume_title in resume_titles:
                similarity = self._string_similarity(resume_title.lower(), job_title.lower())
                best_match = max(best_match, similarity)
            
            return best_match
            
        except Exception as e:
            logger.error(f"Error calculating title similarity boost: {str(e)}")
            return 0.0
    
    def _calculate_domain_similarity_boost(self, resume_text: str, job_text: str) -> float:
        """Calculate domain/industry similarity boost"""
        try:
            # Define domain keywords
            domains = {
                'software': ['software', 'application', 'system', 'platform'],
                'web': ['web', 'website', 'frontend', 'backend', 'fullstack'],
                'mobile': ['mobile', 'ios', 'android', 'app'],
                'data': ['data', 'analytics', 'database', 'big data'],
                'cloud': ['cloud', 'aws', 'azure', 'gcp', 'saas'],
                'devops': ['devops', 'deployment', 'infrastructure', 'ci/cd'],
                'security': ['security', 'cybersecurity', 'authentication'],
                'ai_ml': ['machine learning', 'ai', 'artificial intelligence', 'ml', 'deep learning']
            }
            
            resume_domains = set()
            job_domains = set()
            
            for domain, keywords in domains.items():
                if any(keyword in resume_text.lower() for keyword in keywords):
                    resume_domains.add(domain)
                if any(keyword in job_text.lower() for keyword in keywords):
                    job_domains.add(domain)
            
            if not job_domains:
                return 0.0
            
            # Calculate domain overlap
            overlap = len(resume_domains & job_domains)
            return overlap / len(job_domains)
            
        except Exception as e:
            logger.error(f"Error calculating domain similarity boost: {str(e)}")
            return 0.0
    
    def _extract_important_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        try:
            # Common technical and business keywords
            important_keywords = {
                'python', 'java', 'javascript', 'react', 'node', 'sql', 'aws', 'docker',
                'kubernetes', 'git', 'linux', 'api', 'devops', 'microservices', 'cloud',
                'machine learning', 'ai', 'data science', 'analytics', 'big data',
                'frontend', 'backend', 'fullstack', 'mobile', 'web', 'software',
                'senior', 'lead', 'manager', 'architect', 'principal', 'director',
                'agile', 'scrum', 'cicd', 'testing', 'security', 'performance'
            }
            
            found_keywords = []
            text_lower = text.lower()
            
            for keyword in important_keywords:
                if keyword in text_lower:
                    found_keywords.append(keyword)
            
            return found_keywords
            
        except Exception as e:
            logger.error(f"Error extracting important keywords: {str(e)}")
            return []
    
    def _extract_job_titles(self, resume_text: str) -> List[str]:
        """Extract job titles from resume text"""
        try:
            # Common job title patterns
            title_patterns = [
                r'(?:senior|lead|principal|staff|junior|associate)\s+(?:software|web|mobile|data|cloud)\s+(?:engineer|developer|architect)',
                r'(?:software|web|mobile|data|cloud)\s+(?:engineer|developer|architect)',
                r'(?:senior|lead|principal)\s+(?:engineer|developer|architect)',
                r'(?:manager|director|head)\s+(?:of\s+)?(?:engineering|technology|development)',
                r'(?:cto|vp\s+of\s+engineering|chief\s+technology\s+officer)'
            ]
            
            titles = []
            for pattern in title_patterns:
                matches = re.findall(pattern, resume_text, re.IGNORECASE)
                titles.extend(matches)
            
            return list(set(titles))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error extracting job titles: {str(e)}")
            return []
    
    def _extract_job_title_from_text(self, job_text: str) -> str:
        """Extract the main job title from job posting text"""
        try:
            lines = job_text.split('\n')
            for line in lines[:5]:  # Check first 5 lines
                line = line.strip()
                if len(line) < 100 and any(word in line.lower() for word in ['engineer', 'developer', 'architect', 'manager', 'director']):
                    return line
            
            return ''
            
        except Exception as e:
            logger.error(f"Error extracting job title from text: {str(e)}")
            return ''
    
    def _string_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using simple character matching"""
        try:
            if not str1 or not str2:
                return 0.0
            
            # Simple character-based similarity
            common_chars = set(str1) & set(str2)
            total_chars = set(str1) | set(str2)
            
            if not total_chars:
                return 0.0
            
            return len(common_chars) / len(total_chars)
            
        except Exception as e:
            logger.error(f"Error calculating string similarity: {str(e)}")
            return 0.0
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
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
            logger.error(f"Error calculating cosine similarity: {str(e)}")
            return 0.0
    
    def _get_ats_grade(self, score: float) -> str:
        """Convert ATS score to grade"""
        if score >= 0.9:
            return 'A+'
        elif score >= 0.8:
            return 'A'
        elif score >= 0.7:
            return 'B+'
        elif score >= 0.6:
            return 'B'
        elif score >= 0.5:
            return 'C+'
        elif score >= 0.4:
            return 'C'
        elif score >= 0.3:
            return 'D'
        else:
            return 'F'
    
    def _get_match_level(self, score: float) -> str:
        """Convert match score to level"""
        if score >= 0.8:
            return 'Excellent Match'
        elif score >= 0.6:
            return 'Good Match'
        elif score >= 0.4:
            return 'Moderate Match'
        else:
            return 'Poor Match'
    
    def _generate_recommendations(self, resume_data: Dict, ats_scores: Dict, matching_jobs: List[Dict]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # Format recommendations
        if ats_scores.get('format_score', 0) < 0.7:
            recommendations.append("Improve resume format: Add clear sections (Summary, Experience, Education, Skills)")
        
        # Skills recommendations
        if ats_scores.get('skills_score', 0) < 0.6:
            recommendations.append("Add more technical skills relevant to your target roles")
        
        # Experience recommendations
        if ats_scores.get('experience_score', 0) < 0.4:
            recommendations.append("Quantify your experience with specific achievements and metrics")
        
        # Education recommendations
        if ats_scores.get('education_score', 0) < 0.5:
            recommendations.append("Highlight your education and any relevant certifications")
        
        # Keyword recommendations
        if ats_scores.get('keyword_score', 0) < 0.6:
            recommendations.append("Optimize keyword density with industry-specific terms")
        
        # Job matching recommendations
        if not matching_jobs:
            recommendations.append("Consider expanding your skill set to match more job opportunities")
        elif matching_jobs[0]['match_score'] < 0.6:
            recommendations.append("Focus on skills mentioned in top matching job descriptions")
        
        return recommendations
    
    def _is_technical_skill(self, skill: str) -> bool:
        """Check if skill is technical"""
        technical_keywords = [
            'python', 'java', 'javascript', 'react', 'node', 'sql', 'aws',
            'docker', 'kubernetes', 'git', 'linux', 'html', 'css', 'angular',
            'vue', 'mongodb', 'postgresql', 'mysql', 'redis', 'api', 'devops'
        ]
        return any(keyword in skill.lower() for keyword in technical_keywords)
    
    def _is_soft_skill(self, skill: str) -> bool:
        """Check if skill is soft skill"""
        soft_keywords = [
            'leadership', 'communication', 'teamwork', 'problem solving',
            'project management', 'analytical', 'creative', 'detail oriented'
        ]
        return any(keyword in skill.lower() for keyword in soft_keywords)
    
    def _get_skill_category(self, skill: str) -> str:
        """Get skill category"""
        categories = {
            'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'go', 'rust'],
            'web': ['html', 'css', 'react', 'angular', 'vue', 'node', 'express'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes'],
            'tools': ['git', 'jenkins', 'terraform', 'ansible']
        }
        
        skill_lower = skill.lower()
        for category, skills in categories.items():
            if any(s in skill_lower for s in skills):
                return category
        
        return 'other'
    
    def _count_skill_categories(self, skills: set) -> int:
        """Count the number of different skill categories represented"""
        categories = {
            'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'go', 'rust', 'cpp', 'csharp', 'typescript'],
            'web': ['html', 'css', 'react', 'angular', 'vue', 'node', 'express', 'sass', 'scss'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'nosql', 'postgres'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'amazon web services', 'google cloud', 'microsoft azure'],
            'tools': ['git', 'jenkins', 'terraform', 'ansible', 'github', 'gitlab'],
            'devops': ['devops', 'cicd', 'ci/cd', 'k8s'],
            'mobile': ['ios', 'android', 'swift', 'kotlin', 'react native', 'flutter'],
            'data': ['machine learning', 'data science', 'analytics', 'tensorflow', 'pytorch', 'pandas', 'numpy']
        }
        
        found_categories = set()
        for skill in skills:
            skill_lower = skill.lower()
            for category, category_skills in categories.items():
                if any(cat_skill in skill_lower or skill_lower in cat_skill for cat_skill in category_skills):
                    found_categories.add(category)
                    break
        
        return len(found_categories)
    
    def _extract_job_experience_requirements(self, job_text: str, job_title: str) -> Dict:
        """Extract experience requirements from job posting"""
        requirements = {
            'required_years': 0,
            'seniority_level': '',
            'required_domains': [],
            'leadership_required': False
        }
        
        # Extract years requirements
        year_patterns = [
            r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)?',
            r'(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)?',
            r'minimum\s*(?:of\s*)?(\d+)\s*(?:years?|yrs?)',
            r'at\s*least\s*(\d+)\s*(?:years?|yrs?)'
        ]
        
        for pattern in year_patterns:
            matches = re.findall(pattern, job_text)
            for match in matches:
                if isinstance(match, tuple):
                    years = max(int(match[0]), int(match[1]) if len(match) > 1 else 0)
                else:
                    years = int(match)
                requirements['required_years'] = max(requirements['required_years'], years)
        
        # Extract seniority level from title and text
        seniority_keywords = {
            'intern': 'intern',
            'entry': 'entry',
            'junior': 'junior',
            'associate': 'associate',
            'mid': 'mid',
            'intermediate': 'intermediate',
            'senior': 'senior',
            'lead': 'lead',
            'principal': 'principal',
            'staff': 'staff',
            'manager': 'manager',
            'director': 'director',
            'head': 'head',
            'vp': 'vp',
            'chief': 'chief',
            'cto': 'cto',
            'ceo': 'ceo'
        }
        
        for keyword, level in seniority_keywords.items():
            if keyword in job_title or keyword in job_text:
                requirements['seniority_level'] = level
                break
        
        # Extract required domains/technologies
        domain_keywords = ['software', 'web', 'mobile', 'data', 'cloud', 'devops', 'security', 'ai', 'ml']
        for domain in domain_keywords:
            if domain in job_text:
                requirements['required_domains'].append(domain)
        
        # Check for leadership requirements
        leadership_indicators = ['manage', 'lead', 'mentor', 'supervise', 'team lead', 'project lead', 'architect']
        if any(indicator in job_text for indicator in leadership_indicators):
            requirements['leadership_required'] = True
        
        return requirements
    
    def _extract_candidate_experience(self, resume_text: str) -> Dict:
        """Extract candidate experience information from resume"""
        experience = {
            'total_years': 0,
            'seniority_level': '',
            'domains': [],
            'leadership_indicators': []
        }
        
        # Extract years of experience
        year_patterns = [
            r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)?',
            r'(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)?',
            r'experience\s*(?:of\s*)?(\d+)\s*(?:years?|yrs?)'
        ]
        
        max_years = 0
        for pattern in year_patterns:
            matches = re.findall(pattern, resume_text)
            for match in matches:
                if isinstance(match, tuple):
                    years = max(int(match[0]), int(match[1]) if len(match) > 1 else 0)
                else:
                    years = int(match)
                max_years = max(max_years, years)
        
        experience['total_years'] = max_years
        
        # Extract seniority indicators
        seniority_indicators = {
            'intern': 'intern',
            'junior': 'junior',
            'associate': 'associate',
            'mid': 'mid',
            'senior': 'senior',
            'lead': 'lead',
            'principal': 'principal',
            'staff': 'staff',
            'manager': 'manager',
            'director': 'director',
            'head': 'head',
            'architect': 'architect'
        }
        
        for indicator, level in seniority_indicators.items():
            if indicator in resume_text:
                experience['seniority_level'] = level
                break
        
        # Extract domain experience
        domain_keywords = ['software', 'web', 'mobile', 'data', 'cloud', 'devops', 'security', 'ai', 'ml']
        for domain in domain_keywords:
            if domain in resume_text:
                experience['domains'].append(domain)
        
        # Extract leadership indicators
        leadership_keywords = ['managed', 'led', 'mentored', 'supervised', 'team lead', 'project lead', 'architect', 'senior']
        for keyword in leadership_keywords:
            if keyword in resume_text:
                experience['leadership_indicators'].append(keyword)
        
        return experience
    
    def _calculate_years_experience_match(self, candidate_years: int, required_years: int) -> float:
        """Calculate years of experience match"""
        if required_years == 0:
            return 1.0
        
        if candidate_years >= required_years:
            # Over-qualification is good, but diminishing returns
            excess_ratio = (candidate_years - required_years) / required_years
            return min(1.0, 0.8 + 0.2 * (1 - min(excess_ratio, 2.0) / 2.0))
        else:
            # Under-qualification penalty
            return max(0.0, candidate_years / required_years)
    
    def _calculate_seniority_match(self, candidate_level: str, required_level: str) -> float:
        """Calculate seniority level match"""
        if not required_level:
            return 1.0
        
        seniority_hierarchy = {
            'intern': 0,
            'entry': 1,
            'junior': 2,
            'associate': 3,
            'mid': 4,
            'intermediate': 4,
            'senior': 5,
            'lead': 6,
            'principal': 7,
            'staff': 7,
            'manager': 8,
            'director': 9,
            'head': 9,
            'architect': 6,
            'vp': 10,
            'chief': 11,
            'cto': 11,
            'ceo': 12
        }
        
        candidate_rank = seniority_hierarchy.get(candidate_level, 4)
        required_rank = seniority_hierarchy.get(required_level, 4)
        
        if candidate_rank >= required_rank:
            return 1.0
        else:
            return max(0.0, candidate_rank / required_rank)
    
    def _calculate_domain_experience_match(self, candidate_domains: List[str], required_domains: List[str]) -> float:
        """Calculate domain experience match"""
        if not required_domains:
            return 1.0
        
        candidate_domain_set = set(candidate_domains)
        required_domain_set = set(required_domains)
        
        if not candidate_domain_set:
            return 0.3  # Penalty for no domain information
        
        match_ratio = len(candidate_domain_set & required_domain_set) / len(required_domain_set)
        return min(match_ratio + 0.2, 1.0)  # Small bonus for having any domain info
    
    def _calculate_leadership_match(self, candidate_leadership: List[str], leadership_required: bool) -> float:
        """Calculate leadership experience match"""
        if not leadership_required:
            return 1.0
        
        if not candidate_leadership:
            return 0.2  # Significant penalty if leadership required but none shown
        
        # Bonus for multiple leadership indicators
        leadership_strength = min(len(candidate_leadership) / 3, 1.0)
        return 0.6 + 0.4 * leadership_strength
