# emotional_busylight.py

import pygame
import hid
import sys
from time import sleep
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import numpy as np
import pyttsx3
from gtts import gTTS
import os
import threading
from pygame import mixer
import pyperclip

import speech_recognition as sr  # pip install SpeechRecognition

# Import our command definitions
from busylight_commands import (
    COMMANDS, KEEPALIVE, COLOR_RGB, EMOTION_COLORS,
    VENDOR_ID, PRODUCT_IDS
)



# Add this to your TextToSpeech class or create a new SpeechInput class
class SpeechInput:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        
        # Adjust for ambient noise on startup
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
    
    def draw_indicator(self, screen, pos=(700, 50), size=30):
        """Draw microphone indicator"""
        # Red when not listening, Green when listening
        color = (0, 255, 0) if self.is_listening else (255, 0, 0)
        pygame.draw.circle(screen, color, pos, size)
        
        # Draw microphone icon
        mic_color = (0, 0, 0) if self.is_listening else (255, 255, 255)
        mic_rect = pygame.Rect(pos[0] - 5, pos[1] - 10, 10, 20)
        pygame.draw.rect(screen, mic_color, mic_rect)
        pygame.draw.circle(screen, mic_color, (pos[0], pos[1] - 10), 5)


    def listen(self):
        """Listen for speech and convert to text"""
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=None)
                text = self.recognizer.recognize_google(audio)
                return text
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return None
        

class TextToSpeech:
    def __init__(self, use_offline=True):
        self.use_offline = use_offline
        if use_offline:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 175)
            self.engine.setProperty('volume', 0.9)
            voices = self.engine.getProperty('voices')
            print("Loading voices...")
        # Print available voices (useful for debugging)
            for idx, voice in enumerate(voices):
                print(f"Voice {idx}:")
                print(f" - ID: {voice.id}")
                print(f" - Name: {voice.name}")
                print(f" - Languages: {voice.languages}")
                print(f" - Gender: {voice.gender}")
                print(f" - Age: {voice.age}\n")
        
        # Set voice (typically index 1 is a female voice if available)
        if len(voices) > 1:
            self.engine.setProperty('voice', voices[1].id)
        
        else:
            mixer.init()

    def speak(self, text):
        if self.use_offline:
            threading.Thread(target=self._speak_offline, args=(text,)).start()
        else:
            threading.Thread(target=self._speak_online, args=(text,)).start()

    def _speak_offline(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

    def _speak_online(self, text):
        try:
            tts = gTTS(text=text, lang='en')
            tts.save("temp_speech.mp3")
            mixer.music.load("temp_speech.mp3")
            mixer.music.play()
            while mixer.music.get_busy():
                sleep(0.1)
            mixer.music.unload()
            os.remove("temp_speech.mp3")
        except Exception as e:
            print(f"Error in text-to-speech: {e}")

class EmotionClassifier:
    def __init__(self, model_name="j-hartmann/emotion-english-distilroberta-base"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.labels = ['anger', 'disgust', 'fear', 'joy', 'neutral', 'sadness', 'surprise']
        
    def classify(self, text):
           
           inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
           inputs = {k: v.to(self.device) for k, v in inputs.items()}
    
           with torch.no_grad():
                outputs = self.model(**inputs)
    
           probs = torch.nn.functional.softmax(outputs.logits, dim=1)
           probs = probs.cpu().numpy()[0]
           prediction = int(np.argmax(probs))
    
           # Create dictionary of emotion probabilities
           emotion_probs = {emotion: float(prob) for emotion, prob in zip(self.labels, probs)}
    
           return self.labels[prediction], emotion_probs
    

class EmotionalBusylight:
    def __init__(self):
        self.vid = VENDOR_ID
        self.pid = PRODUCT_IDS
        self.device = None
        self.current_color = 'off'
        
        # Initialize emotion classifier and text-to-speech
        self.emotion_classifier = EmotionClassifier()
        self.tts = TextToSpeech(use_offline=True)
        
        # Start connection
        self.connect()
        
        # Start keepalive thread
        self.keepalive_thread = threading.Thread(target=self._keepalive_loop)
        self.keepalive_thread.daemon = True
        self.keepalive_thread.start()

    def _keepalive_loop(self):
        """Send keepalive signals periodically"""
        while True:
            if self.device:
                try:
                    self.device.write(KEEPALIVE)
                except Exception as e:
                    print(f"Keepalive error: {e}")
            sleep(30)

    def connect(self):
        """Connect to multiple Busylight devices"""
        self.devices = []
        for pid in self.pid:
            devices = hid.enumerate(self.vid, pid)
            for device_info in devices:
                try:
                    device = hid.device()
                    device.open_path(device_info['path'])
                    self.devices.append(device)
                    print(f"Connected to Busylight at {device_info['path']}")
                except Exception as e:
                    print(f"Failed to connect to device: {e}")

            if not self.devices:
                print("No Busylight devices found")
        else:
            print(f"Connected to {len(self.devices)} Busylight device(s)")
    
    def disconnect(self):
        """Disconnect from the Busylight device"""
        if self.device:
            self.device.close()

    def process_text(self, text):
        """Process text through emotion classification and speech"""
        # Classify emotion
        emotion, probs = self.emotion_classifier.classify(text)
        
        # Speak the text
        self.tts.speak(text)
        
        # Set light color
        self.set_emotion_color(emotion, probs)
        
        return emotion, probs


    def set_emotion_color(self, emotion, probs):
        """Set the light color based on detected emotion"""
        """Set the light color based on detected emotion for all devices"""
        if not self.devices:
             print("No devices connected")
             return

        color = EMOTION_COLORS.get(emotion, 'off')
        command = COMMANDS.get(color, COMMANDS['off'])
    
        for i, device in enumerate(self.devices):
            try:
                 device.write(command)
                 print(f"Set color for device {i}: {emotion} ({color}) - Confidence: {probs[emotion]*100:.1f}%")
            except Exception as e:
                print(f"Error setting color for device {i}: {e}")


    def turn_off(self):
        """Turn off the light"""
        if self.device:
            self.device.write(COMMANDS['off'])
            self.current_color = 'off'
            print("Light turned off")

def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 400))
    pygame.display.set_caption("Emotional Busylight Controller with Speech")
    
    # Initialize the Emotional Busylight
    light = EmotionalBusylight()
    speech_input = SpeechInput()

    # Set up font for display
    font = pygame.font.Font(None, 36)
    input_text = ""
    input_active = False
    
    running = True
    last_analysis_time = 0
    emotion_result = None
    
    while running:
        current_time = pygame.time.get_ticks()
        screen.fill((40, 40, 40))  # Dark gray background
        
           # Check for backtick key hold
        keys = pygame.key.get_pressed()
        speech_input.is_listening = keys[pygame.K_EQUALS]
        
        if speech_input.is_listening:
            # Try to get speech input
            spoken_text = speech_input.listen()
            if spoken_text:
                input_text += spoken_text + " "

        #remove = from inpit text
        input_text = input_text.replace("=", "")
        # Draw text input box
        input_box = pygame.Rect(50, 300, 700, 40)
        color = (255, 255, 255) if input_active else (128, 128, 128)
        pygame.draw.rect(screen, color, input_box, 2)
        
        # Render input text
        txt_surface = font.render(input_text, True, (255, 255, 255))
        screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))
        
        # Draw instructions
        instructions = font.render("Type, paste, or hold SPACE key for speak", True, (255, 255, 255))
        screen.blit(instructions, (50, 250))
        
        speech_input.draw_indicator(screen)
        # Display current emotion and color
        if emotion_result:
            emotion_text = font.render(f"Detected Emotion: {emotion_result[0]} ({emotion_result[1][emotion_result[0]]*100:.1f}%)", 
                             True, (255, 255, 255))
            screen.blit(emotion_text, (50, 100))
    
            color_name = EMOTION_COLORS.get(emotion_result[0], 'off')
            rgb = COLOR_RGB.get(color_name, (40, 40, 40))
            color_rect = pygame.Rect(50, 150, 300, 50)
            pygame.draw.rect(screen, rgb, color_rect)
        
        pygame.display.flip()
        
        for event in pygame.event.get():
           
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_RETURN and input_text.strip():
                    if current_time - last_analysis_time >= 3000:
                        emotion_result = light.process_text(input_text)
                        input_text = ""
                        last_analysis_time = current_time
                # Add paste support (Ctrl+V)
                elif event.key == pygame.K_v and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    try:
                        input_text += pyperclip.paste()
                    except:
                        print("Error pasting text")
                # Add cut support (Ctrl+X)
                elif event.key == pygame.K_x and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    try:
                        pyperclip.copy(input_text)
                        input_text = ""
                    except:
                        print("Error cutting text")
                # Add copy support (Ctrl+C)
                elif event.key == pygame.K_c and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    try:
                        pyperclip.copy(input_text)
                    except:
                        print("Error copying text")
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    input_text += event.unicode
        
        sleep(0.1)
    
    # Cleanup
    light.turn_off()
    light.disconnect()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
