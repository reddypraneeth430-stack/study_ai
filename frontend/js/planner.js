/**
 * StudyMate AI — Study Planner Page Logic
 */

async function generatePlan() {
  const subjectsRaw = document.getElementById('subjects-input').value.trim();
  const topicsRaw = document.getElementById('topics-input').value.trim();
  const examDate = document.getElementById('exam-date').value;
  const hoursPerDay = parseFloat(document.getElementById('hours-per-day').value);
  const sessionDuration = parseInt(document.getElementById('session-duration').value);

  if (!subjectsRaw) { showToast('Please enter at least one subject.', 'warning'); return; }
  if (!topicsRaw) { showToast('Please enter at least one topic.', 'warning'); return; }
  if (!examDate) { showToast('Please select an exam date.', 'warning'); return; }

  const today = new Date().toISOString().split('T')[0];
  if (examDate <= today) { showToast('Exam date must be in the future.', 'warning'); return; }

  const subjects = subjectsRaw.split(',').map(s => s.trim()).filter(Boolean);
  const topics = topicsRaw.split(',').map(t => t.trim()).filter(Boolean);

  const btn = document.getElementById('generate-plan-btn');
  setLoading(btn, true, 'Generating plan…');

  try {
    const data = await apiFetch('/planner/generate', {
      method: 'POST',
      body: {
        subjects,
        topics,
        exam_date: examDate,
        available_hours_per_day: hoursPerDay,
        preferred_session_duration: sessionDuration,
      }
    });
    renderPlan(data);
  } catch (err) {
    showToast('Error: ' + err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
}

function renderPlan(data) {
  document.getElementById('planner-form').style.display = 'none';
  const panel = document.getElementById('plan-output');
  panel.style.display = 'block';

  const plan = data.plan;
  const daily = plan.daily_schedule || [];
  const tips = plan.study_tips || [];
  const milestones = plan.milestones || [];

  panel.innerHTML = `
    <div class="flex justify-between items-center mb-4">
      <div>
        <div class="card-title">${data.title}</div>
        <div class="text-muted text-sm">Exam: ${data.exam_date}</div>
      </div>
      <button class="btn btn-ghost btn-sm" onclick="resetPlan()">← New Plan</button>
    </div>

    ${plan.overview ? `
      <div class="card mb-4" style="border-left:3px solid var(--accent-primary);">
        <div class="font-semibold mb-2">📌 Plan Overview</div>
        <p style="color:var(--text-secondary);line-height:1.7;">${plan.overview}</p>
      </div>` : ''}

    ${daily.length ? `
      <div class="card-title mb-3">📆 Daily Schedule</div>
      ${daily.map(day => `
        <div class="card mb-4">
          <div class="flex justify-between items-center mb-3">
            <div class="font-semibold">${day.date_label || 'Day ' + day.day}</div>
            <span class="badge badge-indigo">${day.total_hours || ''} hrs</span>
          </div>
          ${(day.sessions || []).map(s => `
            <div class="flex items-center gap-3 mb-2" style="padding:8px 12px;background:var(--bg-tertiary);border-radius:var(--radius-md);">
              <span class="badge badge-teal">${s.duration_minutes}m</span>
              <div>
                <div class="text-sm font-semibold">${s.subject}</div>
                <div class="text-xs text-muted">${s.topic} — ${s.activity}</div>
              </div>
            </div>`).join('')}
        </div>`).join('')}` : ''}

    ${tips.length ? `
      <div class="card mb-4">
        <div class="card-title mb-3">💡 Study Tips</div>
        ${tips.map(t => `
          <div class="flex gap-2 mb-2" style="color:var(--text-secondary);font-size:0.875rem;">
            <span style="color:var(--accent-primary);">▸</span>
            <span>${t}</span>
          </div>`).join('')}
      </div>` : ''}

    ${milestones.length ? `
      <div class="card">
        <div class="card-title mb-3">🏁 Milestones</div>
        ${milestones.map((m, i) => `
          <div class="flex gap-3 items-start mb-3">
            <div style="width:24px;height:24px;border-radius:50%;background:var(--gradient-primary);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0;">${i+1}</div>
            <div style="color:var(--text-secondary);font-size:0.875rem;line-height:1.6;">${typeof m === 'string' ? m : JSON.stringify(m)}</div>
          </div>`).join('')}
      </div>` : ''}`;
}

function resetPlan() {
  document.getElementById('planner-form').style.display = 'block';
  document.getElementById('plan-output').style.display = 'none';
}

// Set min date to tomorrow
document.addEventListener('DOMContentLoaded', () => {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  document.getElementById('exam-date').min = tomorrow.toISOString().split('T')[0];
});
