(function () {
  'use strict';

  var CHAT_API = '/chatbot/chat';
  var chatHistory = [];
  var isOpen = false;
  var isThinking = false;

  // ── Inject widget HTML ────────────────────────────────────────────────────
  var widgetHTML = [
    '<div id="arcadia-chat-widget">',
    '  <div id="arcadia-chat-panel" class="arcadia-chat-panel" style="display:none;">',
    '    <div class="arcadia-chat-header">',
    '      <div class="arcadia-chat-header-info">',
    '        <span class="arcadia-chat-dot"></span>',
    '        <div>',
    '          <div class="arcadia-chat-agent-name">Aria</div>',
    '          <div class="arcadia-chat-agent-role">Arcadia Finance Support</div>',
    '        </div>',
    '      </div>',
    '      <button class="arcadia-chat-close" id="arcadia-chat-close" aria-label="Close chat">&#10005;</button>',
    '    </div>',
    '    <div class="arcadia-chat-messages" id="arcadia-chat-messages">',
    '      <div class="arcadia-chat-message bot">',
    '        <div class="arcadia-chat-bubble">',
    "          Hi! I'm Aria, your Arcadia Finance support assistant. How can I help you today?",
    '        </div>',
    '      </div>',
    '    </div>',
    '    <div class="arcadia-chat-input-area">',
    '      <input type="text" id="arcadia-chat-input" class="arcadia-chat-input"',
    '             placeholder="Ask me anything..." autocomplete="off">',
    '      <button id="arcadia-chat-send" class="arcadia-chat-send" aria-label="Send message">',
    '        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">',
    '          <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>',
    '        </svg>',
    '      </button>',
    '    </div>',
    '  </div>',
    '  <button id="arcadia-chat-toggle" class="arcadia-chat-toggle" aria-label="Open support chat">',
    '    <svg id="arcadia-icon-chat" viewBox="0 0 24 24" width="26" height="26" fill="currentColor">',
    '      <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>',
    '    </svg>',
    '    <svg id="arcadia-icon-close" viewBox="0 0 24 24" width="22" height="22" fill="currentColor" style="display:none;">',
    '      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>',
    '    </svg>',
    '    <span id="arcadia-chat-badge" class="arcadia-chat-badge" style="display:none;">1</span>',
    '  </button>',
    '</div>'
  ].join('\n');

  function init() {
    var wrapper = document.createElement('div');
    wrapper.innerHTML = widgetHTML;
    document.body.appendChild(wrapper.firstElementChild);

    document.getElementById('arcadia-chat-toggle').addEventListener('click', toggleChat);
    document.getElementById('arcadia-chat-close').addEventListener('click', closeChat);
    document.getElementById('arcadia-chat-send').addEventListener('click', sendMessage);
    document.getElementById('arcadia-chat-input').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  // ── Panel open / close ────────────────────────────────────────────────────
  function toggleChat() {
    if (isOpen) { closeChat(); } else { openChat(); }
  }

  function openChat() {
    isOpen = true;
    document.getElementById('arcadia-chat-panel').style.display = 'flex';
    document.getElementById('arcadia-icon-chat').style.display = 'none';
    document.getElementById('arcadia-icon-close').style.display = 'block';
    document.getElementById('arcadia-chat-badge').style.display = 'none';
    document.getElementById('arcadia-chat-input').focus();
  }

  function closeChat() {
    isOpen = false;
    document.getElementById('arcadia-chat-panel').style.display = 'none';
    document.getElementById('arcadia-icon-chat').style.display = 'block';
    document.getElementById('arcadia-icon-close').style.display = 'none';
  }

  // ── Messaging ─────────────────────────────────────────────────────────────
  function sendMessage() {
    if (isThinking) return;

    var input = document.getElementById('arcadia-chat-input');
    var text = input.value.trim();
    if (!text) return;

    input.value = '';
    appendMessage('user', text);

    isThinking = true;
    var typingId = appendTyping();

    fetch(CHAT_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: chatHistory })
    })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        removeElement(typingId);
        isThinking = false;
        var reply = data.response || 'Sorry, I received an empty response.';
        appendMessage('bot', reply);
        chatHistory.push({ role: 'user', content: text });
        chatHistory.push({ role: 'assistant', content: reply });
        if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);
        if (!isOpen) showBadge();
      })
      .catch(function () {
        removeElement(typingId);
        isThinking = false;
        appendMessage(
          'bot',
          "I'm having trouble connecting right now. Please try again or call us at 888-123-2323."
        );
      });
  }

  // ── DOM helpers ───────────────────────────────────────────────────────────
  function appendMessage(role, content) {
    var messages = document.getElementById('arcadia-chat-messages');
    var div = document.createElement('div');
    div.className = 'arcadia-chat-message ' + role;
    var bubble = document.createElement('div');
    bubble.className = 'arcadia-chat-bubble';
    bubble.textContent = content;
    div.appendChild(bubble);
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function appendTyping() {
    var messages = document.getElementById('arcadia-chat-messages');
    var id = 'arcadia-typing-' + Date.now();
    var div = document.createElement('div');
    div.id = id;
    div.className = 'arcadia-chat-message bot';
    div.innerHTML =
      '<div class="arcadia-chat-bubble arcadia-typing">' +
      '<span></span><span></span><span></span>' +
      '</div>';
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return id;
  }

  function removeElement(id) {
    var el = document.getElementById(id);
    if (el) el.parentNode.removeChild(el);
  }

  function showBadge() {
    document.getElementById('arcadia-chat-badge').style.display = 'flex';
  }

  // ── Bootstrap ─────────────────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
