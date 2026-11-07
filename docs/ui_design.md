# UI design and behavior

Dayglass uses a compact, frameless floating window with a translucent
rounded glass surface, subtle border, and draggable title bar. The surface
uses a low-contrast diagonal tint and a faint top highlight; task rows,
weekly objectives, note/subtask panels, editors, buttons, progress tracks,
and scrollbars repeat the same translucent fill and fine edge treatment.
Hover and keyboard focus brighten edges to keep interactive controls clear.
A small
bottom-centered pill switches between the Plan and Focus screens. Its
active glass fill slides to the selected tab and animates with a soft
accent gradient and highlight sheen. The surface alpha lets the desktop
show through where the compositor supports translucent windows.

The Plan screen has date navigation, daily completion progress, expandable
task notes and subtasks, a scratchpad, and weekly objectives. Repeated task
and objective rows use separate soft glass cards so their actions remain
visually distinct without introducing opaque panels. The Focus
screen gives the 25-minute countdown its own uncluttered view. Weekly
objectives are shown alongside the selected date's plan. Each objective has
a deliberate completion checkbox, edit/delete controls, and a supporting
action count. A task's `◎` control associates it with one or more current
week objectives.

Wallpaper-derived accents are lightened when too dark and fall back to a
fixed accent if unavailable. The current stylesheet is dark; a separate
light theme is not implemented. Text and controls use a consistent dark
smoke-glass surface, muted labels, and accent highlights. Translucency
depends on the desktop compositor; Qt styles provide gradients and edge
highlights but do not blur arbitrary desktop content behind widgets. Task completion and objective
completion are separate states. Objectives with no linked tasks display
“No supporting actions,” never a misleading percentage.

Opening notes closes that task's subtask panel, and vice versa. The window
grows to fit content up to the available screen height. The 25-minute focus
timer supports start, pause, resume, and reset; it continues while minimized
and resets after application restart. It has no sound or notification.
