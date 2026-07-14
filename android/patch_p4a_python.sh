#!/bin/bash
set -e
P4A_DIR="$(cd "$(dirname "$0")" && pwd)/.buildozer/android/platform/python-for-android"

if [ ! -d "$P4A_DIR" ]; then
    echo "p4a 还没 clone，先跑一次 buildozer android debug 让它 clone 然后 Ctrl+C 中断"
    exit 1
fi

echo "锁定 Python 版本为 3.12..."

for recipe in hostpython3 python3; do
    RECIPE="$P4A_DIR/pythonforandroid/recipes/$recipe/__init__.py"
    [ ! -f "$RECIPE" ] && continue
    cp "$RECIPE" "${RECIPE}.bak"
    sed -i -E 's/(version\s*=\s*['"'"'"])3\.[0-9]+\.[0-9]+(['"'"'"])/\13.12.10\2/' "$RECIPE"
    sed -i -E 's/\(3,\s*[0-9]+,\s*[0-9]+\)/(3, 12, 10)/' "$RECIPE"
    echo "  $recipe"
    grep 'version\s*=' "$RECIPE" | head -1
done

KIVY_RECIPE="$P4A_DIR/pythonforandroid/recipes/kivy/__init__.py"
if [ -f "$KIVY_RECIPE" ]; then
    sed -i -E 's/(version\s*=\s*['"'"'"])[^'"'"'"]+(['"'"'"])/\12.3.1\2/' "$KIVY_RECIPE"
    echo "  kivy"
fi

echo ""
echo "搞定。跑: buildozer android debug"
