from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from pdf.pdf_service import PDFService
from database.database_service import DatabaseService
from tasks import process_resume_background, batch_score_resumes, calculate_resume_ranking
from job.job_service import JobService
from ats.ats_service import ATSService
from nlp.nlp_service import NLPService
from nlp.embedding_service import EmbeddingService

app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize database and all tables on startup
print("Initializing database and creating tables...")
db_service = DatabaseService()
print("✓ Resume database initialized")

# Initialize job service and load sample jobs
job_service = JobService()
print("✓ Job database initialized")

# Initialize other services
ats_service = ATSService(db_service=db_service)
pdf_service = PDFService()
embedding_service = EmbeddingService()
nlp_service = NLPService()

# Load sample jobs if database is empty
try:
    # Check jobs using DatabaseService instead of JobService
    conn = db_service.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM job_descriptions")
    job_count = cursor.fetchone()[0]
    conn.close()
    
    if job_count == 0:
        print("Loading sample jobs...")
        # Use the same loading logic as load_jobs.py
        import csv
        jobs_loaded = 0
        with open('sample_jobs.csv', 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            
            # Create default user if needed
            try:
                user_id = db_service.create_user("Default User", "default@example.com")
            except:
                users = db_service.get_all_users()
                user_id = users[0]['id'] if users else 1
            
            for row in csv_reader:
                try:
                    # Parse requirements - they're comma-separated in CSV
                    requirements = row.get('requirements', '')
                    if requirements:
                        # Split by comma and clean up each skill
                        required_skills = [skill.strip() for skill in requirements.split(',')]
                        # Remove empty strings and duplicates
                        required_skills = [skill for skill in required_skills if skill and skill.strip()]
                        # Limit to reasonable number
                        required_skills = required_skills[:10]
                    else:
                        required_skills = []
                    
                    # Create job description text
                    job_text = f"{row.get('title', '')} - {row.get('company', '')}\n"
                    job_text += f"Location: {row.get('location', '')}\n"
                    job_text += f"Description: {row.get('description', '')}\n"
                    job_text += f"Requirements: {requirements}"
                    
                    # Generate embedding
                    embedding_result = embedding_service.generate_embedding(job_text)
                    embedding = embedding_result.get('embedding', [])
                    
                    # Prepare job data
                    job_data = {
                        'job_title': row.get('title', ''),
                        'job_text': job_text,
                        'required_skills': required_skills,
                        'embedding': embedding
                    }
                    
                    # Store job in database
                    job_id = db_service.store_job_description(user_id, job_data)
                    jobs_loaded += 1
                    
                    # Console log each job being loaded
                    print(f"  ✓ Loaded: {row.get('title', 'Unknown')} - {row.get('company', 'Unknown')}")
                    print(f"    Skills: {', '.join(required_skills[:3])}{'...' if len(required_skills) > 3 else ''}")
                    
                except Exception as e:
                    print(f"Error loading job {row.get('title', 'Unknown')}: {str(e)}")
        print(f"✓ Loaded {jobs_loaded} sample jobs")
    else:
        print(f"✓ Database already contains {job_count} jobs:")
        # Show first few jobs
        conn = db_service.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT job_title, company FROM job_descriptions LIMIT 5")
        jobs = cursor.fetchall()
        for i, job in enumerate(jobs, 1):
            print(f"  {i}. {job[0]} - {job[1]}")
        conn.close()
        
except Exception as e:
    print(f"⚠️  Warning: Could not load sample jobs: {str(e)}")

print("✓ All services initialized successfully")
print(f"✓ Database files created at: {db_service.db_path}")
print("🚀 Server ready to accept requests")

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    """Upload and process resume PDF with ATS scoring and job matching"""
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process PDF - use direct text extraction
            extracted_text = pdf_service.extract_text_from_pdf(filepath)
            
            # Debug: Check if text extraction worked
            if not extracted_text or extracted_text.strip() == "":
                print("⚠️  Warning: No text extracted from PDF")
                extracted_text = f"Error: No text could be extracted from {filename}"
            elif len(extracted_text.strip()) < 100:
                print(f"⚠️  Warning: Very little text extracted ({len(extracted_text)} chars)")
                print(f"Raw text: '{extracted_text}'")
            
            # Process with NLP
            nlp_results = nlp_service.extract_skills_and_keywords(extracted_text)
            
            # Generate embedding
            embedding_result = embedding_service.generate_embedding(extracted_text)
            
            # Prepare result
            result = {
                'filename': filename,
                'filepath': filepath,
                'extracted_text': extracted_text,
                'full_text': extracted_text,  # Add full_text for ATS processing
                'nlp_analysis': nlp_results,
                'embedding': embedding_result.get('embedding', [])
            }
            
            # Store resume in database (create default user if needed)
            try:
                # Create or get default user
                user_id = db_service.create_user("Default User", "default@example.com")
                
                # Prepare resume data for database
                resume_data = {
                    'file_name': result.get('filename', filename),
                    'extracted_text': result.get('extracted_text', ''),
                    'skills': result.get('nlp_analysis', {}).get('SKILL', []),
                    'embedding': result.get('embedding', [])
                }
                
                # Store resume
                resume_id = db_service.store_resume(user_id, resume_data)
                result['resume_id'] = resume_id
                
            except Exception as db_error:
                result['database_error'] = str(db_error)
            
            # Process with ATS service
            ats_result = ats_service.process_resume_with_ats(result)
            
            # Add console logging for debugging
            print(f"📄 Processed resume: {filename}")
            print(f"📝 Extracted text length: {len(extracted_text)} characters")
            print(f"📄 First 200 chars: {extracted_text[:200]}...")
            print(f"🔍 Found skills: {len(nlp_results.get('SKILL', []))}")
            print(f"🔍 Skills found: {nlp_results.get('SKILL', [])}")
            print(f"🔍 Keywords found: {nlp_results.get('KEYWORDS', [])[:10]}")  # First 10 keywords
            print(f"🎯 ATS Score: {ats_result.get('ats_scores', {}).get('overall_score', 0):.3f}")
            print(f"💼 Matching jobs: {len(ats_result.get('matching_jobs', []))}")
            
            # Check if jobs are loaded in database
            conn = db_service.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM job_descriptions")
            job_count = cursor.fetchone()[0]
            conn.close()
            print(f"📊 Total jobs in database: {job_count}")
            if job_count > 0:
                conn = db_service.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT job_title FROM job_descriptions LIMIT 1")
                sample_job = cursor.fetchone()
                conn.close()
                print(f"📊 Sample job: {sample_job[0] if sample_job else 'Unknown'}")
            
            return jsonify({
                'message': 'Resume processed successfully with ATS analysis',
                'ats_analysis': ats_result
            }), 200
            
        except Exception as e:
            return jsonify({'error': f'Error processing PDF: {str(e)}'}), 500
    
    else:
        return jsonify({'error': 'Only PDF files are allowed'}), 400

@app.route('/resumes', methods=['GET'])
def get_resumes():
    """Get all stored resumes"""
    try:
        resumes = db_service.get_all_resumes()
        return jsonify({
            'message': 'Resumes retrieved successfully',
            'resumes': resumes,
            'count': len(resumes)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve resumes: {str(e)}'}), 500

@app.route('/resumes/<int:resume_id>', methods=['GET'])
def get_resume(resume_id):
    """Get specific resume by ID"""
    try:
        resume = db_service.get_resume(resume_id)
        if resume:
            return jsonify({
                'message': 'Resume retrieved successfully',
                'resume': resume
            })
        else:
            return jsonify({'error': 'Resume not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve resume: {str(e)}'}), 500

@app.route('/search/skills', methods=['POST'])
def search_by_skills():
    """Search resumes by skills"""
    try:
        data = request.get_json()
        if not data or 'skills' not in data:
            return jsonify({'error': 'Skills list required in request body'}), 400
        
        skills = data['skills']
        if not isinstance(skills, list):
            return jsonify({'error': 'Skills must be a list'}), 400
        
        results = db_service.search_by_skills(skills)
        return jsonify({
            'message': 'Skill search completed',
            'searched_skills': skills,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'error': f'Skill search failed: {str(e)}'}), 500

@app.route('/search/similar', methods=['POST'])
def find_similar():
    """Find similar resumes using embedding"""
    try:
        data = request.get_json()
        if not data or 'embedding' not in data:
            return jsonify({'error': 'Embedding required in request body'}), 400
        
        embedding = data['embedding']
        limit = data.get('limit', 10)
        
        results = db_service.find_similar_resumes(embedding, limit)
        return jsonify({
            'message': 'Similarity search completed',
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'error': f'Similarity search failed: {str(e)}'}), 500

@app.route('/stats', methods=['GET'])
def get_statistics():
    """Get database statistics"""
    try:
        stats = db_service.get_statistics()
        return jsonify({
            'message': 'Statistics retrieved successfully',
            'statistics': stats
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get statistics: {str(e)}'}), 500

@app.route('/process/<int:resume_id>', methods=['POST'])
def process_resume_async(resume_id):
    """Start background processing for a resume"""
    try:
        task = process_resume_background.delay(resume_id)
        return jsonify({
            'message': 'Resume processing started',
            'task_id': task.id,
            'resume_id': resume_id
        })
    except Exception as e:
        return jsonify({'error': f'Failed to start processing: {str(e)}'}), 500

@app.route('/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get status of a background task"""
    try:
        from celery.result import AsyncResult
        task = AsyncResult(task_id)
        
        response = {
            'task_id': task_id,
            'status': task.status,
            'result': task.result if task.ready() else None
        }
        
        if task.status == 'FAILURE':
            response['error'] = str(task.result)
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': f'Failed to get task status: {str(e)}'}), 500

@app.route('/score/batch', methods=['POST'])
def batch_score():
    """Batch score resumes against job description"""
    try:
        data = request.get_json()
        if not data or 'job_description' not in data:
            return jsonify({'error': 'Job description required'}), 400
        
        job_description = data['job_description']
        resume_ids = data.get('resume_ids', [])
        
        # Generate embedding for job description
        from nlp.embedding_service import EmbeddingService
        embedding_service = EmbeddingService()
        job_embedding_result = embedding_service.generate_embedding(job_description)
        
        if 'embedding' not in job_embedding_result:
            return jsonify({'error': 'Failed to generate job description embedding'}), 500
        
        job_embedding = job_embedding_result['embedding']
        
        # Start batch scoring task
        task = batch_score_resumes.delay(job_embedding, resume_ids)
        
        return jsonify({
            'message': 'Batch scoring started',
            'task_id': task.id,
            'job_description_length': len(job_description),
            'resume_count': len(resume_ids) if resume_ids else 'all'
        })
    except Exception as e:
        return jsonify({'error': f'Batch scoring failed: {str(e)}'}), 500

@app.route('/rank', methods=['POST'])
def rank_resumes():
    """Rank resumes based on custom criteria"""
    try:
        data = request.get_json()
        resume_ids = data.get('resume_ids', [])
        criteria_weights = data.get('criteria_weights', {
            'similarity': 0.4,
            'skills': 0.3,
            'experience': 0.2,
            'education': 0.1
        })
        
        if not resume_ids:
            return jsonify({'error': 'Resume IDs required'}), 400
        
        # Start ranking task
        task = calculate_resume_ranking.delay(resume_ids, criteria_weights)
        
        return jsonify({
            'message': 'Resume ranking started',
            'task_id': task.id,
            'resume_count': len(resume_ids),
            'criteria_weights': criteria_weights
        })
    except Exception as e:
        return jsonify({'error': f'Ranking failed: {str(e)}'}), 500

# Job Management Endpoints

@app.route('/jobs/feed', methods=['POST'])
def feed_jobs():
    """Feed jobs from CSV file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are allowed'}), 400
        
        # Save CSV temporarily
        csv_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(csv_path)
        
        # Process CSV
        result = job_service.feed_jobs_from_csv(csv_path)
        
        # Clean up temporary file
        os.remove(csv_path)
        
        return jsonify({
            'message': 'Job feeding completed',
            **result
        })
        
    except Exception as e:
        return jsonify({'error': f'Job feeding failed: {str(e)}'}), 500

@app.route('/jobs', methods=['GET'])
def get_jobs():
    """Get all jobs"""
    try:
        limit = request.args.get('limit', 100, type=int)
        jobs = job_service.get_all_jobs(limit)
        return jsonify({
            'message': 'Jobs retrieved successfully',
            'jobs': jobs,
            'count': len(jobs)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve jobs: {str(e)}'}), 500

@app.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get specific job by ID"""
    try:
        job = job_service.get_job(job_id)
        if job:
            return jsonify({
                'message': 'Job retrieved successfully',
                'job': job
            })
        else:
            return jsonify({'error': 'Job not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve job: {str(e)}'}), 500

@app.route('/jobs/search/skills', methods=['POST'])
def search_jobs_by_skills():
    """Search jobs by required skills"""
    try:
        data = request.get_json()
        if not data or 'skills' not in data:
            return jsonify({'error': 'Skills list required'}), 400
        
        skills = data['skills']
        limit = data.get('limit', 50)
        
        if not isinstance(skills, list):
            return jsonify({'error': 'Skills must be a list'}), 400
        
        results = job_service.search_jobs_by_skills(skills, limit)
        return jsonify({
            'message': 'Job skill search completed',
            'searched_skills': skills,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'error': f'Job skill search failed: {str(e)}'}), 500

@app.route('/jobs/search/similar', methods=['POST'])
def find_similar_jobs():
    """Find similar jobs using embedding"""
    try:
        data = request.get_json()
        if not data or 'embedding' not in data:
            return jsonify({'error': 'Embedding required'}), 400
        
        embedding = data['embedding']
        limit = data.get('limit', 10)
        
        results = job_service.find_similar_jobs(embedding, limit)
        return jsonify({
            'message': 'Similar job search completed',
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'error': f'Similar job search failed: {str(e)}'}), 500

@app.route('/jobs/stats', methods=['GET'])
def get_job_statistics():
    """Get job database statistics"""
    try:
        stats = job_service.get_job_statistics()
        return jsonify({
            'message': 'Job statistics retrieved successfully',
            'statistics': stats
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get job statistics: {str(e)}'}), 500

# ATS Endpoints

@app.route('/ats/analyze', methods=['POST'])
def ats_analyze():
    """Analyze resume with ATS scoring"""
    try:
        data = request.get_json()
        if not data or 'resume_id' not in data:
            return jsonify({'error': 'Resume ID required'}), 400
        
        resume_id = data['resume_id']
        resume_data = db_service.get_resume(resume_id)
        
        if not resume_data:
            return jsonify({'error': 'Resume not found'}), 404
        
        ats_result = ats_service.process_resume_with_ats(resume_data)
        
        return jsonify({
            'message': 'ATS analysis completed',
            'resume_id': resume_id,
            'ats_analysis': ats_result
        })
        
    except Exception as e:
        return jsonify({'error': f'ATS analysis failed: {str(e)}'}), 500

@app.route('/ats/score', methods=['POST'])
def ats_score():
    """Calculate ATS score for resume"""
    try:
        data = request.get_json()
        if not data or 'resume_data' not in data:
            return jsonify({'error': 'Resume data required'}), 400
        
        resume_data = data['resume_data']
        ats_scores = ats_service.calculate_ats_score(resume_data)
        
        return jsonify({
            'message': 'ATS score calculated',
            'ats_scores': ats_scores
        })
        
    except Exception as e:
        return jsonify({'error': f'ATS scoring failed: {str(e)}'}), 500

@app.route('/ats/match-jobs', methods=['POST'])
def ats_match_jobs():
    """Find matching jobs for resume"""
    try:
        data = request.get_json()
        if not data or 'resume_data' not in data:
            return jsonify({'error': 'Resume data required'}), 400
        
        resume_data = data['resume_data']
        limit = data.get('limit', 10)
        
        matching_jobs = ats_service.find_matching_jobs(resume_data, limit)
        
        return jsonify({
            'message': 'Job matching completed',
            'matching_jobs': matching_jobs,
            'count': len(matching_jobs)
        })
        
    except Exception as e:
        return jsonify({'error': f'Job matching failed: {str(e)}'}), 500

@app.route('/')
def hello():
    return jsonify({
        'message': 'Resume Processing & ATS System API',
        'version': '1.0.0',
        'status': 'running',
        'database': 'connected',
        'endpoints': {
            'upload_pdf': 'POST /upload-pdf - Upload resume with ATS analysis',
            'get_resumes': 'GET /resumes - List all resumes',
            'get_jobs': 'GET /jobs - List all jobs',
            'feed_jobs': 'POST /jobs/feed - Upload CSV jobs',
            'ats_analyze': 'POST /ats/analyze - ATS analysis',
            'stats': 'GET /stats - Database statistics'
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        stats = db_service.get_statistics()
        job_stats = job_service.get_job_statistics()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'services': {
                'database': 'ok',
                'pdf_service': 'ok',
                'nlp_service': 'ok',
                'embedding_service': 'ok',
                'ats_service': 'ok',
                'job_service': 'ok'
            },
            'database_stats': {
                'resumes_count': stats.get('total_resumes', 0),
                'jobs_count': job_stats.get('total_jobs', 0)
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 STARTING RESUME ATS SYSTEM")
    print("=" * 60)
    print("📊 Database: SQLite (auto-initialized)")
    print("🔍 NLP Engine: spaCy")
    print("🧠 Embedding: SentenceTransformers")
    print("📋 ATS Scoring: Multi-criteria analysis")
    print("💼 Job Matching: Semantic + Skills + Experience")
    print("⚡ Background Processing: Celery + Redis")
    print("=" * 60)
    print("🌐 Server will be available at: http://localhost:5000")
    print("🏥 Health check: http://localhost:5000/health")
    print("📖 API docs: http://localhost:5000/")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
