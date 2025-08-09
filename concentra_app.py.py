import sys
import os
import time
import io

# --- PyQt6 Imports ---
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt6.QtGui import QMovie, QFont
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal

# --- Voice Assistant Imports ---
# Make sure you have installed these libraries: pip install PyQt6 pygame gTTS SpeechRecognition word2number pyaudio
import pygame
from gtts import gTTS
import speech_recognition as sr
from word2number import w2n

# --- PyInstaller Helper Function ---
# This function is the key to making sure the GIF is always found.
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# --- Helper Functions for Voice Assistant ---
def speak_text(text):
    """Converts text to speech and plays it."""
    try:
        tts = gTTS(text=text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        pygame.mixer.init()
        pygame.mixer.music.load(fp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            continue
        pygame.mixer.quit()
        del fp
    except Exception as e:
        print(f"Error in speak_text: {e}")

def word_to_num(word):
    """Converts a word representing a number to a float."""
    if not isinstance(word, str):
        return None
    word = word.lower().strip()
    try:
        return float(word)
    except ValueError:
        pass
    try:
        return float(w2n.word_to_num(word))
    except ValueError:
        return None

# --- Worker Thread for Voice Logic ---
class VoiceWorker(QThread):
    """Worker thread to handle all voice and alarm logic."""
    status_updated = pyqtSignal(str)
    finished = pyqtSignal()

    def get_voice_input(self, prompt_text="When should I remind you"):
        """Listens for voice input and returns the recognized text."""
        speak_text(prompt_text)
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            self.status_updated.emit("Listening...")
            speak_text("Listening")
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=5)
            except sr.WaitTimeoutError:
                self.status_updated.emit("Listening timed out. Try again.")
                return None
        try:
            text = r.recognize_google(audio)
            self.status_updated.emit(f"You said: {text}")
            speak_text(f"You said {text}")
            return text
        except sr.UnknownValueError:
            self.status_updated.emit("Could not understand audio. Please try again.")
            speak_text("Sorry, I did not understand.")
            return None
        except sr.RequestError:
            self.status_updated.emit("Speech service error. Please check connection.")
            speak_text("Sorry, there is a problem with the speech service.")
            return None

    def run(self):
        """The main logic for the voice assistant alarm."""
        self.status_updated.emit("Hello! I am Concentra. How many minutes?")
        speak_text("Hello! I am Concentra, your study and focus assistant. I am here to help you stay focused. Please tell me how many minutes you want to set the alarm for.")
        alarm_minutes = 0
        while True:
            user_input = self.get_voice_input("Set alarm time in minutes")
            if user_input is None:
                continue
            minutes = word_to_num(user_input)
            if minutes is not None and minutes > 0:
                alarm_minutes = minutes
                break
            else:
                self.status_updated.emit("Invalid input. Please say a positive number.")
                speak_text("Invalid input. Please say a number.")
        original_minutes = alarm_minutes
        self.status_updated.emit(f"Timer set for {original_minutes} minutes.")
        speak_text(f"Okay, I will remind you in {original_minutes} minutes.")
        while True:
            # For testing, you can use a shorter time, e.g., time.sleep(10) for 10 seconds
            time.sleep(original_minutes * 60)
            self.status_updated.emit("Time's up! Say 'stop' to end.")
            speak_text("Hey, are you studying? I’m just here to remind you — stay focused, you can do it! Do you want to continue with the same timer or stop? Say 'stop' to end, or say nothing to continue.")
            response = self.get_voice_input("Continue or stop?")
            if response and "stop" in response.lower():
                self.status_updated.emit("Alarm stopped. Great work!")
                speak_text("Okay, stopping the alarm. Have a great day!")
                break
            else:
                self.status_updated.emit(f"Continuing timer for {original_minutes} minutes.")
                speak_text(f"Okay, continuing for another {original_minutes} minutes.")
        self.finished.emit()

# --- Main Application GUI ---
class GifBackgroundApp(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.setWindowTitle("Concentra")
        self.setFixedSize(1000, 700)
        self.setup_background()
        self.setup_foreground()

    def setup_background(self):
        """Sets up the background GIF or a fallback color."""
        self.background_label = QLabel(self)
        self.background_label.setGeometry(0, 0, self.width(), self.height())
        
        # This uses the helper function to reliably find the GIF
        gif_path = resource_path("background.gif")
        
        if os.path.exists(gif_path):
            self.movie = QMovie(gif_path)
            if self.movie.isValid():
                self.background_label.setMovie(self.movie)
                self.movie.setScaledSize(QSize(self.width(), self.height()))
                self.movie.start()
                return
        
        print(f"Error: Could not find or load {gif_path}")
        self.set_fallback_background()

    def set_fallback_background(self):
        self.background_label.setStyleSheet("background-color: #3B4252;")

    def setup_foreground(self):
        """Sets up the UI elements on top of the background."""
        self.foreground_container = QWidget(self)
        self.foreground_container.setGeometry(0, 0, self.width(), self.height())
        self.foreground_container.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(self.foreground_container)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label = QLabel("Concentra")
        font = QFont("Helvetica", 60, QFont.Weight.Bold)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: white; background-color: transparent;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.start_button = QPushButton("Start Assistant")
        self.start_button.setFont(QFont("Helvetica", 14, QFont.Weight.Bold))
        self.start_button.setFixedSize(200, 50)
        self.start_button.setStyleSheet("""
            QPushButton { color: white; background-color: #5E81AC; border-radius: 15px; border: 2px solid #81A1C1; }
            QPushButton:hover { background-color: #81A1C1; }
            QPushButton:pressed { background-color: #4C566A; }
        """)
        self.start_button.clicked.connect(self.start_voice_assistant)
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(20)

    def start_voice_assistant(self):
        """Creates and starts the voice worker thread."""
        self.start_button.hide()
        self.update_status("Starting assistant...")
        self.worker = VoiceWorker()
        self.worker.status_updated.connect(self.update_status)
        self.worker.finished.connect(self.on_assistant_finished)
        self.worker.start()

    def update_status(self, text):
        """Updates the window title with status from the worker thread."""
        self.setWindowTitle(f"Concentra - {text}")

    def on_assistant_finished(self):
        """Re-enables and shows the start button when the thread is done."""
        self.setWindowTitle("Concentra")
        self.start_button.show()
        self.worker = None

    def resizeEvent(self, event):
        """Handles window resize events."""
        if hasattr(self, 'movie') and self.movie.isValid():
            self.movie.setScaledSize(QSize(self.width(), self.height()))
        self.background_label.setGeometry(0, 0, self.width(), self.height())
        self.foreground_container.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GifBackgroundApp()
    window.show()
    sys.exit(app.exec())