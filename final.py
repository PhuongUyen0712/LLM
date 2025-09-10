import google.generativeai as genai
import json
import re
import time

# --- Cấu hình ---
# Vui lòng thay thế bằng API key của bạn
API_KEY = "AIzaSyAAWA__p1Dw6zSBMnCLi57wZZcSY_ExUq0"
MODEL_NAME = "gemini-1.5-flash"

# Tên tệp đã được cập nhật để khớp với tệp bạn đã tải lên
DATASET_FILE = "Conversation.txt"
#PROMPT_OLD_FILE = "prompt_old.txt"
PROMPT_NEW_FILE = "new_prompt_with_example.txt"

RESULTS_OLD = "results_old.jsonl"
RESULTS_NEW = "results_new.jsonl"
# Giới hạn số lượng hội thoại để xử lý (đặt là None để chạy toàn bộ dataset)
MAX_DIALOGUES = 5


# --- Khởi tạo Model ---
try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    print(f"Lỗi khi cấu hình Generative AI: {e}")
    print("Vui lòng đảm bảo bạn đã đặt API_KEY hợp lệ.")
    exit()

def load_prompts():
    """Tải nội dung từ các tệp prompt."""
    try:
        # with open(PROMPT_OLD_FILE, "r", encoding="utf-8") as f:
        #     prompt_old = f.read()
        with open(PROMPT_NEW_FILE, "r", encoding="utf-8") as f:
            prompt_new = f.read()
        return prompt_new
    except FileNotFoundError as e:
        print(f"Lỗi: Không tìm thấy tệp prompt - {e.filename}")
        exit()

def load_dataset():
    """Tải và phân tách các hội thoại từ tệp dataset."""
    dialogues = []
    buffer = []

    try:
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line and buffer: # Thay đổi: Nhận diện hội thoại bằng dòng trống
                    dialogues.append("\n".join(buffer))
                    buffer = []
                elif line:
                    buffer.append(line)

        if buffer: # Đảm bảo hội thoại cuối cùng được thêm vào
            dialogues.append("\n".join(buffer))

        return dialogues
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy tệp dataset - {DATASET_FILE}")
        exit()

def run_prompt_with_retry(prompt_template, dialogue, max_retries=3):
    """
    Chạy prompt với logic thử lại để xử lý các lỗi tạm thời từ API.
    """
    final_prompt = prompt_template.replace("{dialogue_transcript}", dialogue)
    attempt = 0
    while attempt < max_retries:
        try:
            response = model.generate_content(final_prompt)
            # Thêm một khoảng nghỉ nhỏ để tránh vượt rate limit
            time.sleep(1)
            return response.text
        except Exception as e:
            attempt += 1
            print(f"Lỗi khi gọi API (lần {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt) # Exponential backoff
    raise Exception("Không thể nhận phản hồi từ API sau nhiều lần thử.")


def extract_json_from_string(text):
    """
    Trích xuất chuỗi JSON từ văn bản thô, thường được trả về trong markdown.
    """
    # Sử dụng regex để tìm nội dung giữa ```json và ```
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    # Nếu không có markdown, tìm JSON object đầu tiên
    match = re.search(r"(\{.*?\})", text, re.DOTALL)
    if match:
        return match.group(1)
    return None

def save_jsonl(filename, results):
    """Lưu kết quả ra tệp .jsonl."""
    with open(filename, "w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    prompt_new = load_prompts()
    dialogues = load_dataset()

    print(f"Đã tải {len(dialogues)} hội thoại từ {DATASET_FILE}.")

    if MAX_DIALOGUES and MAX_DIALOGUES > 0:
        dialogues = dialogues[:MAX_DIALOGUES]
        print(f"Đang xử lý {len(dialogues)} hội thoại đầu tiên.")

    results_old, results_new = [], []

    for idx, dialogue in enumerate(dialogues, 1):
        print(f"=== Đang xử lý hội thoại {idx}/{len(dialogues)} ===")

        # # Chạy với prompt cũ
        # try:
        #     out_old = run_prompt_with_retry(prompt_old, dialogue)
        #     results_old.append({"id": idx, "dialogue": dialogue, "result": out_old})
        # except Exception as e:
        #     print(f"Lỗi với prompt cũ: {e}")
        #     results_old.append({"id": idx, "dialogue": dialogue, "error": str(e)})

        # Chạy với prompt mới và xử lý JSON
        try:
            out_new_raw = run_prompt_with_retry(prompt_new, dialogue)
            json_string = extract_json_from_string(out_new_raw)

            if json_string:
                try:
                    parsed_json = json.loads(json_string)
                    results_new.append({"id": idx, "dialogue": dialogue, "result": parsed_json})
                except json.JSONDecodeError as json_err:
                    print(f"  Lỗi phân tích JSON: {json_err}")
                    results_new.append({
                        "id": idx,
                        "dialogue": dialogue,
                        "error": "JSONDecodeError",
                        "raw_text": out_new_raw
                    })
            else:
                print("  Không tìm thấy chuỗi JSON hợp lệ trong phản hồi.")
                results_new.append({
                    "id": idx,
                    "dialogue": dialogue,
                    "error": "NoJSONFound",
                    "raw_text": out_new_raw
                })
        except Exception as e:
            print(f"Lỗi với prompt mới: {e}")
            results_new.append({"id": idx, "dialogue": dialogue, "error": str(e)})

    save_jsonl(RESULTS_NEW, results_new)

    print(f"\nĐã lưu tệp vào{RESULTS_NEW}")
