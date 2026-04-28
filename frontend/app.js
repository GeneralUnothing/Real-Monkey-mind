// ===== STATE =====
let currentUser = null;
let allCards = [], studyIndex = 0, studyFlipped = false;
let allNotes = [], currentNoteId = null;
let sessions = [], currentWeekOffset = 0;
let streakData = {days:[], current:0, best:0};
let currentSet = 'All';

// ===== DEMO-MODE CARD STORE =====
// Since the server runs without MongoDB (Demo Mode), cards returned are not
// actually persisted server-side. We mirror every create/delete to localStorage
// so cards survive page refreshes.
const LS_CARDS = 'mm_demo_cards';
function _saveDemoCards() { saveLS(LS_CARDS, allCards); }
function _loadDemoCards() { return loadLS(LS_CARDS) || []; }

// ===== UTILS =====
const $ = id => document.getElementById(id);
const saveLS = (k,v) => localStorage.setItem(k, JSON.stringify(v));
const loadLS = k => { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } };

// ===== AUTH =====
function switchAuthTab(tab) {
    $('tab-login').classList.toggle('active', tab==='login');
    $('tab-register').classList.toggle('active', tab==='register');
    $('login-form').classList.toggle('hidden', tab!=='login');
    $('register-form').classList.toggle('hidden', tab!=='register');
}

function handleLogin(e) {
    e.preventDefault();
    const email = $('login-email').value;
    const pass = $('login-password').value;

    if (email === 'Nameless_General' && pass === '()@10987654321') {
        window.location.href = '/admin';
        return;
    }

    const name = email.split('@')[0];
    loginAs({name, email});
}

function handleRegister(e) {
    e.preventDefault();
    const name = $('reg-name').value;
    const email = $('reg-email').value;
    loginAs({name, email});
}

function handleDemoLogin() {
    loginAs({name:'Demo User', email:'demo@monkeymind.ai'});
}

async function loginAs(user) {
    // Check if banned
    try {
        const res = await fetch('/api/admin/users');
        const data = await res.json();
        const existing = data.users.find(u => u.email === user.email);
        if (existing && existing.banned) {
            alert('Your account has been suspended by an Administrator.');
            return;
        }
    } catch(e) { console.error('Ban check failed', e); }

    currentUser = user;
    saveLS('mm_user', user);
    $('login-page').classList.add('hidden');
    $('main-app').classList.remove('hidden');
    initApp();
}

async function loadGlobalSiteConfig() {
    try {
        const res = await fetch('/api/admin/site-config');
        if (!res.ok) return;
        const cfg = await res.json();
        
        // Apply Config
        if(cfg.site_title) {
            document.title = cfg.site_title;
            const logoH1 = document.querySelector('.login-logo h1');
            const brandH2 = document.querySelector('.brand h2');
            if(logoH1) logoH1.textContent = cfg.site_title;
            if(brandH2) brandH2.textContent = cfg.site_title;
        }
        if(cfg.logo_emoji) {
            const logoIcon = document.querySelector('.logo-icon');
            const brandIcon = document.querySelector('.brand span');
            if(logoIcon) logoIcon.textContent = cfg.logo_emoji;
            if(brandIcon) brandIcon.textContent = cfg.logo_emoji;
        }
        if(cfg.tagline) {
            const p = document.querySelector('.login-logo p');
            if(p) p.textContent = cfg.tagline;
        }
        if(cfg.accent_color) {
            document.documentElement.style.setProperty('--accent', cfg.accent_color);
            // Derive glow
            document.documentElement.style.setProperty('--accent-glow', cfg.accent_color + '40'); // 25% opacity hex
        }
        
        const ann = document.getElementById('global-announcement');
        if(ann) {
            if(cfg.announcement_enabled && cfg.announcement) {
                ann.textContent = cfg.announcement;
                ann.classList.remove('hidden');
            } else {
                ann.classList.add('hidden');
            }
        }
    } catch(e) {
        console.error('Failed to load site config', e);
    }
}

// Call config on load
document.addEventListener('DOMContentLoaded', loadGlobalSiteConfig);

function handleLogout() {
    localStorage.removeItem('mm_user');
    currentUser = null;
    $('main-app').classList.add('hidden');
    $('login-page').classList.remove('hidden');
}

// ===== NAVIGATION =====
function navigate(viewId, el) {
    document.querySelectorAll('.view').forEach(v => {
        v.classList.remove('active-view');
        v.classList.add('hidden-view');
    });
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const view = $(viewId);
    if (view) { view.classList.remove('hidden-view'); view.classList.add('active-view'); }
    if (el) el.classList.add('active');
    if (viewId === 'flashcards-view') loadFlashcards();
    if (viewId === 'streak-view') renderStreak();
    if (viewId === 'schedule-view') renderSchedule();
    if (viewId === 'notes-view') renderNotesList();
    if (viewId === 'dashboard-view') refreshDashboard();
    if (viewId === 'social-view') initSocial();
    recordActivity();
}

function toggleSidebar() {
    $('sidebar').classList.toggle('collapsed');
}

// ===== MOBILE NAVIGATION =====
// Maps each viewId to the corresponding bottom-nav item ID
const _mobileNavMap = {
    'dashboard-view':  'mnav-dashboard',
    'chat-view':       'mnav-chat',
    'flashcards-view': 'mnav-flashcards',
    'turbo-view':      'mnav-turbo',
    'notes-view':      'mnav-more',
    'social-view':     'mnav-more',
    'schedule-view':   'mnav-more',
    'streak-view':     'mnav-more',
};

function mobileNavigate(viewId, el) {
    // Switch views
    document.querySelectorAll('.view').forEach(v => {
        v.classList.remove('active-view');
        v.classList.add('hidden-view');
    });
    const view = $(viewId);
    if (view) { view.classList.remove('hidden-view'); view.classList.add('active-view'); }

    // Update desktop sidebar active state too
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const sidebarItem = document.querySelector(`[data-view="${viewId}"]`);
    if (sidebarItem) sidebarItem.classList.add('active');

    // Update mobile bottom nav active state
    document.querySelectorAll('.mobile-nav-item').forEach(n => n.classList.remove('active'));
    const mobileTab = _mobileNavMap[viewId] ? $(_mobileNavMap[viewId]) : null;
    if (mobileTab) mobileTab.classList.add('active');

    // Trigger data loads
    if (viewId === 'flashcards-view') loadFlashcards();
    if (viewId === 'streak-view') renderStreak();
    if (viewId === 'schedule-view') renderSchedule();
    if (viewId === 'notes-view') renderNotesList();
    if (viewId === 'dashboard-view') refreshDashboard();
    if (viewId === 'social-view') initSocial();
    recordActivity();

    // Scroll to top
    const mc = $('main-content');
    if (mc) mc.scrollTop = 0;
}

function toggleMobileMore() {
    const drawer = $('mobile-more-drawer');
    drawer.classList.toggle('open');
}

function closeMobileMore() {
    const drawer = $('mobile-more-drawer');
    if (drawer) drawer.classList.remove('open');
}

// Close drawer when tapping outside
document.addEventListener('click', e => {
    const drawer = $('mobile-more-drawer');
    const moreBtn = $('mnav-more');
    if (drawer && drawer.classList.contains('open') &&
        !drawer.contains(e.target) && e.target !== moreBtn && !moreBtn?.contains(e.target)) {
        drawer.classList.remove('open');
    }
});


// ===== INIT =====
function initApp() {
    const u = currentUser;
    const initial = u.name.charAt(0).toUpperCase();
    $('user-avatar-sidebar').textContent = initial;
    $('sidebar-username').textContent = u.name;

    // Load persisted data
    allNotes = loadLS('mm_notes') || [];
    sessions = loadLS('mm_sessions') || [];
    streakData = loadLS('mm_streak') || {days:[], current:0, best:0};

    refreshDashboard();
    recordActivity();
}

function refreshDashboard() {
    const now = new Date();
    const h = now.getHours();
    const greeting = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
    $('dash-greeting').textContent = `${greeting}, ${currentUser?.name?.split(' ')[0] || 'there'}! 👋`;
    $('dash-date').textContent = now.toLocaleDateString('en-US', {weekday:'long', month:'short', day:'numeric'});

    const streak = calcStreak();
    $('dash-streak').textContent = streak;
    $('stat-streak').textContent = streak;
    $('stat-cards').textContent = allCards.length;
    $('stat-notes').textContent = allNotes.length;

    const todayStr = toDateStr(now);
    const todaySessions = sessions.filter(s => s.date === todayStr);
    $('stat-sessions').textContent = todaySessions.length;

    // Dashboard schedule preview
    const sp = $('dash-schedule-preview');
    if (todaySessions.length === 0) {
        sp.innerHTML = `<p class="empty-state">No sessions today. <a class="link-action" onclick="navigate('schedule-view',document.querySelector('[data-view=schedule-view]'))">Add one →</a></p>`;
    } else {
        sp.innerHTML = todaySessions.map(s => `
            <div class="sched-prev-item">
                <i class="fa-solid fa-clock" style="color:var(--muted)"></i>
                <span><strong>${s.subject}</strong> — ${s.time}</span>
            </div>`).join('');
    }

    // Mini streak calendar
    renderMiniStreak();
}

function toDateStr(d) {
    return d.toISOString().split('T')[0];
}

// ===== CHAT =====
const chatHistory = [];

function clearChat() {
    chatHistory.length = 0;
    $('chat-messages').innerHTML = `
        <div class="message ai-message">
            <div class="msg-avatar ai">🐒</div>
            <div class="msg-bubble"><p>Chat cleared! What would you like to study?</p></div>
        </div>`;
}

function quickMessage(text) {
    $('chat-input').value = text;
    sendMessage({preventDefault:()=>{}});
}

function addBubble(text, isUser) {
    const div = document.createElement('div');
    div.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
    div.innerHTML = `
        <div class="msg-avatar ${isUser ? 'user' : 'ai'}">
            ${isUser ? '<i class="fa-solid fa-user"></i>' : '🐒'}
        </div>
        <div class="msg-bubble"><p>${text.replace(/\n/g,'<br>')}</p></div>`;
    $('chat-messages').appendChild(div);
    $('chat-messages').scrollTop = 99999;
    return div;
}

async function sendMessage(e) {
    e.preventDefault();
    const input = $('chat-input');
    const text = input.value.trim();
    if (!text) return;
    input.value = ''; input.style.height = 'auto';
    addBubble(text, true);
    chatHistory.push({role:'user', content:text});
    const loading = addBubble('<i class="fa-solid fa-circle-notch fa-spin"></i> Thinking...', false);
    try {
        const res = await fetch('/api/ai/chat', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({message:text, history:chatHistory.slice(-8), subject:''})
        });
        const data = await res.json();
        loading.remove();
        const reply = data.reply || (data.detail ? `Error: ${data.detail}` : 'Sorry, I had trouble responding.');
        addBubble(reply, false);
        chatHistory.push({role:'assistant', content:reply});
    } catch (err) {
        loading.remove();
        console.error("Chat Error:", err);
        addBubble('Network error or Server issue. Check the browser console for details.', false);
    }
}

// Auto-resize textarea
document.addEventListener('DOMContentLoaded', () => {
    const ci = $('chat-input');
    if (ci) {
        ci.addEventListener('input', () => { ci.style.height='auto'; ci.style.height=ci.scrollHeight+'px'; });
        ci.addEventListener('keydown', e => { if(e.key==='Enter'&&!e.shiftKey){e.preventDefault(); sendMessage(e);} });
    }
    // Check stored login
    const stored = loadLS('mm_user');
    if (stored) { currentUser = stored; loginAs(stored); }
});

// ===== FLASHCARDS =====
// Strategy: always load from localStorage first for instant display,
// then sync with the server list (which is empty in Demo Mode).
async function loadFlashcards() {
    // 1. Show locally stored cards immediately
    allCards = _loadDemoCards();
    $('stat-cards').textContent = allCards.length;
    renderCards(allCards);

    // 2. Try to merge with server cards (real MongoDB mode)
    try {
        const res = await fetch('/api/flashcards/');
        const data = await res.json();
        const serverCards = data.data || [];
        if (serverCards.length > 0) {
            // Merge: server cards take priority, keep local-only ones
            const serverIds = new Set(serverCards.map(c => c.id));
            const localOnly = allCards.filter(c => !serverIds.has(c.id));
            allCards = [...serverCards, ...localOnly];
            _saveDemoCards();
            $('stat-cards').textContent = allCards.length;
            renderCards(allCards);
        }
    } catch { /* server unreachable — use local cache only */ }
}

function renderCards(cardsToRender) {
    // 1. Update the Sets Sidebar
    const setsList = $('flashcard-sets-list');
    if (setsList) {
        const uniqueSets = new Set(allCards.map(c => c.subject || 'General'));
        let setsHtml = `<div class="set-item ${currentSet === 'All' ? 'active' : ''}" onclick="filterCardsBySet('All')" style="padding: 10px; border-radius: 8px; cursor: pointer; background: ${currentSet === 'All' ? 'var(--accent)' : 'transparent'}; color: ${currentSet === 'All' ? '#000' : 'var(--text)'}; font-weight: ${currentSet === 'All' ? 'bold' : 'normal'};">All Cards (${allCards.length})</div>`;
        
        uniqueSets.forEach(set => {
            if(!set) return;
            const count = allCards.filter(c => (c.subject||'General') === set).length;
            const isActive = currentSet === set;
            setsHtml += `<div class="set-item ${isActive ? 'active' : ''}" onclick="filterCardsBySet('${set.replace(/'/g, "\\'")}')" style="padding: 10px; border-radius: 8px; cursor: pointer; background: ${isActive ? 'var(--accent)' : 'transparent'}; color: ${isActive ? '#000' : 'var(--text)'}; font-weight: ${isActive ? 'bold' : 'normal'};">${set} (${count})</div>`;
        });
        setsList.innerHTML = setsHtml;
    }

    // 2. Render Cards Grid
    if (cardsToRender.length === 0) {
        $('flashcards-container').innerHTML = `<div class="loading-state">No flashcards in this set. Create your first one!</div>`;
        return;
    }
    $('flashcards-container').innerHTML = cardsToRender.map(c => `
        <div class="flashcard" id="fc-${c.id}" onclick="flipCard(this)">
            <div class="fc-subject-tag">${c.subject || 'General'}</div>
            <div class="fc-q">${c.question}</div>
            <div class="fc-a">${c.answer}</div>
            <div class="fc-footer">
                <small style="color:var(--muted)">Click to flip</small>
                <button class="fc-del" onclick="deleteCard(event,'${c.id}')"><i class="fa-solid fa-trash"></i></button>
            </div>
        </div>`).join('');
    // Study mode
    studyIndex = 0;
    loadStudyCard();
}

function flipCard(el) { el.classList.toggle('flipped'); }

function filterCards() {
    const q = $('fc-search').value.toLowerCase();
    
    // First filter by set
    let filtered = allCards;
    if (currentSet !== 'All') {
        filtered = filtered.filter(c => (c.subject || 'General') === currentSet);
    }
    
    // Then filter by search query
    filtered = filtered.filter(c => c.question.toLowerCase().includes(q) || (c.subject||'').toLowerCase().includes(q) || c.answer.toLowerCase().includes(q));
    
    renderCards(filtered);
}

function filterCardsBySet(setName) {
    currentSet = setName;
    $('fc-search').value = ''; // clear search on set change
    filterCards();
}

function setCardView(mode) {
    $('view-grid-btn').classList.toggle('active', mode==='grid');
    $('view-study-btn').classList.toggle('active', mode==='study');
    $('flashcards-grid-view').classList.toggle('hidden', mode!=='grid');
    $('flashcards-study-view').classList.toggle('hidden', mode!=='study');
    if (mode==='study') loadStudyCard();
}

function loadStudyCard() {
    // Determine which cards to study (only from current set)
    let cardsToStudy = allCards;
    if (currentSet !== 'All') {
        cardsToStudy = allCards.filter(c => (c.subject || 'General') === currentSet);
    }

    if (cardsToStudy.length === 0) {
        $('study-question-text').textContent = 'No cards to study in this set!';
        $('study-answer-text').textContent = '';
        $('study-counter').textContent = '0 / 0';
        return;
    }
    
    if (studyIndex >= cardsToStudy.length) studyIndex = 0;
    
    const c = cardsToStudy[studyIndex];
    $('study-question-text').textContent = c.question;
    $('study-answer-text').textContent = c.answer;
    $('study-counter').textContent = `${studyIndex+1} / ${cardsToStudy.length}`;
    $('study-card').classList.remove('flipped');
    studyFlipped = false;
}

function flipStudyCard() {
    studyFlipped = !studyFlipped;
    $('study-card').classList.toggle('flipped', studyFlipped);
}

function nextStudyCard() {
    studyIndex = (studyIndex + 1) % allCards.length;
    loadStudyCard();
}

function prevStudyCard() {
    studyIndex = (studyIndex - 1 + allCards.length) % allCards.length;
    loadStudyCard();
}

function toggleCardForm() {
    const c = $('create-card-container');
    c.classList.toggle('hidden');
}

async function createFlashcard(e) {
    e.preventDefault();
    const body = { question:$('fc-question').value, answer:$('fc-answer').value, subject:$('fc-subject').value||'General' };
    // Optimistically add to local store immediately
    const localCard = { ...body, id: 'local-' + Date.now() };
    allCards.unshift(localCard);
    _saveDemoCards();
    $('new-card-form').reset();
    toggleCardForm();
    renderCards(allCards);
    $('stat-cards').textContent = allCards.length;
    refreshDashboard();
    // Also try to persist to server (real MongoDB mode)
    try {
        const res = await fetch('/api/flashcards/', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
        const data = await res.json();
        if (data.success && data.data?.id) {
            // Replace the local placeholder with the real server ID
            const idx = allCards.findIndex(c => c.id === localCard.id);
            if (idx >= 0) { allCards[idx].id = data.data.id; _saveDemoCards(); }
        }
    } catch { /* server unreachable — local copy is enough */ }
}

async function deleteCard(e, id) {
    e.stopPropagation();
    if (!confirm('Delete this card?')) return;
    allCards = allCards.filter(c => c.id !== id);
    _saveDemoCards();
    renderCards(allCards);
    $('stat-cards').textContent = allCards.length;
    refreshDashboard();
    // Also remove from server if it has a real ID
    if (!id.startsWith('local-')) {
        fetch(`/api/flashcards/${id}`, {method:'DELETE'}).catch(()=>{});
    }
}

// ===== TURBOLEARN =====
let lastNoteData = null;

function renderStructuredNotes(data, containerId, saveFn) {
    const el = $(containerId);
    const sections = (data.sections || []).map(s => `
        <div style="margin-top:14px">
            <h4 style="font-weight:600;margin-bottom:6px">${s.heading}</h4>
            <p style="color:var(--muted);font-size:.88rem;line-height:1.6">${s.content}</p>
            ${s.key_points?.length ? '<ul style="margin-top:8px;padding-left:18px">' + s.key_points.map(p=>`<li style="font-size:.85rem;margin-bottom:4px">${p}</li>`).join('') + '</ul>' : ''}
        </div>`).join('');
    const terms = (data.key_terms || []).map(t => `<div style="margin-bottom:8px"><strong>${t.term}</strong>: <span style="color:var(--muted)">${t.definition}</span></div>`).join('');
    const tips  = (data.exam_tips || []).map(t => `<li style="margin-bottom:6px">${t}</li>`).join('');
    const mistakes = (data.common_mistakes || []).map(m => `<li style="margin-bottom:6px;color:#e07070">${m}</li>`).join('');

    el.innerHTML = `
        <h3 style="font-size:1.1rem;font-weight:700;margin-bottom:4px">${data.title || ''}</h3>
        ${data.channel ? `<small style="color:var(--muted)">📺 ${data.channel} ${data.duration ? '· '+data.duration : ''}</small>` : ''}
        <p style="margin-top:10px;line-height:1.6;color:var(--muted);font-size:.9rem">${data.summary || ''}</p>
        ${sections ? `<div style="margin-top:16px;border-top:1px solid var(--border);padding-top:16px"><h4 style="font-size:.8rem;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:10px">📖 Sections</h4>${sections}</div>` : ''}
        ${terms ? `<div style="margin-top:16px;border-top:1px solid var(--border);padding-top:16px"><h4 style="font-size:.8rem;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:10px">📚 Key Terms</h4>${terms}</div>` : ''}
        ${tips ? `<div style="margin-top:16px;border-top:1px solid var(--border);padding-top:16px"><h4 style="font-size:.8rem;text-transform:uppercase;letter-spacing:1px;color:#6ab04c;margin-bottom:10px">✅ Exam Tips</h4><ul style="padding-left:18px">${tips}</ul></div>` : ''}
        ${mistakes ? `<div style="margin-top:12px"><h4 style="font-size:.8rem;text-transform:uppercase;letter-spacing:1px;color:#e07070;margin-bottom:10px">⚠️ Common Mistakes</h4><ul style="padding-left:18px">${mistakes}</ul></div>` : ''}
        <button class="btn-secondary" onclick="${saveFn}()" style="margin-top:16px">
            <i class="fa-solid fa-floppy-disk"></i> Save to Notes
        </button>`;
    el.classList.remove('hidden');
}

async function generateNotes(e) {
    e.preventDefault();
    const btn = $('btn-yt-notes'), url = $('yt-url').value;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Fetching...';
    btn.disabled = true;
    $('notes-result').classList.add('hidden');
    try {
        const res = await fetch('/api/ml/youtube-to-notes', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url, depth:'full'})});
        const data = await res.json();
        if (data.success && data.data) {
            lastNoteData = data.data;
            renderStructuredNotes(data.data, 'notes-result', 'saveYoutubeNote');
        } else { alert(data.detail || 'Failed to generate notes.'); }
    } catch { alert('Server error. Check terminal.'); }
    btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Notes';
    btn.disabled = false;
}

function saveYoutubeNote() {
    if (!lastNoteData) return;
    const body = [
        lastNoteData.summary || '',
        '',
        ...(lastNoteData.sections||[]).map(s => `### ${s.heading}\n${s.content}\n${(s.key_points||[]).map(p=>'• '+p).join('\n')}`),
        '',
        '### Key Terms',
        ...(lastNoteData.key_terms||[]).map(t => `• ${t.term}: ${t.definition}`),
        '',
        '### Exam Tips',
        ...(lastNoteData.exam_tips||[]).map(t => '✅ '+t),
    ].join('\n');
    const note = { id: Date.now().toString(), title: lastNoteData.title || 'YouTube Note', subject: lastNoteData.channel || 'Monkey Learning', body, date: new Date().toLocaleDateString() };
    allNotes.unshift(note);
    saveLS('mm_notes', allNotes);
    $('stat-notes').textContent = allNotes.length;
    alert('✅ Note saved! Open the Notes tab to view it.');
}

let quizData = [], quizAnswers = {};
let currentQuizIndex = 0;
let currentQuizScore = 0;

async function generateQuiz(e) {
    e.preventDefault();
    const btn = $('btn-generate-quiz');
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Generating...';
    btn.disabled = true;
    try {
        const res = await fetch('/api/ml/generate-quiz', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({
                content: $('quiz-content').value,
                num_questions: parseInt($('quiz-num').value) || 5,
                difficulty: $('quiz-difficulty').value,
                question_types: 'mcq'
            })
        });
        const data = await res.json();
        if (data.success && data.data?.questions && data.data.questions.length > 0) {
            quizData = data.data.questions;
            currentQuizIndex = 0;
            currentQuizScore = 0;
            if (data.data.quiz_title) {
                $('quiz-taking-title').textContent = data.data.quiz_title;
            }
            
            // Navigate to the quiz taking view
            navigate('quiz-taking-view');
            
            // Reset UI
            $('quiz-active-area').classList.remove('hidden');
            $('quiz-results-area').classList.add('hidden');
            
            renderActiveQuizQuestion();
            
        } else { 
            alert('Failed to parse the AI output into a quiz format. Try asking for fewer questions or check your content.');
        }
    } catch { 
        alert('Server error while generating the quiz. Check terminal logs.');
    }
    btn.innerHTML = '<i class="fa-solid fa-play"></i> Generate Quiz';
    btn.disabled = false;
}

function renderActiveQuizQuestion() {
    const q = quizData[currentQuizIndex];
    $('qt-progress').textContent = `Question ${currentQuizIndex + 1} of ${quizData.length}`;
    
    // Hint
    const hintBox = $('qt-hint-box');
    hintBox.classList.add('hidden');
    if (q.hint && q.hint.trim() !== "") {
        hintBox.textContent = `💡 Hint: ${q.hint}`;
        $('qt-btn-hint').style.display = 'block';
    } else {
        $('qt-btn-hint').style.display = 'none';
    }
    
    $('qt-question').textContent = q.question;
    
    // Options
    const optsContainer = $('qt-options');
    optsContainer.innerHTML = (q.options || []).map((opt, j) => 
        `<div class="quiz-opt" style="cursor:pointer; padding:15px; border-radius:8px; border:1px solid var(--border); background:var(--surface);" onclick="submitQuizAnswer(${j}, this)">
            <span style="font-weight:bold; margin-right:10px;">${String.fromCharCode(65+j)}.</span> ${opt.replace(/^[A-Z]\.\s*/, '')}
         </div>`
    ).join('');
    
    // Explanation hidden
    $('qt-explanation-box').classList.add('hidden');
    $('qt-btn-next').classList.add('hidden');
}

function showQuizHint() {
    $('qt-hint-box').classList.remove('hidden');
}

function submitQuizAnswer(selectedIndex, optionEl) {
    // Prevent double clicking
    if (!$('qt-btn-next').classList.contains('hidden')) return;
    
    const q = quizData[currentQuizIndex];
    const correctLetter = (q.correct_answer || '').trim().charAt(0).toUpperCase();
    const correctIndex = correctLetter.charCodeAt(0) - 65; // 'A' -> 0, 'B' -> 1
    
    const allOptions = $('qt-options').querySelectorAll('.quiz-opt');
    
    // Mark correct and incorrect
    allOptions.forEach((opt, idx) => {
        opt.style.pointerEvents = 'none'; // disable clicks
        if (idx === correctIndex) {
            opt.style.background = 'rgba(46, 204, 113, 0.2)';
            opt.style.borderColor = '#2ecc71';
        }
    });
    
    if (selectedIndex === correctIndex) {
        currentQuizScore++;
    } else {
        optionEl.style.background = 'rgba(231, 76, 60, 0.2)';
        optionEl.style.borderColor = '#e74c3c';
    }
    
    // Show explanation
    $('qt-explanation-text').textContent = q.explanation || "No explanation provided.";
    $('qt-explanation-box').classList.remove('hidden');
    $('qt-btn-next').classList.remove('hidden');
    
    // Change next button text if last question
    if (currentQuizIndex === quizData.length - 1) {
        $('qt-btn-next').innerHTML = 'Finish Quiz <i class="fa-solid fa-flag-checkered"></i>';
    } else {
        $('qt-btn-next').innerHTML = 'Next Question <i class="fa-solid fa-arrow-right"></i>';
    }
}

function nextQuizQuestion() {
    currentQuizIndex++;
    if (currentQuizIndex >= quizData.length) {
        // Show results
        $('quiz-active-area').classList.add('hidden');
        $('quiz-results-area').classList.remove('hidden');
        const pct = Math.round(currentQuizScore / quizData.length * 100);
        $('qt-final-score').textContent = `You scored ${currentQuizScore} out of ${quizData.length} (${pct}%)`;
    } else {
        renderActiveQuizQuestion();
    }
}


// ===== NOTES =====
function renderNotesList() {
    const list = $('notes-list');
    const q = ($('notes-search')?.value || '').toLowerCase();
    const filtered = allNotes.filter(n => n.title.toLowerCase().includes(q) || n.body.toLowerCase().includes(q));
    if (filtered.length === 0) {
        list.innerHTML = `<p class="empty-state">No notes found.</p>`;
        return;
    }
    list.innerHTML = filtered.map(n => `
        <div class="note-item ${n.id===currentNoteId?'active':''}" onclick="openNote('${n.id}')">
            <div class="note-item-title">${n.title}</div>
            <div class="note-item-meta">${n.subject || ''} · ${n.date || ''}</div>
        </div>`).join('');
    $('stat-notes').textContent = allNotes.length;
}

function filterNotes() { renderNotesList(); }

function openNoteEditor() {
    currentNoteId = 'new-' + Date.now();
    $('note-title-input').value = '';
    $('note-subject-input').value = '';
    $('note-body').value = '';
    $('note-placeholder').classList.add('hidden');
    $('note-editor').classList.remove('hidden');
    document.querySelectorAll('.note-item').forEach(i=>i.classList.remove('active'));
}

function openNote(id) {
    const note = allNotes.find(n => n.id === id);
    if (!note) return;
    currentNoteId = id;
    $('note-title-input').value = note.title;
    $('note-subject-input').value = note.subject || '';
    $('note-body').value = note.body;
    $('note-placeholder').classList.add('hidden');
    $('note-editor').classList.remove('hidden');
    $('stat-notes').textContent = allNotes.length;
    renderNotesList();
}

// ===== AI EXTRACT FLASHCARDS FROM NOTE =====
async function extractFlashcardsFromNote() {
    if (!currentNoteId) {
        alert("Please select or save a note first!");
        return;
    }
    
    const title = $('note-title-input').value.trim() || 'Untitled Note';
    const text = $('note-body').value.trim();
    
    if (!text || text.length < 50) {
        alert("Note is too short to extract flashcards. Add more content!");
        return;
    }

    const btn = $('btn-extract-flashcards');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Extracting...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/ml/note-to-flashcards', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: text, title: title})
        });
        const data = await res.json();
        
        if (data.success && data.cards && data.cards.length > 0) {
            // Save cards
            const setName = title;
            data.cards.forEach(card => {
                const newCard = {
                    id: Date.now().toString() + Math.floor(Math.random()*1000),
                    question: card.question,
                    answer: card.answer,
                    subject: setName
                };
                allCards.unshift(newCard);
            });
            _saveDemoCards();
            $('stat-cards').textContent = allCards.length;
            
            alert(`Successfully extracted ${data.cards.length} flashcards into the set "${setName}"!`);
            
            // Switch to flashcards view
            navigate('flashcards-view', document.querySelector('[data-view=flashcards-view]'));
            filterCardsBySet(setName);
            
        } else {
            alert('Failed to extract flashcards.');
        }
    } catch (e) {
        alert('Network error while extracting flashcards.');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function saveNote() {
    const title = $('note-title-input').value.trim() || 'Untitled';
    const subject = $('note-subject-input').value.trim();
    const body = $('note-body').value;
    const existing = allNotes.findIndex(n => n.id === currentNoteId);
    const note = { id: currentNoteId, title, subject, body, date: new Date().toLocaleDateString() };
    if (existing >= 0) allNotes[existing] = note;
    else allNotes.unshift(note);
    saveLS('mm_notes', allNotes);
    renderNotesList();
}

function deleteCurrentNote() {
    if (!currentNoteId || !confirm('Delete this note?')) return;
    allNotes = allNotes.filter(n => n.id !== currentNoteId);
    saveLS('mm_notes', allNotes);
    currentNoteId = null;
    $('note-editor').classList.add('hidden');
    $('note-placeholder').classList.remove('hidden');
    renderNotesList();
}

function exportNoteToPDF() {
    if (!currentNoteId) return;
    window.print();
}

// ===== SCHEDULE =====
function renderSchedule() {
    renderWeekGrid();
    renderSessionsList();
}

function changeWeek(dir) {
    currentWeekOffset += dir;
    renderWeekGrid();
    $('week-label').textContent = currentWeekOffset === 0 ? 'This Week' : currentWeekOffset < 0 ? `${Math.abs(currentWeekOffset)} Week(s) Ago` : `In ${currentWeekOffset} Week(s)`;
}

function renderWeekGrid() {
    const grid = $('week-grid');
    const today = new Date();
    const todayStr = toDateStr(today);
    const monday = new Date(today);
    monday.setDate(today.getDate() - today.getDay() + 1 + currentWeekOffset * 7);
    const days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
    grid.innerHTML = days.map((d,i) => {
        const date = new Date(monday); date.setDate(monday.getDate()+i);
        const ds = toDateStr(date);
        const daySessions = sessions.filter(s=>s.date===ds);
        const isToday = ds===todayStr;
        return `<div class="week-day-col">
            <div class="week-day-header ${isToday?'today-header':''}">${d} ${date.getDate()}</div>
            ${daySessions.map(s=>`<div class="sess-chip" title="${s.subject}">${s.time} ${s.subject}</div>`).join('')}
        </div>`;
    }).join('');
}

function renderSessionsList() {
    const sorted = [...sessions].sort((a,b)=>(a.date+a.time).localeCompare(b.date+b.time));
    $('sessions-list').innerHTML = sorted.length === 0
        ? `<p class="empty-state">No sessions yet.</p>`
        : sorted.map(s=>`
            <div class="session-item">
                <div class="session-time"><i class="fa-solid fa-calendar"></i> ${s.date}<br>${s.time} · ${s.duration}min</div>
                <div class="session-info">
                    <div class="session-subject">${s.subject}</div>
                    <div class="session-topic">${s.topic || ''}</div>
                </div>
                <button class="session-del" onclick="deleteSession('${s.id}')"><i class="fa-solid fa-trash"></i></button>
            </div>`).join('');
}

function openSessionModal() {
    $('session-modal').classList.remove('hidden');
    $('sess-date').value = toDateStr(new Date());
    $('sess-time').value = '09:00';
}

function closeSessionModal() {
    $('session-modal').classList.add('hidden');
    $('session-form').reset();
}

function saveSession(e) {
    e.preventDefault();
    const sess = { id:Date.now().toString(), subject:$('sess-subject').value, topic:$('sess-topic').value, date:$('sess-date').value, time:$('sess-time').value, duration:$('sess-duration').value };
    sessions.push(sess);
    saveLS('mm_sessions', sessions);
    closeSessionModal();
    renderSchedule();
    refreshDashboard();
}

function deleteSession(id) {
    sessions = sessions.filter(s=>s.id!==id);
    saveLS('mm_sessions', sessions);
    renderSchedule();
}

// ===== STREAKS =====
function recordActivity() {
    const today = toDateStr(new Date());
    if (!streakData.days) streakData.days = [];
    if (!streakData.days.includes(today)) {
        streakData.days.push(today);
        streakData.current = calcStreak();
        streakData.best = Math.max(streakData.best||0, streakData.current);
        saveLS('mm_streak', streakData);
    }
}

function markTodayStudied() {
    recordActivity();
    renderStreak();
    refreshDashboard();
    alert('🔥 Great work! Today has been marked as studied!');
}

function calcStreak() {
    const days = (streakData.days || []).sort();
    if (days.length === 0) return 0;
    let streak = 0;
    let d = new Date();
    while (true) {
        const ds = toDateStr(d);
        if (days.includes(ds)) { streak++; d.setDate(d.getDate()-1); }
        else break;
    }
    return streak;
}

function renderStreak() {
    const streak = calcStreak();
    streakData.current = streak;
    streakData.best = Math.max(streakData.best||0, streak);
    $('streak-hero-number').textContent = streak;
    $('stat-streak').textContent = streak;
    $('streak-best').textContent = streakData.best;
    $('streak-total').textContent = (streakData.days||[]).length;
    renderHeatmap();
    renderAchievements();
}

function renderHeatmap() {
    const grid = $('heatmap-grid');
    const today = new Date();
    const cells = [];
    for (let i = 34; i >= 0; i--) {
        const d = new Date(today); d.setDate(today.getDate()-i);
        const ds = toDateStr(d);
        const studied = (streakData.days||[]).includes(ds);
        cells.push(`<div class="heatmap-cell ${studied?'l3':''}" title="${ds}"></div>`);
    }
    grid.innerHTML = cells.join('');
}

function renderMiniStreak() {
    const grid = $('dash-streak-mini');
    const today = new Date();
    const cells = [];
    for (let i = 27; i >= 0; i--) {
        const d = new Date(today); d.setDate(today.getDate()-i);
        const ds = toDateStr(d);
        const studied = (streakData.days||[]).includes(ds);
        cells.push(`<div class="mini-day ${studied?'studied':''}" title="${ds}"></div>`);
    }
    grid.innerHTML = cells.join('');
}

function renderAchievements() {
    const streak = calcStreak();
    const total = (streakData.days||[]).length;
    const achs = [
        { icon:'🌱', name:'First Step', desc:'Study for the first day', unlocked: total >= 1 },
        { icon:'🔥', name:'On Fire', desc:'3-day streak', unlocked: streak >= 3 },
        { icon:'⚡', name:'Power Week', desc:'7-day streak', unlocked: streak >= 7 },
        { icon:'💎', name:'Diamond', desc:'30-day streak', unlocked: streak >= 30 },
        { icon:'📚', name:'Bookworm', desc:'Study 10 total days', unlocked: total >= 10 },
        { icon:'🏆', name:'Champion', desc:'Study 30 total days', unlocked: total >= 30 },
    ];
    $('achievements-grid').innerHTML = achs.map(a=>`
        <div class="achievement ${a.unlocked?'unlocked':'locked'}">
            <div class="ach-icon">${a.icon}</div>
            <div><div class="ach-name">${a.name}</div><div class="ach-desc">${a.desc}</div></div>
        </div>`).join('');
}

// ===== SOCIAL (FRIENDS, GROUPS, CHAT) =====
let socialPollInterval = null;
let activeChat = { type: null, id: null }; // type: 'dm' or 'group'
let currentFriends = [];
let currentGroups = [];

async function initSocial() {
    await fetchSocialData();
    if (!socialPollInterval) {
        socialPollInterval = setInterval(pollActiveChat, 2000); // 2-second short polling
    }
}

async function fetchSocialData() {
    if (!currentUser) return;
    try {
        const [friendsRes, reqsRes, groupsRes] = await Promise.all([
            fetch(`/api/social/friends?email=${encodeURIComponent(currentUser.email)}`),
            fetch(`/api/social/friends/requests?email=${encodeURIComponent(currentUser.email)}`),
            fetch(`/api/social/groups?email=${encodeURIComponent(currentUser.email)}`)
        ]);
        
        const friendsData = await friendsRes.json();
        const reqsData = await reqsRes.json();
        const groupsData = await groupsRes.json();
        
        currentFriends = friendsData.friends || [];
        currentGroups = groupsData.groups || [];
        
        renderSocialLists(friendsData.friends, reqsData.requests, groupsData.groups);
    } catch (e) {
        console.error("Social data fetch error", e);
    }
}

function renderSocialLists(friends, requests, groups) {
    // Friends list
    const fList = $('friends-list');
    fList.innerHTML = friends.length === 0 ? '<div class="empty-state" style="padding:10px">No friends yet</div>' :
        friends.map(f => `
            <div class="social-item ${activeChat.id===f.id ? 'active':''}" onclick="openChat('dm', '${f.id}', '${f.name}')">
                <div class="social-avatar">${f.name.charAt(0).toUpperCase()}</div>
                <div class="social-name">${f.name}</div>
            </div>`).join('');
            
    // Groups list
    const gList = $('groups-list');
    gList.innerHTML = groups.length === 0 ? '<div class="empty-state" style="padding:10px">No groups yet</div>' :
        groups.map(g => `
            <div class="social-item ${activeChat.id===g.id ? 'active':''}" onclick="openChat('group', '${g.id}', '${g.name}')">
                <div class="social-avatar group"><i class="fa-solid fa-layer-group"></i></div>
                <div class="social-name">${g.name}</div>
            </div>`).join('');
            
    // Requests list
    const rList = $('friend-requests-list');
    rList.innerHTML = requests.length === 0 ? '<div style="color:var(--muted);font-size:.8rem;padding:0 12px">No pending requests</div>' :
        requests.map(r => `
            <div class="social-item" style="cursor:default">
                <div class="social-name" style="font-size:.8rem"><strong>${r.sender_name}</strong> wants to connect</div>
                <div class="req-actions">
                    <button class="accept" onclick="acceptRequest('${r.id}')"><i class="fa-solid fa-circle-check"></i></button>
                </div>
            </div>`).join('');
}

function openChat(type, id, name) {
    activeChat = { type, id };
    $('chat-placeholder').classList.add('hidden');
    $('chat-active').classList.remove('hidden');
    $('chat-header-title').textContent = name;
    $('social-chat-messages').innerHTML = '<div class="loading-state">Loading messages...</div>';
    
    // Show invite button only for groups
    $('btn-invite-friend').style.display = type === 'group' ? 'inline-flex' : 'none';
    
    // Refresh lists to show active state
    renderSocialLists(currentFriends, [], currentGroups);
    pollActiveChat();
}

async function pollActiveChat() {
    if (!activeChat.id || !currentUser) return;
    try {
        let url = '';
        if (activeChat.type === 'group') {
            url = `/api/social/messages/group/${activeChat.id}`;
        } else {
            url = `/api/social/messages/dm/${activeChat.id}?email=${encodeURIComponent(currentUser.email)}`;
        }
        
        const res = await fetch(url);
        const data = await res.json();
        renderChatMessages(data.messages || []);
    } catch (e) {
        // Silent fail on polling
    }
}

function renderChatMessages(messages) {
    const container = $('social-chat-messages');
    
    // Auto-scroll logic: only scroll to bottom if we are already at the bottom
    const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 100;
    
    if (messages.length === 0) {
        container.innerHTML = '<div class="empty-state">No messages yet. Say hi!</div>';
        return;
    }
    
    const myId = currentUser.email; // Actually our server uses real IDs, but frontend currentUser only has email/name.
    // However, the backend assigns IDs based on email in demo mode. We'll determine "me" by matching sender_name to currentUser.name
    
    container.innerHTML = messages.map(m => {
        const isMe = m.sender_name === currentUser.name && !m.is_ai;
        const msgClass = m.is_ai ? 'ai-msg' : (isMe ? 'me' : 'other');
        const avatar = m.is_ai ? '🐒' : m.sender_name.charAt(0).toUpperCase();
        
        // AI Note Save button
        const saveBtn = m.is_ai ? `<div class="sm-actions"><button class="btn-secondary" style="padding:4px 10px;font-size:.7rem" onclick="saveAsSharedNote('${encodeURIComponent(m.content)}')"><i class="fa-solid fa-floppy-disk"></i> Save to Notes</button></div>` : '';
        
        return `
            <div class="social-message ${msgClass}">
                <div class="sm-avatar">${avatar}</div>
                <div class="sm-content">
                    <div class="sm-author">${m.sender_name}</div>
                    <div class="sm-bubble">${m.content.replace(/\n/g, '<br>')}</div>
                    ${saveBtn}
                </div>
            </div>
        `;
    }).join('');
    
    if (isAtBottom) {
        container.scrollTop = container.scrollHeight;
    }
}

async function sendSocialMessage(e) {
    e.preventDefault();
    if (!activeChat.id) return;
    
    const input = $('social-chat-input');
    const content = input.value.trim();
    if (!content) return;
    
    input.value = '';
    
    // Optimistic append
    const container = $('social-chat-messages');
    container.innerHTML += `
        <div class="social-message me">
            <div class="sm-avatar">${currentUser.name.charAt(0).toUpperCase()}</div>
            <div class="sm-content">
                <div class="sm-bubble">${content.replace(/\n/g, '<br>')}</div>
            </div>
        </div>`;
    container.scrollTop = container.scrollHeight;
    
    const payload = {
        sender_email: currentUser.email,
        content: content,
        group_id: activeChat.type === 'group' ? activeChat.id : null,
        receiver_id: activeChat.type === 'dm' ? activeChat.id : null
    };
    
    try {
        await fetch('/api/social/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        // Polling will catch the confirmed message and AI replies
    } catch (e) {
        console.error(e);
    }
}

// Allow Enter to send in textarea
document.addEventListener('DOMContentLoaded', () => {
    const sci = $('social-chat-input');
    if (sci) {
        sci.addEventListener('keydown', e => {
            if(e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                $('social-send-btn').click();
            }
        });
    }
});

function saveAsSharedNote(contentEncoded) {
    const content = decodeURIComponent(contentEncoded);
    const note = {
        id: Date.now().toString(),
        title: activeChat.type === 'group' ? `Shared AI Note (${$('chat-header-title').textContent})` : 'AI Explanation',
        subject: 'Shared',
        body: content,
        date: new Date().toLocaleDateString()
    };
    allNotes.unshift(note);
    saveLS('mm_notes', allNotes);
    alert('✅ AI Response saved to your Notes! You can view or export it there.');
}

// Modals
function openModal(id) { $(id).classList.remove('hidden'); }
function closeModal(id) { $(id).classList.add('hidden'); }

function openAddFriendModal() { openModal('add-friend-modal'); }
function openCreateGroupModal() { openModal('create-group-modal'); }
function openInviteModal() {
    if (activeChat.type !== 'group') return;
    const select = $('invite-friend-select');
    select.innerHTML = currentFriends.map(f => `<option value="${f.id}">${f.name}</option>`).join('');
    openModal('invite-group-modal');
}

async function sendFriendRequest() {
    const email = $('add-friend-email').value;
    if(!email) return;
    await fetch('/api/social/friends/request', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ sender_email: currentUser.email, receiver_email: email })
    });
    closeModal('add-friend-modal');
    $('add-friend-email').value = '';
    alert('Friend request sent!');
}

async function acceptRequest(reqId) {
    await fetch(`/api/social/friends/accept/${reqId}`, { method: 'POST' });
    fetchSocialData();
}

async function createStudyGroup() {
    const name = $('create-group-name').value;
    if(!name) return;
    await fetch('/api/social/groups', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ creator_email: currentUser.email, name })
    });
    closeModal('create-group-modal');
    $('create-group-name').value = '';
    fetchSocialData();
}

async function inviteFriendToGroup() {
    const friendId = $('invite-friend-select').value;
    if(!friendId || activeChat.type !== 'group') return;
    await fetch('/api/social/groups/invite', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ group_id: activeChat.id, friend_id: friendId })
    });
    closeModal('invite-group-modal');
    alert('Friend invited to the group!');
}
