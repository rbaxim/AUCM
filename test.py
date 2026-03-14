"""AUCM Obfuscator test script"""
import os
import struct
import sys
try:
    __AUCM__
except BaseException:
    print("Script is not obfuscated")
    exit(1)
step = ""
errors = []
try:
    print("Obfuscation tests")
    print("1. Dunder method tests")
    step = "1a"
    print("1a. __name__ test")
    if __name__ == "__main__":
        print("__name__ is properly set to __main__")
    else:
        print("__name__ is not properly set to __main__. It is set to %s" % __name__)
        errors.append(step)
    step = "1b"
    print("1b. __doc__ test")
    if __doc__ == "AUCM Obfuscator test script":
        print("__doc__ is properly set to \"AUCM Obfuscator test script\"")
    else:
        print("__doc__ is not properly set to \"AUCM Obfuscator test script\". It is set to %s" % __doc__)
    step = "1c"
    print("1c. __file__ test")
    if __file__.endswith("test.pyc") or __file__.endswith("test.py") or __file__.endswith("test"):
        print(f"__file__ is properly set to \"{__file__}\" absolute path")
    else:
        print("__file__ is not properly set to \"test.pyc\" nor \"test.py\" nor \"test\" absolute path. It is set to %s" % __file__)
        errors.append(step)
        
    print("2. AUCM Metadata tests")
    step = "2a"
    print("2a. Is EXE")
    if __AUCM__["IsEXE"] and __file__.endswith("test.py") and __file__.endswith("test"):
        print("File is either misnamed or not an executable")
        errors.append(step)
    elif __AUCM__["IsEXE"]:
        print("File is a valid executable")
    else:
        print("File is not a executable")
    step = "2b"
    print("2b. Is PYC")
    if __AUCM__["IsPYC"] and (__file__.endswith("test.pyc") or __file__.endswith("test.py")):
        print("File is a valid pyc/py file")
        with open(__file__, "rb") as f:
            magic = struct.unpack("<I", f.read(4))[0]
            flags = struct.unpack("<I", f.read(4))[0]
            print("PYC flags:", flags)
            pyc_hash = str(struct.unpack("<Q", f.read(8))[0])
            print("PYC hash:", pyc_hash[8:] + "...")
    elif __AUCM__["IsPYC"] and not (__file__.endswith("test.pyc") or __file__.endswith("test.py")):
        print("Somehow file is not a pyc/py file yet metadata says something different")
        errors.append(step)
    else:
        print("File is not a pyc/py file")
    step = "2c"
    print("2c. Error suppression")
    if __AUCM__["ErrorSuppressed"]:
        print("Error suppression is enabled")
    else:
        print("Error suppression is disabled")
    step = "2d"
    print("2d. Is password-protected")
    if __AUCM__["IsEncrypted"]:
        print("File is password-protected")
    else:
        print("File is not password-protected")
    step = "2e"
    print("2e. Profile level")
    print(f"Profile level is {__AUCM__['Profile']}")

    print("3. Runtime tests")
    step = "3a"
    print("3a. sys.argv[0] test")
    argv0 = os.path.basename(sys.argv[0]) if sys.argv else ""
    file_base = os.path.basename(__file__)
    if argv0 in (file_base, os.path.splitext(file_base)[0], ""):
        print(f"sys.argv[0] looks valid: {sys.argv[0]}")
    else:
        print(f"sys.argv[0] does not match __file__: {sys.argv[0]} vs {__file__}")
        errors.append(step)

    step = "3b"
    print("3b. __package__ test")
    if __name__ == "__main__" and __package__ not in (None, ""):
        print(f"__package__ is not None/empty for __main__: {__package__}")
        errors.append(step)
    else:
        print(f"__package__ is acceptable: {__package__}")

    step = "3c"
    print("3c. __spec__ test")
    if __name__ == "__main__" and __spec__ is not None:
        print(f"__spec__ is not None for __main__: {__spec__}")
        errors.append(step)
    else:
        print(f"__spec__ is acceptable: {__spec__}")

    step = "3d"
    print("3d. __cached__ test")
    if "__cached__" in globals() and __cached__:
        if __cached__.endswith(".pyc"):
            print(f"__cached__ is a pyc path: {__cached__}")
        else:
            print(f"__cached__ is set but not a pyc path: {__cached__}")
            errors.append(step)
    else:
        print("__cached__ is not set")

    step = "3e"
    print("3e. __AUCM__ required keys")
    required_keys = {"IsEXE", "IsPYC", "ErrorSuppressed", "IsEncrypted", "Profile"}
    missing = sorted(required_keys.difference(__AUCM__.keys()))
    if missing:
        print("Missing __AUCM__ keys:", ", ".join(missing))
        errors.append(step)
    else:
        print("All required __AUCM__ keys are present")
    step = "3f"
    try:
        import json
        assert json.__name__ == "json"
        print("JSON import test passed")
    except Exception as e:
        print(f"JSON import test failed: {e}")  
        errors.append(step)
except BaseException as e:
    print(f"ERROR IN TEST {step}: {e}")
if errors:
    print("ERRORS IN TESTS:")
    for i in errors:
        print(i)
    exit(1)
else:
    print("No errors found")
