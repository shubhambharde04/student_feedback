import os
import json
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from django.apps import apps

def import_data(file_path):
    print(f"Opening {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} objects. Grouping by model...")
    
    model_data = {}
    for item in data:
        model_name = item['model']
        if model_name not in model_data:
            model_data[model_name] = []
        model_data[model_name].append(item)

    model_order = [
        'users.department', 'users.branch', 'users.semester', 'users.subject',
        'auth.group', 'users.user', 'users.subjectoffering', 'users.feedbacksession',
        'users.question', 'users.feedbackform', 'users.formquestionmapping',
        'users.sessionoffering', 'users.studentsemester', 'users.feedbacksubmission',
        'users.feedbackresponse', 'users.answer'
    ]
    
    all_models = list(model_data.keys())
    for m in all_models:
        if m not in model_order:
            model_order.append(m)

    for model_label in model_order:
        if model_label not in model_data:
            continue
            
        items = model_data[model_label]
        print(f"Importing {len(items)} objects for {model_label}...")
        model = apps.get_model(model_label)
        
        # Get FK field names to append _id
        fk_fields = {f.name: f.attname for f in model._meta.fields if f.is_relation and not f.many_to_many}
        # Get M2M field names to exclude
        m2m_fields = {f.name for f in model._meta.many_to_many}
        
        objs = []
        for item in items:
            fields = item['fields']
            processed_fields = {}
            for k, v in fields.items():
                if k in m2m_fields:
                    continue # Skip M2M fields for bulk_create
                if k in fk_fields:
                    processed_fields[fk_fields[k]] = v
                else:
                    processed_fields[k] = v
            
            objs.append(model(pk=item['pk'], **processed_fields))
        
        try:
            model.objects.bulk_create(objs, ignore_conflicts=True, batch_size=50)
            print(f"  Done {model_label}")
        except Exception as e:
            print(f"  Error on {model_label}: {e}")

if __name__ == "__main__":
    import_data('my_data.json')
