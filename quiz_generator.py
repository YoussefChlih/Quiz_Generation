"""
Quiz Generator Module
Uses Mistral AI to generate quizzes from document content
"""

import json
import re
from typing import List, Dict, Optional
from mistralai import Mistral


class QuizGenerator:
    """Generate quizzes using Mistral AI"""
    
    DIFFICULTY_PROMPTS = {
        'facile': {
            'name': 'Facile',
            'description': 'Questions simples et directes, basées sur des faits explicites du document.',
            'complexity': 'basic recall and straightforward comprehension'
        },
        'moyen': {
            'name': 'Moyen',
            'description': 'Questions nécessitant une compréhension approfondie et des liens entre concepts.',
            'complexity': 'moderate analysis and connection of concepts'
        },
        'difficile': {
            'name': 'Difficile',
            'description': 'Questions complexes nécessitant analyse, synthèse et réflexion critique.',
            'complexity': 'deep analysis, synthesis, and critical thinking'
        }
    }
    
    QUESTION_TYPE_PROMPTS = {
        'comprehension': {
            'name': 'Compréhension',
            'description': 'Questions testant la compréhension du contenu',
            'format': '''Create comprehension questions that test understanding of concepts and ideas.
            Format: Open-ended questions requiring explanation.
            Example: "Expliquez le concept de X et son importance dans Y."'''
        },
        'memorisation': {
            'name': 'Mémorisation',
            'description': 'Questions testant la mémorisation de faits',
            'format': '''Create memorization questions testing recall of specific facts, dates, definitions.
            Format: Direct questions with specific answers.
            Example: "Quelle est la définition de X?" or "En quelle année s'est produit Y?"'''
        },
        'qcm': {
            'name': 'QCM (Choix Multiple)',
            'description': 'Questions à choix multiples avec 4 options',
            'format': '''Create multiple choice questions with exactly 4 options (A, B, C, D).
            Only ONE option should be correct.
            Format:
            Question: [question text]
            A) [option A]
            B) [option B]
            C) [option C]
            D) [option D]
            Correct Answer: [letter]'''
        },
        'vrai_faux': {
            'name': 'Vrai/Faux',
            'description': 'Questions vrai ou faux',
            'format': '''Create true/false statements based on the document content.
            Make some statements true and some false.
            Format:
            Statement: [statement]
            Answer: Vrai/Faux
            Explanation: [brief explanation]'''
        },
        'reponse_courte': {
            'name': 'Réponse Courte',
            'description': 'Questions à réponse courte',
            'format': '''Create short answer questions requiring brief, specific answers.
            Format:
            Question: [question]
            Expected Answer: [1-2 sentence answer]'''
        }
    }
    
    def __init__(self, api_key: str):
        self.client = Mistral(api_key=api_key)
        self.model = "mistral-large-latest"
    
    def generate_quiz(
        self,
        context: str,
        num_questions: int = 5,
        difficulty: str = 'moyen',
        question_types: List[str] = None,
        language: str = 'french'
    ) -> Dict:
        """
        Generate a quiz from the given context
        
        Args:
            context: Document content to base questions on
            num_questions: Number of questions to generate
            difficulty: Difficulty level (facile, moyen, difficile)
            question_types: List of question types to include
            language: Language for the quiz (french/english)
            
        Returns:
            Dictionary containing quiz questions and metadata
        """
        if question_types is None:
            question_types = ['qcm']
        
        # Validate inputs
        difficulty = difficulty.lower() if difficulty else 'moyen'
        if difficulty not in self.DIFFICULTY_PROMPTS:
            difficulty = 'moyen'
        
        valid_types = [qt for qt in question_types if qt in self.QUESTION_TYPE_PROMPTS]
        if not valid_types:
            valid_types = ['qcm']
        
        # Build the prompt
        prompt = self._build_prompt(context, num_questions, difficulty, valid_types, language)
        
        # Call Mistral API
        try:
            response = self._call_mistral(prompt)
            quiz = self._parse_response(response, difficulty, valid_types)
            return quiz
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'questions': []
            }
    
    def _build_prompt(
        self,
        context: str,
        num_questions: int,
        difficulty: str,
        question_types: List[str],
        language: str
    ) -> str:
        """Build the prompt for quiz generation"""
        
        diff_info = self.DIFFICULTY_PROMPTS[difficulty]
        
        # Build question type instructions
        type_instructions = []
        questions_per_type = max(1, num_questions // len(question_types))
        
        for qt in question_types:
            qt_info = self.QUESTION_TYPE_PROMPTS[qt]
            type_instructions.append(f"""
### {qt_info['name']}
{qt_info['format']}
Generate approximately {questions_per_type} questions of this type.
""")
        
        lang_instruction = "Générez le quiz UNIQUEMENT en français." if language == 'french' else "Generate the quiz in English."
        
        prompt = f"""Tu es un expert en création de quiz éducatifs. Ta tâche est de créer des questions de quiz basées UNIQUEMENT sur le contenu du document fourni ci-dessous.

## CONTENU DU DOCUMENT (BASE UNIQUE POUR LES QUESTIONS):
\"\"\"
{context[:12000]}
\"\"\"

## RÈGLES STRICTES:
1. {lang_instruction}
2. **TOUTES les questions DOIVENT être basées UNIQUEMENT sur le contenu du document ci-dessus.**
3. **NE PAS inventer d'informations qui ne sont pas dans le document.**
4. **NE PAS poser de questions générales ou hors sujet.**
5. Niveau de difficulté: {diff_info['name']} - {diff_info['description']}
6. Générer exactement {num_questions} questions au total.
7. Chaque question doit pouvoir être répondue en utilisant UNIQUEMENT les informations du document.

## Types de questions demandés:
{''.join(type_instructions)}

## FORMAT DE SORTIE (JSON STRICT):
Tu DOIS retourner UNIQUEMENT un objet JSON valide avec cette structure exacte:

{{
    "quiz_title": "Titre du quiz basé sur le sujet du document",
    "questions": [
        {{
            "id": 1,
            "type": "qcm",
            "question": "Texte de la question basée sur le document",
            "options": ["A) première option", "B) deuxième option", "C) troisième option", "D) quatrième option"],
            "correct_answer": "A",
            "explanation": "Explication de pourquoi c'est correct selon le document",
            "difficulty": "{difficulty}"
        }}
    ]
}}

## IMPORTANT POUR LES QCM:
- Exactement 4 options: A, B, C, D
- Le champ "correct_answer" doit contenir UNIQUEMENT la lettre (A, B, C ou D)
- Les options doivent commencer par "A) ", "B) ", "C) ", "D) "
- UNE SEULE réponse correcte par question

## IMPORTANT POUR VRAI/FAUX:
- Le champ "correct_answer" doit être "Vrai" ou "Faux"
- Pas de champ "options"

RETOURNE UNIQUEMENT LE JSON, sans texte avant ou après, sans balises markdown."""
        return prompt
    
    def _call_mistral(self, prompt: str) -> str:
        """Call Mistral API"""
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        response = self.client.chat.complete(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=4000
        )
        
        return response.choices[0].message.content
    
    def _parse_response(self, response: str, difficulty: str, question_types: List[str]) -> Dict:
        """Parse the Mistral response into structured quiz data"""
        
        try:
            # Clean the response - remove markdown code blocks
            cleaned_response = response.strip()
            cleaned_response = re.sub(r'^```json?\s*', '', cleaned_response)
            cleaned_response = re.sub(r'\s*```$', '', cleaned_response)
            cleaned_response = cleaned_response.strip()
            
            # Try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', cleaned_response)
            if json_match:
                json_str = json_match.group()
                quiz_data = json.loads(json_str)
                
                # Validate and clean the data
                quiz_data['success'] = True
                quiz_data['difficulty'] = difficulty
                quiz_data['question_types'] = question_types
                
                # Process and fix each question
                processed_questions = []
                for i, q in enumerate(quiz_data.get('questions', [])):
                    processed_q = self._process_question(q, i + 1, difficulty, question_types)
                    if processed_q:
                        processed_questions.append(processed_q)
                
                quiz_data['questions'] = processed_questions
                return quiz_data
            else:
                # If no JSON found, try to parse as plain text
                return self._parse_plain_text(response, difficulty, question_types)
                
        except json.JSONDecodeError as e:
            # Try to fix common JSON issues
            try:
                # More aggressive cleaning
                cleaned = re.sub(r'```json?\s*', '', response)
                cleaned = re.sub(r'```\s*', '', cleaned)
                cleaned = re.sub(r',\s*}', '}', cleaned)  # Remove trailing commas
                cleaned = re.sub(r',\s*]', ']', cleaned)  # Remove trailing commas in arrays
                cleaned = cleaned.strip()
                
                quiz_data = json.loads(cleaned)
                quiz_data['success'] = True
                
                # Process questions
                processed_questions = []
                for i, q in enumerate(quiz_data.get('questions', [])):
                    processed_q = self._process_question(q, i + 1, difficulty, question_types)
                    if processed_q:
                        processed_questions.append(processed_q)
                
                quiz_data['questions'] = processed_questions
                return quiz_data
            except:
                return {
                    'success': False,
                    'error': f'Erreur lors de l\'analyse de la réponse: {str(e)}',
                    'raw_response': response[:1000],
                    'questions': []
                }
    
    def _process_question(self, q: Dict, index: int, difficulty: str, question_types: List[str]) -> Dict:
        """Process and validate a single question"""
        if not q.get('question'):
            return None
        
        processed = {
            'id': index,
            'question': q.get('question', ''),
            'type': q.get('type', question_types[0] if question_types else 'qcm'),
            'difficulty': q.get('difficulty', difficulty),
            'explanation': q.get('explanation', '')
        }
        
        q_type = processed['type'].lower()
        
        # Handle QCM questions
        if q_type == 'qcm':
            options = q.get('options', [])
            
            # Ensure we have 4 options
            if isinstance(options, list) and len(options) >= 4:
                # Clean and format options
                formatted_options = []
                for i, opt in enumerate(options[:4]):
                    opt_str = str(opt).strip()
                    letter = chr(65 + i)  # A, B, C, D
                    # Remove existing letter prefix if present
                    opt_str = re.sub(r'^[A-Da-d][.)]\s*', '', opt_str)
                    formatted_options.append(f"{letter}) {opt_str}")
                processed['options'] = formatted_options
            else:
                # If not enough options, create placeholders
                processed['options'] = options if options else []
            
            # Fix correct_answer - should be just the letter
            correct = q.get('correct_answer', 'A')
            if isinstance(correct, str):
                # Extract just the letter
                letter_match = re.match(r'^([A-Da-d])', correct.strip())
                if letter_match:
                    processed['correct_answer'] = letter_match.group(1).upper()
                else:
                    # Try to find the answer in options
                    processed['correct_answer'] = 'A'
            else:
                processed['correct_answer'] = 'A'
        
        # Handle Vrai/Faux questions
        elif q_type == 'vrai_faux':
            correct = str(q.get('correct_answer', '')).strip().lower()
            if 'vrai' in correct or 'true' in correct:
                processed['correct_answer'] = 'Vrai'
            elif 'faux' in correct or 'false' in correct:
                processed['correct_answer'] = 'Faux'
            else:
                processed['correct_answer'] = q.get('correct_answer', 'Vrai')
        
        # Handle other question types
        else:
            processed['correct_answer'] = q.get('correct_answer', '')
        
        return processed
    
    def _parse_plain_text(self, response: str, difficulty: str, question_types: List[str]) -> Dict:
        """Fallback parser for plain text responses"""
        questions = []
        
        # Try to extract questions using patterns
        lines = response.split('\n')
        current_question = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_question.get('question'):
                    questions.append(current_question)
                    current_question = {}
                continue
            
            # Detect question patterns
            if re.match(r'^(Question\s*\d*[:.)]|Q\d*[:.)]|\d+[.)]\s)', line, re.IGNORECASE):
                if current_question.get('question'):
                    questions.append(current_question)
                current_question = {
                    'id': len(questions) + 1,
                    'question': re.sub(r'^(Question\s*\d*[:.)]|Q\d*[:.)]|\d+[.)]\s*)', '', line).strip(),
                    'type': question_types[0] if question_types else 'qcm',
                    'difficulty': difficulty,
                    'options': [],
                    'correct_answer': '',
                    'explanation': ''
                }
            elif re.match(r'^[A-D][.)]\s', line):
                if current_question:
                    current_question.setdefault('options', []).append(line)
            elif re.match(r'^(Correct Answer|Answer|Réponse)[:.]\s*', line, re.IGNORECASE):
                if current_question:
                    current_question['correct_answer'] = re.sub(
                        r'^(Correct Answer|Answer|Réponse)[:.]\s*', '', line, flags=re.IGNORECASE
                    ).strip()
        
        # Don't forget the last question
        if current_question.get('question'):
            questions.append(current_question)
        
        return {
            'success': len(questions) > 0,
            'quiz_title': 'Quiz généré',
            'questions': questions,
            'difficulty': difficulty,
            'question_types': question_types
        }
    
    def get_available_options(self) -> Dict:
        """Get available difficulty levels and question types"""
        return {
            'difficulties': [
                {'key': k, 'name': v['name'], 'description': v['description']}
                for k, v in self.DIFFICULTY_PROMPTS.items()
            ],
            'question_types': [
                {'key': k, 'name': v['name'], 'description': v['description']}
                for k, v in self.QUESTION_TYPE_PROMPTS.items()
            ]
        }
