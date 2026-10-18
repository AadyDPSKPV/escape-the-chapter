import os
import json
import re
import time
import random
import html
from typing import Any

import requests
import streamlit as st

# ------------------------------------------------------------
# ESCAPE THE CHAPTER
# A single-file Streamlit app with optional Gemini API support.
# ------------------------------------------------------------

st.set_page_config(
    page_title="Escape the Chapter",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Visual design ----------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --gold: #f6c86a; --cyan: #7de3ef; --ink: #09111f; }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp {
      background:
        radial-gradient(circle at 12% 4%, rgba(43, 93, 148, .25), transparent 28%),
        radial-gradient(circle at 88% 14%, rgba(146, 90, 42, .16), transparent 25%),
        linear-gradient(145deg, #07101d 0%, #0d1728 55%, #101a2b 100%);
      color: #f5f7fb;
    }
    h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; }
    .hero {
      padding: 1.45rem 1.6rem; border: 1px solid rgba(125,227,239,.25);
      border-radius: 22px; background: linear-gradient(120deg, rgba(24,45,71,.88), rgba(18,29,48,.75));
      box-shadow: 0 18px 60px rgba(0,0,0,.22); margin-bottom: 1.1rem;
    }
    .eyebrow { color: var(--cyan); font-weight: 700; letter-spacing: .16em; font-size: .76rem; text-transform: uppercase; }
    .hero-title { font-family: 'Space Grotesk', sans-serif; font-size: clamp(2rem, 4vw, 3.2rem); line-height: 1.02; font-weight: 700; margin: .45rem 0 .6rem; }
    .hero-copy { color: #c5d0df; max-width: 780px; font-size: 1rem; }
    .panel {
      border: 1px solid rgba(190,210,235,.16); border-radius: 18px; padding: 1rem 1.15rem;
      background: rgba(15,27,44,.78); margin-bottom: .8rem;
    }
    .level-card {
      border: 1px solid rgba(125,227,239,.2); border-radius: 16px; padding: 1rem;
      background: linear-gradient(140deg, rgba(24,43,67,.95), rgba(14,25,42,.95));
      min-height: 120px;
    }
    .level-number { color: var(--gold); text-transform: uppercase; letter-spacing: .12em; font-size: .7rem; font-weight: 700; }
    .level-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.25rem; font-weight: 700; margin-top: .3rem; }
    .muted { color: #aab9cc; font-size: .9rem; }
    .clue {
      display: inline-block; border: 1px solid rgba(246,200,106,.4); color: #ffe6a5;
      background: rgba(246,200,106,.09); padding: .45rem .7rem; border-radius: 10px; margin: .15rem .25rem .15rem 0;
      font-weight: 700;
    }
    .success-banner {
      border: 1px solid rgba(104,226,164,.38); background: rgba(44,139,91,.12);
      border-radius: 16px; padding: 1rem 1.2rem;
    }
    div.stButton > button {
      border-radius: 11px; border: 1px solid rgba(125,227,239,.28);
      font-weight: 700; min-height: 2.8rem; transition: all .15s ease;
    }
    div.stButton > button[kind="primary"] {
      background: linear-gradient(100deg, #78dce9, #f6c86a); color: #09111f; border: none;
    }
    div.stButton > button:hover { border-color: #f6c86a; transform: translateY(-1px); }
    [data-testid="stSidebar"] { background: #0a1422; border-right: 1px solid rgba(190,210,235,.12); }
    .small-note { font-size: .78rem; color: #9caec3; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Constants / example passage ----------
EXAMPLE_PASSAGE = """The Delhi Sultanate was established in 1206 by Qutb-ud-din Aibak. Five dynasties ruled the Sultanate: the Mamluk, Khalji, Tughlaq, Sayyid, and Lodi dynasties. Alauddin Khalji expanded the Sultanate's territory and introduced market-control measures. The Delhi Sultanate ended in 1526 after Ibrahim Lodi was defeated by Babur at the First Battle of Panipat."""

DIFFICULTIES = ["Easy", "Medium", "Hard"]
DIFFICULTY_DESCRIPTIONS = {
    "Easy": "Knowledge Gate",
    "Medium": "Mystery Gate",
    "Hard": "Final Trial",
}
DEFAULT_QUESTIONS = [
    {
        "difficulty": "Easy",
        "question": "In which year was the Delhi Sultanate established, according to the passage?",
        "options": ["1206", "1290", "1398", "1526"],
        "answer": "1206",
        "hint": "Look at the opening sentence for the year.",
        "evidence": "The passage says the Delhi Sultanate was established in 1206.",
        "explanation": "The first sentence gives 1206 as the year the Delhi Sultanate was established.",
    },
    {
        "difficulty": "Medium",
        "question": "Which ruler introduced market-control measures, according to the passage?",
        "options": ["Qutb-ud-din Aibak", "Alauddin Khalji", "Ibrahim Lodi", "Babur"],
        "answer": "Alauddin Khalji",
        "hint": "Find the sentence that mentions market-control measures.",
        "evidence": "The passage says Alauddin Khalji introduced market-control measures.",
        "explanation": "The third sentence directly connects Alauddin Khalji with market-control measures.",
    },
    {
        "difficulty": "Hard",
        "question": "Which event does the passage identify as marking the end of the Delhi Sultanate?",
        "options": [
            "The establishment of the Sultanate in 1206",
            "Alauddin Khalji's market reforms",
            "Ibrahim Lodi's defeat by Babur at the First Battle of Panipat",
            "The beginning of the Tughlaq dynasty",
        ],
        "answer": "Ibrahim Lodi's defeat by Babur at the First Battle of Panipat",
        "hint": "Read the final sentence and look for the event linked to 1526.",
        "evidence": "The passage says the Delhi Sultanate ended in 1526 after Ibrahim Lodi was defeated by Babur at the First Battle of Panipat.",
        "explanation": "The final sentence explicitly connects the Sultanate's end with Ibrahim Lodi's defeat by Babur at Panipat.",
    },
]

# ---------- Session state ----------
def init_state():
    defaults = {
        "passage": EXAMPLE_PASSAGE,
        "chapter_title": "The Delhi Sultanate",
        "subject": "History",
        "questions": None,
        "question_source": None,
        "level": 0,
        "completed": [],
        "clues": [],
        "score": 0,
        "hints_used": [],
        "attempts": {},
        "start_time": None,
        "finished": False,
        "validation_report": None,
        "player_name": "Explorer",
        "last_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

# ---------- AI helpers ----------
def get_api_key() -> str:
    key = ""
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass
    return key or os.getenv("GEMINI_API_KEY", "")

def strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

def call_gemini(passage: str, subject: str, chapter_title: str) -> list[dict[str, Any]]:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("No Gemini API key found. Add GEMINI_API_KEY in Streamlit Secrets or environment variables.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    prompt = f"""
You are a careful educational quiz designer. Use ONLY the supplied passage. Do not use outside knowledge.
Create exactly 3 multiple-choice questions in the order Easy, Medium, Hard.
Each question must be answerable directly or by a simple inference from the passage.
For every question provide:
- difficulty: exactly Easy, Medium, or Hard
- question: clear, age-appropriate question
- options: exactly 4 distinct strings
- answer: exactly one option copied verbatim from options
- hint: helpful hint that does not reveal the answer
- evidence: a short exact quote copied from the passage that supports the answer
- explanation: one or two sentences explaining why the answer is supported
Do not make a question if the passage does not support it. If the passage has insufficient information for 3 valid questions, return fewer questions and set "insufficient_information": true.
Return JSON only, with this structure:
{{
  "questions": [
    {{
      "difficulty": "Easy",
      "question": "...",
      "options": ["...", "...", "...", "..."],
      "answer": "...",
      "hint": "...",
      "evidence": "exact quote from passage",
      "explanation": "..."
    }}
  ],
  "insufficient_information": false,
  "note": "short note"
}}
Subject: {subject}
Chapter title: {chapter_title}
PASSAGE START
{passage}
PASSAGE END
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    response = requests.post(url, json=payload, timeout=60)
    if response.status_code != 200:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(f"Gemini API error ({response.status_code}): {detail}")
    data = response.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(strip_json_fences(text))
    except Exception as exc:
        raise RuntimeError(f"Could not read the AI response as JSON: {exc}")
    questions = parsed.get("questions", [])
    if not isinstance(questions, list):
        raise RuntimeError("The AI response did not contain a valid questions list.")
    return questions

def normalize_and_validate(raw_questions: list[dict[str, Any]], passage: str) -> tuple[list[dict[str, Any]], list[str]]:
    valid = []
    warnings = []
    passage_norm = re.sub(r"\s+", " ", passage).strip().casefold()
    expected = ["Easy", "Medium", "Hard"]
    for i, q in enumerate(raw_questions[:3]):
        if not isinstance(q, dict):
            warnings.append(f"Question {i+1}: skipped because it was not structured correctly.")
            continue
        difficulty = q.get("difficulty", expected[i] if i < 3 else "")
        if difficulty not in DIFFICULTIES:
            difficulty = expected[i] if i < 3 else "Easy"
        question = str(q.get("question", "")).strip()
        options = q.get("options", [])
        answer = str(q.get("answer", "")).strip()
        hint = str(q.get("hint", "")).strip()
        evidence = str(q.get("evidence", "")).strip()
        explanation = str(q.get("explanation", "")).strip()
        if not question or not isinstance(options, list) or len(options) != 4:
            warnings.append(f"{difficulty}: skipped because the question/options were incomplete.")
            continue
        options = [str(x).strip() for x in options]
        if len(set(options)) != 4 or any(not x for x in options):
            warnings.append(f"{difficulty}: skipped because options were empty or duplicated.")
            continue
        if answer not in options:
            warnings.append(f"{difficulty}: skipped because the answer did not exactly match an option.")
            continue
        evidence_norm = re.sub(r"\s+", " ", evidence).strip().casefold()
        # Require evidence to be an exact substring after whitespace normalization.
        if not evidence_norm or evidence_norm not in passage_norm:
            warnings.append(f"{difficulty}: rejected because its evidence was not an exact quote from the supplied passage.")
            continue
        if not hint:
            hint = "Re-read the sentence that supports this question."
        if not explanation:
            explanation = "The quoted evidence supports the correct answer."
        valid.append({
            "difficulty": difficulty,
            "question": question,
            "options": options,
            "answer": answer,
            "hint": hint,
            "evidence": evidence,
            "explanation": explanation,
        })
    # Keep at most one of each difficulty, in required order.
    by_difficulty = {}
    for q in valid:
        if q["difficulty"] not in by_difficulty:
            by_difficulty[q["difficulty"]] = q
    ordered = [by_difficulty[d] for d in expected if d in by_difficulty]
    if len(ordered) < 3:
        warnings.append(f"Only {len(ordered)} of 3 questions passed the basic evidence and format checks. Try a longer passage or use the demo questions.")
    return ordered, warnings

def reset_game():
    st.session_state.questions = None
    st.session_state.question_source = None
    st.session_state.level = 0
    st.session_state.completed = []
    st.session_state.clues = []
    st.session_state.score = 0
    st.session_state.hints_used = []
    st.session_state.attempts = {}
    st.session_state.start_time = None
    st.session_state.finished = False
    st.session_state.validation_report = None
    st.session_state.last_error = None

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🔐 Mission Control")
    st.caption("Configure your escape mission.")
    st.session_state.player_name = st.text_input("Explorer name", value=st.session_state.player_name, max_chars=30)
    st.session_state.chapter_title = st.text_input("Chapter / passage title", value=st.session_state.chapter_title, max_chars=100)
    st.session_state.subject = st.selectbox(
        "Subject",
        ["History", "Science", "Geography", "English", "Mathematics", "Civics", "Other"],
        index=["History", "Science", "Geography", "English", "Mathematics", "Civics", "Other"].index(st.session_state.subject)
        if st.session_state.subject in ["History", "Science", "Geography", "English", "Mathematics", "Civics", "Other"] else 0,
    )
    st.markdown("---")
    st.markdown("### 🧪 AI configuration")
    if get_api_key():
        st.success("Gemini API key detected")
    else:
        st.warning("No API key detected")
        st.caption("You can still try the app with the built-in demo questions.")
    st.markdown("---")
    if st.button("↻ Reset current game", use_container_width=True):
        reset_game()
        st.rerun()
    st.markdown(
        '<div class="small-note">Tip: use a passage with several clear facts. AI-generated content is checked for quoted evidence, but should still be reviewed.</div>',
        unsafe_allow_html=True,
    )

# ---------- Hero ----------
st.markdown(
    f"""
    <div class="hero">
      <div class="eyebrow">AI-Powered Learning Adventure</div>
      <div class="hero-title">ESCAPE THE<br>CHAPTER <span style="color:#f6c86a;">✦</span></div>
      <div class="hero-copy">Welcome, {html.escape(st.session_state.player_name or "Explorer")}. Turn a textbook passage into three trials. Solve, collect clues, and unlock the final door.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Input / mission creation ----------
if st.session_state.questions is None:
    left, right = st.columns([1.45, 1])
    with left:
        st.markdown("### 📜 1. Enter your passage")
        passage = st.text_area(
            "Paste a textbook passage below",
            value=st.session_state.passage,
            height=250,
            help="For best results, use a passage containing several clear facts. Aim for about 100–800 words.",
            label_visibility="collapsed",
        )
        st.session_state.passage = passage
        char_count = len(passage.strip())
        st.caption(f"{char_count} characters · {len(passage.split())} words")
    with right:
        st.markdown("### 🗝️ 2. Choose your mission")
        st.markdown(
            """
            <div class="panel">
              <div class="level-number">YOUR OBJECTIVE</div>
              <h3 style="margin:.35rem 0;">Unlock all three gates</h3>
              <p class="muted">Answer an Easy, Medium, and Hard question. Each correct answer earns a clue fragment.</p>
              <hr style="border-color:rgba(190,210,235,.15)">
              <p>🟢 <b>Gate I</b> — Knowledge</p>
              <p>🟡 <b>Gate II</b> — Mystery</p>
              <p>🔴 <b>Gate III</b> — Final Trial</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        use_demo = st.checkbox("Use built-in demo questions (no API required)", value=not bool(get_api_key()))
        if st.button("⚡ Generate my escape mission", type="primary", use_container_width=True):
            if len(passage.strip()) < 80:
                st.error("Please enter a longer passage (at least 80 characters) so the questions have enough context.")
            else:
                with st.spinner("Preparing your escape mission..."):
                    try:
                        if use_demo:
                            # Demo questions are only valid for the included sample passage.
                            if passage.strip() != EXAMPLE_PASSAGE.strip():
                                st.warning("The built-in demo questions are specifically for the sample Delhi Sultanate passage. The sample passage has been loaded.")
                                st.session_state.passage = EXAMPLE_PASSAGE
                                st.session_state.chapter_title = "The Delhi Sultanate"
                                st.session_state.subject = "History"
                            questions, warnings = normalize_and_validate(DEFAULT_QUESTIONS, st.session_state.passage)
                            source = "Built-in demo"
                        else:
                            raw = call_gemini(passage, st.session_state.subject, st.session_state.chapter_title)
                            questions, warnings = normalize_and_validate(raw, passage)
                            source = "Gemini API"
                        if len(questions) != 3:
                            st.session_state.validation_report = warnings
                            st.error("We couldn't verify three complete questions from this passage. Try a longer passage with more explicit facts, or use the built-in demo.")
                        else:
                            st.session_state.questions = questions
                            st.session_state.question_source = source
                            st.session_state.validation_report = warnings
                            st.session_state.level = 0
                            st.session_state.completed = []
                            st.session_state.clues = []
                            st.session_state.score = 0
                            st.session_state.hints_used = []
                            st.session_state.attempts = {}
                            st.session_state.start_time = time.time()
                            st.session_state.finished = False
                            st.session_state.last_error = None
                            st.rerun()
                    except Exception as exc:
                        st.session_state.last_error = str(exc)
                        st.error(f"Could not create the mission: {exc}")
    if st.session_state.validation_report:
        with st.expander("Question validation report", expanded=True):
            for warning in st.session_state.validation_report:
                st.write("• " + warning)
    st.markdown("---")
    with st.expander("Need a sample passage? Click to use the demo passage"):
        st.code(EXAMPLE_PASSAGE, language="text")
        if st.button("Load sample passage"):
            st.session_state.passage = EXAMPLE_PASSAGE
            st.session_state.chapter_title = "The Delhi Sultanate"
            st.session_state.subject = "History"
            st.rerun()

# ---------- Gameplay ----------
else:
    questions = st.session_state.questions
    total = len(questions)
    completed_count = len(st.session_state.completed)
    progress = completed_count / max(total, 1)
    top1, top2, top3 = st.columns(3)
    top1.metric("Clues collected", f"{len(st.session_state.clues)}/3")
    top2.metric("Explorer score", st.session_state.score)
    top3.metric("Gates unlocked", f"{completed_count}/3")
    st.progress(progress, text=f"Mission progress · {completed_count} of 3 gates cleared")

    st.markdown("### 🏰 Your escape route")
    route_cols = st.columns(3)
    for idx, q in enumerate(questions):
        with route_cols[idx]:
            if idx in st.session_state.completed:
                status, symbol = "UNLOCKED", "🔓"
            elif idx == st.session_state.level:
                status, symbol = "CURRENT GATE", "🚪"
            else:
                status, symbol = "SEALED", "🔒"
            st.markdown(
                f"""
                <div class="level-card">
                  <div class="level-number">TRIAL {idx+1} · {html.escape(q['difficulty'].upper())}</div>
                  <div class="level-title">{symbol} {html.escape(DIFFICULTY_DESCRIPTIONS.get(q['difficulty'], 'Challenge'))}</div>
                  <div class="muted">{status}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("")
    if st.session_state.finished or completed_count == total:
        st.session_state.finished = True
        elapsed = int(time.time() - (st.session_state.start_time or time.time()))
        mins, secs = divmod(elapsed, 60)
        st.markdown(
            """
            <div class="success-banner">
              <h2>🏆 ESCAPE SUCCESSFUL!</h2>
              <p>You solved all three trials and unlocked the final door. Mission complete!</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        a, b, c = st.columns(3)
        a.metric("Final score", st.session_state.score)
        b.metric("Time taken", f"{mins}m {secs}s")
        c.metric("Hints used", len(st.session_state.hints_used))
        st.markdown("### 💎 Your collected clue fragments")
        st.markdown("".join([f'<span class="clue">{html.escape(x)}</span>' for x in st.session_state.clues]), unsafe_allow_html=True)
        st.markdown("### 🧠 Mission review")
        for q in questions:
            with st.expander(f"{q['difficulty']}: {q['question']}"):
                st.write("**Correct answer:**", q["answer"])
                st.write("**Why:**", q["explanation"])
                st.write("**Evidence from passage:**", f"“{q['evidence']}”")
        st.download_button(
            "⬇️ Download mission report",
            data=json.dumps({
                "player": st.session_state.player_name,
                "chapter": st.session_state.chapter_title,
                "subject": st.session_state.subject,
                "score": st.session_state.score,
                "clues": st.session_state.clues,
                "completed_levels": completed_count,
                "time_seconds": elapsed,
                "hints_used": len(st.session_state.hints_used),
                "question_source": st.session_state.question_source,
                "questions": questions,
            }, indent=2, ensure_ascii=False),
            file_name="escape_the_chapter_report.json",
            mime="application/json",
        )
        if st.button("🔁 Play another mission", type="primary"):
            reset_game()
            st.rerun()
    else:
        idx = st.session_state.level
        q = questions[idx]
        st.markdown(
            f"""
            <div class="panel">
              <div class="level-number">LEVEL {idx+1} OF 3 · {html.escape(q['difficulty'].upper())}</div>
              <h2 style="margin:.4rem 0;">{html.escape(DIFFICULTY_DESCRIPTIONS.get(q['difficulty'], 'Challenge'))}</h2>
              <p class="muted">Answer correctly to claim your clue fragment and unlock the next gate.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(f"### {q['question']}")
        answer_key = f"answer_{idx}"
        if answer_key not in st.session_state:
            st.session_state[answer_key] = None
        selected = st.radio(
            "Choose your answer",
            q["options"],
            index=None,
            key=f"radio_{idx}",
            label_visibility="collapsed",
        )
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("🔑 Submit answer", type="primary", use_container_width=True):
                if not selected:
                    st.warning("Choose an answer first.")
                elif idx in st.session_state.completed:
                    st.info("This gate is already unlocked.")
                elif selected == q["answer"]:
                    st.session_state.completed.append(idx)
                    clue_words = ["KNOWLEDGE", "CURIOSITY", "DISCOVERY"]
                    st.session_state.clues.append(clue_words[idx])
                    bonus = 100 if idx not in st.session_state.hints_used else 60
                    st.session_state.score += bonus
                    st.success(f"Correct! Gate unlocked. You earned the clue fragment: {clue_words[idx]} (+{bonus} points)")
                    if len(st.session_state.completed) == total:
                        st.session_state.finished = True
                    else:
                        st.session_state.level = min(idx + 1, total - 1)
                    st.rerun()
                else:
                    st.session_state.attempts[idx] = st.session_state.attempts.get(idx, 0) + 1
                    st.error("Not quite! The gate remains locked. Try a hint or review the passage and try again.")
        with col_b:
            if st.button("💡 Reveal hint", use_container_width=True):
                st.session_state.hints_used.append(idx) if idx not in st.session_state.hints_used else None
                st.info(q["hint"])
        with st.expander("📖 Review the supplied passage"):
            st.write(st.session_state.passage)
        with st.expander("🧾 Show supporting evidence (available for review)"):
            st.write(f"“{q['evidence']}”")
            st.caption("Evidence is checked against the supplied passage before the mission starts.")
        st.caption(f"Attempts on this gate: {st.session_state.attempts.get(idx, 0)}")
        if st.button("Quit mission and start over"):
            reset_game()
            st.rerun()

# ---------- Footer ----------
st.markdown("---")
st.markdown(
    '<p class="small-note">Escape the Chapter · Learning through play. AI-generated questions can make mistakes; always review educational content. The app checks that each accepted question includes an exact supporting quote from the supplied passage.</p>',
    unsafe_allow_html=True,
)
