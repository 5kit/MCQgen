import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
import random

from MCQgen.utils import CACHE_FILE, SAMPLE_FORMAT, parse_questions
from MCQgen.quiz_app import QuizApp
from MCQgen.question_bank import QuestionBankPanel

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def launch_app():
    root = ctk.CTk()
    root.title("Quiz Generator")
    root.geometry("1000x880")
    root.minsize(760, 700)
    root.resizable(True, True)

    def launch_quiz(questions, timer_mode, time_limit, shuffle_q, shuffle_o, instant_feedback, allow_backtrack):
        root.destroy()

        def reopen_launcher():
            launch_app()

        app = QuizApp(
            questions, timer_mode=timer_mode, time_limit=time_limit,
            shuffle_questions=shuffle_q, shuffle_options=shuffle_o,
            instant_feedback=instant_feedback, allow_backtrack=allow_backtrack,
            on_return_to_builder=reopen_launcher
        )
        app.mainloop()

    tabview = ctk.CTkTabview(root, width=960, height=850)
    tabview.pack(fill="both", expand=True, padx=15, pady=15)
    tab_quiz = tabview.add("Quick Quiz")
    tab_bank = tabview.add("Question Bank")

    bank_panel = QuestionBankPanel(tab_bank, on_start_quiz=launch_quiz)

    def start_quiz():
        text = input_box.get("1.0", "end")
        questions, skipped = parse_questions(text)

        if not questions:
            messagebox.showerror(
                "Parse Error",
                "No valid questions found. Ensure your prompt format follows:\n\n"
                "Q: [Question Text]\n"
                "A: [Option]\nB: [Option]\nC: [Option]\nD: [Option]\n"
                "Answer: [Letter]\n\n"
                "(Category: and Explanation: lines are optional.)"
            )
            return

        if skipped > 0:
            proceed = messagebox.askyesno(
                "Some Questions Skipped",
                f"{len(questions)} question(s) parsed successfully, but {skipped} block(s) could not "
                "be parsed and will be skipped. Continue with the questions that did parse?"
            )
            if not proceed:
                return

        count_text = quiz_count_entry.get().strip()
        if count_text:
            try:
                count = int(count_text)
                if count <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Enter a valid number of questions, or leave it blank.")
                return
            if count < len(questions):
                questions = random.sample(questions, count)

        if timer_mode.get() == "countdown":
            try:
                minutes = float(time_entry.get())
                if minutes <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Enter a valid time limit in minutes.")
                return
            mode = "countdown"
            time_limit = int(minutes * 60)
        else:
            mode = "stopwatch"
            time_limit = 0

        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            pass

        launch_quiz(
            questions, mode, time_limit,
            shuffle_q_var.get(), shuffle_o_var.get(),
            instant_feedback_var.get(), allow_backtrack_var.get()
        )

    def save_to_bank():
        text = input_box.get("1.0", "end")
        if not text.strip():
            messagebox.showerror("Empty", "Paste some questions first.")
            return
        bank_panel.merge_import(text)
        tabview.set("Question Bank")

    def paste_sample():
        input_box.delete("1.0", "end")
        input_box.insert("1.0", SAMPLE_FORMAT)

    def import_from_file():
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            input_box.delete("1.0", "end")
            input_box.insert("1.0", content)
        except OSError as e:
            messagebox.showerror("Import Failed", str(e))

    def load_last_input():
        if not os.path.exists(CACHE_FILE):
            messagebox.showinfo("No Cached Input", "No previously saved input was found.")
            return
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            input_box.delete("1.0", "end")
            input_box.insert("1.0", content)
        except OSError as e:
            messagebox.showerror("Load Failed", str(e))

    def update_timer_setting():
        time_entry.configure(state="normal" if timer_mode.get() == "countdown" else "disabled")

    ctk.CTkLabel(
        tab_quiz, text="Quick Quiz from Pasted Text", font=ctk.CTkFont(size=18, weight="bold")
    ).pack(pady=(10, 5))

    guide_frame = ctk.CTkFrame(tab_quiz)
    guide_frame.pack(fill="x", padx=15, pady=5)

    guide_header_row = ctk.CTkFrame(guide_frame, fg_color="transparent")
    guide_header_row.pack(fill="x", padx=15, pady=(8, 2))

    ctk.CTkLabel(
        guide_header_row, text="🤖 How to Prompt AI (ChatGPT / Claude / Gemini):",
        font=ctk.CTkFont(size=12, weight="bold")
    ).pack(side="left")

    AI_PROMPT_TEXT = (
        'Generate 10 CCAT multiple choice questions. Format each question exactly like this:\n'
        'Q: [Question Text]\n'
        'Category: [optional]\n'
        'A: [Option]\n'
        'B: [Option]\n'
        'C: [Option]\n'
        'D: [Option]\n'
        'Answer: [Letter]\n'
        'Explanation: [optional]'
    )

    def copy_prompt():
        root.clipboard_clear()
        root.clipboard_append(AI_PROMPT_TEXT)
        copy_prompt_btn.configure(text="Copied!")
        root.after(1500, lambda: copy_prompt_btn.configure(text="Copy Prompt"))

    copy_prompt_btn = ctk.CTkButton(
        guide_header_row, text="Copy Prompt", width=110, height=24, font=ctk.CTkFont(size=11),
        fg_color="#3A3A3A", hover_color="#4A4A4A", command=copy_prompt
    )
    copy_prompt_btn.pack(side="right")

    guide_text = (
        'Ask the AI: "Generate 10 CCAT multiple choice questions. Format each question exactly like this:\n'
        'Q: [Question Text] \\n Category: [optional] \\n A: [Option] \\n B: [Option] \\n C: [Option] \\n '
        'D: [Option] \\n Answer: [Letter] \\n Explanation: [optional]"\n'
        'Category and Explanation lines are optional but unlock score-by-category breakdowns and\n'
        'answer explanations. Use "Save to Bank" below to keep questions for later, not just this session.'
    )

    ctk.CTkLabel(
        guide_frame, text=guide_text, font=ctk.CTkFont(size=11), justify="left", text_color="#A0A0A0"
    ).pack(anchor="w", padx=15, pady=(0, 8))

    box_header = ctk.CTkFrame(tab_quiz, fg_color="transparent")
    box_header.pack(fill="x", padx=15, pady=(5, 0))

    ctk.CTkLabel(box_header, text="Paste your formatted text below:", font=ctk.CTkFont(size=12)).pack(side="left")

    button_bar = ctk.CTkFrame(box_header, fg_color="transparent")
    button_bar.pack(side="right")

    ctk.CTkButton(
        button_bar, text="Load Last Input", width=120, height=24, font=ctk.CTkFont(size=11),
        fg_color="#3A3A3A", hover_color="#4A4A4A", command=load_last_input
    ).pack(side="left", padx=(0, 6))
    ctk.CTkButton(
        button_bar, text="Import from File", width=120, height=24, font=ctk.CTkFont(size=11),
        fg_color="#3A3A3A", hover_color="#4A4A4A", command=import_from_file
    ).pack(side="left", padx=(0, 6))
    ctk.CTkButton(
        button_bar, text="Paste Sample Text", width=130, height=24, font=ctk.CTkFont(size=11),
        fg_color="#3A3A3A", hover_color="#4A4A4A", command=paste_sample
    ).pack(side="left")

    input_box = ctk.CTkTextbox(tab_quiz, height=200, font=("Consolas", 11))
    input_box.pack(padx=15, pady=5, fill="both", expand=True)

    count_row = ctk.CTkFrame(tab_quiz, fg_color="transparent")
    count_row.pack(fill="x", padx=15, pady=(5, 0))
    ctk.CTkLabel(count_row, text="Number of questions to include (blank = all parsed):").pack(side="left")
    quiz_count_entry = ctk.CTkEntry(count_row, width=70)
    quiz_count_entry.pack(side="left", padx=8)

    opts_frame = ctk.CTkFrame(tab_quiz)
    opts_frame.pack(fill="x", padx=15, pady=10)

    opts_row1 = ctk.CTkFrame(opts_frame, fg_color="transparent")
    opts_row1.pack(fill="x", padx=10, pady=(10, 4))
    shuffle_q_var = ctk.BooleanVar(value=False)
    shuffle_o_var = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(opts_row1, text="Shuffle question order", variable=shuffle_q_var).pack(side="left", padx=(0, 15))
    ctk.CTkCheckBox(opts_row1, text="Shuffle answer options", variable=shuffle_o_var).pack(side="left")

    opts_row2 = ctk.CTkFrame(opts_frame, fg_color="transparent")
    opts_row2.pack(fill="x", padx=10, pady=4)
    instant_feedback_var = ctk.BooleanVar(value=False)
    allow_backtrack_var = ctk.BooleanVar(value=True)
    ctk.CTkCheckBox(
        opts_row2, text="Show answer confirmation after each question", variable=instant_feedback_var
    ).pack(side="left", padx=(0, 15))
    ctk.CTkCheckBox(
        opts_row2, text="Allow going back to previous questions", variable=allow_backtrack_var
    ).pack(side="left")

    timer_row = ctk.CTkFrame(opts_frame, fg_color="transparent")
    timer_row.pack(fill="x", padx=10, pady=(4, 12))
    timer_mode = ctk.StringVar(value="stopwatch")
    ctk.CTkRadioButton(
        timer_row, text="Stopwatch (Count Up)", variable=timer_mode, value="stopwatch",
        command=update_timer_setting
    ).pack(side="left", padx=(0, 15))
    ctk.CTkRadioButton(
        timer_row, text="Time Limit (Countdown):", variable=timer_mode, value="countdown",
        command=update_timer_setting
    ).pack(side="left")
    time_entry = ctk.CTkEntry(timer_row, width=60, state="disabled")
    time_entry.pack(side="left", padx=8)
    ctk.CTkLabel(timer_row, text="minutes").pack(side="left")

    action_row = ctk.CTkFrame(tab_quiz, fg_color="transparent")
    action_row.pack(pady=10)

    ctk.CTkButton(
        action_row, text="Start Quiz", font=ctk.CTkFont(size=16, weight="bold"),
        width=200, height=45, fg_color="#1F6AA5", command=start_quiz
    ).pack(side="left", padx=6)

    ctk.CTkButton(
        action_row, text="Save to Bank", font=ctk.CTkFont(size=14),
        width=160, height=45, fg_color="#3A3A3A", hover_color="#4A4A4A", command=save_to_bank
    ).pack(side="left", padx=6)

    root.mainloop()


if __name__ == "__main__":
    launch_app()
