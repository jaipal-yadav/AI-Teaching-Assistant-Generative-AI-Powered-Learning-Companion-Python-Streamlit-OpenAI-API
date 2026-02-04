import streamlit as st
from openai import OpenAI
import os
import json
import PyPDF2
from dotenv import load_dotenv
import pyttsx3
import speech_recognition as sr

from googleapiclient.discovery import build

YOUTUBE_API_KEY = "AIzaSyC2Vq8cnDmwacn-ZLXmVy3o77b8f97DoYk"
import requests

# YOUTUBE_API_KEY = "YOUR_API_KEY_HERE"  # 🔑 Replace with your key

def search_youtube(query, max_results=5):
    try:
        # make query educational
        query = query + " lecture tutorial explanation engineering"

        # YouTube Data API endpoint
        search_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "key": YOUTUBE_API_KEY,
            "videoDuration": "medium",
            "relevanceLanguage": "en",
        }

        response = requests.get(search_url, params=params)
        data = response.json()

        videos = []
        if "items" in data:
            for item in data["items"]:
                video_id = item["id"]["videoId"]
                title = item["snippet"]["title"]
                channel = item["snippet"]["channelTitle"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                videos.append((f"{title} ({channel})", video_url))

        if not videos:
            videos.append(("No relevant educational videos found.", ""))

        return videos

    except Exception as e:
        return [(f"Error fetching YouTube videos: {str(e)}", "")]





# -----------------------
# Helpers: TTS and STT
# -----------------------
def speak_text(text):
    engine = pyttsx3.init()
    engine.setProperty("rate", 170)
    engine.setProperty("volume", 1.0)
    voices = engine.getProperty("voices")
    # choose default voice safely
    if voices:
        engine.setProperty("voice", voices[0].id)
    engine.say(text)
    engine.runAndWait()

def speech_to_text():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            st.info("🎙️ Listening… please speak clearly")
            r.adjust_for_ambient_noise(source, duration=0.4)
            audio = r.listen(source, timeout=5, phrase_time_limit=8)
    except Exception as e:
        st.error(f"Microphone error: {e}")
        return ""
    try:
        text = r.recognize_google(audio)
        st.success(f"✅ Recognized: {text}")
        return text
    except sr.UnknownValueError:
        st.error("❌ Couldn’t understand. Try again.")
    except sr.RequestError:
        st.error("🌐 Network error with Google Speech API.")
    return ""

# -----------------------
# Load env & client
# -----------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="AI Teaching Assistant", page_icon="💬", layout="wide")
st.title("🎓 AI Teaching Assistant")

HISTORY_FILE = "chat_history.json"
FLASH_FILE = "flashcards_memory.json"

# -----------------------
# Tab labels & active memory
# -----------------------
tab_labels = ["💬 Chat Assistant", "🧩 Flashcards & Quiz", "📄 PDF Summarizer"]
if "active_tab" not in st.session_state:
    st.session_state.active_tab = tab_labels[0]

# Ensure session state defaults
if "messages" not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                st.session_state.messages = json.load(f)
        except Exception:
            st.session_state.messages = []
    else:
        st.session_state.messages = []

# Controlled inputs defaults
if "chat_input" not in st.session_state:
    st.session_state.chat_input = ""
if "chat_response" not in st.session_state:
    st.session_state.chat_response = ""
if "flash_input" not in st.session_state:
    st.session_state.flash_input = ""
if "spoken_text_temp" not in st.session_state:
    st.session_state.spoken_text_temp = ""

# Create tabs
tab1, tab2, tab3 = st.tabs(tab_labels)

# Helper to set active tab (call when you want to keep focus)
def set_active_tab(label):
    st.session_state.active_tab = label
    
# Keeping the custom button fixed 
# --- Custom CSS to fix chat input at bottom ---


# --- Custom CSS to fix chat layout ---
st.markdown("""
    <style>
    /* Fix the input and custom button container */
    .fixed-input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: white;
        z-index: 999;
        padding: 10px 20px;
        border-top: 1px solid #ddd;
        box-shadow: 0 -2px 6px rgba(0,0,0,0.05);
    }

    /* Make the main chat scrollable */
    .main-chat-container {
        overflow-y: auto;
        max-height: calc(100vh - 180px);
        padding-bottom: 120px;
    }

    /* Optional scrollbar style */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-thumb {
        background: #ccc;
        border-radius: 4px;
    }
    </style>
""", unsafe_allow_html=True)



# -----------------------
# TAB 1: Chat Assistant
# -----------------------
# ------------------- CHAT ASSISTANT TAB -------------------
with tab1:
    set_active_tab(tab_labels[0])

    if st.session_state.active_tab == tab_labels[0]:
        st.subheader("🤖 Chat with your AI Assistant")

        # Display previous messages in chat format
        st.markdown('<div class="main-chat-container">', unsafe_allow_html=True)
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="fixed-input-container">', unsafe_allow_html=True)


        # --- Input section (text + speech) ---
        st.markdown("### 💬 Ask something:")
        user_input_local = st.chat_input("Type your message and press Enter (or use 🎤 Speak below)")

        # --- Handle typed input ---
        if user_input_local:
            st.session_state.messages.append({"role": "user", "content": user_input_local})
            with st.chat_message("user"):
                st.markdown(user_input_local)

            with st.spinner("Thinking..."):
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=st.session_state.messages
                )
            reply = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.session_state["chat_response"] = reply

            # Display AI response immediately under input
            with st.chat_message("assistant"):
                st.markdown(reply)

                # 🎬 YouTube video suggestions
                st.markdown("### 🎥 Recommended YouTube Videos:")
                videos = search_youtube(user_input_local)
                for title, link in videos:
                    st.markdown(f"- [{title}]({link})")

            # Save chat automatically
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(st.session_state.messages, f, indent=4)

        # --- Speech Input Button (auto triggers response) ---
        if st.button("🎤 Speak", key="chat_speak"):
            spoken = speech_to_text()
            if spoken:
                st.session_state.messages.append({"role": "user", "content": spoken})
                with st.chat_message("user"):
                    st.markdown(spoken)

                with st.spinner("Thinking..."):
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=st.session_state.messages
                    )
                reply = response.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": reply})
                st.session_state["chat_response"] = reply

                with st.chat_message("assistant"):
                    st.markdown(reply)

                    # 🎬 YouTube videos for spoken query
                    st.markdown("### 🎥 Recommended YouTube Videos:")
                    videos = search_youtube(spoken)
                    for title, link in videos:
                        st.markdown(f"- [{title}]({link})")

                # Save chat automatically
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(st.session_state.messages, f, indent=4)

                st.rerun()

        # --- Read Response Button ---
        if st.button("🗣️ Read Last Response", key="chat_read"):
            if st.session_state.get("chat_response"):
                speak_text(st.session_state["chat_response"])
            else:
                st.warning("No response yet to read.")

        # --- Chat Management ---
        st.markdown("### ⚙️ Chat Management")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Save Chat", key="chat_save"):
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(st.session_state.messages, f, indent=4)
                st.success("✅ Chat saved successfully!")

        with col2:
            if st.button("📂 Load Chat", key="chat_load"):
                if os.path.exists(HISTORY_FILE):
                    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                        st.session_state.messages = json.load(f)
                    st.success("✅ Chat loaded!")
                    st.rerun()
                else:
                    st.error("No chat history file found!")

        # --- Clear Chat ---
        with st.expander("🧹 Clear Chat History"):
            confirm = st.checkbox("Yes, I really want to clear my chat history", key="confirm_clear_chat")
            if st.button("🧼 Clear Now", key="chat_clear"):
                if confirm:
                    st.session_state.messages = []
                    if os.path.exists(HISTORY_FILE):
                        os.remove(HISTORY_FILE)
                    st.success("Chat history cleared!")
                    st.rerun()
                else:
                    st.warning("Please confirm before clearing.")

                    
        

# -----------------------
# TAB 2: Flashcards & Quiz
# -----------------------
with tab2:
    set_active_tab(tab_labels[1])
    if st.session_state.active_tab == tab_labels[1]:
        st.subheader("🧩 Generate & Study Flashcards or Quizzes")

        # --- Helper functions
        def generate_flashcards(text):
            prompt = f"Create 10 short flashcards from the text below:\n\n{text}\n\nFormat:\nQ: ...\nA: ..."
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content

        def generate_quiz(text):
            prompt = f"Create 10 multiple-choice questions (4 options each) with answers based on:\n\n{text}\n\nFormat:\nQ1. ...\na) ...\nb) ...\nc) ...\nd) ...\nAnswer: ..."
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content

        # --- UI selectors
        option = st.radio("📘 Choose type:", ["Flashcards", "Quiz"], horizontal=True, key="fc_choice")
        source = st.radio("📚 Generate from:", ["Chat History", "Custom Text", "PDF File"], horizontal=True, key="fc_source")

        # ensure state keys exist
        for key in ["flash_input", "spoken_text_temp"]:
            if key not in st.session_state:
                st.session_state[key] = ""

        text_data = ""

        # ============ 1️⃣ Chat History =============
        if source == "Chat History":
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    chat_data = json.load(f)
                text_data = " ".join([msg["content"] for msg in chat_data if msg["role"] == "user"])
                st.success("✅ Loaded chat history for generation.")
            except FileNotFoundError:
                st.error("Chat history not found! Please chat first.")

        # ============ 2️⃣ Custom Text (with speech) =============
        elif source == "Custom Text":
            st.write("🎧 You can type below or use your voice to enter notes.")

            col1, col2 = st.columns([3, 1])
            with col1:
                st.session_state.flash_input = st.text_area(
                    "Enter your custom content here:",
                    value=st.session_state.flash_input or st.session_state.spoken_text_temp,
                    key="custom_text_area",
                    height=200,
                )

            with col2:
                if st.button("🎤 Speak", key="flashcard_speak"):
                    spoken_text = speech_to_text()
                    if spoken_text:
                        # Append new speech text instead of replacing
                        st.session_state.flash_input += " " + spoken_text
                        st.session_state.spoken_text_temp = st.session_state.flash_input

            # text_data = st.session_state.flash_input.strip()
            
            
            st.write("🗣️ Debug speech:", st.session_state.flash_input)
            text_data = (st.session_state.flash_input or st.session_state.spoken_text_temp).strip()

            
            


        # ============ 3️⃣ PDF Upload =============
        elif source == "PDF File":
            uploaded_pdf = st.file_uploader("📄 Upload a PDF file", type=["pdf"], key="fc_pdf")
            if uploaded_pdf:
                pdf_reader = PyPDF2.PdfReader(uploaded_pdf)
                text_data = "".join(page.extract_text() or "" for page in pdf_reader.pages)
                st.success(f"✅ Extracted {len(text_data)} characters from PDF.")

        # ============ ⚙️ Generate Flashcards/Quiz =============
        if st.button("🚀 Generate Flashcards/Quiz", key="generate_flashcards"):
            if not text_data:
                st.warning("Please provide some text first.")
            else:
                with st.spinner("Generating..."):
                    output = generate_flashcards(text_data[:8000]) if option == "Flashcards" else generate_quiz(text_data[:8000])

                cards = []
                for block in output.split("Q:")[1:]:
                    parts = block.strip().split("A:")
                    if len(parts) == 2:
                        q, a = parts
                        cards.append({"Q": q.strip(), "A": a.strip()})

                if not cards:  # fallback for quiz or unstructured output
                    cards = [{"Q": "Generated Output", "A": output.strip()}]

                st.session_state["flashcards"] = cards
                st.session_state["current_card"] = 0

                # Auto-save
                with open(FLASH_FILE, "w", encoding="utf-8") as f:
                    json.dump(cards, f, indent=4)
                st.success(f"✅ Generated & saved {len(cards)} items!")

        # ============ 💾 Viewer / Save / Load Section ============
        if "flashcards" in st.session_state and st.session_state["flashcards"]:
            cards = st.session_state.flashcards
            idx = st.session_state.get("current_card", 0)
            current = cards[idx]

            st.markdown("---")
            st.markdown(f"### 🧠 Card {idx + 1} of {len(cards)}")
            st.info(f"**❓ Q:** {current.get('Q', '')}")
            st.success(f"**💡 A:** {current.get('A', '')}")

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("⬅️ Prev", key="prev_card"):
                    if idx > 0:
                        st.session_state.current_card -= 1
                        st.rerun()
            with c2:
                if st.button("🗣️ Read Q", key="read_q"):
                    speak_text(current.get("Q", ""))
            with c3:
                if st.button("🔊 Read A", key="read_a"):
                    speak_text(current.get("A", ""))
            with c4:
                if st.button("➡️ Next", key="next_card"):
                    if idx < len(cards) - 1:
                        st.session_state.current_card += 1
                        st.rerun()

            st.markdown("---")
            save_col, load_col = st.columns(2)
            with save_col:
                if st.button("💾 Save Flashcards", key="save_flashcards_btn"):
                    with open(FLASH_FILE, "w", encoding="utf-8") as f:
                        json.dump(cards, f, indent=4)
                    st.success("✅ Saved successfully!")
            with load_col:
                if st.button("📂 Load Saved Cards", key="load_flashcards_btn"):
                    if os.path.exists(FLASH_FILE):
                        with open(FLASH_FILE, "r", encoding="utf-8") as f:
                            st.session_state["flashcards"] = json.load(f)
                            st.session_state["current_card"] = 0
                        st.success("✅ Loaded saved flashcards!")
                        st.rerun()
                    else:
                        st.warning("No saved file found.")


# -----------------------
# TAB 3: PDF Summarizer
# -----------------------
with tab3:
    set_active_tab(tab_labels[2])
    if st.session_state.active_tab == tab_labels[2]:
        st.subheader("📄 Summarize or Generate from Your Study PDFs")
        user_prompt = st.text_input(
            "Enter what you want me to do (e.g., 'Summarize in 5 points', 'Create quiz from this PDF', 'Make flashcards', etc.)",
            value="Summarize this PDF in simple bullet points.",
            key="pdf_prompt"
        )

        uploaded_pdf = st.file_uploader("Upload a PDF file", type=["pdf"], key="pdf_uploader_tab3")
        if uploaded_pdf:
            pdf_reader = PyPDF2.PdfReader(uploaded_pdf)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
            st.success(f"✅ Extracted {len(text)} characters from PDF.")

            if st.button("Generate Output", key="pdf_process"):
                with st.spinner("Processing your PDF..."):
                    prompt = f"{user_prompt}\n\nPDF Content:\n{text[:10000]}"
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a helpful AI tutor."},
                            {"role": "user", "content": prompt},
                        ],
                    )
                    summary = response.choices[0].message.content
                    st.text_area("📘 Output:", value=summary, height=400)

# End of file
