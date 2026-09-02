import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
import json
import random
import time
from datetime import datetime
from MCQgen.utils import LETTERS, HISTORY_FILE


class QuizApp(ctk.CTk):
    def __init__(self, questions, timer_mode="stopwatch", time_limit=0,
                 shuffle_questions=False, shuffle_options=False,
                 instant_feedback=False, allow_backtrack=True,
                 on_return_to_builder=None):
        super().__init__()
        self.timer_mode = timer_mode
        self.time_limit = time_limit
        self.shuffle_questions = shuffle_questions
        self.shuffle_options = shuffle_options
        self.instant_feedback = instant_feedback
        self.allow_backtrack = allow_backtrack
        self.on_return_to_builder = on_return_to_builder

        self.questions = self._prepare_questions(questions)

        self.current = 0
        self.score = 0
        self.user_answers = [None] * len(self.questions)
        self.flagged = set()

        self.start_time = time.time()
        self.timer_running = True
        self.quiz_completed = False

        self.title("CCAT Practice Quiz")
        self.geometry("960x780")
        self.minsize(760, 640)
        self.resizable(True, True)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Key>", self.on_key)

        self.build_ui()
        self.show_question()
        self.update_timer()

    def _prepare_questions(self, questions):
        qs = [dict(q) for q in questions]

        if self.shuffle_questions:
            random.shuffle(qs)

        if self.shuffle_options:
            for q in qs:
                pairs = [(letter, q["options"][letter]) for letter in LETTERS]
                correct_text = q["options"][q["answer"]]
                random.shuffle(pairs)

                new_options = {}
                new_answer = q["answer"]
                for new_letter, (_, opt_text) in zip(LETTERS, pairs):
                    new_options[new_letter] = opt_text
                    if opt_text == correct_text:
                        new_answer = new_letter

                q["options"] = new_options
                q["answer"] = new_answer

        return qs

    def build_ui(self):
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=30, pady=(20, 5))

        self.progress_label = ctk.CTkLabel(
            self.top_frame, text="", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.progress_label.pack(side="left")

        self.timer_label = ctk.CTkLabel(
            self.top_frame, text="", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.timer_label.pack(side="right")

        self.dots_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dots_frame.pack(fill="x", padx=30, pady=(0, 5))

        self.dot_buttons = []
        cols = 20
        for i in range(len(self.questions)):
            b = ctk.CTkButton(
                self.dots_frame,
                text=str(i + 1),
                width=28,
                height=28,
                corner_radius=14,
                font=ctk.CTkFont(size=10),
                fg_color="#3A3A3A",
                hover_color="#4A4A4A",
                command=lambda idx=i: self.jump_to(idx)
            )
            b.grid(row=i // cols, column=i % cols, padx=2, pady=2)
            if not self.allow_backtrack:
                b.configure(state="disabled")
            self.dot_buttons.append(b)

        self.question_frame = ctk.CTkFrame(self, corner_radius=10)
        self.question_frame.pack(fill="x", padx=30, pady=10)

        self.question_label = ctk.CTkLabel(
            self.question_frame,
            text="",
            font=ctk.CTkFont(size=16, weight="bold"),
            wraplength=850,
            justify="left",
            anchor="w"
        )
        self.question_label.pack(padx=20, pady=20, fill="x")

        self.answer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.answer_frame.pack(fill="both", expand=True, padx=30, pady=10)

        self.answer_buttons = []
        for i in range(4):
            button = ctk.CTkButton(
                self.answer_frame,
                text="",
                font=ctk.CTkFont(size=14),
                anchor="w",
                height=50,
                corner_radius=8,
                fg_color="#2b2b2b",
                hover_color="#3b3b3b",
                command=lambda index=i: self.answer_clicked(index)
            )
            button.pack(fill="x", pady=6)
            self.answer_buttons.append(button)

        self.feedback_label = ctk.CTkLabel(
            self.answer_frame,
            text="",
            font=ctk.CTkFont(size=13),
            wraplength=850,
            justify="left",
            anchor="w"
        )
        self.feedback_label.pack(fill="x", pady=(4, 0))

        self.navigation = ctk.CTkFrame(self, fg_color="transparent")
        self.navigation.pack(fill="x", padx=30, pady=(10, 20))

        self.previous_button = ctk.CTkButton(
            self.navigation,
            text="← Previous",
            width=120,
            command=self.previous_question
        )
        self.previous_button.pack(side="left")
        if not self.allow_backtrack:
            self.previous_button.configure(state="disabled")

        self.next_button = ctk.CTkButton(
            self.navigation,
            text="Next →",
            width=120,
            command=self.next_question
        )
        self.next_button.pack(side="left", padx=10)

        self.flag_button = ctk.CTkButton(
            self.navigation,
            text="⚑ Flag",
            width=100,
            fg_color="#3A3A3A",
            hover_color="#4A4A4A",
            command=self.toggle_flag
        )
        self.flag_button.pack(side="left")

        self.review_button = ctk.CTkButton(
            self.navigation,
            text="Review Questions",
            width=140,
            fg_color="#3A3A3A",
            hover_color="#3A3A3A",
            state="disabled",
            command=self.show_review
        )
        self.review_button.pack(side="right")

        shortcut_text = "Shortcuts: 1-4 / A-D select an answer · Enter next · F flag"
        if self.allow_backtrack:
            shortcut_text = "Shortcuts: 1-4 / A-D select an answer · ← → navigate · Enter next · F flag"

        hint = ctk.CTkLabel(
            self, text=shortcut_text, font=ctk.CTkFont(size=10), text_color="#808080"
        )
        hint.pack(pady=(0, 8))

    def on_key(self, event):
        if self.quiz_completed:
            return

        key = event.keysym.lower()
        mapping = {"1": 0, "2": 1, "3": 2, "4": 3, "a": 0, "b": 1, "c": 2, "d": 3}

        if key in mapping:
            self.answer_clicked(mapping[key])
        elif key == "left":
            self.previous_question()
        elif key in ("right", "return"):
            self.next_question()
        elif key == "f":
            self.toggle_flag()

    def show_question(self):
        if self.current >= len(self.questions):
            self.attempt_finish()
            return

        q = self.questions[self.current]

        self.progress_label.configure(
            text=f"Question {self.current + 1} of {len(self.questions)}"
            + (f"  ·  {q['category']}" if q.get("category") else "")
        )
        self.question_label.configure(text=q["question"])

        selected = self.user_answers[self.current]
        locked = self.instant_feedback and selected is not None

        for i, letter in enumerate(LETTERS):
            opt_text = f"{letter}. {q['options'][letter]}"
            self.answer_buttons[i].configure(text=opt_text)

            if locked:
                if letter == q["answer"]:
                    color = "#2FA572"
                elif letter == selected:
                    color = "#EA5455"
                else:
                    color = "#2b2b2b"
                self.answer_buttons[i].configure(fg_color=color, state="disabled")
            else:
                color = "#1F6AA5" if letter == selected else "#2b2b2b"
                self.answer_buttons[i].configure(fg_color=color, state="normal")

        if locked:
            correct = selected == q["answer"]
            text = "✓ Correct!" if correct else f"✗ Incorrect — correct answer is {q['answer']}."
            if q.get("explanation"):
                text += f"\n{q['explanation']}"
            self.feedback_label.configure(
                text=text, text_color="#2FA572" if correct else "#EA5455"
            )
        else:
            self.feedback_label.configure(text="")

        if self.allow_backtrack:
            self.previous_button.configure(
                state="disabled" if self.current == 0 else "normal"
            )
        else:
            self.previous_button.configure(state="disabled")

        self.next_button.configure(
            text="Finish" if self.current == len(self.questions) - 1 else "Next →"
        )

        self.update_flag_button()
        self.update_progress_dots()

    def update_flag_button(self):
        flagged = self.current in self.flagged
        self.flag_button.configure(
            text="⚑ Flagged" if flagged else "⚑ Flag",
            fg_color="#B58B00" if flagged else "#3A3A3A"
        )

    def update_progress_dots(self):
        for i, b in enumerate(self.dot_buttons):
            if i == self.current:
                color = "#1F6AA5"
            elif i in self.flagged:
                color = "#B58B00"
            elif self.user_answers[i] is not None:
                if self.instant_feedback:
                    color = "#2FA572" if self.user_answers[i] == self.questions[i]["answer"] else "#EA5455"
                else:
                    color = "#2FA572"
            else:
                color = "#3A3A3A"
            b.configure(fg_color=color)

    def answer_clicked(self, index):
        if self.instant_feedback and self.user_answers[self.current] is not None:
            return
        self.user_answers[self.current] = LETTERS[index]
        self.show_question()

    def toggle_flag(self):
        if self.current in self.flagged:
            self.flagged.discard(self.current)
        else:
            self.flagged.add(self.current)
        self.update_flag_button()
        self.update_progress_dots()

    def jump_to(self, idx):
        if not self.allow_backtrack:
            return
        self.current = idx
        self.show_question()

    def previous_question(self):
        if not self.allow_backtrack:
            return
        if self.current > 0:
            self.current -= 1
            self.show_question()

    def next_question(self):
        if self.current < len(self.questions) - 1:
            self.current += 1
            self.show_question()
        else:
            self.attempt_finish()

    def attempt_finish(self):
        unanswered = sum(1 for a in self.user_answers if a is None)
        if unanswered > 0:
            proceed = messagebox.askyesno(
                "Unanswered Questions",
                f"You have {unanswered} unanswered question(s). Finish anyway?"
            )
            if not proceed:
                return
        self.finish_quiz()

    def on_close(self):
        if not self.quiz_completed:
            if not messagebox.askyesno(
                "Quit Quiz",
                "The quiz is still in progress. Quitting now will lose your progress. Continue?"
            ):
                return
        self.destroy()

    def show_review(self):
        if not self.quiz_completed:
            return

        review_window = ctk.CTkToplevel(self)
        review_window.title("Review Questions")
        review_window.geometry("880x700")
        review_window.grab_set()

        title = ctk.CTkLabel(
            review_window, text="Review Questions", font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=15)

        scroll_frame = ctk.CTkScrollableFrame(review_window, width=820, height=550)
        scroll_frame.pack(padx=20, pady=10, fill="both", expand=True)

        for i, q in enumerate(self.questions):
            user_answer = self.user_answers[i]
            correct_answer = q["answer"]

            q_frame = ctk.CTkFrame(scroll_frame)
            q_frame.pack(fill="x", pady=10, padx=5)

            header_text = f"Q{i + 1}: {q['question']}"
            if i in self.flagged:
                header_text = "⚑ " + header_text
            if q.get("category"):
                header_text += f"  [{q['category']}]"

            ctk.CTkLabel(
                q_frame, text=header_text, font=ctk.CTkFont(size=14, weight="bold"),
                wraplength=760, justify="left", anchor="w"
            ).pack(anchor="w", padx=15, pady=(10, 5))

            for letter in LETTERS:
                status = ""
                text_color = ("#DCE4EE", "#DCE4EE")

                if letter == correct_answer:
                    status = "✓ Correct Answer"
                    text_color = "#2FA572"
                elif letter == user_answer:
                    status = "✗ Your Answer"
                    text_color = "#EA5455"

                opt_text = f"{letter}. {q['options'][letter]}"
                if status:
                    opt_text += f"    ({status})"

                ctk.CTkLabel(
                    q_frame, text=opt_text, font=ctk.CTkFont(size=12), text_color=text_color,
                    wraplength=740, justify="left", anchor="w"
                ).pack(anchor="w", padx=30, pady=2)

            if user_answer is None:
                res_text = f"Status: Not Answered | Correct Answer: {correct_answer}"
            elif user_answer == correct_answer:
                res_text = "Status: Correct"
            else:
                res_text = f"Status: Incorrect | Correct Answer: {correct_answer}"

            ctk.CTkLabel(
                q_frame, text=res_text, font=ctk.CTkFont(size=11, slant="italic"), anchor="w"
            ).pack(anchor="w", padx=15, pady=(5, 0))

            if q.get("explanation"):
                ctk.CTkLabel(
                    q_frame, text=f"Explanation: {q['explanation']}", font=ctk.CTkFont(size=11),
                    text_color="#A0A0A0", wraplength=740, justify="left", anchor="w"
                ).pack(anchor="w", padx=15, pady=(3, 10))

        ctk.CTkButton(review_window, text="Close", command=review_window.destroy).pack(pady=15)

    def update_timer(self):
        if not self.timer_running:
            return

        elapsed = int(time.time() - self.start_time)

        if self.timer_mode == "stopwatch":
            minutes = elapsed // 60
            seconds = elapsed % 60
            self.timer_label.configure(text=f"Time: {minutes:02d}:{seconds:02d}")
        else:
            remaining = self.time_limit - elapsed
            if remaining <= 0:
                self.timer_label.configure(text="Time: 00:00")
                if not self.quiz_completed:
                    self.finish_quiz()
                return

            minutes = remaining // 60
            seconds = remaining % 60
            self.timer_label.configure(text=f"Time: {minutes:02d}:{seconds:02d}")

        self.after(250, self.update_timer)

    def finish_quiz(self):
        if self.quiz_completed:
            return
        self.timer_running = False
        self.quiz_completed = True
        self.score = sum(
            1 for i, answer in enumerate(self.user_answers)
            if answer is not None and answer == self.questions[i]["answer"]
        )
        self._save_history_entry()
        self.show_result()

    def _category_stats(self):
        stats = {}
        for i, q in enumerate(self.questions):
            cat = q.get("category") or "Uncategorized"
            correct, total = stats.get(cat, (0, 0))
            total += 1
            if self.user_answers[i] == q["answer"]:
                correct += 1
            stats[cat] = (correct, total)
        return stats

    def _load_history(self):
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def _save_history_entry(self):
        total = len(self.questions)
        percentage = (self.score / total) * 100 if total > 0 else 0
        elapsed = int(time.time() - self.start_time)

        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "score": self.score,
            "total": total,
            "percentage": round(percentage, 1),
            "elapsed_seconds": elapsed,
        }

        history = self._load_history()
        history.append(entry)
        history = history[-50:]

        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except OSError:
            pass

    def show_result(self):
        for widget in self.winfo_children():
            widget.destroy()

        total = len(self.questions)
        percentage = (self.score / total) * 100 if total > 0 else 0
        elapsed = int(time.time() - self.start_time)
        minutes, seconds = elapsed // 60, elapsed % 60

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        content = ctk.CTkFrame(scroll, fg_color="transparent")
        content.pack(fill="x", expand=True)

        ctk.CTkLabel(
            content, text="Quiz Complete", font=ctk.CTkFont(size=26, weight="bold")
        ).pack(pady=(20, 15))

        ctk.CTkLabel(
            content, text=f"Score: {self.score} / {total}", font=ctk.CTkFont(size=20)
        ).pack(pady=4)

        ctk.CTkLabel(
            content, text=f"Percentage: {percentage:.1f}%", font=ctk.CTkFont(size=18)
        ).pack(pady=4)

        ctk.CTkLabel(
            content, text=f"Total Time: {minutes:02d}:{seconds:02d}", font=ctk.CTkFont(size=14)
        ).pack(pady=4)

        flagged_count = len(self.flagged)
        if flagged_count:
            ctk.CTkLabel(
                content, text=f"Flagged for review: {flagged_count}",
                font=ctk.CTkFont(size=12), text_color="#B58B00"
            ).pack(pady=(0, 5))

        cat_stats = self._category_stats()
        if len(cat_stats) > 1 or "Uncategorized" not in cat_stats:
            cat_frame = ctk.CTkFrame(content, corner_radius=10)
            cat_frame.pack(fill="x", pady=(15, 10), padx=20)
            ctk.CTkLabel(
                cat_frame, text="Score by Category", font=ctk.CTkFont(size=14, weight="bold")
            ).pack(pady=(12, 6))
            for cat, (correct, total_c) in cat_stats.items():
                pct = (correct / total_c) * 100 if total_c else 0
                ctk.CTkLabel(
                    cat_frame, text=f"{cat}: {correct}/{total_c}  ({pct:.0f}%)", font=ctk.CTkFont(size=12)
                ).pack(pady=2)

        history = self._load_history()
        previous = history[:-1][-5:]
        if previous:
            hist_frame = ctk.CTkFrame(content, corner_radius=10)
            hist_frame.pack(fill="x", pady=10, padx=20)
            ctk.CTkLabel(
                hist_frame, text="Recent Attempts", font=ctk.CTkFont(size=14, weight="bold")
            ).pack(pady=(12, 6))
            for entry in reversed(previous):
                date_str = entry["timestamp"].split("T")[0]
                ctk.CTkLabel(
                    hist_frame,
                    text=f"{date_str}:  {entry['score']}/{entry['total']}  ({entry['percentage']}%)",
                    font=ctk.CTkFont(size=12)
                ).pack(pady=2)

        button_row = ctk.CTkFrame(content, fg_color="transparent")
        button_row.pack(pady=(20, 15))

        ctk.CTkButton(
            button_row, text="Review Questions", width=160, height=40,
            fg_color="#4A4A4A", hover_color="#5A5A5A", command=self.show_review
        ).grid(row=0, column=0, padx=6, pady=6)

        ctk.CTkButton(
            button_row, text="Export Results", width=160, height=40,
            fg_color="#4A4A4A", hover_color="#5A5A5A", command=self.export_results
        ).grid(row=0, column=1, padx=6, pady=6)

        ctk.CTkButton(
            button_row, text="Restart Quiz", width=160, height=40,
            fg_color="#2FA572", hover_color="#1E7A52", command=self.restart
        ).grid(row=1, column=0, padx=6, pady=6)

        ctk.CTkButton(
            button_row, text="Back to Builder", width=160, height=40,
            fg_color="#1F6AA5", hover_color="#184E7A", command=self.return_to_builder
        ).grid(row=1, column=1, padx=6, pady=6)

    def return_to_builder(self):
        self.destroy()
        if self.on_return_to_builder:
            self.on_return_to_builder()

    def export_results(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="quiz_results.txt"
        )
        if not path:
            return

        total = len(self.questions)
        percentage = (self.score / total) * 100 if total > 0 else 0
        elapsed = int(time.time() - self.start_time)
        minutes, seconds = elapsed // 60, elapsed % 60

        lines = [
            "CCAT Practice Quiz Results",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Score: {self.score} / {total} ({percentage:.1f}%)",
            f"Time: {minutes:02d}:{seconds:02d}",
            "",
            "Score by Category:",
        ]
        for cat, (correct, total_c) in self._category_stats().items():
            pct = (correct / total_c) * 100 if total_c else 0
            lines.append(f"  {cat}: {correct}/{total_c} ({pct:.0f}%)")

        lines += ["", "Missed / Unanswered Questions:"]
        missed_any = False
        for i, q in enumerate(self.questions):
            user_answer = self.user_answers[i]
            if user_answer != q["answer"]:
                missed_any = True
                lines.append(f"  Q{i + 1}: {q['question']}")
                lines.append(f"    Your answer: {user_answer or 'None'} | Correct: {q['answer']}")
                if q.get("explanation"):
                    lines.append(f"    Explanation: {q['explanation']}")
        if not missed_any:
            lines.append("  None — perfect score!")

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            messagebox.showinfo("Export Complete", f"Results exported to:\n{path}")
        except OSError as e:
            messagebox.showerror("Export Failed", str(e))

    def restart(self):
        if not messagebox.askyesno(
            "Restart Quiz", "This will reset your score and answers. Continue?"
        ):
            return

        for widget in self.winfo_children():
            widget.destroy()

        self.questions = self._prepare_questions(self.questions)
        self.current = 0
        self.score = 0
        self.user_answers = [None] * len(self.questions)
        self.flagged = set()
        self.start_time = time.time()
        self.timer_running = True
        self.quiz_completed = False

        self.build_ui()
        self.show_question()
        self.update_timer()
