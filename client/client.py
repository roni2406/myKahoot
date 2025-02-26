import socket
import threading
import json
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import CustomStyle
import base64
from io import BytesIO

# client.py
class QuizClient:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.setup_gui()
        
    def setup_gui(self):
        self.window = tk.Tk()
        self.window.title("Quiz Player")
        self.window.geometry("600x800")
        self.window.configure(bg=CustomStyle.BACKGROUND_COLOR)
        
        # Apply custom styles
        CustomStyle.setup_styles()
        
        # Main container
        main_frame = ttk.Frame(self.window, style="Custom.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header_frame = ttk.Frame(main_frame, style="Custom.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        header_label = ttk.Label(header_frame,
                                text="Quiz Player",
                                font=("Helvetica", 24, "bold"),
                                style="Custom.TLabel")
        header_label.pack()
        
        # Connection frame
        connection_frame = ttk.Frame(main_frame, style="Custom.TFrame")
        connection_frame.pack(fill=tk.X, pady=10)
        
        # Server details
        server_frame = ttk.Frame(connection_frame, style="Custom.TFrame")
        server_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(server_frame,
                 text="Server IP:",
                 font=("Helvetica", 12),
                 style="Custom.TLabel").pack(side=tk.LEFT)
        # Create ip_entry first, then modify it
        self.ip_entry = ttk.Entry(server_frame, width=20)  # Create the entry widget
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        # Update default IP field
        self.ip_entry.delete(0, tk.END)
        self.ip_entry.insert(0, "25.33.6.122")  # Users will replace with actual Hamachi IP
        
        # Add helper label
        ttk.Label(server_frame,
                 text="Enter Port:",
                 font=("Helvetica", 10),
                 style="Custom.TLabel").pack(side=tk.LEFT, padx=(10, 0))
        
        self.port_entry = ttk.Entry(server_frame, width=6)
        self.port_entry.pack(side=tk.LEFT, padx=5)
        self.port_entry.insert(0, "5000")
        
        # Player name frame
        name_frame = ttk.Frame(connection_frame, style="Custom.TFrame")
        name_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(name_frame,
                 text="Your Name:",
                 font=("Helvetica", 12),
                 style="Custom.TLabel").pack(side=tk.LEFT)
        
        self.name_entry = ttk.Entry(name_frame, width=20)
        self.name_entry.pack(side=tk.LEFT, padx=5)
        
        # Connect button
        self.connect_button = ttk.Button(connection_frame,
                                       text="Connect to Quiz",
                                       style="Success.TButton",
                                       command=self.connect_to_server)
        self.connect_button.pack(pady=10)
                
        # Create main scrollable area
        self.create_scrollable_area(main_frame)
        
        # Status display
        self.status_label = ttk.Label(main_frame,
                                    text="",
                                    font=("Helvetica", 12),
                                    style="Custom.TLabel")
        self.status_label.pack(pady=20)

    def create_scrollable_area(self, parent):
        # Create a container frame for the canvas and scrollbar
        container = ttk.Frame(parent, style="Custom.TFrame")
        container.pack(fill=tk.BOTH, expand=True)
        
        # Make the container frame expand with the window
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(container, bg=CustomStyle.BACKGROUND_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        
        # Configure canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create main scrollable frame
        self.scrollable_frame = ttk.Frame(canvas, style="Custom.TFrame")
        
        # Create window in canvas with proper width
        canvas_window = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configure canvas and scrollbar
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Update the scroll region when the frame size changes
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            
        self.scrollable_frame.bind("<Configure>", on_frame_configure)
        
        # Update the canvas window when the canvas size changes
        def on_canvas_configure(event):
            # Update the width of the window to match the canvas width
            canvas.itemconfig(canvas_window, width=event.width)
            
        canvas.bind("<Configure>", on_canvas_configure)
        
        # Enable mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Add content to scrollable frame
        self.add_content_to_scrollable_frame()

    def add_content_to_scrollable_frame(self):
         # Center container for scores
        scores_container = ttk.Frame(self.scrollable_frame, style="Custom.TFrame")
        scores_container.pack(fill=tk.X, pady=10)
        
        # Configure grid weights to center the scores frame
        scores_container.grid_columnconfigure(0, weight=1)
        scores_container.grid_columnconfigure(2, weight=1)

        # Scores frame
        scores_frame = ttk.Frame(scores_container, style="Custom.TFrame")
        scores_frame.pack(fill=tk.BOTH, expand = True, pady=10)
        
        self.scores_label = ttk.Label(scores_frame,
                                    text="Your Score: 0\nOther Players: None",
                                    font=("Helvetica", 12),
                                    style="Custom.TLabel",
                                    justify="center")
        self.scores_label.pack(fill="both", expand=True)
        
        # Timer display
        self.timer_label = ttk.Label(self.scrollable_frame,
                                   text="",
                                   font=("Helvetica", 12, "bold"),
                                   style="Custom.TLabel")
        self.timer_label.pack(pady=5)
        
        # Question display
        question_frame = ttk.Frame(self.scrollable_frame, style="Custom.TFrame")
        question_frame.pack(fill=tk.X, pady=20)
        
        self.question_label = ttk.Label(question_frame,
                                      text="Waiting for question...",
                                      font=("Helvetica", 14),
                                      wraplength=500,
                                      style="Custom.TLabel")
        self.question_label.pack(pady=10)
        
        # Image display
        self.image_label = ttk.Label(self.scrollable_frame, style="Custom.TLabel")
        self.image_label.pack(pady=10)
        
        # Answer section frame with fixed height
        self.answer_section = ttk.Frame(self.scrollable_frame, style="Custom.TFrame")
        self.answer_section.pack(fill=tk.X, pady=10, padx=10)
        
        # MCQ frame with scrollable options
        self.mcq_frame = ttk.Frame(self.answer_section, style="Custom.TFrame")
        self.answer_buttons = []
        for i in range(4):
            btn = ttk.Button(self.mcq_frame,
                           text=f"Option {i+1}",
                           style="Custom.TButton",
                           command=lambda x=i: self.submit_answer(x))
            btn.pack(pady=5, fill=tk.X)
            btn.config(state=tk.DISABLED)
            self.answer_buttons.append(btn)
        
        # Short answer frame
        self.short_answer_frame = ttk.Frame(self.answer_section, style="Custom.TFrame")
        
        # Add text widget instead of entry for multiline support
        self.answer_entry = ttk.Entry(self.short_answer_frame, width=40)
        self.answer_entry.pack(pady=5)
        
        self.submit_text_button = ttk.Button(self.short_answer_frame,
                                           text="Submit Answer",
                                           style="Success.TButton",
                                           command=self.submit_text_answer)
        self.submit_text_button.pack(pady=5)
        
        # Initially hide both frames
        self.mcq_frame.pack_forget()
        self.short_answer_frame.pack_forget()

    def connect_to_server(self):
        try:
            server_ip = self.ip_entry.get()
            server_port = int(self.port_entry.get())
            player_name = self.name_entry.get()

            if not player_name:
                messagebox.showerror("Error", "Please enter your name")
                return
                
            # Try to connect to the server
            self.socket.settimeout(5)  # 5 seconds timeout
            self.socket.connect((server_ip, server_port))
            self.socket.settimeout(None)  # Remove timeout

            # Send player name
            self.socket.send(player_name.encode())
            
            # Start listening for server messages
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            # Update GUI
            self.connect_button.config(state=tk.DISABLED)
            self.status_label.config(text="Connected to server")
            self.ip_entry.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.DISABLED)
            self.name_entry.config(state=tk.DISABLED)
            
        except socket.timeout:
            messagebox.showerror("Error", "Connection timed out. Please check the server IP and port.")
        except ValueError:
            messagebox.showerror("Error", "Invalid port number")
        except Exception as e:
            messagebox.showerror("Error", f"Could not connect to server: {str(e)}")
    
    def handle_disconnect(self):
        """Handle disconnection from server"""
        self.socket.close()
        self.status_label.config(text="Disconnected from server")
        self.connect_button.config(state=tk.NORMAL)
        self.ip_entry.config(state=tk.NORMAL)
        self.port_entry.config(state=tk.NORMAL)
        self.name_entry.config(state=tk.NORMAL)
        
        for button in self.answer_buttons:
            button.config(state=tk.DISABLED)
            
        messagebox.showwarning("Disconnected", "Lost connection to server")
            
    def receive_messages(self):
        buffer = ""
        while True:
            try:
                # Receive data in chunks
                chunk = self.socket.recv(4096).decode()  # Increased buffer size for images
                if not chunk:
                    break
                    
                buffer += chunk
                
                try:
                    # Try to parse the complete message
                    message = json.loads(buffer)
                    # If successful, process the message and clear buffer
                    self.handle_message(message)
                    buffer = ""
                except json.JSONDecodeError:
                    # If we can't parse yet, continue receiving more data
                    continue
                    
            except socket.error as e:
                print(f"Socket error: {e}")
                self.window.after(0, self.handle_disconnect)
                break
            except Exception as e:
                print(f"Error in receive_messages: {e}")
                self.window.after(0, self.handle_disconnect)
                break
                
        self.window.after(0, self.handle_disconnect)
        
    def handle_message(self, message):
        if message["type"] == "question":
            question_data = message["data"]
            self.question_label.config(text=f"Question {question_data['question_number']}/{question_data['total_questions']}: {question_data['question']}")            
            
             # Handle image if present
            if "image" in question_data and question_data["image"]:
                try:
                    # Clear any existing image
                    self.image_label.config(image='')
                    
                    # Decode and display image
                    image_data = base64.b64decode(question_data["image"])
                    image = Image.open(BytesIO(image_data))
                    
                    # Calculate new dimensions while maintaining aspect ratio
                    max_width = 800
                    max_height = 600
                    ratio = min(max_width/image.width, max_height/image.height)
                    new_width = int(image.width * ratio)
                    new_height = int(image.height * ratio)
                    
                    image = image.resize((new_width, new_height), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    self.image_label.config(image=photo)
                    self.image_label.image = photo  # Keep a reference!
                except Exception as e:
                    print(f"Error displaying image: {str(e)}")
                    self.image_label.config(image='')
            else:
                self.image_label.config(image='')
            
            # Handle timer
            if question_data["timer_mode"]:
                self.time_remaining = question_data["time_limit"]
                self.timer_label.config(text=f"Time remaining: {self.time_remaining}s")
                self.window.after(1000, self.update_timer)
            else:
                self.timer_label.config(text="")

            # Show appropriate answer input
            if question_data["type"] == "multiple_choice":
                self.short_answer_frame.pack_forget()
                self.mcq_frame.pack(fill=tk.X)
                for i, option in enumerate(question_data["options"]):
                    self.answer_buttons[i].config(text=option, state=tk.NORMAL)
            else:
                self.mcq_frame.pack_forget()
                self.short_answer_frame.pack(fill=tk.X)
                self.answer_entry.config(state=tk.NORMAL)
                self.answer_entry.delete(0, tk.END)
                self.submit_text_button.config(state=tk.NORMAL)
        
        elif message["type"] == "end":
            self.update_scores(message["data"])
            self.question_label.config(text="Quiz has ended!")
            # Disable answer inputs
            for button in self.answer_buttons:
                button.config(state=tk.DISABLED)
            self.answer_entry.config(state=tk.DISABLED)
            self.submit_text_button.config(state=tk.DISABLED)
            
        elif message["type"] == "score_update":
            self.update_scores(message["data"])
            
        elif message["type"] == "restart":
            self.update_scores(message["data"])
            self.question_label.config(text="Waiting for question...")
            # Clear timer and stop any running timer updates
            self.timer_label.config(text="")
            if hasattr(self, 'time_remaining'):
                delattr(self, 'time_remaining')
            self.image_label.config(image="")
            # Reset answer inputs
            for button in self.answer_buttons:
                button.config(state=tk.DISABLED)
            self.answer_entry.config(state=tk.DISABLED)
            self.submit_text_button.config(state=tk.DISABLED)
            self.mcq_frame.pack_forget()
            self.short_answer_frame.pack_forget()
                
    def update_timer(self):
        if hasattr(self, 'time_remaining') and self.time_remaining > 0:
            self.time_remaining -= 1
            self.timer_label.config(text=f"Time remaining: {self.time_remaining}s")
            if self.time_remaining == 0:
                # Auto-submit empty answer when time runs out
                self.submit_answer(-1) if self.mcq_frame.winfo_ismapped() else self.submit_text_answer()
            else:
                if hasattr(self, 'time_remaining'):
                    self.window.after(1000, self.update_timer)
                
    def update_scores(self, scores):
        my_name = self.name_entry.get()
        other_scores = "\n".join(f"{name}: {score}" for name, score in scores.items() if name != my_name)
        self.scores_label.config(text=f"Your Score: {scores.get(my_name, 0)}\nOther Players:\n{other_scores or 'None'}")
        
    def submit_text_answer(self):
        answer = self.answer_entry.get()
        answer_data = {
            "type": "short_answer",
            "answer": answer
        }
        self.socket.send(json.dumps(answer_data).encode())
        self.answer_entry.config(state=tk.DISABLED)
        self.submit_text_button.config(state=tk.DISABLED)
        self.timer_label.config(text="Answer submitted")
        
    def submit_answer(self, answer_index):
        answer_data = {
            "type": "multiple_choice",
            "answer": answer_index
        }
        self.socket.send(json.dumps(answer_data).encode())
        for button in self.answer_buttons:
            button.config(state=tk.DISABLED)
        self.timer_label.config(text="Answer submitted")

            
    def start(self):
        self.window.mainloop()

# Run server
if __name__ == "__main__":
    # For client.py
    client = QuizClient()
    client.start()