/**
 * Quiz RAG Generator - Main Application JavaScript
 */

// =====================================================
// Global State
// =====================================================

const state = {
    uploadedFiles: [],
    currentQuiz: null,
    userAnswers: {},
    isLoading: false
};

// =====================================================
// Utility Functions
// =====================================================

function showLoading(message = 'Chargement en cours...') {
    const overlay = document.getElementById('loading-overlay');
    const messageEl = document.getElementById('loading-message');
    messageEl.textContent = message;
    overlay.classList.add('active');
    state.isLoading = true;
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    overlay.classList.remove('active');
    state.isLoading = false;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        info: 'fas fa-info-circle'
    };
    
    toast.innerHTML = `
        <i class="${icons[type] || icons.info}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const icons = {
        pdf: 'fas fa-file-pdf',
        pptx: 'fas fa-file-powerpoint',
        ppt: 'fas fa-file-powerpoint',
        docx: 'fas fa-file-word',
        doc: 'fas fa-file-word',
        txt: 'fas fa-file-alt',
        rtf: 'fas fa-file-alt'
    };
    return icons[ext] || 'fas fa-file';
}

// =====================================================
// API Functions
// =====================================================

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData
    });
    
    return await response.json();
}

async function generateQuiz(options) {
    const response = await fetch('/api/generate-quiz', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(options)
    });
    
    return await response.json();
}

async function clearDocuments() {
    const response = await fetch('/api/documents/clear', {
        method: 'POST'
    });
    
    return await response.json();
}

async function getDocumentStats() {
    const response = await fetch('/api/documents');
    return await response.json();
}

// =====================================================
// Navigation
// =====================================================

function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const section = link.dataset.section;
            navigateToSection(section);
        });
    });
}

function navigateToSection(sectionName) {
    // Update nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle('active', link.dataset.section === sectionName);
    });
    
    // Update sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.toggle('active', section.id === `${sectionName}-section`);
    });
}

// =====================================================
// Upload Section
// =====================================================

function initUploadSection() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const clearAllBtn = document.getElementById('clear-all-btn');
    const proceedBtn = document.getElementById('proceed-btn');
    
    // Drag and drop handlers
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });
    
    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });
    
    dropzone.addEventListener('drop', async (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files);
        await handleFiles(files);
    });
    
    // Click to upload
    dropzone.addEventListener('click', () => {
        fileInput.click();
    });
    
    fileInput.addEventListener('change', async (e) => {
        const files = Array.from(e.target.files);
        await handleFiles(files);
        fileInput.value = '';
    });
    
    // Clear all button
    clearAllBtn.addEventListener('click', async () => {
        if (confirm('Êtes-vous sûr de vouloir supprimer tous les documents ?')) {
            showLoading('Suppression des documents...');
            try {
                await clearDocuments();
                state.uploadedFiles = [];
                updateFilesList();
                showToast('Tous les documents ont été supprimés', 'success');
            } catch (error) {
                showToast('Erreur lors de la suppression', 'error');
            } finally {
                hideLoading();
            }
        }
    });
    
    // Proceed button
    proceedBtn.addEventListener('click', () => {
        navigateToSection('generate');
    });
}

async function handleFiles(files) {
    const validExtensions = ['pdf', 'pptx', 'ppt', 'docx', 'doc', 'txt', 'rtf'];
    
    for (const file of files) {
        const ext = file.name.split('.').pop().toLowerCase();
        
        if (!validExtensions.includes(ext)) {
            showToast(`Format non supporté: ${file.name}`, 'error');
            continue;
        }
        
        showLoading(`Traitement de ${file.name}...`);
        
        try {
            const result = await uploadFile(file);
            
            if (result.success) {
                state.uploadedFiles.push({
                    name: file.name,
                    size: file.size,
                    ...result.data
                });
                showToast(`${file.name} chargé avec succès`, 'success');
            } else {
                showToast(result.error || 'Erreur lors du chargement', 'error');
            }
        } catch (error) {
            showToast(`Erreur: ${error.message}`, 'error');
        }
    }
    
    hideLoading();
    updateFilesList();
}

function updateFilesList() {
    const filesList = document.getElementById('files-list');
    const clearAllBtn = document.getElementById('clear-all-btn');
    const proceedBtn = document.getElementById('proceed-btn');
    
    if (state.uploadedFiles.length === 0) {
        filesList.innerHTML = '<p class="no-files">Aucun document chargé</p>';
        clearAllBtn.style.display = 'none';
        proceedBtn.style.display = 'none';
        return;
    }
    
    clearAllBtn.style.display = 'inline-flex';
    proceedBtn.style.display = 'inline-flex';
    
    filesList.innerHTML = state.uploadedFiles.map((file, index) => `
        <div class="file-item" data-index="${index}">
            <div class="file-info">
                <i class="${getFileIcon(file.name)} file-icon"></i>
                <div class="file-details">
                    <h4>${file.name}</h4>
                    <span>${formatFileSize(file.size)} • ${file.chunks_created || 0} chunks</span>
                </div>
            </div>
            <div class="file-status success">
                <i class="fas fa-check-circle"></i>
                <span>Traité</span>
            </div>
        </div>
    `).join('');
}

// =====================================================
// Generate Section
// =====================================================

function initGenerateSection() {
    const numQuestionsInput = document.getElementById('num-questions');
    const numQuestionsValue = document.getElementById('num-questions-value');
    const generateBtn = document.getElementById('generate-btn');
    
    // Update range value display
    numQuestionsInput.addEventListener('input', () => {
        numQuestionsValue.textContent = numQuestionsInput.value;
    });
    
    // Difficulty option selection
    document.querySelectorAll('.option-card').forEach(card => {
        card.addEventListener('click', () => {
            document.querySelectorAll('.option-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
        });
    });
    
    // Generate button
    generateBtn.addEventListener('click', handleGenerateQuiz);
}

async function handleGenerateQuiz() {
    // Check if documents are loaded
    if (state.uploadedFiles.length === 0) {
        showToast('Veuillez d\'abord charger un document', 'error');
        navigateToSection('upload');
        return;
    }
    
    // Get options
    const numQuestions = parseInt(document.getElementById('num-questions').value);
    const topic = document.getElementById('topic').value;
    const difficulty = document.querySelector('input[name="difficulty"]:checked')?.value || 'moyen';
    
    const questionTypes = Array.from(document.querySelectorAll('input[name="question_type"]:checked'))
        .map(cb => cb.value);
    
    if (questionTypes.length === 0) {
        showToast('Veuillez sélectionner au moins un type de question', 'error');
        return;
    }
    
    showLoading('Génération du quiz en cours...\nCela peut prendre quelques instants.');
    
    try {
        const result = await generateQuiz({
            num_questions: numQuestions,
            difficulty: difficulty,
            question_types: questionTypes,
            topic: topic
        });
        
        if (result.success && result.data) {
            state.currentQuiz = result.data;
            state.userAnswers = {};
            displayQuiz(result.data);
            navigateToSection('quiz');
            showToast('Quiz généré avec succès!', 'success');
        } else {
            showToast(result.error || 'Erreur lors de la génération', 'error');
        }
    } catch (error) {
        showToast(`Erreur: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// =====================================================
// Quiz Section
// =====================================================

function initQuizSection() {
    const newQuizBtn = document.getElementById('new-quiz-btn');
    const checkAnswersBtn = document.getElementById('check-answers-btn');
    const exportBtn = document.getElementById('export-btn');
    
    newQuizBtn.addEventListener('click', () => {
        navigateToSection('generate');
    });
    
    checkAnswersBtn.addEventListener('click', checkAnswers);
    exportBtn.addEventListener('click', exportQuiz);
}

function displayQuiz(quiz) {
    const container = document.getElementById('quiz-container');
    const actions = document.getElementById('quiz-actions');
    const results = document.getElementById('results-container');
    const titleEl = document.getElementById('quiz-title');
    const infoEl = document.getElementById('quiz-info');
    
    // Update title
    titleEl.textContent = quiz.quiz_title || 'Quiz Généré';
    infoEl.textContent = `${quiz.questions?.length || 0} questions • Difficulté: ${getDifficultyLabel(quiz.difficulty)}`;
    
    // Show actions, hide results
    actions.style.display = 'flex';
    results.style.display = 'none';
    
    // Render questions
    if (!quiz.questions || quiz.questions.length === 0) {
        container.innerHTML = `
            <div class="quiz-placeholder">
                <i class="fas fa-exclamation-triangle"></i>
                <p>Aucune question n'a pu être générée. Veuillez réessayer.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = quiz.questions.map((q, index) => renderQuestion(q, index)).join('');
    
    // Add event listeners for answers
    initAnswerListeners();
}

function renderQuestion(question, index) {
    const typeLabel = getTypeLabel(question.type);
    const diffLabel = getDifficultyLabel(question.difficulty);
    
    let answerSection = '';
    
    switch (question.type) {
        case 'qcm':
            answerSection = renderMCQOptions(question, index);
            break;
        case 'vrai_faux':
            answerSection = renderTrueFalseOptions(question, index);
            break;
        case 'comprehension':
        case 'memorisation':
        case 'reponse_courte':
        default:
            answerSection = renderOpenQuestion(question, index);
            break;
    }
    
    return `
        <div class="question-card" id="question-${index}">
            <div class="question-header">
                <div class="question-number">
                    <i class="fas fa-question-circle"></i>
                    Question ${index + 1}
                </div>
                <div class="question-badges">
                    <span class="badge badge-difficulty">${diffLabel}</span>
                    <span class="badge badge-type">${typeLabel}</span>
                </div>
            </div>
            <p class="question-text">${question.question}</p>
            ${answerSection}
            <div class="question-explanation" style="display: none;">
                <h5><i class="fas fa-lightbulb"></i> Explication</h5>
                <p>${question.explanation || 'Pas d\'explication disponible.'}</p>
                <p><strong>Réponse correcte:</strong> ${question.correct_answer}</p>
            </div>
        </div>
    `;
}

function renderMCQOptions(question, index) {
    const options = question.options || [];
    
    return `
        <div class="answer-options" data-question="${index}" data-type="mcq">
            ${options.map((opt, i) => {
                const letter = String.fromCharCode(65 + i);
                const optionText = opt.replace(/^[A-D][.)]\s*/, '');
                return `
                    <label class="answer-option" data-option="${letter}">
                        <input type="radio" name="q${index}" value="${letter}">
                        <div class="answer-content">
                            <span class="answer-marker">${letter}</span>
                            <span class="answer-text">${optionText}</span>
                        </div>
                    </label>
                `;
            }).join('')}
        </div>
    `;
}

function renderTrueFalseOptions(question, index) {
    return `
        <div class="answer-options true-false-options" data-question="${index}" data-type="tf">
            <label class="answer-option tf-option" data-option="Vrai">
                <input type="radio" name="q${index}" value="Vrai">
                <div class="answer-content tf-content">
                    <i class="fas fa-check"></i>
                    <span>Vrai</span>
                </div>
            </label>
            <label class="answer-option tf-option" data-option="Faux">
                <input type="radio" name="q${index}" value="Faux">
                <div class="answer-content tf-content">
                    <i class="fas fa-times"></i>
                    <span>Faux</span>
                </div>
            </label>
        </div>
    `;
}

function renderOpenQuestion(question, index) {
    return `
        <div class="answer-options" data-question="${index}" data-type="open">
            <textarea class="open-question-input" 
                      placeholder="Écrivez votre réponse ici..."
                      data-question="${index}"></textarea>
        </div>
    `;
}

function initAnswerListeners() {
    // Radio buttons
    document.querySelectorAll('.answer-options input[type="radio"]').forEach(input => {
        input.addEventListener('change', (e) => {
            const questionIndex = e.target.closest('.answer-options').dataset.question;
            state.userAnswers[questionIndex] = e.target.value;
        });
    });
    
    // Textareas
    document.querySelectorAll('.open-question-input').forEach(textarea => {
        textarea.addEventListener('input', (e) => {
            const questionIndex = e.target.dataset.question;
            state.userAnswers[questionIndex] = e.target.value;
        });
    });
}

function checkAnswers() {
    if (!state.currentQuiz || !state.currentQuiz.questions) return;
    
    let correctCount = 0;
    const totalQuestions = state.currentQuiz.questions.length;
    
    state.currentQuiz.questions.forEach((question, index) => {
        const questionCard = document.getElementById(`question-${index}`);
        const userAnswer = state.userAnswers[index];
        const correctAnswer = question.correct_answer;
        
        // Show explanation
        const explanation = questionCard.querySelector('.question-explanation');
        explanation.style.display = 'block';
        
        // Check answer based on type
        let isCorrect = false;
        
        if (question.type === 'qcm') {
            // Extract letter from correct answer
            const correctLetter = correctAnswer?.match(/^[A-D]/)?.[0] || correctAnswer;
            isCorrect = userAnswer === correctLetter;
            
            // Highlight options
            questionCard.querySelectorAll('.answer-option').forEach(opt => {
                const optLetter = opt.dataset.option;
                if (optLetter === correctLetter) {
                    opt.classList.add('correct');
                } else if (optLetter === userAnswer && !isCorrect) {
                    opt.classList.add('incorrect');
                }
            });
        } else if (question.type === 'vrai_faux') {
            const correctValue = correctAnswer?.toLowerCase().includes('vrai') ? 'Vrai' : 'Faux';
            isCorrect = userAnswer === correctValue;
            
            questionCard.querySelectorAll('.answer-option').forEach(opt => {
                const optValue = opt.dataset.option;
                if (optValue === correctValue) {
                    opt.classList.add('correct');
                } else if (optValue === userAnswer && !isCorrect) {
                    opt.classList.add('incorrect');
                }
            });
        } else {
            // For open questions, we can't automatically check
            // Just mark as reviewed
            isCorrect = null;
        }
        
        // Update card style
        if (isCorrect === true) {
            questionCard.classList.add('correct');
            correctCount++;
        } else if (isCorrect === false) {
            questionCard.classList.add('incorrect');
        }
    });
    
    // Show results
    showResults(correctCount, totalQuestions);
}

function showResults(correct, total) {
    const resultsContainer = document.getElementById('results-container');
    const scoreEl = document.getElementById('score');
    const totalEl = document.getElementById('total');
    const scoreFill = document.getElementById('score-fill');
    const scoreMessage = document.getElementById('score-message');
    
    resultsContainer.style.display = 'block';
    scoreEl.textContent = correct;
    totalEl.textContent = total;
    
    const percentage = (correct / total) * 100;
    scoreFill.style.width = `${percentage}%`;
    
    // Set message based on score
    if (percentage >= 80) {
        scoreMessage.textContent = 'Excellent travail! 🎉';
    } else if (percentage >= 60) {
        scoreMessage.textContent = 'Bon travail! Continuez ainsi. 👍';
    } else if (percentage >= 40) {
        scoreMessage.textContent = 'Pas mal! Quelques révisions seraient utiles. 📚';
    } else {
        scoreMessage.textContent = 'N\'abandonnez pas! Révisez et réessayez. 💪';
    }
    
    // Scroll to results
    resultsContainer.scrollIntoView({ behavior: 'smooth' });
}

function exportQuiz() {
    if (!state.currentQuiz) {
        showToast('Aucun quiz à exporter', 'error');
        return;
    }
    
    const quiz = state.currentQuiz;
    let content = `# ${quiz.quiz_title || 'Quiz'}\n\n`;
    content += `Difficulté: ${getDifficultyLabel(quiz.difficulty)}\n`;
    content += `Nombre de questions: ${quiz.questions?.length || 0}\n\n`;
    content += `---\n\n`;
    
    quiz.questions?.forEach((q, i) => {
        content += `## Question ${i + 1}\n\n`;
        content += `${q.question}\n\n`;
        
        if (q.options && q.options.length > 0) {
            q.options.forEach(opt => {
                content += `${opt}\n`;
            });
            content += '\n';
        }
        
        content += `**Réponse:** ${q.correct_answer}\n\n`;
        
        if (q.explanation) {
            content += `**Explication:** ${q.explanation}\n\n`;
        }
        
        content += `---\n\n`;
    });
    
    // Download
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `quiz-${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast('Quiz exporté avec succès!', 'success');
}

// =====================================================
// Helper Functions
// =====================================================

function getDifficultyLabel(difficulty) {
    const labels = {
        'facile': 'Facile',
        'moyen': 'Moyen',
        'difficile': 'Difficile',
        'easy': 'Facile',
        'medium': 'Moyen',
        'hard': 'Difficile'
    };
    return labels[difficulty?.toLowerCase()] || difficulty || 'Moyen';
}

function getTypeLabel(type) {
    const labels = {
        'qcm': 'QCM',
        'comprehension': 'Compréhension',
        'memorisation': 'Mémorisation',
        'vrai_faux': 'Vrai/Faux',
        'reponse_courte': 'Réponse Courte',
        'multiple_choice': 'QCM',
        'true_false': 'Vrai/Faux',
        'short_answer': 'Réponse Courte'
    };
    return labels[type?.toLowerCase()] || type || 'Question';
}

// =====================================================
// Initialization
// =====================================================

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initUploadSection();
    initGenerateSection();
    initQuizSection();
    
    // Check for existing documents
    getDocumentStats().then(result => {
        if (result.success && result.data.total_chunks > 0) {
            showToast('Documents existants détectés', 'info');
        }
    }).catch(() => {});
});
