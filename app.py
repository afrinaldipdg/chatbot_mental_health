import streamlit as st
import json
import os
import base64
from io import BytesIO
import time

# Impor ChatterBot dan trainernya
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer

# Impor gTTS untuk Text-to-Speech fallback
from gtts import gTTS

# --- Konfigurasi Global ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, 'db.sqlite3') # Path absolut untuk database SQLite

# --- Pemuatan CSS Kustom ---
def load_css(file_name):
    """Membaca file CSS dan menginjeksikannya ke Streamlit."""
    css_path = os.path.join(PROJECT_ROOT, 'assets', file_name)
    try:
        with open(css_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"File CSS '{file_name}' tidak ditemukan di assets/. Menggunakan gaya default.")

load_css("styles.css")

# --- Inisialisasi dan Training ChatterBot ---
@st.cache_resource # Cache sumber daya ini agar bot tidak diinisialisasi ulang setiap rerun
def initialize_chatbot():
    """Menginisialisasi dan melatih ChatterBot."""
    st.session_state.chatbot_initialized = False # Flag untuk menunjukkan inisialisasi
    # --- Unduh Model spaCy jika belum ada ---
    # Cek apakah model 'en_core_web_sm' sudah terinstal
    # Ini akan memicu pengunduhan jika belum ada
    try:
        import spacy
        spacy.load("en_core_web_sm")
        st.success("Model spaCy 'en_core_web_sm' sudah tersedia.")
    except OSError:
        st.info("Mengunduh model spaCy 'en_core_web_sm' (diperlukan oleh ChatterBot)... Ini mungkin memakan waktu sebentar.")
        try:
            # Perintah untuk mengunduh model
            subprocess.check_call(['python', '-m', 'spacy', 'download', 'en_core_web_sm'])
            st.success("Model spaCy 'en_core_web_sm' berhasil diunduh!")
        except Exception as e:
            st.error(f"Gagal mengunduh model spaCy: {e}")
            st.warning("Chatbot mungkin tidak berfungsi dengan benar tanpa model spaCy.")
    # --- Akhir bagian unduh spaCy ---
    if not os.path.exists(DB_PATH):
        # Jika database belum ada, ini berarti bot belum pernah dilatih
        st.info("Melatih chatbot untuk pertama kali... Ini mungkin memakan waktu sebentar.")
        
        # Inisialisasi ChatterBot dengan read_only=False untuk memungkinkan training
        chatbot_instance = ChatBot('MentalHealthBot',
                                   read_only=False, # Izinkan bot untuk dilatih
                                   storage_adapter='chatterbot.storage.SQLStorageAdapter',
                                   database_uri=f'sqlite:///{DB_PATH}', # Path ke database
                                   logic_adapters=[
                                       'chatterbot.logic.SpecificStatementAdapter',
                                       'chatterbot.logic.BestMatch'
                                   ])

        trainer = ChatterBotCorpusTrainer(chatbot_instance)
        
        # Latih dengan korpus bawaan bahasa Indonesia
        st.text("Training dengan korpus bawaan bahasa Indonesia...")
        trainer.train("chatterbot.corpus.indonesia")
        
        # Latih dengan korpus kustom Anda
        custom_corpus_path = os.path.join(PROJECT_ROOT, 'data', 'mental_health_corpus.yml')
        if os.path.exists(custom_corpus_path):
            st.text("Training dengan korpus kustom mental_health_corpus.yml...")
            try:
                trainer.train(f"data{os.sep}mental_health_corpus.yml") 
                st.success("Pelatihan dengan korpus kustom selesai!")
            except Exception as e:
                st.error(f"Terjadi kesalahan saat melatih dengan korpus kustom: {e}")
        else:
            st.warning("File 'mental_health_corpus.yml' tidak ditemukan di folder data/. Lanjutkan tanpa korpus kustom.")
        
        st.success("Pelatihan chatbot selesai! Bot siap digunakan dalam mode read-only.")
        
    else:
        # Jika database sudah ada, ini berarti bot sudah pernah dilatih
        st.info("Memuat chatbot yang sudah terlatih...")
        chatbot_instance = ChatBot('MentalHealthBot',
                                   read_only=True, # Bot akan selalu dalam mode read-only setelah training
                                   storage_adapter='chatterbot.storage.SQLStorageAdapter',
                                   database_uri=f'sqlite:///{DB_PATH}', # Path ke database
                                   logic_adapters=[
                                       'chatterbot.logic.SpecificStatementAdapter',
                                       'chatterbot.logic.BestMatch'
                                   ])
        st.success("Chatbot berhasil dimuat dalam mode read-only.")
    
    st.session_state.chatbot_initialized = True
    return chatbot_instance

chatbot = initialize_chatbot()

# --- Fungsi untuk Mengonversi Teks ke Suara (gTTS) ---
def text_to_speech_gtts(text):
    """Mengonversi teks ke audio MP3 menggunakan gTTS dan mengembalikan Base64 Data URL."""
    try:
        tts = gTTS(text=text, lang='id', slow=False)
        audio_fp = BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        audio_base64 = base64.b64encode(audio_fp.read()).decode('utf-8')
        return f"data:audio/mp3;base64,{audio_base64}"
    except Exception as e:
        st.error(f"Gagal mengonversi teks ke suara dengan gTTS: {e}")
        return None

# --- Streamlit UI ---
st.set_page_config(page_title="Chatbot Cek Kesehatan Mental", layout="centered")

st.title("🤖 Chatbot Cek Kesehatan Mental")
st.markdown("Halo! Saya adalah bot yang bisa membantumu bicara tentang perasaanmu.")
st.markdown("Tekan tombol **'Mulai Bicara'** untuk merekam suaramu.")

# Inisialisasi riwayat chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Tampilkan riwayat chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Komponen HTML/JS untuk Input Suara dan TTS ---
html_component = """
<div id="voice-input-output">
    <button id="startRecording" style="background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-top: 10px;">Mulai Bicara</button>
    <button id="stopRecording" style="background-color: #f44336; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-top: 10px; display:none;">Stop Rekam</button>
    <p id="status" style="margin-top: 10px; font-style: italic;">Tekan "Mulai Bicara" untuk memulai...</p>
    <audio id="audioPlayback" controls style="display:none;"></audio>
</div>

<script>
    const startRecordingBtn = document.getElementById('startRecording');
    const stopRecordingBtn = document.getElementById('stopRecording');
    const statusDiv = document.getElementById('status');
    const audioPlayback = document.getElementById('audioPlayback');

    let recognition;
    let isRecording = false;

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        recognition = new (window.webkitSpeechRecognition || window.SpeechRecognition)();
        recognition.continuous = false; 
        recognition.interimResults = false;
        recognition.lang = 'id-ID'; 

        recognition.onstart = function() {
            isRecording = true;
            statusDiv.textContent = 'Merekam suara... Katakan sesuatu.';
            startRecordingBtn.style.display = 'none';
            stopRecordingBtn.style.display = 'inline-block';
        };

        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            statusDiv.textContent = 'Kamu bilang: "' + transcript + '"';
            if (window.streamlitReportMessage) {
                window.streamlitReportMessage({
                    type: 'FROM_JS',
                    command: 'send_text',
                    text: transcript
                });
            }
        };

        recognition.onend = function() {
            isRecording = false;
            statusDiv.textContent = 'Perekaman berakhir.';
            stopRecordingBtn.style.display = 'none';
            startRecordingBtn.style.display = 'inline-block';
        };

        recognition.onerror = function(event) {
            console.error('Speech Recognition Error:', event.error);
            statusDiv.textContent = 'Terjadi kesalahan pada pengenalan suara: ' + event.error + '. Coba lagi atau pastikan mikrofon aktif.';
            isRecording = false;
            stopRecordingBtn.style.display = 'none';
            startRecordingBtn.style.display = 'inline-block';
        };

        startRecordingBtn.onclick = function() {
            if (!isRecording) {
                recognition.start();
            }
        };

        stopRecordingBtn.onclick = function() {
            if (isRecording) {
                recognition.stop();
            }
        };

    } else {
        statusDiv.textContent = 'Maaf, browser Anda tidak mendukung Web Speech API untuk input suara.';
        startRecordingBtn.disabled = true;
    }

    window.speakText = function(text, audioUrl) {
        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'id-ID'; 
            utterance.rate = 1.0; 
            utterance.pitch = 1.0; 
            window.speechSynthesis.cancel(); 
            window.speechSynthesis.speak(utterance);
            console.log("Speaking via browser TTS:", text);
        } else {
            console.warn('Maaf, browser Anda tidak mendukung Speech Synthesis API. Memutar audio dari server (gTTS) jika tersedia.');
            if (audioUrl) {
                audioPlayback.src = audioUrl;
                audioPlayback.style.display = 'block';
                audioPlayback.play();
                console.log("Playing audio via gTTS fallback.");
            }
        }
    };

    window.addEventListener('message', event => {
        if (event.source !== window.parent) {
            return;
        }
        if (event.data.type === 'streamlit:component_data' && event.data.payload && event.data.payload.command === 'send_to_js') {
            const payload = event.data.payload.payload;
            if (payload.type === 'FROM_PY' && payload.command === 'speak_text') {
                window.speakText(payload.text, payload.audio_url);
            }
        }
    });

</script>
"""

from streamlit.components.v1 import html
component_value = html(html_component, height=200)

# Logic untuk menerima pesan dari JavaScript
if component_value:
    if "command" in component_value and component_value["command"] == "send_text":
        user_input = component_value["text"]
        if user_input and (not st.session_state.messages or st.session_state.messages[-1]["content"] != user_input or st.session_state.messages[-1]["role"] != "user"):
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.experimental_rerun()

# Jika ada input user yang baru dan bot sudah diinisialisasi
if st.session_state.get('chatbot_initialized', False) and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    user_message = st.session_state.messages[-1]["content"]
    lower_user_message = user_message.lower() # Konversi ke lowercase sekali untuk efisiensi

    with st.spinner("Bot sedang berpikir..."):
        bot_response = "" # Inisialisasi respons bot
        response_handled_by_custom_logic = False # Flag untuk menandai apakah respons sudah ditangani oleh logika kustom

        # --- Logika Deteksi Kesehatan Mental Berbasis Kata Kunci (Ditingkatkan) ---
        # PRIORITAS TERTINGGI UNTUK KRISIS KESEHATAN MENTAL
        if any(keyword in lower_user_message for keyword in ["bunuh diri", "mengakhiri hidup", "mati saja", "tidak ingin hidup", "menyakiti diri", "self-harm", "mengiris", "lompat", "akhiri penderitaan"]):
            bot_response = (
                "Saya sangat mengkhawatirkanmu mendengar ini. Hidupmu sangat berharga dan kamu tidak sendirian dalam menghadapi ini. "
                "Penting untuk diingat bahwa emosi ini adalah sementara dan kamu bisa melewatinya. Ada banyak orang yang peduli padamu dan siap membantu. "
                "Tolong segera cari bantuan profesional. Kamu bisa menghubungi **hotline bunuh diri di 119 ext. 8 (Indonesia)** atau berbicara dengan psikolog, psikiater, atau orang terpercaya. "
                "Bertahanlah. Kamu kuat, dan ada harapan. Apa yang bisa kamu lakukan saat ini untuk merasa lebih aman?"
            )
            response_handled_by_custom_logic = True

        # Kategori: Kesedihan / Depresi (Tetap prioritas di logika custom untuk respons lebih mendalam)
        elif any(keyword in lower_user_message for keyword in ["sedih", "sendu", "murung", "galau", "depresi", "dukacita", "patah hati", "hancur", "terpuruk", "berat", "kosong"]):
            bot_response = (
                "Saya turut prihatin mendengar perasaanmu. Perasaan sedih dan terpuruk itu adalah bagian alami dari pengalaman manusia, "
                "tetapi jangan biarkan itu merenggut harapanmu. Ingat, kamu tidak sendirian dalam merasakan ini. "
                "Sebagaimana filosof stoa mengajarkan, ada hal-hal yang bisa kita kendalikan (pikiran dan tindakan kita) dan ada yang tidak. "
                "Fokuslah pada apa yang bisa kamu ubah, dan lepaskan kekhawatiran atas yang tidak bisa. Apa yang paling memberatkanmu saat ini?"
            )
            if "ingin sendiri" in lower_user_message:
                bot_response += " Meskipun keinginan untuk menyendiri terkadang dibutuhkan, cobalah untuk tidak terlalu lama terisolasi. Terhubung dengan orang yang kamu percaya bisa menjadi jembatan untuk keluar dari kegelapan."
            if "menangis" in lower_user_message:
                bot_response += " Menangis adalah bentuk pelepasan emosi yang sehat. Biarkan air matamu mengalir jika itu membuatmu merasa lega. Itu bukan tanda kelemahan, melainkan kekuatan untuk merasakan."
            if "putus asa" in lower_user_message or "tidak ada harapan" in lower_user_message:
                bot_response += " Ketika harapan terasa pudar, ingatlah bahwa setiap malam akan diikuti fajar. Ada kekuatan dalam dirimu yang mungkin belum kamu sadari. Cobalah fokus pada satu langkah kecil yang bisa kamu lakukan hari ini."
            response_handled_by_custom_logic = True

        # Kategori: Kecemasan / Stres (Tetap prioritas di logika custom untuk respons lebih mendalam)
        elif any(keyword in lower_user_message for keyword in ["cemas", "khawatir", "panik", "gelisah", "stres", "takut", "deg-degan", "overthinking", "tegang", "bingung", "berat pikiran"]):
            bot_response = (
                "Saya memahami bahwa kamu sedang merasakan kecemasan atau stres. Perasaan ini bisa sangat membebani. "
                "Dalam pandangan stoikisme, kita tidak bisa mengendalikan peristiwa eksternal, tetapi kita bisa mengendalikan bagaimana kita meresponsnya. "
                "Fokuskan energimu pada hal-hal yang berada dalam kendalimu. Tarik napas dalam-dalam, pusatkan perhatianmu pada saat ini. Apa yang paling membebani pikiranmu saat ini?"
            )
            if "sulit tidur" in lower_user_message or "insomnia" in lower_user_message:
                bot_response += " Kecemasan memang seringkali mengganggu kualitas tidur. Cobalah menciptakan rutinitas tidur yang menenangkan, seperti membaca buku atau mendengarkan musik lembut sebelum tidur, dan hindari layar gawai."
            if "jantung berdebar" in lower_user_message:
                bot_response += " Jika jantungmu berdebar kencang atau merasakan serangan panik, cobalah teknik pernapasan 4-7-8: tarik napas 4 detik, tahan 7 detik, embuskan 8 detik. Ini bisa membantu menenangkan sistem sarafmu."
            if "tekanan" in lower_user_message:
                bot_response += " Tekanan hidup memang bisa sangat menekan. Ingatlah untuk memecah masalah besar menjadi bagian-bagian kecil yang lebih mudah dikelola. Setiap langkah maju, tidak peduli seberapa kecil, adalah kemajuan."
            response_handled_by_custom_logic = True

        # Kategori: Kemarahan / Frustrasi (Tetap prioritas di logika custom untuk respons lebih mendalam)
        elif any(keyword in lower_user_message for keyword in ["marah", "emosi", "frustasi", "jengkel", "kesal", "benci", "geram", "dendam", "meledak"]):
            bot_response = (
                "Kemarahan yang kamu rasakan adalah emosi yang kuat dan wajar. Namun, bagaimana kita mengelolanya adalah hal yang penting. "
                "Stoikisme mengajarkan kita untuk tidak membiarkan emosi menguasai diri. Kenali pemicunya, dan cobalah untuk merespons dengan bijak daripada bereaksi impulsif. "
                "Apa yang paling memicu kemarahanmu saat ini?"
            )
            if "merusak" in lower_user_message or "menyakiti" in lower_user_message:
                bot_response = ( # Override untuk keamanan
                    "Jika kamu merasa ingin merusak sesuatu atau menyakiti diri sendiri/orang lain karena kemarahan, tolong hentikan. "
                    "Prioritaskan keselamatan. Cari tempat yang tenang, tarik napas dalam, dan pertimbangkan untuk berbicara dengan seseorang segera. "
                    "Ada cara sehat untuk menyalurkan kemarahanmu."
                )
            response_handled_by_custom_logic = True

        # Kategori: Stigma / Penilaian Diri Negatif (Tetap prioritas di logika custom untuk respons lebih mendalam)
        elif any(keyword in lower_user_message for keyword in ["malu", "aib", "gila", "tidak waras", "rendah diri", "tidak berharga", "buruk", "cacat", "gagal", "bodoh", "tak pantas"]):
            bot_response = (
                "Perasaan seperti itu bisa sangat melukai, tapi saya ingin kamu tahu bahwa kamu berharga. "
                "Kata-kata yang kita ucapkan pada diri sendiri memiliki kekuatan besar. Coba tantang pikiran negatif itu. "
                "Ingatlah, kesehatan mental sama pentingnya dengan kesehatan fisik. Tidak ada yang perlu dimalukan dalam mencari dukungan jika kamu merasa tidak baik. Kamu layak mendapatkan kebaikan."
            )
            response_handled_by_custom_logic = True
            
        # Kategori: Rasa Sakit Fisik Akibat Psikis (Tetap prioritas di logika custom untuk respons lebih mendalam)
        elif any(keyword in lower_user_message for keyword in ["sakit kepala", "sakit perut", "pusing", "mual", "badan lemas", "nyeri", "pegel"]) and any(emo_keyword in lower_user_message for emo_keyword in ["stres", "cemas", "depresi", "tekanan"]):
             bot_response = (
                 "Terkadang, pikiran dan emosi kita, seperti stres atau kecemasan yang kamu rasakan, dapat bermanifestasi sebagai rasa sakit fisik. "
                 "Ini adalah cara tubuhmu berkomunikasi denganmu. Penting untuk mendengarkannya dan mempertimbangkan bagaimana kondisi mentalmu memengaruhi fisikmu. "
                 "Mengelola stres bisa membantu meredakan gejala fisik ini."
             )
             response_handled_by_custom_logic = True

        # Untuk semua kasus lain yang tidak ditangani oleh logika kustom prioritas tinggi, gunakan ChatterBot
        if not response_handled_by_custom_logic:
            bot_response = str(chatbot.get_response(user_message))
            # Fallback jika ChatterBot tidak memiliki respons yang baik
            if bot_response.strip() == "": # Jika respons kosong
                bot_response = "Saya kurang mengerti apa yang kamu maksud. Bisakah kamu jelaskan lebih lanjut?"
            elif "unknown" in bot_response.lower() or "tidak mengerti" in bot_response.lower(): # Jika respons generic dari ChatterBot
                 bot_response = "Saya mendengar kamu, tapi mungkin butuh sedikit lebih banyak informasi. Bisakah kamu ceritakan lebih detail tentang perasaanmu?"


        # Tambahkan respons bot ke riwayat chat
        if not st.session_state.messages or st.session_state.messages[-1]["content"] != bot_response or st.session_state.messages[-1]["role"] != "assistant":
            st.session_state.messages.append({"role": "assistant", "content": bot_response})

            # Kirim respons bot kembali ke JavaScript untuk dibacakan
            audio_data_url = text_to_speech_gtts(bot_response)

            # Fix the f-string issue by preparing the text outside the f-string
            escaped_bot_response = bot_response.replace("`", "\\`").replace("$", "\\$")
            
            js_to_execute = f"""
                <script>
                    if (window.parent) {{
                        window.parent.postMessage({{
                            type: 'streamlit:component_data',
                            command: 'send_to_js',
                            payload: {{
                                type: 'FROM_PY',
                                command: 'speak_text',
                                text: `{escaped_bot_response}`,
                                audio_url: '{audio_data_url}'
                            }}
                        }}, '*');
                    }}
                </script>
            """
            st.markdown(js_to_execute, unsafe_allow_html=True)
            
            st.experimental_rerun()
