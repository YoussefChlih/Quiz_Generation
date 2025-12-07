import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB max
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'pdf', 'pptx', 'ppt', 'docx', 'doc', 'txt', 'rtf'}
    
    # RAG settings - augmenté pour mieux capturer le contenu
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 100
    TOP_K_RESULTS = 10
    
    # Quiz settings
    DIFFICULTY_LEVELS = {
        'facile': 'easy',
        'moyen': 'medium', 
        'difficile': 'hard'
    }
    
    QUESTION_TYPES = {
        'comprehension': 'comprehension',
        'memorisation': 'memorization',
        'qcm': 'multiple_choice',
        'vrai_faux': 'true_false',
        'reponse_courte': 'short_answer'
    }
