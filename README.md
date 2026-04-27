# 🐒 MonkeyMind AI - Collaborative Social Learning Platform

![MonkeyMind Banner](https://img.shields.io/badge/MonkeyMind-AI%20Social%20Learning-f39c12?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Vanilla JS](https://img.shields.io/badge/Vanilla_JS-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)

**MonkeyMind AI** is an advanced, gamified social ecosystem built to revolutionize studying. We transformed the solitary experience of note-taking into a vibrant, multiplayer environment powered by an omnipresent AI.

## 🌟 Key Features

### 1. 🤝 Social Study Ecosystem
- **Friend Groups & Direct Messaging**: Connect with classmates, share notes instantly, and chat in real-time.
- **Group AI Integration**: Tag `@monky` in your group chats to instantly bring the AI into the conversation. It reads the last 20 messages for context, settling academic debates and answering questions instantly!

### 2. 🧠 Monkey Learning Engine (TurboLearn)
- **YouTube to Notes**: Paste a YouTube link and watch as MonkeyMind extracts transcripts, summarizes key concepts, and outputs detailed, perfectly formatted markdown notes.
- **Smart AI Flashcards**: Highlight any text in your Notes and generate 5-10 high-yield Question & Answer flashcards in a single click.

### 3. 🛡️ Powerful Developer Dashboard
- **Live Site Management**: A sleek WYSIWYG Admin Dashboard to change site themes, global announcements, and branding without touching the code.
- **Complete User Control**: Monitor active users, inspect their friend lists, and ban/kick disruptive users from the entire ecosystem.
- **In-Browser Terminal & IDE**: Edit code and run shell commands directly from the dashboard!

## 🚀 Tech Stack
- **Backend**: Python, FastAPI
- **Frontend**: Vanilla HTML/CSS/JS (Zero-build glassmorphism architecture)
- **AI Integration**: Featherless AI (Qwen 2.5) via OpenAI API standard
- **Tooling**: `yt-dlp` for media extraction, WebSockets / Long-polling for social sync.

## 🛠️ How to Run Locally

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
pip install yt-dlp
```

2. **Set your Environment Variables**:
Create a `.env` file and add your AI key:
```env
FEATHERLESS_API_KEY=your_api_key_here
```

3. **Start the Server**:
```bash
python main.py
```
Open your browser to `http://localhost:8000`. To access the Admin Dashboard, navigate to `http://localhost:8000/admin`.

---
*Built with passion at a hackathon.* 🐒💭
