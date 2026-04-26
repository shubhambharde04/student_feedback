import json
import re

log_file = r"C:\Users\shubh\.gemini\antigravity\brain\118529ab-be40-42e0-a247-208226ea9e87\.system_generated\logs\overview.txt"
with open(log_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for line in lines:
    try:
        data = json.loads(line)
        if data.get('type') == 'TOOL_RESPONSE':
            for res in data.get('tool_responses', []):
                if res.get('name') == 'view_file':
                    output = res.get('response', {}).get('output', '')
                    if 'File Path: `file:///d:/student_feedback/backend/users/views.py`' in output:
                        if 'Showing lines' in output:
                            print(f"Found chunk: {output.split('Showing lines')[1][:20]}")
    except Exception as e:
        pass
