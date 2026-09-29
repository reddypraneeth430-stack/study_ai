/**
 * StudyMate AI — Quiz Page Logic
 */

let currentQuiz = null;
let userAnswers = {};

async function loadDocsForQuiz() {
  try {
    const data = await apiFetch('/documents');
    const sel = document.getElementById('quiz-doc-select');
    sel.innerHTML = '<option value="">— Select Document —</option>';
    (data.documents || []).forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.id;
      opt.textContent = d.original_filename;
      sel.appendChild(opt);
    });

    const params = new URLSearchParams(window.location.search);
    const docId = params.get('doc');
    if (docId) sel.value = docId;
  } catch (err) {
    showToast('Could not load documents: ' + err.message, 'error');
  }
}

async function generateQuiz() {
  const docId = document.getElementById('quiz-doc-select').value;
  const numQ = parseInt(document.getElementById('quiz-num').value);
  const difficulty = document.getElementById('quiz-difficulty').value;

  if (!docId) { showToast('Please select a document first.', 'warning'); return; }

  const btn = document.getElementById('generate-quiz-btn');
  setLoading(btn, true, 'Generating quiz…');

  try {
    const data = await apiFetch(`/documents/${docId}/quiz`, {
      method: 'POST',
      body: { num_questions: numQ, difficulty },
    });

    currentQuiz = data;
    userAnswers = {};
    showQuizPanel(data);
  } catch (err) {
    showToast('Failed to generate quiz: ' + err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
}

function showQuizPanel(quiz) {
  document.getElementById('setup-panel').style.display = 'none';
  document.getElementById('quiz-panel').style.display = 'block';
  document.getElementById('results-panel').style.display = 'none';

  document.getElementById('quiz-title').textContent = quiz.title;
  document.getElementById('quiz-progress').textContent = `${quiz.num_questions} questions`;

  const container = document.getElementById('quiz-questions-container');
  container.innerHTML = quiz.questions.map((q, i) => `
    <div class="quiz-question-card" data-question-id="${q.id}">
      <div class="quiz-question-num">Question ${i + 1}</div>
      <div class="quiz-question-text">${q.question}</div>
      ${['A','B','C','D'].map(letter => `
        <div class="quiz-option" id="opt-${q.id}-${letter}" onclick="selectAnswer('${q.id}', '${letter}')">
          <div class="quiz-option-letter">${letter}</div>
          <span>${q['option_' + letter.toLowerCase()]}</span>
        </div>`).join('')}
    </div>`).join('');

  updateAnsweredCount();
}

function selectAnswer(questionId, letter) {
  // Deselect previous
  ['A','B','C','D'].forEach(l => {
    document.getElementById(`opt-${questionId}-${l}`)?.classList.remove('selected');
  });
  // Select new
  document.getElementById(`opt-${questionId}-${letter}`)?.classList.add('selected');
  userAnswers[questionId] = letter;
  updateAnsweredCount();
}

function updateAnsweredCount() {
  const total = currentQuiz?.questions?.length || 0;
  const answered = Object.keys(userAnswers).length;
  document.getElementById('answered-count').textContent = `${answered} of ${total} answered`;
}

async function submitQuiz() {
  if (!currentQuiz) return;
  const total = currentQuiz.questions.length;
  const answered = Object.keys(userAnswers).length;

  if (answered < total) {
    if (!confirm(`You've only answered ${answered} of ${total} questions. Submit anyway?`)) return;
  }

  const btn = document.getElementById('submit-quiz-btn');
  setLoading(btn, true, 'Submitting…');

  try {
    const data = await apiFetch(`/quiz/${currentQuiz.quiz_id}/submit`, {
      method: 'POST',
      body: { answers: userAnswers },
    });
    showResults(data);
  } catch (err) {
    showToast('Submission failed: ' + err.message, 'error');
    setLoading(btn, false);
  }
}

function showResults(data) {
  document.getElementById('setup-panel').style.display = 'none';
  document.getElementById('quiz-panel').style.display = 'none';
  const panel = document.getElementById('results-panel');
  panel.style.display = 'block';

  const color = scoreColor(data.percentage);
  const emoji = data.percentage >= 80 ? '🎉' : data.percentage >= 60 ? '👍' : '📚';

  panel.innerHTML = `
    <div class="card mb-6" style="text-align:center;padding:40px;">
      <div style="font-size:3rem;margin-bottom:12px;">${emoji}</div>
      <div style="font-size:2.5rem;font-weight:800;color:${color};margin-bottom:4px;">${data.percentage}%</div>
      <div class="card-title mb-2">${data.score} / ${data.total} Correct</div>
      <div class="text-secondary text-sm">${getScoreMessage(data.percentage)}</div>
      <div class="flex gap-3 mt-6" style="justify-content:center;">
        <button class="btn btn-primary" onclick="resetQuiz()">🔄 New Quiz</button>
      </div>
    </div>

    <div class="card-title mb-4">Detailed Results</div>
    ${data.results.map((r, i) => `
      <div class="quiz-question-card mb-4">
        <div class="quiz-question-num">Question ${i + 1}</div>
        <div class="quiz-question-text">${r.question}</div>
        ${['A','B','C','D'].map(letter => {
          let cls = '';
          if (letter === r.correct_answer) cls = 'correct';
          else if (letter === r.selected && !r.is_correct) cls = 'incorrect';
          return `
            <div class="quiz-option ${cls}">
              <div class="quiz-option-letter">${letter}</div>
              <span>${r['option_' + letter.toLowerCase()]}</span>
              ${letter === r.correct_answer ? '<span style="margin-left:auto;">✓</span>' : ''}
              ${letter === r.selected && !r.is_correct ? '<span style="margin-left:auto;">✗</span>' : ''}
            </div>`;
        }).join('')}
        <div style="margin-top:12px;padding:12px;background:var(--bg-tertiary);border-radius:var(--radius-md);font-size:0.82rem;color:var(--text-secondary);">
          💡 <strong>Explanation:</strong> ${r.explanation}
        </div>
      </div>`).join('')}`;
}

function getScoreMessage(pct) {
  if (pct >= 90) return 'Excellent! Outstanding performance!';
  if (pct >= 80) return 'Great job! You have a strong grasp of the material.';
  if (pct >= 70) return 'Good work! Keep studying to improve further.';
  if (pct >= 60) return 'Fair attempt. Review the explanations to reinforce your knowledge.';
  return 'Keep studying! Review the material and try again.';
}

function resetQuiz() {
  currentQuiz = null;
  userAnswers = {};
  document.getElementById('setup-panel').style.display = 'block';
  document.getElementById('quiz-panel').style.display = 'none';
  document.getElementById('results-panel').style.display = 'none';
}

document.addEventListener('DOMContentLoaded', loadDocsForQuiz);
