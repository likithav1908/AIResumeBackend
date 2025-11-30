#!/usr/bin/env python3

"""
Database initialization script for Resume ATS System.
This script creates all necessary tables and indexes.
"""

import os
import sys
from database.database_service import DatabaseService
from job_service import JobService

def initialize_database():
    """Initialize all database tables"""
    print("🗄️  Initializing Resume ATS Database...")
    print("=" * 50)
    
    try:
        # Initialize resume database
        print("📋 Creating resume database and tables...")
        db_service = DatabaseService()
        print("✅ Resume database initialized successfully")
        
        # Initialize job database
        print("💼 Creating job database and tables...")
        job_service = JobService()
        print("✅ Job database initialized successfully")
        
        # Test database operations
        print("🧪 Testing database operations...")
        resume_stats = db_service.get_statistics()
        job_stats = job_service.get_job_statistics()
        
        print(f"📊 Resume database: {resume_stats}")
        print(f"💼 Job database: {job_stats}")
        
        print("=" * 50)
        print("🎉 Database initialization completed successfully!")
        print(f"📁 Database files created at: {db_service.db_path}")
        print("✅ All tables and indexes are ready")
        print("🚀 You can now start the server with: python server.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        return False

if __name__ == '__main__':
    success = initialize_database()
    sys.exit(0 if success else 1)
