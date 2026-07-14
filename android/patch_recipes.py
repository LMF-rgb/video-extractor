"""Patch python-for-android recipes for Python 3.10 + Kivy 2.3.1"""
import os, re, sys

p4a_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".buildozer/android/platform/python-for-android"
)

recipes_dir = os.path.join(p4a_dir, "pythonforandroid", "recipes")

# Patch Python version to 3.10.13
for recipe in ["hostpython3", "python3"]:
    path = os.path.join(recipes_dir, recipe, "__init__.py")
    if not os.path.exists(path):
        continue
    with open(path) as f:
        content = f.read()
    # string version
    content = re.sub(r'version\s*=\s*["\']3\.\d+\.\d+["\']', 'version = "3.10.13"', content)
    # tuple version
    content = re.sub(r'\(3,\s*\d+,\s*\d+\)', '(3, 10, 13)', content)
    with open(path, "w") as f:
        f.write(content)
    print(f"Patched {recipe}")
    # verify
    with open(path) as f:
        for line in f:
            if 'version =' in line and 'p_version' not in line:
                print(f"  >> {line.strip()}")
                break

# Patch Kivy version
kivy_path = os.path.join(recipes_dir, "kivy", "__init__.py")
if os.path.exists(kivy_path):
    with open(kivy_path) as f:
        content = f.read()
    content = re.sub(r'version\s*=\s*["\'][^"\']+["\']', 'version = "2.3.1"', content)
    with open(kivy_path, "w") as f:
        f.write(content)
    print("Patched kivy")

print("Done")
