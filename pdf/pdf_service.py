import PyPDF2
import os
from werkzeug.utils import secure_filename
from nlp.nlp_service import NLPService
from nlp.embedding_service import EmbeddingService
from database.database_service import DatabaseService

class PDFService:
    def __init__(self):
        self.nlp_service = NLPService()
        self.embedding_service = EmbeddingService()
        self.db_service = DatabaseService()
    
    def extract_text_from_pdf(self, filepath):
        """Extract text from PDF using PyPDF2"""
        try:
            with open(filepath, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
            return text
        except Exception as e:
            return f"Error extracting text: {str(e)}"
    
    def process_pdf(self, file, upload_folder, store_in_db=True):
        """Process uploaded PDF file"""
        # Validate file
        if file.filename == '':
            return {"error": "No file selected"}
        
        if not self._allowed_file(file.filename):
            return {"error": "Only PDF files are allowed"}
        
        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        # Extract text
        extracted_text = self.extract_text_from_pdf(filepath)
        
        # Process with NLP
        nlp_results = self.nlp_service.extract_skills_and_keywords(extracted_text)
        
        # Generate embedding
        embedding_result = self.embedding_service.generate_embedding(extracted_text)
        
        # Prepare resume data
        resume_data = {
            "filename": filename,
            "filepath": filepath,
            "full_text": extracted_text,  # Store full text
            "extracted_text": extracted_text[:1000] + '...' if len(extracted_text) > 1000 else extracted_text,
            "nlp_analysis": nlp_results,
            "embedding": embedding_result
        }
        
        # Store in database if requested
        resume_id = None
        if store_in_db:
            try:
                resume_id = self.db_service.store_resume(resume_data)
                resume_data["database_id"] = resume_id
            except Exception as e:
                resume_data["database_error"] = str(e)
        
        return resume_data
    
    def _allowed_file(self, filename):
        """Check if file has allowed extension"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}
