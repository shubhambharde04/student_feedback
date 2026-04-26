import json
import os

log_file = r"C:\Users\shubh\.gemini\antigravity\brain\118529ab-be40-42e0-a247-208226ea9e87\.system_generated\logs\overview.txt"
file_to_recover = r"d:\student_feedback\backend\users\views.py"

with open(log_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open(file_to_recover, 'r', encoding='utf-8') as f:
    content = f.read().replace('\r\n', '\n') # Normalize file content

for line in lines:
    try:
        data = json.loads(line)
        if data.get('type') == 'PLANNER_RESPONSE':
            for call in data.get('tool_calls', []):
                name = call.get('name')
                args = call.get('args', {})
                target_file = args.get('TargetFile', '').strip('"').strip("'")
                
                # Normalize paths
                if target_file and target_file.lower().replace('\\', '/') == file_to_recover.lower().replace('\\', '/'):
                    if name == 'replace_file_content':
                        target_content = args.get('TargetContent', '').replace('\r\n', '\n')
                        replacement_content = args.get('ReplacementContent', '').replace('\r\n', '\n')
                        if target_content in content:
                            content = content.replace(target_content, replacement_content)
                            print("Replaced chunk.")
                        else:
                            print("TargetContent NOT FOUND in replace_file_content!")
                            
                    elif name == 'multi_replace_file_content':
                        for chunk in args.get('ReplacementChunks', []):
                            target_content = chunk.get('TargetContent', '').replace('\r\n', '\n')
                            replacement_content = chunk.get('ReplacementContent', '').replace('\r\n', '\n')
                            if target_content in content:
                                content = content.replace(target_content, replacement_content)
                                print("Replaced chunk in multi.")
                            else:
                                print("TargetContent NOT FOUND in multi_replace_file_content!")
    except Exception as e:
        pass

with open(file_to_recover + '.recovered', 'w', encoding='utf-8') as f:
    f.write(content)
print("Saved recovered file.")
