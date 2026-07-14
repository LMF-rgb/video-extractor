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

# Add configure flags to python3 recipe to skip Unix-only modules
python3_path = os.path.join(recipes_dir, "python3", "__init__.py")
if os.path.exists(python3_path):
    with open(python3_path) as f:
        content = f.read()
    # Ensure get_recipe_env includes ac_cv overrides for grp/crypt
    if "ac_cv_func_setgrent" not in content:
        # Find get_recipe_env and add the overrides
        old = "def get_recipe_env(self, arch):"
        new = '''def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env["ac_cv_func_setgrent"] = "no"
        env["ac_cv_func_endgrent"] = "no"
        env["ac_cv_func_getgrent"] = "no"
        env["ac_cv_func_crypt"] = "no"
        env["ac_cv_func_crypt_r"] = "no"
        return env'''
        if old in content:
            content = content.replace(old, new)
            with open(python3_path, "w") as f:
                f.write(content)
            print("Patched python3 with ac_cv overrides")

print("Done")
