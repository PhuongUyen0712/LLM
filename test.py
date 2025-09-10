import json

with open('results_old.jsonl', 'r', encoding='utf-8') as f:
    # Lặp qua từng dòng của file
    for line in f:
        # Chuyển đổi mỗi dòng JSON thành đối tượng Python
        data = json.loads(line)
        # In ra dữ liệu
        print(data)