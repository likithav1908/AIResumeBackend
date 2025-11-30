#!/usr/bin/env python3
import sqlite3
import json

def check_database():
    """Check the database contents"""
    conn = sqlite3.connect('database/resume_database.db')
    cursor = conn.cursor()
    
    print("🗄️  Database Tables:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  - {table[0]}")
    
    print("\n📊 Job Descriptions:")
    try:
        cursor.execute("SELECT COUNT(*) FROM job_descriptions;")
        job_count = cursor.fetchone()[0]
        print(f"  Total jobs: {job_count}")
        
        if job_count > 0:
            cursor.execute("""
                SELECT job_title, company, location, required_skills 
                FROM job_descriptions 
                LIMIT 5;
            """)
            jobs = cursor.fetchall()
            for i, job in enumerate(jobs, 1):
                skills = json.loads(job[3]) if job[3] else []
                print(f"  {i}. {job[0]} - {job[1]} ({job[2]})")
                print(f"     Skills: {', '.join(skills[:3])}{'...' if len(skills) > 3 else ''}")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n👥 Users:")
    try:
        cursor.execute("SELECT COUNT(*) FROM users;")
        user_count = cursor.fetchone()[0]
        print(f"  Total users: {user_count}")
        
        if user_count > 0:
            cursor.execute("SELECT name, email FROM users LIMIT 3;")
            users = cursor.fetchall()
            for i, user in enumerate(users, 1):
                print(f"  {i}. {user[0]} ({user[1]})")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n📄 Resumes:")
    try:
        cursor.execute("SELECT COUNT(*) FROM resumes;")
        resume_count = cursor.fetchone()[0]
        print(f"  Total resumes: {resume_count}")
        
        if resume_count > 0:
            cursor.execute("""
                SELECT file_name, LENGTH(extracted_text) as text_length 
                FROM resumes 
                LIMIT 3;
            """)
            resumes = cursor.fetchall()
            for i, resume in enumerate(resumes, 1):
                print(f"  {i}. {resume[0]} ({resume[1]} chars)")
    except Exception as e:
        print(f"  Error: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_database()
