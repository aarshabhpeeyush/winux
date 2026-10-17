# Changelog

## 1.0.2 (2026-10-17)

Everything from the 1.0.2 beta (new widgets and the Judgment Hall Sans fight), plus:


- 4 new themes, each with its own animated pixel wallpaper:
  - **Hotland**: red rock, a magma river, steam vents, and the CORE pulsing in the distance.
  - **The Ruins**: purple brick, the big bare tree, falling red leaves and Toriel's house.
  - **Mettaton Stage**: pink spotlights, curtains, floating hearts and Mettaton EX posing.
  - **Spamton's Basement**: a dark alley full of [[DEALS]]; Spamton pops out of the dumpster.
- **Share themes as files**: SHARE on any of your themes saves a `.winux` file (with your
  wallpaper picture inside). Friends open it with IMPORT THEME.
- **Startup jingle**: a short chiptune plays when WinUx starts with your PC. Pick one in
  ICONS+SOUNDS: WinUx boot, Vanishing, Dark World or NGAAAAH! (originals inspired by the
  games), or YOUR OWN .wav or .mp3. Switch it off in BACKUP.
- **Tray icon + hotkey**: a red soul by the clock. Click it to open WinUx or switch to any
  theme; **Ctrl+Alt+T** flips to the next theme from anywhere.
- **Soul color picker** (COLORS): pick one of the seven human souls. Every heart in WinUx
  follows it: the Soul cursor, the widgets and the panel.
- **Lock screen matches your wallpaper** (WALLPAPER tab): live wallpapers become a snapshot.
  Your old lock screen is saved first, and RESTORE puts it back.

## 1.0.2 beta (2026-10-15)

A first look at 1.0.2. Still coming in the full 1.0.2: four new themes (Hotland + CORE,
the Ruins, Mettaton's stage, Spamton's basement), sharing themes as files, a startup
jingle, a tray menu + hotkey, lock screen matching, and a soul color picker.


- 4 new widgets:
  - **Party Stats**: a Deltarune-style twin of PC Status. Kris, Susie and Ralsei's HP is your
    free CPU, RAM and disk (a busy PC takes damage; under 10 HP they're DOWN).
  - **Annoying Dog**: wanders along the bottom of your screen, naps, barks when clicked.
  - **Mettaton Ratings**: your internet speed as Mettaton's TV ratings chart.
  - **Bullet Board**: a music visualizer in a battle box. Bones rise to the beat, your soul hops.
- **Judgment Hall is now playable, with music**: press any key to fight Sans for fun.
  His real moves (blue-soul gravity, bone walls, Gaster Blasters, blue bones, bone stabs,
  KARMA) plus new ones (ketchup rain, hot dog barrage, bones that spell HEH). He dodges every
  FIGHT... until turn 25, when you hit him with ketchup. "Song That Might Play When You Fight
  Sans" plays only during the fight. Sans is the WinUx creator's own art, including a
  ketchup-covered version, a silhouette for the hall and his blue eye.
- Fixed: turning on a widget could fail with "Couldn't find the widget" while Rainmeter was
  saving its settings, and updated widgets didn't always reload.

## 1.0.1 (fixed edition) (2026-10-15)

- **Fixed:** picking ORIGINAL in App icons left some icons blank. It now puts every icon back
  correctly, and it also repairs shortcuts the first 1.0.1 broke. If your icons went blank,
  update and click **ORIGINAL** again.
- Apps pinned while pixel icons were on now go back to their own icon too.

## 1.0.1 (2026-10-15)

- 6 new widgets:
  - **Weather**: the weather as a Spamton sales pitch ("THE CURRENT WEATHER IS [[CLOUDY]]!!"). Uses wttr.in, no account.
  - **Battery HP**: your battery as an HP bar with your Windows name. Shakes when low, heals when plugged in. Desktops have ∞ HP.
  - **Calendar**: this month, with today sitting on a red soul.
  - **Save Point**: click the star to save. Shows your name, LV (days your PC has been on) and uptime.
  - **Tem Shop**: hOI!! A Temmie shop that opens your apps.
  - **Focus Timer**: a pomodoro timer as a battle. FIGHT, ACT, MERCY.
- Widgets that are already on now reload when WinUx updates them.
- **App icons** (ICONS+SOUNDS): pixel-art logos for Chrome, File Explorer, Claude, VLC, Discord,
  Spotify, Roblox, DELTARUNE, UNDERTALE and Steam shortcuts (desktop, Start menu, taskbar),
  plus a pixel folder icon. One Windows permission prompt; ORIGINAL puts every icon back.
- Lively Wallpaper gets a 7-souls icon. Also pixel icons for Zoom, Python/IDLE and game tools.
- With Windhawk's **Taskbar Styler** mod (Windows 11), the Start button becomes the classic
  four-color Windows logo, and search and Task View get pixel icons.
- Fixes from the first Windows 10 tester:
  - `.bat` and `.ps1` files now always have Windows line endings in downloads.
  - The installer unblocks its downloaded files, saves `install-log.txt`, and shows what went wrong.
  - WinUx no longer fails silently: errors go to `winux-error.log` with a message box,
    and `Start WinUx.bat` shows the error if the panel doesn't come up.
  - Widgets start in spots that fit the screen (no more off-screen widgets on 1366x768).

## 1.0.0 (2026-10-15): first public release

- Control panel at `http://127.0.0.1:7777` with COLORS, WALLPAPER, LIVE WALLS, TASKBAR,
  WIDGETS, ICONS+SOUNDS, ART → THEME, THEMES and BACKUP.
- 14 built-in themes, each with its own animated pixel-art wallpaper:
  Dark World, Soul Red, Pirate Gaster, Cyber City, Field of Hopes, Neon Skyline, Light World,
  Card Castle, Queen's Mansion, TV World, Snowdin, Waterfall, Judgment Hall, Forgotten Man.
- Playable wallpapers: Soul Red (dodge Flowey) and Cyber City (fight Spamton NEO).
- Music themes: Snowdin and Forgotten Man.
- PLAYABLE / MUSIC labels on theme thumbnails.
- Works with Lively Wallpaper, TranslucentTB, Rainmeter and Windhawk.
- Pixel cursors, desktop icons and chiptune sounds.
- Backup and one-click restore of your original look.
- Windows 10 and Windows 11 support.
- `install.bat` / `uninstall.bat`.
