let _fs = null;
let _path = null;
let _child_process = null;

try {
    if (typeof require !== 'undefined') {
        _fs = require('fs');
        _path = require('path');
        _child_process = require('child_process');
    }
} catch (e) {
    console.error('Electron modules not available');
}

const translations = {
    en: {
        nav_home: "Home",
        nav_stats: "Statistics",
        nav_profile: "Profile",
        nav_settings: "Settings",
        start_btn: "Start analysis",
        stop_btn: "Stop",
        theme_label: "Theme:",
        lang_label: "Language:",
        status_none: "None (analysis stopped)",
        video_placeholder: "Analysis stopped. Please press button 'Start analysis' to begin.",
        attention_text: "Attention:",
        fatigue_text: "Fatigue:",
        status_text: "Current status:",
        theme_dark: "Dark",
        theme_light: "Light",
        lang_en: "English",
        lang_uk: "Українська",
        prof_name: "Name:",
        prof_user: "Username:",
        prof_email: "Email:",
        prof_since: "Member Since:",
        logout_btn: "Log out",
        session_label: "Session:",
        select_session: "Select session"
    },
    uk: {
        nav_home: "Головна",
        nav_stats: "Статистика",
        nav_profile: "Профіль",
        nav_settings: "Налаштування",
        start_btn: "Почати аналіз",
        stop_btn: "Зупинити",
        theme_label: "Тема:",
        lang_label: "Мова:",
        status_none: "Відсутній (аналіз зупинено)",
        video_placeholder: "Аналіз зупинено. Будь ласка, натисніть кнопку 'Почати аналіз', щоб розпочати.",
        attention_text: "Увага:",
        fatigue_text: "Втома:",
        status_text: "Поточний стан:",
        theme_dark: "Темна",
        theme_light: "Світла",
        lang_en: "English",
        lang_uk: "Українська",
        prof_name: "Ім'я:",
        prof_user: "Логін:",
        prof_email: "Пошта:",
        prof_since: "У системі з:",
        logout_btn: "Вийти",
        session_label: "Сесія:",
        select_session: "Оберіть сесію"
    }
};

const startBtn = document.getElementById('start_btn');
const stopBtn = document.getElementById('stop_btn');
const videoEl = document.getElementById('video');
const videoLabel = document.getElementById('video_label');
const attentionLabel = document.getElementById('attention_label');
const fatigueLabel = document.getElementById('fatigue_label');
const statusLabel = document.getElementById('status_label');
const metricsCanvas = document.getElementById('metrics_canvas');
const sessionSelect = document.getElementById('session_select');
const themeCombo = document.getElementById('theme_combo');
const langCombo = document.getElementById('lang_combo');

let videoStream = null;
let pythonProcess = null;
let analysisInterval = null;
let attentionHistory = [];
let fatigueHistory = [];
let sessionSaved = false;
let sessionData = {
    attention: [],
    fatigue: [],
    start_time: new Date().toISOString()
};

const FRAME_INTERVAL = 500;
const MAX_POINTS = 60;

document.querySelectorAll('.nav-btn').forEach(b => {
    b.addEventListener('click', () => showPage(b.dataset.page));
});

function showPage(id) {
    document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
    const el = document.getElementById(id);
    if (el) el.style.display = 'block';
}

function setTheme(theme) {
    if (theme === 'light') {
        document.body.classList.add('light-theme');
    } else {
        document.body.classList.remove('light-theme');
    }
    localStorage.setItem('pref-theme', theme);
    themeCombo.value = theme;
}

function setLanguage(lang) {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (translations[lang] && translations[lang][key]) {
            const text = translations[lang][key];
            if (['SPAN', 'LABEL', 'STRONG', 'H2', 'H3', 'OPTION'].includes(el.tagName)) {
                el.textContent = text;
            } else if (el.querySelector('span')) {
                el.querySelector('span').textContent = text;
            } else {
                el.textContent = text;
            }
        }
    });
    localStorage.setItem('pref-lang', lang);
    langCombo.value = lang;
}

themeCombo.addEventListener('change', (e) => setTheme(e.target.value));
langCombo.addEventListener('change', (e) => setLanguage(e.target.value));

function formatTime(date = new Date()) {
    return date.toLocaleTimeString('uk-UA', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatDate(d = new Date()) {
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}_` +
           `${pad(d.getHours())}-${pad(d.getMinutes())}-${pad(d.getSeconds())}`;
}

function computeFatigueState(attention, fatigue) {
    if (fatigue < 0.6 && attention > 0.5) {
        return 'Normal';
    }
    if (fatigue >= 0.6) {
        return 'Tired';
    }
    return 'Normal';
}

const metricsChart = new Chart(metricsCanvas.getContext('2d'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            { label: 'Attention', data: [], borderWidth: 2 },
            { label: 'Fatigue', data: [], borderWidth: 2 }
        ]
    },
    options: {
        animation: false,
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: { min: 0, max: 1 }
        }
    }
});

function startPythonAnalysis() {
    const analysisPy = _path.join(__dirname, 'backend', 'analysis.py');
    pythonProcess = _child_process.spawn('python', [analysisPy], {
        stdio: ['pipe', 'pipe', 'pipe'],
        cwd: _path.join(__dirname, 'backend'),
        windowsHide: true
    });
    pythonProcess.stdout.on('data', data => {
        data.toString().trim().split('\n').forEach(line => {
            try {
                const result = JSON.parse(line);
                updateUI(result);
            } catch {}
        });
    });
    pythonProcess.stderr.on('data', data => {
        console.error(`Python Error: ${data}`);
    });
    pythonProcess.on('close', () => stopAnalysis());
}

function stopPythonAnalysis() {
    if (pythonProcess) {
        pythonProcess.kill();
        pythonProcess = null;
    }
}

function updateUI(result) {
    const attention = parseFloat(result.attention);
    const fatigue = parseFloat(result.fatigue);

    attentionLabel.textContent = attention.toFixed(2);
    fatigueLabel.textContent = fatigue.toFixed(2);

    attentionHistory.push(attention);
    fatigueHistory.push(fatigue);

    if (attentionHistory.length > MAX_POINTS) {
        attentionHistory.shift();
        fatigueHistory.shift();
    }

    statusLabel.textContent = computeFatigueState(attention, fatigue);

    const now = new Date();
    const timeLabel = formatTime(now);

    metricsChart.data.labels.push(timeLabel);
    metricsChart.data.datasets[0].data.push(attention);
    metricsChart.data.datasets[1].data.push(fatigue);

    if (metricsChart.data.labels.length > MAX_POINTS) {
        metricsChart.data.labels.shift();
        metricsChart.data.datasets.forEach(d => d.data.shift());
    }

    metricsChart.update('none');

    sessionData.attention.push({
        time: now.toISOString(),
        attention
    });

    sessionData.fatigue.push({
        time: now.toISOString(),
        fatigue
    });
}

async function analyzeFrame() {
    if (!videoEl || !pythonProcess) return;
    const canvas = document.createElement('canvas');
    canvas.width = videoEl.videoWidth;
    canvas.height = videoEl.videoHeight;
    canvas.getContext('2d').drawImage(videoEl, 0, 0);
    const img = canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
    pythonProcess.stdin.write(img + '\n');
}

async function initCamera() {
    videoStream = await navigator.mediaDevices.getUserMedia({ video: true });
    videoEl.srcObject = videoStream;
    videoEl.style.display = 'block';
    videoLabel.style.display = 'none';
    await videoEl.play();
}

function stopAnalysis() {
    if (sessionSaved) return;
    sessionSaved = true;
    clearInterval(analysisInterval);
    analysisInterval = null;
    stopPythonAnalysis();
    if (videoStream) {
        videoStream.getTracks().forEach(t => t.stop());
        videoStream = null;
    }
    sessionData.end_time = new Date().toISOString();
    saveSession(sessionData);
    
    startBtn.disabled = false;
    stopBtn.disabled = true;
    videoEl.style.display = 'none';
    videoLabel.style.display = 'flex';

    const currentLang = localStorage.getItem('pref-lang') || 'en';
    statusLabel.textContent = translations[currentLang].status_none;
    videoLabel.textContent = translations[currentLang].video_placeholder;
    
    loadSessions();
}

startBtn.addEventListener('click', async () => {
    showPage('home');
    startBtn.disabled = true;
    stopBtn.disabled = true;
    sessionSaved = false;
    sessionData = {
        attention: [],
        fatigue: [],
        start_time: new Date().toISOString()
    };
    attentionHistory = [];
    fatigueHistory = [];
    metricsChart.data.labels = [];
    metricsChart.data.datasets.forEach(d => d.data = []);
    metricsChart.update();
    startPythonAnalysis();
    await initCamera();
    analysisInterval = setInterval(analyzeFrame, FRAME_INTERVAL);
    stopBtn.disabled = false;
    statusLabel.textContent = 'Initializing...';
});

stopBtn.addEventListener('click', stopAnalysis);

function historyDir() {
    return _path.join(__dirname, 'history');
}

function saveSession(data) {
    if (!_fs) return;
    const dir = historyDir();
    if (!_fs.existsSync(dir)) _fs.mkdirSync(dir);
    const name = `session_${formatDate()}.json`;
    _fs.writeFileSync(_path.join(dir, name), JSON.stringify(data, null, 2));
}

function loadSessions() {
    if (!_fs) return;
    const dir = historyDir();
    if (!_fs.existsSync(dir)) return;
    sessionSelect.innerHTML = '';
    const defOption = document.createElement('option');
    const currentLang = localStorage.getItem('pref-lang') || 'en';
    defOption.textContent = translations[currentLang].select_session;
    sessionSelect.appendChild(defOption);

    _fs.readdirSync(dir).forEach(f => {
        const o = document.createElement('option');
        o.value = f;
        o.textContent = f;
        sessionSelect.appendChild(o);
    });
}

function loadSession(name) {
    const data = JSON.parse(_fs.readFileSync(_path.join(historyDir(), name)));
    metricsChart.data.labels = data.attention.map(e => formatTime(new Date(e.time)));
    metricsChart.data.datasets[0].data = data.attention.map(e => e.attention);
    metricsChart.data.datasets[1].data = data.fatigue.map(e => e.fatigue);
    metricsChart.update();
}

sessionSelect.addEventListener('change', e => {
    if (e.target.value) loadSession(e.target.value);
});

window.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('pref-theme') || 'dark';
    const savedLang = localStorage.getItem('pref-lang') || 'en';
    setTheme(savedTheme);
    setLanguage(savedLang);
    loadSessions();
});