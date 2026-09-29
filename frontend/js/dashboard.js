/**
 * StudyMate AI — Dashboard Page Logic
 */

let scoreChart = null;

async function loadDashboard() {
  try {
    const data = await apiFetch('/dashboard/stats');
    renderStats(data.stats);
    renderRecentDocs(data.recent_documents);
    renderRecentResults(data.recent_quiz_results);
    renderScoreChart(data.score_history);
  } catch (err) {
    showToast('Failed to load dashboard: ' + err.message, 'error');
    document.getElementById('recent-docs').innerHTML =
      '<div class="text-muted text-sm" style="padding:16px;">Could not load data.</div>';
    document.getElementById('recent-results').innerHTML =
      '<div class="text-muted text-sm" style="padding:16px;">Could not load data.</div>';
  }
}

function renderStats(stats) {
  document.getElementById('stat-docs').textContent = stats.documents_uploaded ?? 0;
  document.getElementById('stat-quizzes').textContent = stats.quizzes_completed ?? 0;
  document.getElementById('stat-avg-score').textContent =
    stats.average_quiz_score > 0 ? `${stats.average_quiz_score}%` : '—';
  document.getElementById('stat-plans').textContent = stats.study_plans_created ?? 0;
}

function renderRecentDocs(docs) {
  const el = document.getElementById('recent-docs');
  if (!docs || docs.length === 0) {
    el.innerHTML = `
      <div class="empty-state" style="padding:24px;">
        <div class="empty-icon" style="font-size:2rem;">📂</div>
        <div class="empty-title" style="font-size:0.9rem;">No documents yet</div>
        <div class="empty-subtitle">Upload your first study material</div>
        <a href="/upload.html" class="btn btn-primary btn-sm mt-4">Upload Now</a>
      </div>`;
    return;
  }

  el.innerHTML = docs.map(d => `
    <div class="flex items-center gap-3" style="padding:10px 0;border-bottom:1px solid var(--border-subtle);">
      <span style="font-size:1.4rem;">${fileTypeIcon(d.file_type)}</span>
      <div style="flex:1;min-width:0;">
        <div class="font-semibold text-sm" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
          ${d.original_filename}
        </div>
        <div class="text-xs text-muted">${formatDate(d.created_at)}</div>
      </div>
      <span class="badge badge-indigo">${d.file_type.toUpperCase()}</span>
    </div>`).join('');
}

function renderRecentResults(results) {
  const el = document.getElementById('recent-results');
  if (!results || results.length === 0) {
    el.innerHTML = `
      <div class="empty-state" style="padding:24px;">
        <div class="empty-icon" style="font-size:2rem;">🧪</div>
        <div class="empty-title" style="font-size:0.9rem;">No quizzes taken yet</div>
        <div class="empty-subtitle">Take a quiz to see results here</div>
        <a href="/quiz.html" class="btn btn-primary btn-sm mt-4">Take Quiz</a>
      </div>`;
    return;
  }

  el.innerHTML = `
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Score</th>
            <th>Percentage</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          ${results.map(r => `
            <tr>
              <td>${r.score} / ${r.total}</td>
              <td>
                <div class="flex items-center gap-2">
                  <div class="progress-bar" style="width:80px;">
                    <div class="progress-fill" style="width:${r.percentage}%;background:${scoreColor(r.percentage)};"></div>
                  </div>
                  <span style="color:${scoreColor(r.percentage)};font-weight:600;">${r.percentage}%</span>
                </div>
              </td>
              <td class="text-muted">${formatDateTime(r.completed_at)}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
}

function renderScoreChart(scores) {
  const canvas = document.getElementById('scoreChart');
  const emptyEl = document.getElementById('chart-empty');

  if (!scores || scores.length === 0) {
    canvas.style.display = 'none';
    emptyEl.style.display = 'block';
    return;
  }

  const labels = scores.map((_, i) => `Quiz ${i + 1}`);

  if (scoreChart) scoreChart.destroy();

  scoreChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Score (%)',
        data: scores,
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99,102,241,0.1)',
        borderWidth: 2,
        tension: 0.4,
        fill: true,
        pointBackgroundColor: '#6366f1',
        pointRadius: 4,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#64748b', font: { size: 11 } },
        },
        y: {
          min: 0, max: 100,
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#64748b', font: { size: 11 }, callback: v => v + '%' },
        }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', loadDashboard);
