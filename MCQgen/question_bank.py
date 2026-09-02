import customtkinter as ctk
from tkinter import messagebox, filedialog, simpledialog
import os
import random

from concurrent.futures import ThreadPoolExecutor
from MCQgen.utils import parse_questions, save_bank_file

from MCQgen.utils import (
    list_question_sets,
    load_bank_file,
    save_bank_file,
    get_bank_filepath,
    parse_questions,
)
from MCQgen.dialogs import QuestionEditorDialog, ImportTextDialog

class QuestionBankPanel:
    def __init__(self, parent, on_start_quiz):
        self.parent = parent
        self.on_start_quiz = on_start_quiz

        self.sets_list = list_question_sets()
        self.current_set = self.sets_list[0]
        self.bank_questions = load_bank_file(self.current_set)

        self.search_var = ctk.StringVar()
        self.category_var = ctk.StringVar(value="All Categories")
        self.set_var = ctk.StringVar(value=self.current_set)

        self.build_ui()
        self.refresh_list()

        self.executor = ThreadPoolExecutor(max_workers=2)

    def build_ui(self):
        set_bar = ctk.CTkFrame(self.parent, corner_radius=8)
        set_bar.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(set_bar, text="Question Set:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(10, 5))
        self.set_menu = ctk.CTkOptionMenu(
            set_bar, values=self.sets_list, variable=self.set_var,
            command=self.change_set, width=180
        )
        self.set_menu.pack(side="left", padx=(0, 10), pady=8)

        ctk.CTkButton(set_bar, text="+ New Set", width=80, command=self.create_set).pack(side="left", padx=2)
        ctk.CTkButton(set_bar, text="Delete Set", width=80, fg_color="#B03A3A", hover_color="#8C2E2E",
                      command=self.delete_set).pack(side="left", padx=2)

        top_bar = ctk.CTkFrame(self.parent, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=(5, 5))

        ctk.CTkLabel(top_bar, text="Search:").pack(side="left", padx=(0, 5))
        search_entry = ctk.CTkEntry(top_bar, width=180, textvariable=self.search_var)
        search_entry.pack(side="left", padx=(0, 15))
        search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())

        ctk.CTkLabel(top_bar, text="Category:").pack(side="left", padx=(0, 5))
        self.category_menu = ctk.CTkOptionMenu(
            top_bar, values=["All Categories"], variable=self.category_var,
            command=lambda _v: self.refresh_list(), width=160
        )
        self.category_menu.pack(side="left", padx=(0, 15))

        button_bar = ctk.CTkFrame(self.parent, fg_color="transparent")
        button_bar.pack(fill="x", padx=15, pady=(0, 5))

        ctk.CTkButton(button_bar, text="+ Add Question", width=130, command=self.add_question).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(
            button_bar, text="Import Text", width=110, fg_color="#3A3A3A", hover_color="#4A4A4A",
            command=self.import_text
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            button_bar, text="Import File", width=110, fg_color="#3A3A3A", hover_color="#4A4A4A",
            command=self.import_file
        ).pack(side="left", padx=6)

        self.count_label = ctk.CTkLabel(self.parent, text="", font=ctk.CTkFont(size=11), text_color="#A0A0A0")
        self.count_label.pack(anchor="w", padx=15, pady=(0, 5))

        self.list_frame = ctk.CTkScrollableFrame(self.parent, height=210)
        self.list_frame.pack(fill="both", expand=True, padx=15, pady=5)

        builder = ctk.CTkFrame(self.parent, corner_radius=10)
        builder.pack(fill="x", padx=15, pady=(10, 15))

        ctk.CTkLabel(
            builder, text="Build a Quiz from Selected Bank", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(12, 6))

        self.pool_label = ctk.CTkLabel(builder, text="", font=ctk.CTkFont(size=11), text_color="#A0A0A0")
        self.pool_label.pack(anchor="w", padx=15)

        count_row = ctk.CTkFrame(builder, fg_color="transparent")
        count_row.pack(fill="x", padx=15, pady=(6, 4))
        ctk.CTkLabel(count_row, text="Number of questions (blank = all filtered):").pack(side="left")
        self.quiz_count_entry = ctk.CTkEntry(count_row, width=70)
        self.quiz_count_entry.pack(side="left", padx=8)

        opts_row1 = ctk.CTkFrame(builder, fg_color="transparent")
        opts_row1.pack(fill="x", padx=15, pady=4)
        self.shuffle_q_var = ctk.BooleanVar(value=True)
        self.shuffle_o_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opts_row1, text="Shuffle question order", variable=self.shuffle_q_var).pack(
            side="left", padx=(0, 15)
        )
        ctk.CTkCheckBox(opts_row1, text="Shuffle answer options", variable=self.shuffle_o_var).pack(side="left")

        opts_row2 = ctk.CTkFrame(builder, fg_color="transparent")
        opts_row2.pack(fill="x", padx=15, pady=4)
        self.instant_feedback_var = ctk.BooleanVar(value=False)
        self.allow_backtrack_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            opts_row2, text="Show answer confirmation after each question", variable=self.instant_feedback_var
        ).pack(side="left", padx=(0, 15))
        ctk.CTkCheckBox(
            opts_row2, text="Allow going back to previous questions", variable=self.allow_backtrack_var
        ).pack(side="left")

        timer_row = ctk.CTkFrame(builder, fg_color="transparent")
        timer_row.pack(fill="x", padx=15, pady=4)
        self.timer_mode_var = ctk.StringVar(value="stopwatch")
        ctk.CTkRadioButton(
            timer_row, text="Stopwatch (Count Up)", variable=self.timer_mode_var, value="stopwatch",
            command=self._update_timer_entry_state
        ).pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(
            timer_row, text="Time Limit (Countdown):", variable=self.timer_mode_var, value="countdown",
            command=self._update_timer_entry_state
        ).pack(side="left")
        self.timer_entry = ctk.CTkEntry(timer_row, width=60, state="disabled")
        self.timer_entry.pack(side="left", padx=8)
        ctk.CTkLabel(timer_row, text="minutes").pack(side="left")

        ctk.CTkButton(
            builder, text="Start Quiz from Bank", font=ctk.CTkFont(size=14, weight="bold"),
            height=42, fg_color="#1F6AA5", command=self.start_quiz_from_bank
        ).pack(pady=(12, 15))

    def update_set_dropdown(self):
        self.sets_list = list_question_sets()
        self.set_menu.configure(values=self.sets_list)

    def change_set(self, new_set):
        self.current_set = new_set
        self.bank_questions = load_bank_file(self.current_set)
        self.category_var.set("All Categories")
        self.refresh_list()

    def create_set(self):
        name = simpledialog.askstring("New Question Set", "Enter name for the new question set:")
        if not name or not name.strip():
            return
        name = name.strip()
        filepath = get_bank_filepath(name)
        if os.path.exists(filepath):
            messagebox.showerror("Error", "A set with that name already exists.")
            return

        save_bank_file(name, [])
        self.update_set_dropdown()
        self.set_var.set(name)
        self.change_set(name)

    def delete_set(self):
        if len(self.sets_list) <= 1:
            messagebox.showerror("Error", "You must keep at least one question set.")
            return

        if not messagebox.askyesno("Delete Set", f"Delete the set '{self.current_set}' and all its questions permanently?"):
            return

        filepath = get_bank_filepath(self.current_set)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError as e:
                messagebox.showerror("Error", f"Failed to delete set file:\n{e}")
                return

        self.update_set_dropdown()
        next_set = self.sets_list[0]
        self.set_var.set(next_set)
        self.change_set(next_set)

    def save_current_bank(self):
        save_bank_file(self.current_set, self.bank_questions)

    def _update_timer_entry_state(self):
        self.timer_entry.configure(
            state="normal" if self.timer_mode_var.get() == "countdown" else "disabled"
        )

    def get_categories(self):
        cats = sorted({q.get("category") or "Uncategorized" for q in self.bank_questions})
        return ["All Categories"] + cats

    def refresh_category_dropdown(self):
        values = self.get_categories()
        self.category_menu.configure(values=values)
        if self.category_var.get() not in values:
            self.category_var.set("All Categories")

    def filtered_questions(self):
        search = self.search_var.get().strip().lower()
        cat = self.category_var.get()
        results = []
        for q in self.bank_questions:
            if cat != "All Categories" and (q.get("category") or "Uncategorized") != cat:
                continue
            if search and search not in q["question"].lower():
                continue
            results.append(q)
        return results

    def refresh_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        results = self.filtered_questions()
        self.count_label.configure(
            text=f"Showing {len(results)} question(s) from '{self.current_set}' ({len(self.bank_questions)} total)"
        )

        if not results:
            ctk.CTkLabel(
                self.list_frame, text="No questions in this set matching your filters.", text_color="#808080"
            ).pack(pady=20)
        else:
            for q in results:
                row = ctk.CTkFrame(self.list_frame, corner_radius=8)
                row.pack(fill="x", pady=4, padx=4)

                preview = q["question"] if len(q["question"]) <= 100 else q["question"][:97] + "..."
                label_text = f"[{q.get('category') or 'Uncategorized'}] {preview}"

                ctk.CTkLabel(
                    row, text=label_text, anchor="w", justify="left", wraplength=520
                ).pack(side="left", padx=10, pady=8, fill="x", expand=True)

                btn_frame = ctk.CTkFrame(row, fg_color="transparent")
                btn_frame.pack(side="right", padx=6)
                ctk.CTkButton(
                    btn_frame, text="Edit", width=60, command=lambda qq=q: self.edit_question(qq)
                ).pack(side="left", padx=3)
                ctk.CTkButton(
                    btn_frame, text="Delete", width=60, fg_color="#B03A3A", hover_color="#8C2E2E",
                    command=lambda qq=q: self.delete_question(qq)
                ).pack(side="left", padx=3)

        self.refresh_category_dropdown()
        self._update_pool_label()

    def _update_pool_label(self):
        pool = len(self.filtered_questions())
        self.pool_label.configure(text=f"Available in current filter: {pool}")

    def add_question(self):
        QuestionEditorDialog(self.parent, existing=None, on_save=self._save_new)

    def _save_new(self, qdict):
        self.bank_questions.append(qdict)
        self.save_current_bank()
        self.refresh_list()

    def edit_question(self, qobj):
        QuestionEditorDialog(self.parent, existing=qobj, on_save=lambda updated: self._save_edit(qobj, updated))

    def _save_edit(self, old_obj, updated):
        idx = next((i for i, x in enumerate(self.bank_questions) if x is old_obj), None)
        if idx is not None:
            self.bank_questions[idx] = updated
            self.save_current_bank()
            self.refresh_list()

    def delete_question(self, qobj):
        if not messagebox.askyesno("Delete Question", "Delete this question from the set?"):
            return
        idx = next((i for i, x in enumerate(self.bank_questions) if x is qobj), None)
        if idx is not None:
            del self.bank_questions[idx]
            self.save_current_bank()
            self.refresh_list()

    def import_text(self):
        ImportTextDialog(self.parent, on_import=self.merge_import)

    def import_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            messagebox.showerror("Import Failed", str(e))
            return
        self.merge_import(content)

    def merge_import(self, text):
        """Dispatches text parsing and disk saving to a background thread."""
        # Show a quick loading message or disable buttons if desired
        self.count_label.configure(text="Importing questions in background...")

        # Offload the heavy work to a worker thread
        self.executor.submit(self._async_merge_worker, text)

    def _async_merge_worker(self, text):
        """Worker function running off the main GUI thread."""
        new_qs, skipped = parse_questions(text)

        existing_keys = {(q["question"].strip().lower(), q["answer"]) for q in self.bank_questions}
        added = 0
        dup = 0

        for q in new_qs:
            key = (q["question"].strip().lower(), q["answer"])
            if key in existing_keys:
                dup += 1
                continue
            self.bank_questions.append(q)
            existing_keys.add(key)
            added += 1

        # Perform disk write in background thread
        save_bank_file(self.current_set, self.bank_questions)

        # Schedule the UI update back on the main Tkinter thread
        self.parent.after(0, self._on_import_complete, added, dup, skipped)

    def _on_import_complete(self, added, dup, skipped):
        """Callback executed safely on the main GUI thread."""
        self.refresh_list()
        messagebox.showinfo(
            "Import Complete",
            f"Added {added} question(s) to '{self.current_set}'.\n"
            f"Skipped {dup} duplicate(s) and {skipped} unparseable block(s)."
        )

    def start_quiz_from_bank(self):
        pool = self.filtered_questions()
        if not pool:
            messagebox.showerror("No Questions", "No questions match the current filter.")
            return

        count_text = self.quiz_count_entry.get().strip()
        if count_text:
            try:
                count = int(count_text)
                if count <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Enter a valid number of questions.")
                return
        else:
            count = len(pool)
        count = min(count, len(pool))

        selected = list(pool)
        random.shuffle(selected)
        selected = selected[:count]

        if self.timer_mode_var.get() == "countdown":
            try:
                minutes = float(self.timer_entry.get())
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

        self.on_start_quiz(
            selected, mode, time_limit,
            self.shuffle_q_var.get(), self.shuffle_o_var.get(),
            self.instant_feedback_var.get(), self.allow_backtrack_var.get()
        )
