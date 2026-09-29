/**
 * StudyMate AI — Chat Page Logic
 */

let selectedDocId = null;
let conversationId = null;

async function loadDocuments() {
  try {
    const data = await apiFetch('/documents');
    const selector = document.getElementById('doc-selector');
    selector.innerHTML = '<option value="">— Select Document —</option>';
    (data.documents || []).forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.id;
      opt.textContent = d.original_filename;
      selector.appendChild(opt);
    });

    // If URL has ?doc=... preselect it
    const params = new URLSearchParams(window.location.search);
    const docId = params.get('doc');
    if (docId) {
      selector.value = docId;
      onDocChange();
    }
  } catch (err) {
    showToast('Could not load documents: ' + err.message, 'error');
  }
}

function onDocChange() {
  const selector = document.getElementById('doc-selector');
  selectedDocId = selector.value;
  conversationId = null;

  if (!selectedDocId) {
    document.getElementById('no-doc-state').style.display = 'flex';
    document.getElementById('chat-interface').style.display = 'none';
    return;
  }

  const selectedText = selector.options[selector.selectedIndex].text;
  document.getElementById('selected-doc-name').textContent = selectedText;
  document.getElementById('no-doc-state').style.display = 'none';
  document.getElementById('chat-interface').style.display = 'flex';

  // Reset chat
  document.getElementById('chat-messages').innerHTML = `
    <div class="chat-message ai">
      <div class="chat-avatar ai">🤖</div>
      <div class="chat-bubble">
        Hello! I've loaded <strong>${selectedText}</strong>. What would you like to know about it?
      </div>
    </div>`;
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const question = input.value.trim();
  if (!question || !selectedDocId) return;

  // Render user message immediately
  appendMessage('user', question);
  input.value = '';
  input.style.height = 'auto';

  // Show AI typing indicator
  const typingId = 'typing-' + Date.now();
  appendTyping(typingId);

  const btn = document.getElementById('send-btn');
  setLoading(btn, true, '…');

  try {
    const data = await apiFetch(`/documents/${selectedDocId}/chat`, {
      method: 'POST',
      body: { question, conversation_id: conversationId },
    });
    conversationId = data.conversation_id;
    removeTyping(typingId);
    appendMessage('ai', data.answer);
  } catch (err) {
    removeTyping(typingId);
    appendMessage('ai', `⚠️ Error: ${err.message}`);
  } finally {
    setLoading(btn, false);
  }
}

function appendMessage(role, content) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `chat-message ${role}`;
  div.innerHTML = `
    <div class="chat-avatar ${role}">${role === 'ai' ? '🤖' : '👤'}</div>
    <div class="chat-bubble">${content.replace(/\n/g, '<br>')}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function appendTyping(id) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-message ai';
  div.id = id;
  div.innerHTML = `
    <div class="chat-avatar ai">🤖</div>
    <div class="chat-bubble" style="display:flex;gap:4px;align-items:center;">
      <span style="animation:pulse 1s ease infinite;">●</span>
      <span style="animation:pulse 1s ease infinite 0.2s;">●</span>
      <span style="animation:pulse 1s ease infinite 0.4s;">●</span>
    </div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

// Auto-resize textarea
document.addEventListener('DOMContentLoaded', () => {
  loadDocuments();
  const input = document.getElementById('chat-input');
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });
});
