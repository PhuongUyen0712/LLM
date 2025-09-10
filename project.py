import google.generativeai as genai
import json

API_KEY = "AIzaSyDk9g_FXGW6IRKORvUrbOKCQzBuWld_Zy8"  
MODEL_NAME = "gemini-1.5-flash" 

DATASET_FILE = "CCPE.txt"
PROMPT_OLD_FILE = "prompt_old.txt"
PROMPT_NEW_FILE = "prompt_new.txt"

RESULTS_OLD = "results_old.jsonl"
RESULTS_NEW = "results_new.jsonl"
MAX_DIALOGUES = 5  


genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

def load_prompts():
    with open(PROMPT_OLD_FILE, "r", encoding="utf-8") as f:
        prompt_old = f.read()
    with open(PROMPT_NEW_FILE, "r", encoding="utf-8") as f:
        prompt_new = f.read()
    return prompt_old, prompt_new

def load_dataset():
    dialogues = []
    buffer = []

    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            buffer.append(line)
            if line.startswith("USER\tOVERALL\tOTHER"):
                dialogues.append("\n".join(buffer))
                buffer = []
    if buffer:
        dialogues.append("\n".join(buffer))

    return dialogues

def run_prompt(prompt_template, dialogue):
  
    final_prompt = prompt_template.replace("{dialogue_transcript}", dialogue)
    response = model.generate_content(final_prompt)
    return response.text

def save_jsonl(filename, results):
    with open(filename, "w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    prompt_old, prompt_new = load_prompts()
    dialogues = load_dataset()

    if MAX_DIALOGUES:
        dialogues = dialogues[:MAX_DIALOGUES]

    results_old, results_new = [], []

    for idx, dialogue in enumerate(dialogues, 1):
        print(f"=== Running dialogue {idx}/{len(dialogues)} ===")

        try:
            out_old = run_prompt(prompt_old, dialogue)
            results_old.append({"id": idx, "dialogue": dialogue, "result": out_old})
        except Exception as e:
            results_old.append({"id": idx, "dialogue": dialogue, "error": str(e)})

        try:
            out_new = run_prompt(prompt_new, dialogue)

            try:
                parsed = json.loads(out_new)
                results_new.append({"id": idx, "dialogue": dialogue, "result": parsed})
            except:
                results_new.append({"id": idx, "dialogue": dialogue, "raw_text": out_new})
        except Exception as e:
            results_new.append({"id": idx, "dialogue": dialogue, "error": str(e)})

    save_jsonl(RESULTS_OLD, results_old)
    save_jsonl(RESULTS_NEW, results_new)

    print(f"\n File saved to {RESULTS_OLD} and {RESULTS_NEW}")
