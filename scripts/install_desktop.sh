#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
app_dir="$data_home/dayglass/app"
bin_dir="$HOME/.local/bin"
applications_dir="$data_home/applications"
icon_dir="$data_home/icons/hicolor/scalable/apps"
desktop_file="$applications_dir/dayglass.desktop"
autostart_file="$config_home/autostart/dayglass.desktop"
icon_file="$icon_dir/dayglass.svg"

if [[ -e "$app_dir" ]]; then
    echo "Dayglass is already installed at $app_dir; uninstall it first (data is preserved)." >&2
    exit 1
fi
if [[ -e "$desktop_file" || -e "$autostart_file" || -e "$icon_file" || -e "$bin_dir/dayglass" ]]; then
    echo "A Dayglass launcher, icon, or command already exists; refusing to overwrite it." >&2
    exit 1
fi
mkdir -p "$app_dir" "$bin_dir" "$applications_dir" "$icon_dir" "$(dirname "$autostart_file")"
app_created=1
cleanup_failed_install() {
    status=$?
    if [[ $status -ne 0 && ${app_created:-0} -eq 1 ]]; then
        rm -r -- "$app_dir"
        rm -f -- "$desktop_file" "$autostart_file" "$icon_file" "$bin_dir/dayglass"
    fi
    trap - EXIT
    exit "$status"
}
trap cleanup_failed_install EXIT
tar -C "$repo_dir" \
    --exclude=.git --exclude=.venv --exclude=venv --exclude=.idea \
    --exclude=.pytest_cache --exclude=__pycache__ --exclude='*.pyc' \
    --exclude='*.sqlite3' --exclude='*.sqlite' --exclude='*.db' \
    --exclude=tests -cf - . | tar -C "$app_dir" -xf -
python3 -m venv "$app_dir/venv"
"$app_dir/venv/bin/python" -m pip install "$app_dir"
install -m 0644 "$app_dir/assets/dayglass.svg" "$icon_file"
cat > "$desktop_file" <<EOF
[Desktop Entry]
Type=Application
Name=Dayglass
Comment=Daily planning and weekly objectives
Exec=$app_dir/venv/bin/dayglass
Icon=dayglass
Terminal=false
Categories=Office;
StartupNotify=true
EOF
cat > "$autostart_file" <<EOF
[Desktop Entry]
Type=Application
Name=Dayglass
Comment=Start the Dayglass planner when you sign in
Exec=$app_dir/venv/bin/dayglass
TryExec=$app_dir/venv/bin/dayglass
Icon=dayglass
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
cat > "$bin_dir/dayglass" <<EOF
#!/usr/bin/env bash
exec "$app_dir/venv/bin/dayglass" "\$@"
EOF
chmod 0755 "$bin_dir/dayglass"
chmod 0644 "$desktop_file" "$autostart_file"
app_created=0
trap - EXIT
echo "Installed. Dayglass will start when you sign in. Launch from the app menu or run: $bin_dir/dayglass"
