# server.py
import socket
import netifaces
import threading
import json
import tkinter as tk
from tkinter import messagebox
from question_importer import QuestionImporter
from tkinter import filedialog
from tkinter import ttk
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import CustomStyle
import base64
from PIL import Image, ImageTk
from io import BytesIO

def get_local_ip():
    """Get the local IP address of the computer"""
    try:
        # Get all network interfaces
        for interface in netifaces.interfaces():
            # Get addresses for this interface
            addrs = netifaces.ifaddresses(interface)
            # Check for IPv4 addresses
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr['addr']
                    # Skip localhost
                    if ip != '127.0.0.1':
                        return ip
    except Exception:
        return None
    return None

def get_hamachi_ip():
    """Get Hamachi VPN IP address if available"""
    try:
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr['addr']
                    # Hamachi IPs typically start with 25.
                    if ip.startswith('25.'):
                        return ip
    except Exception:
        return None
    return None

class QuizServer:
    def __init__(self):
        self.host = get_local_ip() or '0.0.0.0'  # Get the WiFi IP address
        self.port = 5000
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}
        self.scores = {}
        self.current_question = 0
        self.questions = []  # Will be loaded from Excel
        self.question_importer = QuestionImporter()
        self.pending_answers = {} 
        # Get Hamachi IP if available
        self.hamachi_ip = get_hamachi_ip()
        self.timer_mode = False
        self.question_time = 30  # default 30 seconds
        self.answered_clients = set()  # Track who has answered current question
        self.question_active = False   # Track if a question is currently active
        self.setup_gui()
        
    def setup_gui(self):
        self.window = tk.Tk()
        self.window.title("Quiz Host")
        self.window.geometry("800x600")
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
                                text="Quiz Control Panel",
                                font=("Helvetica", 24, "bold"),
                                style="Custom.TLabel")
        header_label.pack()
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame, style="Custom.TFrame")
        control_frame.pack(fill=tk.X, pady=10)

        # Add restart button
        self.restart_button = ttk.Button(control_frame,
                                    text="Restart Quiz",
                                    style="Warning.TButton",
                                    command=self.restart_quiz)
        self.restart_button.pack(side=tk.LEFT, padx=5)
        self.restart_button.config(state=tk.DISABLED)   

        # Add timer mode controls
        timer_frame = ttk.Frame(control_frame, style="Custom.TFrame")
        timer_frame.pack(side=tk.LEFT, padx=5)
        
        self.timer_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(timer_frame,
                       text="Timer Mode",
                       variable=self.timer_var,
                       command=self.toggle_timer_mode).pack(side=tk.LEFT)
        
        ttk.Label(timer_frame,
                 text="Seconds:",
                 style="Custom.TLabel").pack(side=tk.LEFT, padx=(5,0))
        
        self.time_entry = ttk.Entry(timer_frame, width=5)
        self.time_entry.pack(side=tk.LEFT, padx=5)
        self.time_entry.insert(0, "30")
        self.time_entry.config(state=tk.DISABLED)
        
        self.load_button = ttk.Button(control_frame,
                        text="Load Questions",
                        style="Custom.TButton",
                        command=self.load_questions)
        self.load_button.pack(side=tk.LEFT, padx=5)
        
        self.start_button = ttk.Button(control_frame,
                                    text="Start Quiz",
                                    style="Success.TButton",
                                    command=self.start_quiz)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.next_button = ttk.Button(control_frame,
                                    text="Next Question",
                                    style="Custom.TButton",
                                    command=self.send_next_question)
        self.next_button.pack(side=tk.LEFT, padx=5)
        self.next_button.config(state=tk.DISABLED)
        
        # Info frame
        info_frame = ttk.Frame(main_frame, style="Custom.TFrame")
        info_frame.pack(fill=tk.X, pady=20)
        
        # Update connection info display
        connection_info = f"Server Port: {self.port}\n"
        if self.hamachi_ip:
            connection_info += f"Hamachi IP: {self.host}"
        else:
            connection_info += f"Local IP: {self.host}"
            
        self.connection_label = ttk.Label(info_frame,
            text=connection_info,
            font=("Helvetica", 12),
            style="Custom.TLabel")
        self.connection_label.pack()
        
        self.question_count_label = ttk.Label(info_frame,
                                            text="Loaded Questions: 0",
                                            font=("Helvetica", 12),
                                            style="Custom.TLabel")
        self.question_count_label.pack(pady=5)
        
        self.players_label = ttk.Label(info_frame,
                                    text="Connected Players: 0",
                                    font=("Helvetica", 12),
                                    style="Custom.TLabel")
        self.players_label.pack(pady=5)
        
        self.create_scrollable_area(main_frame)
      
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
        
        # Create window in canvas
        canvas_window = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configure canvas and scrollbar
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Update scroll region when frame size changes
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        self.scrollable_frame.bind("<Configure>", on_frame_configure)
        
        # Update canvas window when canvas size changes
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", on_canvas_configure)
        
        # Enable mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Add content to scrollable frame
        self.add_content_to_scrollable_frame()

    def add_content_to_scrollable_frame(self):
        # Question display frame
        question_frame = ttk.Frame(self.scrollable_frame, style="Custom.TFrame")
        question_frame.pack(fill=tk.X, pady=10)
        
        self.question_label = ttk.Label(question_frame,
                                    text="No question displayed",
                                    font=("Helvetica", 14),
                                    wraplength=700,
                                    style="Custom.TLabel")
        self.question_label.pack(pady=10)
        
        # Image display
        self.image_label = ttk.Label(self.scrollable_frame, style="Custom.TLabel")
        self.image_label.pack(pady=10)
        
        # Multiple choice options display
        self.options_frame = ttk.LabelFrame(self.scrollable_frame, 
                                        text="Multiple Choice Options",
                                        style="Custom.TFrame")
        self.options_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.option_labels = []
        for i in range(4):
            label = ttk.Label(self.options_frame,
                            text=f"Option {i+1}",
                            font=("Helvetica", 12),
                            style="Custom.TLabel")
            label.pack(pady=5, padx=10, anchor="w")
            self.option_labels.append(label)
        # Initially hide options frame
        self.options_frame.pack_forget()
        
        # Scores display with adjustment controls
        scores_frame = ttk.LabelFrame(self.scrollable_frame,
                                text="Player Scores",
                                style="Custom.TFrame")
        scores_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create a frame for the score list and adjustment controls
        score_controls_frame = ttk.Frame(scores_frame, style="Custom.TFrame")
        score_controls_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Split into left and right columns
        left_column = ttk.Frame(score_controls_frame, style="Custom.TFrame")
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        right_column = ttk.Frame(score_controls_frame, style="Custom.TFrame")
        right_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Score display in left column
        self.scores_text = tk.Text(left_column,
                                height=10,
                                width=30,
                                font=("Helvetica", 12),
                                bg="white",
                                relief="solid")
        self.scores_text.pack(pady=5, fill=tk.BOTH, expand=True)
        
        # Score adjustment controls in right column
        adjust_frame = ttk.Frame(right_column, style="Custom.TFrame")
        adjust_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(adjust_frame,
                text="Adjust Score:",
                font=("Helvetica", 12, "bold"),
                style="Custom.TLabel").pack(pady=5)
        
        # Player selection
        ttk.Label(adjust_frame,
                text="Select Player:",
                style="Custom.TLabel").pack()
        
        self.player_var = tk.StringVar()
        self.player_dropdown = ttk.Combobox(adjust_frame,
                                        textvariable=self.player_var,
                                        state="readonly")
        self.player_dropdown.pack(pady=5)
        
        # Score adjustment
        adjust_buttons_frame = ttk.Frame(adjust_frame, style="Custom.TFrame")
        adjust_buttons_frame.pack(pady=5)
        
        ttk.Button(adjust_buttons_frame,
                text="-1",
                style="Custom.TButton",
                command=lambda: self.adjust_score(-1)).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(adjust_buttons_frame,
                text="+1",
                style="Custom.TButton",
                command=lambda: self.adjust_score(1)).pack(side=tk.LEFT, padx=2)
        
        # Manual score entry
        manual_frame = ttk.Frame(adjust_frame, style="Custom.TFrame")
        manual_frame.pack(pady=5)
        
        ttk.Label(manual_frame,
                text="Set Score:",
                style="Custom.TLabel").pack(side=tk.LEFT, padx=2)
        
        self.score_entry = ttk.Entry(manual_frame, width=5)
        self.score_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(manual_frame,
                text="Set",
                style="Custom.TButton",
                command=self.set_manual_score).pack(side=tk.LEFT, padx=2)
        
        # Grading frame for short answers (keep existing code)
        grading_frame = ttk.LabelFrame(self.scrollable_frame,
                                    text="Short Answer Grading",
                                    style="Custom.TFrame")
        grading_frame.pack(fill=tk.X, pady=10)
        
        self.answer_text = tk.Text(grading_frame, height=4, width=40)
        self.answer_text.pack(pady=5)
        
        grading_buttons = ttk.Frame(grading_frame, style="Custom.TFrame")
        grading_buttons.pack(fill=tk.X)
        
        self.correct_button = ttk.Button(grading_buttons,
                                    text="Correct",
                                    style="Success.TButton",
                                    command=lambda: self.grade_answer(True))
        self.correct_button.pack(side=tk.LEFT, padx=5)
        
        self.incorrect_button = ttk.Button(grading_buttons,
                                        text="Incorrect",
                                        style="Custom.TButton",
                                        command=lambda: self.grade_answer(False))
        self.incorrect_button.pack(side=tk.LEFT, padx=5)

    def adjust_score(self, amount):
        """Adjust selected player's score by the given amount"""
        player = self.player_var.get()
        if player in self.scores:
            self.scores[player] += amount
            self.update_scores_display()
            self.broadcast_scores()

    def set_manual_score(self):
        """Set a player's score manually"""
        player = self.player_var.get()
        try:
            new_score = int(self.score_entry.get())
            if player in self.scores:
                self.scores[player] = new_score
                self.update_scores_display()
                self.broadcast_scores()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")

    def restart_quiz(self):
        # Reset quiz state
        self.current_question = 0
        self.question_active = False
        self.answered_clients.clear()
        self.pending_answers.clear()

        # Reset timer-related state
        if self.timer_mode:
            try:
                self.question_time = int(self.time_entry.get())
            except ValueError:
                self.question_time = 30
                self.time_entry.delete(0, tk.END)
                self.time_entry.insert(0, "30")

        for player in self.scores:
            self.scores[player] = 0
        self.update_scores_display()
        self.update_answered_status()
        
        # Send reset notification to all clients
        message = json.dumps({
            "type": "restart",
            "data": self.scores,
            "timer_reset": True 
        })
        
        for client in self.clients.values():
            try:
                client.send(message.encode())
            except:
                continue
        
        # Reset UI state
        self.start_button.config(state=tk.NORMAL)
        self.next_button.config(state=tk.DISABLED)
        self.restart_button.config(state=tk.DISABLED)
        self.question_label.config(text="No question displayed")

    def toggle_timer_mode(self):
        self.timer_mode = self.timer_var.get()
        self.time_entry.config(state=tk.NORMAL if self.timer_mode else tk.DISABLED)
        if self.timer_mode:
            try:
                self.question_time = int(self.time_entry.get())
            except ValueError:
                self.question_time = 30
                self.time_entry.delete(0, tk.END)
                self.time_entry.insert(0, "30")

    def send_next_question(self):
        if self.current_question >= len(self.questions):
            self.end_quiz()
            return
        # Reset tracking for new question
        self.answered_clients.clear()
        self.pending_answers.clear()
        self.question_active = True
            
        question_data = self.questions[self.current_question]
        self.question_label.config(text=f"Question {self.current_question + 1}: {question_data['question']}")

        # Handle multiple choice options display
        if question_data["type"] == "multiple_choice":
            self.options_frame.pack(fill=tk.X, pady=10, padx=10)
            for i, option in enumerate(question_data["options"]):
                self.option_labels[i].config(text=f"{i+1}. {option}")
                if "correct" in question_data and i == question_data["correct"]:
                    self.option_labels[i].config(font=("Helvetica", 12, "bold"))
                else:
                    self.option_labels[i].config(font=("Helvetica", 12))
        else:
            self.options_frame.pack_forget()

        # Handle image display if present
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

        self.update_answered_status()

        # Enhanced question data with timer and question number
        enhanced_data = {
            "question": question_data["question"],
            "type": question_data["type"],
            "question_number": self.current_question + 1,
            "total_questions": len(self.questions),
            "timer_mode": self.timer_mode
        }
        
        if question_data["type"] == "multiple_choice":
            enhanced_data["options"] = question_data["options"]
        elif question_data["type"] == "short_answer":
            enhanced_data["answer"] = question_data["answer"]
            
         # Handle image if present - just pass through the already encoded image data
        if "image" in question_data and question_data["image"]:
            print(f"Server: Found image data for question {self.current_question + 1}")
            enhanced_data["image"] = question_data["image"]
            
        if self.timer_mode:
            enhanced_data["time_limit"] = self.question_time
            
        # Send question to all clients
        message = json.dumps({
            "type": "question",
            "data": enhanced_data
        })
        
        for client in self.clients.values():
            try:
                client.send(message.encode())
            except:
                continue
                
        self.current_question += 1

    # Add method to update the answered status display:
    def update_answered_status(self):
        status_text = "\nAnswered Players:\n"
        for player in self.clients.keys():
            status = "✓" if player in self.answered_clients else "..."
            status_text += f"{player}: {status}\n"
        
        # Update the scores text to include who has answered
        self.scores_text.delete(1.0, tk.END)
        for player, score in self.scores.items():
            self.scores_text.insert(tk.END, f"{player}: {score}\n")
        self.scores_text.insert(tk.END, status_text)

    # Update process_answer method:
    def process_answer(self, player_name, answer_data):
        """Process answer from client with type checking"""
        if not self.question_active:
            return  # Ignore answers when no question is active
            
        try:
            question = self.questions[self.current_question - 1]
            
            # Ensure answer_data is properly formatted
            if not isinstance(answer_data, dict):
                answer_data = json.loads(answer_data)
                
            # Mark this client as having answered
            self.answered_clients.add(player_name)
            self.update_answered_status()
                
            answer_type = answer_data.get("type")
            answer = answer_data.get("answer")
            
            if answer_type == "multiple_choice" and question["type"] == "multiple_choice":
                if answer == question["correct"]:
                    self.scores[player_name] += 1
                    self.update_scores_display()
                    self.broadcast_scores()
                    
                # Check if all clients have answered
                if len(self.answered_clients) == len(self.clients):
                    self.show_answer_summary(question)
                    
            elif answer_type == "short_answer" and question["type"] == "short_answer":
                answer_key = f"{player_name}_{self.current_question - 1}"
                self.pending_answers[answer_key] = {
                    "player": player_name,
                    "answer": answer,
                    "question_num": self.current_question - 1
                }
                self.show_next_pending_answer()
                
                # Check if all clients have answered
                if len(self.answered_clients) == len(self.clients):
                    self.next_button.config(state=tk.NORMAL)
                    messagebox.showinfo("All Answered", "All players have submitted their answers!")
                    
        except Exception as e:
            print(f"Error processing answer: {str(e)}")
    
    # Add method to show answer summary for multiple choice:
    def show_answer_summary(self, question):
        if question["type"] == "multiple_choice":
            correct_option = question["options"][question["correct"]]
            summary = f"All players have answered!\n\nCorrect answer: {correct_option}\n\nCurrent scores:"
            for player, score in self.scores.items():
                summary += f"\n{player}: {score}"
            
            self.next_button.config(state=tk.NORMAL)
            messagebox.showinfo("Question Complete", summary)
            
    # Add a method to broadcast scores:
    def broadcast_scores(self):
        """Send updated scores to all clients"""
        message = json.dumps({
            "type": "score_update",
            "data": self.scores
        })
        
        for client in self.clients.values():
            try:
                client.send(message.encode())
            except:
                continue

    def show_next_pending_answer(self):
        if not self.pending_answers:
            self.answer_text.delete(1.0, tk.END)
            self.answer_text.insert(tk.END, "No pending answers to grade")
            self.correct_button.config(state=tk.DISABLED)
            self.incorrect_button.config(state=tk.DISABLED)
            return
            
        answer_key = next(iter(self.pending_answers))
        answer_data = self.pending_answers[answer_key]
        
        self.answer_text.delete(1.0, tk.END)
        self.answer_text.insert(tk.END, f"Player: {answer_data['player']}\n")
        self.answer_text.insert(tk.END, f"Answer: {answer_data['answer']}\n")
        self.answer_text.insert(tk.END, f"Correct Answer: {self.questions[answer_data['question_num']]['answer']}")
        
        self.correct_button.config(state=tk.NORMAL)
        self.incorrect_button.config(state=tk.NORMAL)
        
    def grade_answer(self, is_correct):
        if not self.pending_answers:
            return
            
        answer_key = next(iter(self.pending_answers))
        answer_data = self.pending_answers[answer_key]
        
        if is_correct:
            self.scores[answer_data['player']] += 1
            
        del self.pending_answers[answer_key]
        self.update_scores_display()
        self.broadcast_scores()
        self.show_next_pending_answer()

    def load_questions(self):
        try:
            file_path = filedialog.askopenfilename(
                title="Select Questions File",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
            )
            
            if file_path:
                self.questions = self.question_importer.load_questions(file_path)
                self.question_count_label.config(text=f"Loaded Questions: {len(self.questions)}")
                messagebox.showinfo("Success", f"Loaded {len(self.questions)} questions")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def start_server(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(4)
            print(f"Server started on {self.host}:{self.port}")
            
            # Start accepting clients in a separate thread
            accept_thread = threading.Thread(target=self.accept_clients)
            accept_thread.daemon = True
            accept_thread.start()
            
            self.window.mainloop()
        except Exception as e:
            messagebox.showerror("Error", f"Could not start server: {str(e)}")
            self.window.destroy()
        
    def accept_clients(self):
        while True:
            client_socket, address = self.server_socket.accept()
            # Get player name
            player_name = client_socket.recv(1024).decode()
            
            self.clients[player_name] = client_socket
            self.scores[player_name] = 0
            
            # Update GUI
            self.players_label.config(text=f"Connected Players: {len(self.clients)}")
            self.update_scores_display()
            
            # Start a thread to handle this client
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket, player_name))
            client_thread.daemon = True
            client_thread.start()
            
    # Update handle_client method to handle disconnections:
    def handle_client(self, client_socket, player_name):
        while True:
            try:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                    
                answer = json.loads(data)
                self.process_answer(player_name, answer)
            except:
                break
                
        # Clean up when client disconnects
        del self.clients[player_name]
        del self.scores[player_name]
        self.answered_clients.discard(player_name)  # Remove from answered set
        client_socket.close()
        self.players_label.config(text=f"Connected Players: {len(self.clients)}")
        self.update_scores_display()
        self.update_answered_status()
        
    def start_quiz(self):
        if len(self.clients) == 0:
            messagebox.showwarning("Warning", "No players connected!")
            return
            
        if self.timer_mode:
            try:
                self.question_time = int(self.time_entry.get())
                if self.question_time <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid time in seconds")
                self.question_time = 30
                self.time_entry.delete(0, tk.END)
                self.time_entry.insert(0, "30")
                return
                
        self.current_question = 0
        # Reset scores at the start of quiz
        for player in self.scores:
            self.scores[player] = 0
        self.update_scores_display()
        
        self.send_next_question()
        self.start_button.config(state=tk.DISABLED)
        self.next_button.config(state=tk.NORMAL)
        self.restart_button.config(state=tk.NORMAL)
                
    def update_scores_display(self):
        """Update the scores display and dropdown"""
        self.scores_text.delete(1.0, tk.END)
        for player, score in self.scores.items():
            self.scores_text.insert(tk.END, f"{player}: {score}\n")
        
        # Update player dropdown
        self.player_dropdown['values'] = list(self.scores.keys())
        if not self.player_var.get() and self.scores:
            self.player_var.set(list(self.scores.keys())[0])
            
    def end_quiz(self):
        message = json.dumps({
            "type": "end",
            "data": self.scores
        })
        
        for client in self.clients.values():
            client.send(message.encode())
            
        self.start_button.config(state=tk.NORMAL)
        self.next_button.config(state=tk.DISABLED)
        messagebox.showinfo("Quiz Ended", "The quiz has ended!")

# Run server
if __name__ == "__main__":
    server = QuizServer()
    server.start_server()