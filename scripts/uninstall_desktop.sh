#!/usr/bin/env bash
set -euo pipefail

data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
app_dir="$data_home/dayglass/app"
bin_dir="$HOME/.local/bin"
applications_dir="$data_home/applications"
autostart_file="$config_home/autostart/dayglass.desktop"
icon_file="$data_home/icons/hicolor/scalable/apps/dayglass.svg"

if [[ -d "$app_dir" ]]; then
    rm -r -- "$app_dir"
fi
rm -f -- "$applications_dir/dayglass.desktop" "$autostart_file" "$icon_file" "$bin_dir/dayglass"
echo "Removed Dayglass application files. User data at $data_home/dayglass was retained."
