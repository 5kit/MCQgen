import os
import re

APP_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(APP_DIR, "quiz_history.json")
CACHE_FILE = os.path.join(APP_DIR, "last_input_cache.txt")
BANKS_DIR = os.path.join(APP_DIR, "question_banks")

# Ensure the sets folder exists
os.makedirs(BANKS_DIR, exist_ok=True)

LETTERS = ["A", "B", "C", "D"]

SAMPLE_FORMAT = """Q: Which word is the antonym of SCANT?
Category: Verbal
A: Abundant
B: Sparse
C: Meager
D: Slender
Answer: A
Explanation: "Scant" means barely sufficient, so its opposite is "Abundant".

Q: A shirt originally priced at $40 is discounted by 25%. What is the new price?
Category: Math
A: $28
B: $30
C: $32
D: $35
Answer: B
Explanation: 25% of $40 is $10, so the new price is $40 - $10 = $30."""


# ---------------------------------------------------------------------------
# Set / File Management Helpers
# ---------------------------------------------------------------------------

def list_question_sets():
    """List available bank set names based on .txt files in BANKS_DIR."""
    files = [f for f in os.listdir(BANKS_DIR) if f.endswith(".txt")]
    sets = [os.path.splitext(f)[0] for f in files]
    if not sets:
        sets = ["Default Bank"]
        save_bank_file("Default Bank", [])
    return sorted(sets)


def get_bank_filepath(set_name):
    clean_name = re.sub(r'[\\/*?:"<>|]', "", set_name).strip()
    return os.path.join(BANKS_DIR, f"{clean_name}.txt")


def load_bank_file(set_name):
    filepath = get_bank_filepath(set_name)
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return []
    if not text.strip():
        return []
    questions, _skipped = parse_questions(text)
    return questions


def save_bank_file(set_name, questions):
    filepath = get_bank_filepath(set_name)
    text = "\n\n".join(serialize_question(q) for q in questions)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError as e:
        from tkinter import messagebox
        messagebox.showerror("Save Failed", f"Could not save the question set:\n{e}")


# ---------------------------------------------------------------------------
# Parsing / Serialization
# ---------------------------------------------------------------------------

def _normalize_option_prefix(match):
    return f"{match.group(1).upper()}: "


def parse_questions(text):
    questions = []
    skipped = 0

    text = re.sub(r'(?im)^Q\d*:\s*', 'Q: ', text)
    text = re.sub(r'(?m)^([A-Da-d])[\.\)]\s*', _normalize_option_prefix, text)

    blocks = re.split(r'\n\s*(?=Q:)', text.strip())

    for block in blocks:
        if not block.strip():
            continue

        q_match = re.search(
            r'Q:\s*(.+?)(?=\nCategory:|\nA:)', block, re.DOTALL | re.IGNORECASE
        )
        options = re.findall(
            r'\n([A-Da-d]):\s*(.+?)(?=\n[A-Da-d]:|\nAnswer:|$)',
            block,
            re.DOTALL
        )
        answer_match = re.search(r'Answer:\s*([A-Da-d])', block, re.IGNORECASE)
        category_match = re.search(r'Category:\s*(.+)', block, re.IGNORECASE)
        explanation_match = re.search(r'Explanation:\s*(.+)', block, re.DOTALL | re.IGNORECASE)

        if q_match and len(options) == 4 and answer_match:
            question = q_match.group(1).strip()

            option_dict = {}
            for letter, opt_text in options:
                option_dict[letter.upper()] = opt_text.strip()

            category = category_match.group(1).strip() if category_match else None
            explanation = explanation_match.group(1).strip() if explanation_match else None

            questions.append({
                "question": question,
                "options": option_dict,
                "answer": answer_match.group(1).upper(),
                "category": category,
                "explanation": explanation,
            })
        else:
            skipped += 1

    return questions, skipped


def serialize_question(q):
    lines = [f"Q: {q['question']}"]
    if q.get("category"):
        lines.append(f"Category: {q['category']}")
    for letter in LETTERS:
        lines.append(f"{letter}: {q['options'][letter]}")
    lines.append(f"Answer: {q['answer']}")
    if q.get("explanation"):
        lines.append(f"Explanation: {q['explanation']}")
    return "\n".join(lines)
