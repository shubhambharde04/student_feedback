from django.contrib.auth import get_user_model

User = get_user_model()

users_data = [
    ("LLBhadekar", "LLB@hadekar#01"),
    ("RLMeshram", "RL@eshram#02"),
    ("ARMahajan", "AR@ahajan#03"),
    ("AGBarsagade", "AG@arsagade#04"),
    ("SMohammde", "SM@ohammde#05"),
    ("DPChanamanwar", "DP@hanamanwar#06"),
    ("SSelokar", "SS@elokar#07"),
    ("LFuljhele", "LF@uljhele#08"),
    ("Shemebekar", "SH@emebekar#09"),
    ("NPotdukhe", "NP@otdukhe#10"),
    ("PKhobragade", "P@Khobragade#11"),
    ("SSGharde", "SS@Gharde#12"),
]

for username, password in users_data:
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_user(username=username, password=password, role='teacher', first_name=username)
        print(f"Created teacher {username}")
    else:
        user = User.objects.get(username=username)
        user.set_password(password)
        user.role = 'teacher'
        user.save()
        print(f"Updated existing user {username}")
