import customtkinter as ctk
from tkinter import messagebox, filedialog, simpledialog
import os
import random
from concurrent.futures import ThreadPoolExecutor

from MCQgen.utils import (
    list_question_sets,
    load_bank_file,
    save_bank_file,
    get_bank_filepath,
    parse_questions,
)
from MCQgen.dialogs import QuestionEditorDialog, ImportTextDialog

PAGE_SIZE = 6

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

        self.current_page = 0
        self.row_pool = []

        self.build_ui()
        self._init_row_pool()
        self.refresh_list()

        self.executor = ThreadPoolExecutor(max_workers=2)

    def build_ui(self):
        # --- Helpers ---
        def add_checkbox(parent, text, variable, **pack_kwargs):
            cb = ctk.CTkCheckBox(parent, text=text, variable=variable)
            cb.pack(side="left", **pack_kwargs)
            return cb

        def add_radio(parent, text, variable, value, command=None, **pack_kwargs):
            rb = ctk.CTkRadioButton(
                parent, text=text, variable=variable, value=value, command=command
            )
            rb.pack(side="left", **pack_kwargs)
            return rb

        # 1. Top Bar (Question Set Selection)
        set_bar = ctk.CTkFrame(self.parent, corner_radius=8)
        set_bar.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(set_bar, text="Question Set:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(10, 5))
        self.set_menu = ctk.CTkOptionMenu(
            set_bar, values=self.sets_list, variable=self.set_var, command=self.change_set, width=180
        )
        self.set_menu.pack(side="left", padx=(0, 10), pady=8)

        ctk.CTkButton(set_bar, text="+ New Set", width=80, command=self.create_set).pack(side="left", padx=2)
        ctk.CTkButton(
            set_bar, text="Delete Set", width=80, fg_color="#B03A3A", hover_color="#8C2E2E", command=self.delete_set
        ).pack(side="left", padx=2)

        # 2. Filters Bar (Search & Category Dropdown)
        top_bar = ctk.CTkFrame(self.parent, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(top_bar, text="Search:").pack(side="left", padx=(0, 5))
        search_entry = ctk.CTkEntry(top_bar, width=180, textvariable=self.search_var)
        search_entry.pack(side="left", padx=(0, 15))
        search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())

        ctk.CTkLabel(top_bar, text="Category:").pack(side="left", padx=(0, 5))
        self.category_menu = ctk.CTkOptionMenu(
            top_bar, values=["All Categories"], variable=self.category_var, command=lambda _v: self.refresh_list(), width=160
        )
        self.category_menu.pack(side="left", padx=(0, 15))

        # 3. Action Buttons Bar
        button_bar = ctk.CTkFrame(self.parent, fg_color="transparent")
        button_bar.pack(fill="x", padx=15, pady=(0, 5))

        btn_config = [
            ("+ Add Question", 130, self.add_question, "#1F6AA5", "#144870", (0, 6)),
            ("Import Text", 110, self.import_text, "#3A3A3A", "#4A4A4A", 6),
            ("Import File", 110, self.import_file, "#3A3A3A", "#4A4A4A", 6),
        ]
        for text, width, cmd, fg, hover, px in btn_config:
            ctk.CTkButton(
                button_bar, text=text, width=width, command=cmd, fg_color=fg, hover_color=hover
            ).pack(side="left", padx=px)

        self.count_label = ctk.CTkLabel(self.parent, text="", font=ctk.CTkFont(size=11), text_color="#A0A0A0")
        self.count_label.pack(anchor="w", padx=15, pady=(0, 5))

        # 4. Outer Bounded Table Box
        outer_box = ctk.CTkFrame(self.parent, fg_color="#1A1D21", corner_radius=10)
        outer_box.pack(fill="x", padx=15, pady=5)

        # Table Column Header Bar
        header_bar = ctk.CTkFrame(outer_box, fg_color="#21252B", corner_radius=8, height=28)
        header_bar.pack(fill="x", padx=6, pady=(6, 2))
        header_bar.pack_propagate(False)

        ctk.CTkLabel(header_bar, text="#", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8A929B", width=24).pack(side="left", padx=(10, 6))
        ctk.CTkLabel(header_bar, text="Category", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8A929B", width=110, anchor="w").pack(side="left", padx=(0, 10))
        ctk.CTkLabel(header_bar, text="Question Preview", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8A929B", anchor="w").pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(header_bar, text="Actions", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8A929B", width=110, anchor="e").pack(side="right", padx=15)

        # Fixed Viewport Container
        self.list_container = ctk.CTkFrame(outer_box, height=265, fg_color="transparent")
        self.list_container.pack(fill="x", expand=False, padx=6, pady=(0, 6))
        self.list_container.pack_propagate(False)

        self.cover_frame = ctk.CTkFrame(self.list_container, fg_color="transparent")
        self.cover_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Empty State Indicator
        self.empty_label = ctk.CTkLabel(
            self.cover_frame,
            text="No questions found in this set.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#8A929B"
        )

        # 5. Pagination Controls Bar
        self.page_controls = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.page_controls.pack(fill="x", padx=15, pady=(2, 5))

        self.prev_page_btn = ctk.CTkButton(
            self.page_controls, text="← Prev Page", width=90, height=24, command=self.prev_page
        )
        self.prev_page_btn.pack(side="left")

        self.page_label = ctk.CTkLabel(self.page_controls, text="Page 1 of 1", font=ctk.CTkFont(size=11))
        self.page_label.pack(side="left", expand=True)

        self.next_page_btn = ctk.CTkButton(
            self.page_controls, text="Next Page →", width=90, height=24, command=self.next_page
        )
        self.next_page_btn.pack(side="right")

        # 6. Quiz Builder Section
        builder = ctk.CTkFrame(self.parent, corner_radius=10)
        builder.pack(fill="x", padx=15, pady=(5, 10))

        ctk.CTkLabel(
            builder, text="Build a Quiz from Selected Bank", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(8, 4))

        self.pool_label = ctk.CTkLabel(builder, text="", font=ctk.CTkFont(size=11), text_color="#A0A0A0")
        self.pool_label.pack(anchor="w", padx=15)

        count_row = ctk.CTkFrame(builder, fg_color="transparent")
        count_row.pack(fill="x", padx=15, pady=(4, 2))
        ctk.CTkLabel(count_row, text="Number of questions (blank = all filtered):").pack(side="left")
        self.quiz_count_entry = ctk.CTkEntry(count_row, width=70)
        self.quiz_count_entry.pack(side="left", padx=8)

        opts_row1 = ctk.CTkFrame(builder, fg_color="transparent")
        opts_row1.pack(fill="x", padx=15, pady=2)
        self.shuffle_q_var = ctk.BooleanVar(value=True)
        self.shuffle_o_var = ctk.BooleanVar(value=False)
        add_checkbox(opts_row1, "Shuffle question order", self.shuffle_q_var, padx=(0, 15))
        add_checkbox(opts_row1, "Shuffle answer options", self.shuffle_o_var)

        opts_row2 = ctk.CTkFrame(builder, fg_color="transparent")
        opts_row2.pack(fill="x", padx=15, pady=2)
        self.instant_feedback_var = ctk.BooleanVar(value=False)
        self.allow_backtrack_var = ctk.BooleanVar(value=True)
        add_checkbox(opts_row2, "Show answer confirmation after each question", self.instant_feedback_var, padx=(0, 15))
        add_checkbox(opts_row2, "Allow going back to previous questions", self.allow_backtrack_var)

        timer_row = ctk.CTkFrame(builder, fg_color="transparent")
        timer_row.pack(fill="x", padx=15, pady=2)
        self.timer_mode_var = ctk.StringVar(value="stopwatch")

        add_radio(
            timer_row, "Stopwatch (Count Up)", self.timer_mode_var, "stopwatch",
            command=self._update_timer_entry_state, padx=(0, 15)
        )
        add_radio(
            timer_row, "Time Limit (Countdown):", self.timer_mode_var, "countdown",
            command=self._update_timer_entry_state
        )

        self.timer_entry = ctk.CTkEntry(timer_row, width=60, state="disabled")
        self.timer_entry.pack(side="left", padx=8)
        ctk.CTkLabel(timer_row, text="minutes").pack(side="left")

        # Large Action Button inside the builder frame
        ctk.CTkButton(
            builder,
            text="Start Quiz from Bank",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=350,
            height=48,
            fg_color="#1F6AA5",
            command=self.start_quiz_from_bank
        ).pack(pady=(8, 12))

    def _init_row_pool(self):
        """Constructs fixed slot rows inside self.cover_frame."""
        for i in range(PAGE_SIZE):
            card = ctk.CTkFrame(
                self.cover_frame,
                fg_color="#24282F",
                border_color="#323842",
                border_width=1,
                corner_radius=8,
                height=38
            )
            card.pack(fill="x", pady=3, padx=6)
            card.pack_propagate(False)

            left_frame = ctk.CTkFrame(card, fg_color="transparent")
            left_frame.pack(side="left", fill="x", expand=True, padx=(10, 5))

            # Row Index Label
            num_lbl = ctk.CTkLabel(
                left_frame,
                text=f"{i + 1}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#6C757D",
                width=24,
                anchor="w"
            )
            num_lbl.pack(side="left", padx=(0, 6))

            # Category Pill Badge
            badge_frame = ctk.CTkFrame(left_frame, fg_color="#1F4E79", corner_radius=12, height=22)
            badge_frame.pack(side="left", padx=(0, 10))

            badge_lbl = ctk.CTkLabel(
                badge_frame, text="", font=ctk.CTkFont(size=10, weight="bold"), text_color="#E0E6ED"
            )
            badge_lbl.pack(padx=8, pady=2)

            # Question Text Preview
            question_lbl = ctk.CTkLabel(left_frame, text="", font=ctk.CTkFont(size=12), anchor="w", justify="left")
            question_lbl.pack(side="left", fill="x", expand=True)

            # Action Buttons
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(side="right", padx=8)

            edit_btn = ctk.CTkButton(btn_frame, text="Edit", width=52, height=24, font=ctk.CTkFont(size=11), fg_color="#2B303A", hover_color="#3A414F")
            edit_btn.pack(side="left", padx=2)

            del_btn = ctk.CTkButton(btn_frame, text="Delete", width=52, height=24, font=ctk.CTkFont(size=11), fg_color="#B03A3A", hover_color="#8C2E2E")
            del_btn.pack(side="left", padx=2)

            card.pack_forget()  # Initially unmapped until refresh_list renders
            self.row_pool.append({
                "frame": card,
                "num_label": num_lbl,
                "badge_frame": badge_frame,
                "badge_label": badge_lbl,
                "label": question_lbl,
                "edit": edit_btn,
                "delete": del_btn
            })

    def update_set_dropdown(self):
        self.sets_list = list_question_sets()
        self.set_menu.configure(values=self.sets_list)

    def change_set(self, new_set):
        """Switches current question set and resets view variables."""
        self.current_set = new_set
        self.bank_questions = load_bank_file(self.current_set)
        self.category_var.set("All Categories")
        self.search_var.set("")
        self.current_page = 0
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
        """Updates slot card contents in place and cleanly hides empty slots."""
        results = self.filtered_questions()
        total_items = len(results)
        max_pages = max(1, (total_items + PAGE_SIZE - 1) // PAGE_SIZE)

        # Keep current_page within bounds
        if self.current_page >= max_pages:
            self.current_page = max_pages - 1
        if self.current_page < 0:
            self.current_page = 0

        # Update Header Counter & Page Indicator
        self.count_label.configure(
            text=f"Showing {total_items} question(s) from '{self.current_set}' ({len(self.bank_questions)} total)"
        )
        self.page_label.configure(text=f"Page {self.current_page + 1} of {max_pages}")

        # Update Navigation Button States
        self.prev_page_btn.configure(state="normal" if self.current_page > 0 else "disabled")
        self.next_page_btn.configure(state="normal" if self.current_page < max_pages - 1 else "disabled")

        # Handle Empty State
        if not results:
            for slot in self.row_pool:
                slot["frame"].pack_forget()

            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
            self.refresh_category_dropdown()
            self._update_pool_label()
            return

        # Hide empty state label if results exist
        self.empty_label.place_forget()

        # Slice current page data
        start_idx = self.current_page * PAGE_SIZE
        page_items = results[start_idx: start_idx + PAGE_SIZE]

        for i, slot in enumerate(self.row_pool):
            if i < len(page_items):
                q = page_items[i]
                category = q.get("category") or "Uncategorized"
                preview = q["question"] if len(q["question"]) <= 85 else q["question"][:82] + "..."

                # Global question index (1, 2, 3...)
                global_index = start_idx + i + 1

                # Configure slot components
                slot["num_label"].configure(text=str(global_index))
                slot["badge_label"].configure(text=category)
                slot["label"].configure(text=preview)

                # Set button commands
                slot["edit"].configure(command=lambda qq=q: self.edit_question(qq))
                slot["delete"].configure(command=lambda qq=q: self.delete_question(qq))

                # Map card frame & internal components
                slot["frame"].pack(fill="x", pady=3, padx=6)
                slot["num_label"].pack(side="left", padx=(0, 6))
                slot["badge_frame"].pack(side="left", padx=(0, 10))
                slot["edit"].pack(side="left", padx=2)
                slot["delete"].pack(side="left", padx=2)
            else:
                # Unmap unused card frames on non-full pages
                slot["frame"].pack_forget()

        self.refresh_category_dropdown()
        self._update_pool_label()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_list()

    def next_page(self):
        results = self.filtered_questions()
        max_pages = (len(results) + PAGE_SIZE - 1) // PAGE_SIZE
        if self.current_page < max_pages - 1:
            self.current_page += 1
            self.refresh_list()

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
        """Dispatches only the text parsing to a background thread (pure computation,
        touches no shared state). Merging into the bank and saving to disk happens
        back on the main thread, so it can never race with Add/Edit/Delete/set-switch."""
        self.count_label.configure(text="Importing questions in background...")
        target_set = self.current_set  # captured now, in case the user switches sets mid-parse
        self.executor.submit(self._async_parse_worker, text, target_set)

    def _async_parse_worker(self, text, target_set):
        """Worker function running off the main GUI thread. Only parses text --
        does not touch self.bank_questions, self.current_set, or any widget."""
        new_qs, skipped = parse_questions(text)
        self.parent.after(0, self._on_parse_complete, new_qs, skipped, target_set)

    def _on_parse_complete(self, new_qs, skipped, target_set):
        """Back on the main thread: safe to merge into the bank and save."""
        # If the user switched away from the target set while parsing ran, merge
        # into that set's saved data directly rather than the currently-viewed list.
        if target_set == self.current_set:
            bank = self.bank_questions
        else:
            bank = load_bank_file(target_set)

        existing_keys = {(q["question"].strip().lower(), q["answer"]) for q in bank}
        added = 0
        dup = 0
        for q in new_qs:
            key = (q["question"].strip().lower(), q["answer"])
            if key in existing_keys:
                dup += 1
                continue
            bank.append(q)
            existing_keys.add(key)
            added += 1

        save_bank_file(target_set, bank)

        if target_set == self.current_set:
            self.refresh_list()
        else:
            self._update_pool_label()

        messagebox.showinfo(
            "Import Complete",
            f"Added {added} question(s) to '{target_set}'.\n"
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
