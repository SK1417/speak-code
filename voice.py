import asyncio
import threading
import time
from typing import List
from dataclasses import dataclass
from enum import Enum

import speech_recognition as sr
import pyttsx3
from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import queue
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotState(Enum):
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"

@dataclass
class ChatState:
    messages: List[BaseMessage]
    current_state: BotState
    interrupt_requested: bool
    audio_queue: queue.Queue
    response_text: str
    user_input: str
    is_voice_input: bool

class VoiceManager:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.tts_engine = pyttsx3.init()
        self.is_speaking = False
        self.interrupt_flag = threading.Event()
        
        # Configure TTS
        self.tts_engine.setProperty('rate', 150)  # Speed of speech
        voices = self.tts_engine.getProperty('voices')
        if voices:
            self.tts_engine.setProperty('voice', voices[0].id)
    
    def listen_continuously(self, audio_queue: queue.Queue, interrupt_flag: threading.Event):
        """Continuously listen for voice input in a separate thread"""
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        
        logger.info("Voice listener started - say something!")
        
        while True:
            try:
                if interrupt_flag.is_set():
                    break
                    
                with self.microphone as source:
                    # Use a shorter timeout and phrase_time_limit for responsiveness
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                
                try:
                    text = self.recognizer.recognize_google(audio)
                    if text:
                        logger.info(f"Voice input detected: {text}")
                        audio_queue.put(("voice_input", text))
                except sr.UnknownValueError:
                    # Ignore unrecognized speech
                    pass
                except sr.RequestError as e:
                    logger.error(f"Speech recognition error: {e}")
                    
            except sr.WaitTimeoutError:
                # Timeout is expected, continue listening
                continue
            except Exception as e:
                logger.error(f"Error in voice listener: {e}")
                time.sleep(0.1)
    
    def speak_with_interrupt(self, text: str, interrupt_callback):
        """Speak text while checking for interrupts"""
        self.is_speaking = True
        
        # Split text into sentences for better interrupt responsiveness
        sentences = text.split('. ')
        
        for sentence in sentences:
            if interrupt_callback():
                logger.info("Speech interrupted by user")
                self.tts_engine.stop()
                break
                
            if sentence.strip():
                sentence = sentence.strip() + '.' if not sentence.endswith('.') else sentence.strip()
                self.tts_engine.say(sentence)
                self.tts_engine.runAndWait()
        
        self.is_speaking = False
    
    def stop_speaking(self):
        """Stop current speech"""
        if self.is_speaking:
            self.tts_engine.stop()

class VoiceChatbot:
    def __init__(self, api_key: str):
        self.llm = ChatGoogleGenerativeAI(api_key=api_key, model="gemini-1.5-flash")
        self.voice_manager = VoiceManager()
        self.audio_queue = queue.Queue()
        self.interrupt_flag = threading.Event()
        
        # Create the LangGraph workflow
        self.workflow = self._create_workflow()
        self.app = self.workflow.compile()
        
        # Start voice listener thread
        self.voice_thread = threading.Thread(
            target=self.voice_manager.listen_continuously,
            args=(self.audio_queue, self.interrupt_flag),
            daemon=True
        )
        self.voice_thread.start()
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow for the chatbot"""
        workflow = StateGraph(ChatState)
        
        workflow.add_node("check_input", self._check_input_node)
        workflow.add_node("process_message", self._process_message_node)
        workflow.add_node("speak_response", self._speak_response_node)
        workflow.add_node("handle_interrupt", self._handle_interrupt_node)
        
        workflow.set_entry_point("check_input")
        
        workflow.add_edge("check_input", "process_message")
        workflow.add_edge("process_message", "speak_response")
        workflow.add_edge("speak_response", "check_input")
        workflow.add_edge("handle_interrupt", "check_input")
        
        return workflow
    
    def _check_input_node(self, state: ChatState) -> ChatState:
        """Check for user input (voice or text)"""
        try:
            # Check for voice input
            event_type, data = self.audio_queue.get(timeout=0.1)
            if event_type == "voice_input":
                # Check if this is an interrupt
                if state.current_state == BotState.SPEAKING:
                    logger.info("Interrupt detected during speech")
                    state.interrupt_requested = True
                    state.current_state = BotState.INTERRUPTED
                    self.voice_manager.stop_speaking()
                
                state.user_input = data
                state.is_voice_input = True
                state.current_state = BotState.PROCESSING
                
        except queue.Empty:
            # No voice input, maintain current state
            if not state.interrupt_requested:
                state.current_state = BotState.LISTENING
        
        return state
    
    def _process_message_node(self, state: ChatState) -> ChatState:
        """Process the user message and generate AI response"""
        if not state.user_input:
            return state
        
        # Add user message to conversation history
        user_message = HumanMessage(content=state.user_input)
        state.messages.append(user_message)
        
        # Generate AI response
        try:
            response = self.llm.invoke(state.messages)
            ai_message = AIMessage(content=response.content)
            state.messages.append(ai_message)
            state.response_text = response.content
            
            logger.info(f"AI Response: {state.response_text}")
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            state.response_text = "I'm sorry, I encountered an error processing your request."
        
        # Clear user input for next iteration
        state.user_input = ""
        
        return state
    
    def _speak_response_node(self, state: ChatState) -> ChatState:
        """Speak the AI response"""
        if not state.response_text:
            return state
        
        state.current_state = BotState.SPEAKING
        
        # Create interrupt callback
        def check_interrupt():
            try:
                event_type, data = self.audio_queue.get(timeout=0.01)
                if event_type == "voice_input":
                    # Put the input back and signal interrupt
                    self.audio_queue.put((event_type, data))
                    return True
            except queue.Empty:
                pass
            return state.interrupt_requested
        
        # Speak with interrupt capability
        self.voice_manager.speak_with_interrupt(state.response_text, check_interrupt)
        
        # Clear response text
        state.response_text = ""
        state.current_state = BotState.LISTENING
        
        return state
    
    def _handle_interrupt_node(self, state: ChatState) -> ChatState:
        """Handle interrupt scenarios"""
        state.interrupt_requested = False
        state.current_state = BotState.LISTENING
        return state
    
    def run_text_mode(self):
        """Run chatbot in text-only mode"""
        print("Voice-enabled chatbot started! Type 'quit' to exit.")
        print("You can also speak at any time - the bot will listen continuously.")
        
        initial_state = ChatState(
            messages=[],
            current_state=BotState.LISTENING,
            interrupt_requested=False,
            audio_queue=self.audio_queue,
            response_text="",
            user_input="",
            is_voice_input=False
        )
        
        current_state = initial_state
        
        while True:
            try:
                # Get text input with timeout to check for voice input
                print("\nYou: ", end="", flush=True)
                
                # Use a simple approach for text input
                user_text = input()
                
                if user_text.lower() in ['quit', 'exit', 'bye']:
                    break
                
                if user_text.strip():
                    current_state.user_input = user_text
                    current_state.is_voice_input = False
                    
                    # Process through the workflow
                    result = self.app.invoke(current_state)
                    current_state = result
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
    
    async def run_async(self):
        """Run chatbot asynchronously"""
        print("Async voice-enabled chatbot started!")
        print("Speak naturally - I'm always listening and can be interrupted.")
        
        initial_state = ChatState(
            messages=[],
            current_state=BotState.LISTENING,
            interrupt_requested=False,
            audio_queue=self.audio_queue,
            response_text="",
            user_input="",
            is_voice_input=False
        )
        
        current_state = initial_state
        
        try:
            while True:
                # Run one iteration of the workflow
                result = self.app.invoke(current_state)
                current_state = result
                
                # Small delay to prevent excessive CPU usage
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nShutting down chatbot...")
        finally:
            self.interrupt_flag.set()
    
    def shutdown(self):
        """Clean shutdown of the chatbot"""
        self.interrupt_flag.set()
        self.voice_manager.stop_speaking()
        print("Chatbot shutdown complete.")

# Example usage
if __name__ == "__main__":
    # You'll need to set your OpenAI API key
    API_KEY = 'AIzaSyARUFX3kjWDjcnhENzMKvRRV7YWtp0_6qI'
    
    try:
        chatbot = VoiceChatbot(API_KEY)
        
        print("Choose mode:")
        print("1. Text mode (with voice interrupt)")
        print("2. Async voice mode")
        
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "1":
            chatbot.run_text_mode()
        elif choice == "2":
            asyncio.run(chatbot.run_async())
        else:
            print("Invalid choice")
            
    except Exception as e:
        logger.error(f"Failed to start chatbot: {e}")
        print("Make sure you have installed all required packages:")
        print("pip install langgraph langchain-openai speechrecognition pyttsx3 pyaudio")
    finally:
        if 'chatbot' in locals():
            chatbot.shutdown()