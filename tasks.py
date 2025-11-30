from celery import Celery
from celery_config.celery_app import celery_app
import math
from database.database_service import DatabaseService
from nlp.embedding_service import EmbeddingService
from nlp.nlp_service import NLPService
from ats.ats_service import ATSService
from pdf.pdf_service import PDFService
from job.job_service import JobService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
db_service = DatabaseService()
embedding_service = EmbeddingService()
nlp_service = NLPService()

@celery_app.task(bind=True)
def process_resume_background(self, resume_id):
    """Background task to process resume with advanced scoring"""
    try:
        # Update task status
        self.update_state(state='PROCESSING', meta={'status': 'Starting resume processing...'})
        
        # Get resume from database
        resume = db_service.get_resume(resume_id)
        if not resume:
            raise Exception(f"Resume with ID {resume_id} not found")
        
        self.update_state(state='PROCESSING', meta={'status': 'Analyzing resume content...'})
        
        # Perform advanced analysis
        analysis_result = analyze_resume_comprehensive(resume)
        
        # Update resume with analysis results
        update_resume_analysis(resume_id, analysis_result)
        
        logger.info(f"Successfully processed resume {resume_id}")
        return {
            'status': 'completed',
            'resume_id': resume_id,
            'analysis': analysis_result
        }
        
    except Exception as e:
        logger.error(f"Error processing resume {resume_id}: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'resume_id': resume_id}
        )
        raise

@celery_app.task
def batch_score_resumes(job_description_embedding, resume_ids=None):
    """Batch score resumes against job description"""
    try:
        logger.info(f"Starting batch scoring for {len(resume_ids) if resume_ids else 'all'} resumes")
        
        # Get resumes to score
        if resume_ids:
            resumes = [db_service.get_resume(rid) for rid in resume_ids]
            resumes = [r for r in resumes if r is not None]
        else:
            resumes = db_service.get_all_resumes()
        
        results = []
        
        for resume in resumes:
            try:
                # Calculate similarity score
                resume_embedding = resume.get('embedding', [])
                if not resume_embedding:
                    continue
                
                similarity_score = calculate_cosine_similarity(
                    job_description_embedding, 
                    resume_embedding
                )
                
                # Calculate skill match score
                skill_score = calculate_skill_match_score(resume)
                
                # Calculate experience score
                experience_score = calculate_experience_score(resume)
                
                # Calculate overall score
                overall_score = calculate_overall_score(
                    similarity_score, 
                    skill_score, 
                    experience_score
                )
                
                result = {
                    'resume_id': resume['id'],
                    'filename': resume['filename'],
                    'similarity_score': similarity_score,
                    'skill_score': skill_score,
                    'experience_score': experience_score,
                    'overall_score': overall_score,
                    'matched_skills': resume.get('skills', [])[:10]  # Top 10 skills
                }
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error scoring resume {resume.get('id')}: {str(e)}")
                continue
        
        # Sort by overall score
        results.sort(key=lambda x: x['overall_score'], reverse=True)
        
        logger.info(f"Batch scoring completed for {len(results)} resumes")
        return {
            'status': 'completed',
            'total_resumes': len(resumes),
            'scored_resumes': len(results),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error in batch scoring: {str(e)}")
        raise

@celery_app.task
def calculate_resume_ranking(resume_ids, criteria_weights=None):
    """Calculate ranking for resumes based on custom criteria"""
    try:
        if not criteria_weights:
            criteria_weights = {
                'similarity': 0.4,
                'skills': 0.3,
                'experience': 0.2,
                'education': 0.1
            }
        
        rankings = []
        
        for resume_id in resume_ids:
            resume = db_service.get_resume(resume_id)
            if not resume:
                continue
            
            # Calculate individual scores
            scores = {
                'similarity': calculate_similarity_score(resume),
                'skills': calculate_skill_score(resume),
                'experience': calculate_experience_score(resume),
                'education': calculate_education_score(resume)
            }
            
            # Calculate weighted score
            weighted_score = sum(
                scores[criterion] * weight 
                for criterion, weight in criteria_weights.items()
            )
            
            ranking = {
                'resume_id': resume_id,
                'filename': resume['filename'],
                'scores': scores,
                'weighted_score': weighted_score,
                'rank': 0  # Will be assigned after sorting
            }
            rankings.append(ranking)
        
        # Sort and assign ranks
        rankings.sort(key=lambda x: x['weighted_score'], reverse=True)
        for i, ranking in enumerate(rankings, 1):
            ranking['rank'] = i
        
        return {
            'status': 'completed',
            'total_resumes': len(rankings),
            'rankings': rankings,
            'criteria_weights': criteria_weights
        }
        
    except Exception as e:
        logger.error(f"Error in resume ranking: {str(e)}")
        raise

def analyze_resume_comprehensive(resume):
    """Comprehensive resume analysis"""
    try:
        text = resume.get('full_text', '')
        skills = resume.get('skills', [])
        
        analysis = {}
        
        # Skill analysis
        analysis['skill_analysis'] = {
            'total_skills': len(skills),
            'technical_skills': [s for s in skills if is_technical_skill(s)],
            'soft_skills': [s for s in skills if is_soft_skill(s)],
            'skill_density': len(skills) / len(text.split()) if text else 0
        }
        
        # Experience analysis
        analysis['experience_analysis'] = extract_experience_analysis(text)
        
        # Education analysis
        analysis['education_analysis'] = extract_education_analysis(text)
        
        # Quality metrics
        analysis['quality_metrics'] = {
            'text_length': len(text),
            'readability_score': calculate_readability_score(text),
            'completeness_score': calculate_completeness_score(resume),
            'structure_score': calculate_structure_score(text)
        }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error in comprehensive analysis: {str(e)}")
        return {'error': str(e)}

def update_resume_analysis(resume_id, analysis):
    """Update resume with analysis results"""
    try:
        # This would update the database with analysis results
        # For now, we'll just log it
        logger.info(f"Updated analysis for resume {resume_id}: {analysis}")
        
    except Exception as e:
        logger.error(f"Error updating resume analysis: {str(e)}")

# Helper functions
def calculate_cosine_similarity(vec1, vec2):
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
        
        return float(dot_product / (mag1 * mag2))
        
    except Exception as e:
        logger.error(f"Error calculating cosine similarity: {str(e)}")
        return 0.0

def calculate_skill_match_score(resume):
    """Calculate skill match score"""
    skills = resume.get('skills', [])
    if not skills:
        return 0.0
    
    # Score based on skill diversity and relevance
    technical_skills = [s for s in skills if is_technical_skill(s)]
    base_score = len(technical_skills) / max(len(skills), 1)
    
    # Bonus for high-demand skills
    high_demand_skills = ['python', 'java', 'javascript', 'aws', 'docker', 'kubernetes']
    bonus = sum(0.1 for skill in technical_skills if skill.lower() in high_demand_skills)
    
    return min(base_score + bonus, 1.0)

def calculate_experience_score(resume):
    """Calculate experience score based on text analysis"""
    text = resume.get('full_text', '').lower()
    
    # Look for years of experience
    import re
    year_patterns = [
        r'(\d+)\+?\s*years?',
        r'(\d+)\s*-\s*(\d+)\s*years?',
        r'experience\s*(?:of\s*)?(\d+)\s*years?'
    ]
    
    total_years = 0
    for pattern in year_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                years = max(int(match[0]), int(match[1]) if len(match) > 1 else 0)
            else:
                years = int(match)
            total_years = max(total_years, years)
    
    # Score based on years (0-1 scale, max at 10+ years)
    return min(total_years / 10.0, 1.0)

def calculate_overall_score(similarity, skill, experience):
    """Calculate overall weighted score"""
    weights = {'similarity': 0.4, 'skill': 0.3, 'experience': 0.3}
    return (
        similarity * weights['similarity'] +
        skill * weights['skill'] +
        experience * weights['experience']
    )

def is_technical_skill(skill):
    """Check if skill is technical"""
    technical_keywords = [
        'python', 'java', 'javascript', 'react', 'node', 'sql', 'aws',
        'docker', 'kubernetes', 'git', 'linux', 'html', 'css', 'angular',
        'vue', 'mongodb', 'postgresql', 'mysql', 'redis', 'api', 'devops'
    ]
    return any(keyword in skill.lower() for keyword in technical_keywords)

def is_soft_skill(skill):
    """Check if skill is soft skill"""
    soft_keywords = [
        'leadership', 'communication', 'teamwork', 'problem solving',
        'project management', 'analytical', 'creative', 'detail oriented'
    ]
    return any(keyword in skill.lower() for keyword in soft_keywords)

def extract_experience_analysis(text):
    """Extract experience-related information"""
    return {
        'has_experience': 'experience' in text.lower(),
        'years_mentioned': len([i for i, word in enumerate(text.lower().split()) if 'year' in word]),
        'job_titles': extract_job_titles(text)
    }

def extract_education_analysis(text):
    """Extract education-related information"""
    education_keywords = ['bachelor', 'master', 'phd', 'degree', 'university', 'college']
    education_found = [keyword for keyword in education_keywords if keyword in text.lower()]
    
    return {
        'education_mentioned': len(education_found) > 0,
        'education_keywords': education_found,
        'education_score': min(len(education_found) / 3.0, 1.0)
    }

def extract_job_titles(text):
    """Extract potential job titles from text"""
    # Simple implementation - could be enhanced with NLP
    job_titles = ['engineer', 'developer', 'manager', 'analyst', 'designer']
    found_titles = [title for title in job_titles if title in text.lower()]
    return found_titles

def calculate_readability_score(text):
    """Simple readability score calculation"""
    if not text:
        return 0.0
    
    words = text.split()
    sentences = text.split('.')
    
    if not sentences:
        return 0.0
    
    avg_sentence_length = len(words) / len(sentences)
    # Simple scoring: prefer moderate sentence length (10-20 words)
    if 10 <= avg_sentence_length <= 20:
        return 1.0
    elif avg_sentence_length < 10:
        return 0.7
    else:
        return max(0.3, 1.0 - (avg_sentence_length - 20) / 30)

def calculate_completeness_score(resume):
    """Calculate resume completeness score"""
    required_elements = ['skills', 'full_text']
    present_elements = sum(1 for element in required_elements if resume.get(element))
    
    return present_elements / len(required_elements)

def calculate_structure_score(text):
    """Calculate text structure score"""
    # Check for structured elements
    structure_indicators = ['summary', 'experience', 'education', 'skills']
    found_indicators = sum(1 for indicator in structure_indicators if indicator in text.lower())
    
    return found_indicators / len(structure_indicators)

# Additional scoring functions for ranking
def calculate_similarity_score(resume):
    """Calculate similarity score (placeholder)"""
    return 0.8  # Would be calculated based on job description

def calculate_skill_score(resume):
    """Calculate skill score"""
    return calculate_skill_match_score(resume)

def calculate_education_score(resume):
    """Calculate education score"""
    text = resume.get('full_text', '')
    education_analysis = extract_education_analysis(text)
    return education_analysis['education_score']
