"""
Quiz RAG System - Flask Application
Main application file with routes and API endpoints
"""

import os
import uuid
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import Config
from document_processor import DocumentProcessor, get_file_info
from rag_system import RAGSystem
from quiz_generator import QuizGenerator


# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_object(Config)
CORS(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize components
document_processor = DocumentProcessor()
rag_system = RAGSystem(
    chunk_size=Config.CHUNK_SIZE,
    chunk_overlap=Config.CHUNK_OVERLAP
)

# Quiz generator (initialized lazily when API key is available)
quiz_generator = None


def get_quiz_generator():
    """Get or create quiz generator instance"""
    global quiz_generator
    if quiz_generator is None:
        api_key = Config.MISTRAL_API_KEY
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not configured")
        quiz_generator = QuizGenerator(api_key)
    return quiz_generator


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


# ==================== Web Routes ====================

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)


# ==================== API Routes ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Quiz RAG System is running'
    })


@app.route('/api/options', methods=['GET'])
def get_options():
    """Get available quiz options (difficulties and question types)"""
    try:
        generator = get_quiz_generator()
        options = generator.get_available_options()
        return jsonify({
            'success': True,
            'data': options
        })
    except ValueError as e:
        # Return default options if API key not set
        return jsonify({
            'success': True,
            'data': {
                'difficulties': [
                    {'key': 'facile', 'name': 'Facile', 'description': 'Questions simples'},
                    {'key': 'moyen', 'name': 'Moyen', 'description': 'Questions modérées'},
                    {'key': 'difficile', 'name': 'Difficile', 'description': 'Questions complexes'}
                ],
                'question_types': [
                    {'key': 'comprehension', 'name': 'Compréhension', 'description': 'Compréhension du contenu'},
                    {'key': 'memorisation', 'name': 'Mémorisation', 'description': 'Rappel de faits'},
                    {'key': 'qcm', 'name': 'QCM', 'description': 'Choix multiples'},
                    {'key': 'vrai_faux', 'name': 'Vrai/Faux', 'description': 'Questions vrai/faux'},
                    {'key': 'reponse_courte', 'name': 'Réponse Courte', 'description': 'Réponses brèves'}
                ]
            }
        })


@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Upload and process a document"""
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No file provided'
        }), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'No file selected'
        }), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'error': f'File type not allowed. Supported types: {", ".join(Config.ALLOWED_EXTENSIONS)}'
        }), 400
    
    try:
        # Save the file
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Process the document
        text_content = document_processor.process(file_path)
        
        if not text_content or not text_content.strip():
            os.remove(file_path)
            return jsonify({
                'success': False,
                'error': 'Could not extract text from document'
            }), 400
        
        # Add to RAG system
        num_chunks = rag_system.add_document(text_content, unique_filename)
        
        # Get file info
        file_info = get_file_info(file_path)
        
        return jsonify({
            'success': True,
            'message': 'Document processed successfully',
            'data': {
                'filename': filename,
                'file_id': unique_filename,
                'text_length': len(text_content),
                'chunks_created': num_chunks,
                'file_size': file_info['size'] if file_info else 0
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/documents', methods=['GET'])
def get_documents():
    """Get information about loaded documents"""
    stats = rag_system.get_stats()
    return jsonify({
        'success': True,
        'data': stats
    })


@app.route('/api/documents/clear', methods=['POST'])
def clear_documents():
    """Clear all loaded documents"""
    try:
        rag_system.clear()
        
        # Optionally clear upload folder
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        return jsonify({
            'success': True,
            'message': 'All documents cleared'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/generate-quiz', methods=['POST'])
def generate_quiz():
    """Generate a quiz from uploaded documents"""
    try:
        # Check if documents are loaded
        stats = rag_system.get_stats()
        if stats['total_chunks'] == 0:
            return jsonify({
                'success': False,
                'error': 'No documents loaded. Please upload a document first.'
            }), 400
        
        # Get parameters from request
        data = request.get_json() or {}
        
        num_questions = data.get('num_questions', 5)
        difficulty = data.get('difficulty', 'moyen')
        question_types = data.get('question_types', ['qcm'])
        topic = data.get('topic', '')  # Optional topic focus
        
        # Validate parameters
        num_questions = min(max(1, int(num_questions)), 20)  # Between 1 and 20
        
        if isinstance(question_types, str):
            question_types = [question_types]
        
        # Get relevant context
        if topic:
            context = rag_system.get_relevant_context(topic, top_k=Config.TOP_K_RESULTS)
        else:
            context = rag_system.get_full_context()
        
        # Generate quiz
        generator = get_quiz_generator()
        quiz = generator.generate_quiz(
            context=context,
            num_questions=num_questions,
            difficulty=difficulty,
            question_types=question_types
        )
        
        return jsonify({
            'success': quiz.get('success', False),
            'data': quiz
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error generating quiz: {str(e)}'
        }), 500


@app.route('/api/search', methods=['POST'])
def search_documents():
    """Search through loaded documents"""
    try:
        data = request.get_json() or {}
        query = data.get('query', '')
        top_k = data.get('top_k', 5)
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query is required'
            }), 400
        
        results = rag_system.vector_store.search(query, top_k)
        
        return jsonify({
            'success': True,
            'data': {
                'query': query,
                'results': results
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Resource not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        'success': False,
        'error': 'File too large. Maximum size is 16MB.'
    }), 413


# ==================== Main ====================

if __name__ == '__main__':
    print("=" * 50)
    print("Quiz RAG System")
    print("=" * 50)
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Allowed extensions: {Config.ALLOWED_EXTENSIONS}")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
