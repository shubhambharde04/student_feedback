import io
import sys
import traceback

try:
    import test_enrollment_fix
    test_enrollment_fix.run_tests()
except Exception as e:
    with open('test_output.txt', 'w', encoding='utf-8') as f:
        traceback.print_exc(file=f)
    print("Test failed. See test_output.txt")
