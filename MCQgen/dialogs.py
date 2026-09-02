import customtkinter as ctk
from tkinter import messagebox
from MCQgen.utils import LETTERS


class QuestionEditorDialog(ctk.CTkToplevel):
    def __init__(self, parent, existing, on_save):
        super().__init__(parent)
        self.title("Edit Question" if existing else "Add Question")
        self.geometry("640x680")
        self.minsize(560, 600)
        self.grab_set()
        self.on_save = on_save

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(scroll, text="Category (optional)", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        self.category_entry = ctk.CTkEntry(scroll, width=560)
        self.category_entry.pack(fill="x", pady=(2, 12))

        ctk.CTkLabel(scroll, text="Question", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        self.question_box = ctk.CTkTextbox(scroll, width=560, height=80)
        self.question_box.pack(fill="x", pady=(2, 12))

        self.option_entries = {}
        for letter in LETTERS:
            ctk.CTkLabel(scroll, text=f"Option {letter}", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
            entry = ctk.CTkEntry(scroll, width=560)
            entry.pack(fill="x", pady=(2, 10))
            self.option_entries[letter] = entry

        ctk.CTkLabel(scroll, text="Correct Answer", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        self.answer_var = ctk.StringVar(value="A")
        ctk.CTkOptionMenu(scroll, values=LETTERS, variable=self.answer_var, width=100).pack(anchor="w", pady=(2, 12))

        ctk.CTkLabel(scroll, text="Explanation (optional)", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        self.explanation_box = ctk.CTkTextbox(scroll, width=560, height=80)
        self.explanation_box.pack(fill="x", pady=(2, 12))

        if existing:
            self.category_entry.insert(0, existing.get("category") or "")
            self.question_box.insert("1.0", existing["question"])
            for letter in LETTERS:
                self.option_entries[letter].insert(0, existing["options"][letter])
            self.answer_var.set(existing["answer"])
            self.explanation_box.insert("1.0", existing.get("explanation") or "")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 15))
        ctk.CTkButton(btn_frame, text="Save", width=140, command=self.save).pack(side="left", padx=6)
        ctk.CTkButton(
            btn_frame, text="Cancel", width=140, fg_color="#3A3A3A", hover_color="#4A4A4A",
            command=self.destroy
        ).pack(side="left", padx=6)

    def save(self):
        question = self.question_box.get("1.0", "end").strip()
        category = self.category_entry.get().strip()
        options = {letter: self.option_entries[letter].get().strip() for letter in LETTERS}
        answer = self.answer_var.get()
        explanation = self.explanation_box.get("1.0", "end").strip()

        if not question or any(not v for v in options.values()):
            messagebox.showerror("Missing Fields", "Question text and all four options are required.")
            return

        qdict = {
            "question": question,
            "options": options,
            "answer": answer,
            "category": category or None,
            "explanation": explanation or None,
        }
        self.on_save(qdict)
        self.destroy()


class ImportTextDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_import):
        super().__init__(parent)
        self.title("Import Questions from Text")
        self.geometry("700x580")
        self.minsize(600, 480)
        self.grab_set()

        ctk.CTkLabel(
            self, text="Paste questions in Q: / A: / B: / C: / D: / Answer: format:"
        ).pack(pady=(15, 5))

        self.textbox = ctk.CTkTextbox(self, width=650, height=420, font=("Consolas", 11))
        self.textbox.pack(padx=20, pady=5, fill="both", expand=True)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Import", width=140, command=lambda: self._do_import(on_import)).pack(
            side="left", padx=6
        )
        ctk.CTkButton(
            btn_frame, text="Cancel", width=140, fg_color="#3A3A3A", hover_color="#4A4A4A",
            command=self.destroy
        ).pack(side="left", padx=6)

    def _do_import(self, on_import):
        text = self.textbox.get("1.0", "end")
        if not text.strip():
            messagebox.showerror("Empty", "Paste some questions first.")
            return
        on_import(text)
        self.destroy()
