import streamlit as st
from transformers import pipeline
from gtts import gTTS
from io import BytesIO
import base64

# Inisialisasi IndoBERT QA
@st.cache_resource
def load_qa_pipeline():
    return pipeline("question-answering", model="indobenchmark/indobert-base-p1")

qa = load_qa_pipeline()

# UI Streamlit
st.set_page_config(page_title="Chatbot Kesehatan Mental", layout="centered")
st.title("🧠 Chatbot Kesehatan Mental - IndoBERT")
st.markdown("Halo! Ngobrol yuk. Ketik perasaanmu, nanti saya bantu tanggapi dengan empatik.")

# Riwayat chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Tampilkan pesan lama
for msg in st.session_state.messages:
    with st.chat_message("user"):
        st.markdown(msg["user"])
    with st.chat_message("bot"):
        st.markdown(msg["bot"])

# Input pengguna
user_input = st.chat_input("Ceritain di sini...")

# Proses input
if user_input:
    context = (
        "Saya adalah chatbot empatik untuk membantu kamu mengelola kesehatan mental. "
        "Saya akan menjawab dengan bijaksana, tenang, dan suportif sesuai pertanyaanmu."
    )
    result = qa(question=user_input, context=context)
    bot_reply = result["answer"]

    # Simpan ke riwayat
    st.session_state.messages.append({"user": user_input, "bot": bot_reply})

    # Tampilkan
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("bot"):
        st.markdown(bot_reply)

    # Konversi ke audio
    tts = gTTS(text=bot_reply, lang='id')
    audio_fp = BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    audio_base64 = base64.b64encode(audio_fp.read()).decode('utf-8')
    audio_url = f"data:audio/mp3;base64,{audio_base64}"
    st.audio(audio_url, format="audio/mp3")

# Tombol WA darurat
st.markdown("---")
st.markdown("### 🚨 Butuh bantuan langsung?")
st.markdown("[🆘 Hubungi Konselor via WhatsApp](https://wa.me/6281374212002?text=Halo%20Konselor%2C%20saya%20butuh%20bantuan)", unsafe_allow_html=True)
