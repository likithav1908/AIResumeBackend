#!/usr/bin/env python3
import csv
import json
from database.database_service import DatabaseService
from nlp.embedding_service import EmbeddingService

def load_sample_jobs():
    """Load sample jobs from CSV into database"""
    print("🔄 Loading sample jobs into database...")
    
    # Initialize services
    db_service = DatabaseService()
    embedding_service = EmbeddingService()
    
    # Create default user if not exists
    try:
        user_id = db_service.create_user("Default User", "default@example.com")
        print(f"✓ User ID: {user_id}")
    except:
        # User might already exist, get it
        users = db_service.get_all_users()
        if users:
            user_id = users[0]['id']
            print(f"✓ Using existing User ID: {user_id}")
        else:
            print("❌ Could not create or find user")
            return
    
    # Load jobs from CSV
    jobs_loaded = 0
    try:
        with open('sample_jobs.csv', 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            
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
                    
                    print(f"  ✓ Loaded: {row.get('title', 'Unknown')} - {row.get('company', 'Unknown')}")
                    print(f"    Skills: {', '.join(required_skills[:3])}{'...' if len(required_skills) > 3 else ''}")
                    print(f"    Job ID: {job_id}")
                    
                except Exception as e:
                    print(f"❌ Error loading job {row.get('title', 'Unknown')}: {str(e)}")
    
    except FileNotFoundError:
        print("❌ sample_jobs.csv file not found")
        return
    except Exception as e:
        print(f"❌ Error reading CSV: {str(e)}")
        return
    
    print(f"\n✅ Successfully loaded {jobs_loaded} jobs into database")
    
    # Verify loading
    try:
        all_jobs = db_service.get_all_jobs()
        print(f"📊 Total jobs in database: {len(all_jobs)}")
        
        if len(all_jobs) > 0:
            print("\n📋 Sample jobs loaded:")
            for i, job in enumerate(all_jobs[:3], 1):
                print(f"  {i}. {job.get('job_title', 'Unknown')} - Skills: {len(job.get('required_skills', []))}")
        
    except Exception as e:
        print(f"❌ Error verifying jobs: {str(e)}")

if __name__ == "__main__":
    load_sample_jobs()
