import json
import os

log_file = r"C:\Users\shubh\.gemini\antigravity\brain\118529ab-be40-42e0-a247-208226ea9e87\.system_generated\logs\overview.txt"
with open(log_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for line in lines:
    try:
        data = json.loads(line)
        if data.get('type') == 'PLANNER_RESPONSE':
            for call in data.get('tool_calls', []):
                name = call.get('name')
                args = call.get('args', {})
                target_file = args.get('TargetFile', '')
                if 'views.py' in target_file or 'session_views.py' in target_file:
                    print(f"Found {name} for {target_file}")
                    # Dump the content or chunks
                    if name == 'write_to_file':
                        out_path = os.path.basename(target_file.strip('"').strip("'")) + '.recovered'
                        with open('scratch/' + out_path, 'w', encoding='utf-8') as out:
                            content = args.get('CodeContent', '').strip('"').encode('utf-8').decode('unicode_escape')
                            out.write(content)
                            print(f"Recovered {out_path} length {len(content)}")
    except Exception as e:
        pass
