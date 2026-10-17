# WinUx

**Linux-style customization for Windows 10 and 11, with a Deltarune / Undertale soul.**

WinUx is a little control panel that changes how your whole PC looks: colors, wallpaper,
live animated backgrounds, the taskbar, desktop widgets, cursors, icons and sounds. Pick a
theme and everything switches at once. Your original look is backed up first, and one click
puts it back.

WinUx is a *hub*: it drives great free tools (Lively Wallpaper, TranslucentTB, Rainmeter,
Windhawk) so you don't have to learn each one.

## Themes

Every theme comes with its own animated pixel-art wallpaper.

| Theme | |
|---|---|
| Dark World | Black, white and that yellow glow |
| Soul Red | **▶ Playable**: dodge Flowey's bullets with the arrow keys / WASD |
| Pirate Gaster | Dark, darker, yet darker. (In Wingdings, of course.) |
| Cyber City | **▶ Playable**: press a key to fight Spamton NEO with Kris, Susie and Ralsei |
| Field of Hopes | Ralsei in a green field, with a little yellow flower |
| Neon Skyline | Night city glass, blue with a pink glow |
| Light World | Daytime in Hometown, light mode |
| Card Castle | Card-suit towers and Lancer bopping by |
| Queen's Mansion | Queen on the big screen, acid pipes |
| TV World | Tenna's studio: spotlights, curtains, channel changes |
| Snowdin | **♪ Music**: snowy town at night, with the Snowdin Town song |
| Waterfall | Glowing echo flowers and falling water |
| Judgment Hall | **▶ Playable + ♪ Music**: press a key to fight Sans for fun (his song plays during the fight) |
| Forgotten Man | **♪ Music**: his red tree, and his theme |
| Hotland | Magma, steam vents and the CORE glowing in the distance |
| The Ruins | Purple halls, falling red leaves, the big tree and Toriel's house |
| Mettaton Stage | Pink spotlights, floating hearts and Mettaton EX posing |
| Spamton's Basement | A dark alley full of [[DEALS]]; Spamton pops out of the dumpster |

## Extras

- **Share themes**: SHARE on any of your themes saves a `.winux` file (your wallpaper picture
  goes inside). Friends open it with IMPORT THEME.
- **Tray icon + Ctrl+Alt+T**: a soul by the clock switches themes; Ctrl+Alt+T = next theme.
- **Startup jingle**: a chiptune when your PC starts. Pick WinUx boot, Vanishing, Dark World,
  NGAAAAH!, or your own .wav / .mp3.
- **Soul color**: pick one of the seven souls; every heart in WinUx follows it.
- **Lock screen match**: your lock screen follows your wallpaper (live ones as a snapshot).
- **Cursor maker**: draw your own pixel cursors (arrow, hand, loading animation) and share
  them as `.winuxcursor` files.
- **Folder colors**: right-click a folder → WinUx folder color / emblem (heart, star,
  controller, music note). On Windows 11, pick **Show more options** first.
- **Achievements**: 29 to collect, some of them secret.
- **Pixel screensaver**: turns on after you've been away for a while (WALLPAPER tab).

## Widgets

Desktop widgets in Deltarune text boxes (powered by Rainmeter). Turn them on in **WIDGETS**.

| Widget | |
|---|---|
| Clock | Big pixel clock with the date |
| PC Status | CPU, RAM and disk as HP bars |
| Now Playing | What Spotify is playing |
| Dialog Box | Says something new every 10 minutes |
| Menu | Quick launcher |
| Weather | The weather, as told by a [[Big Shot]] |
| Battery HP | Your battery as your HP bar (desktops have ∞ HP) |
| Calendar | This month, with today on your soul |
| Save Point | Click the star to save |
| Tem Shop | hOI!! Opens your apps |
| Focus Timer | FIGHT your task for 25 minutes, then take a break |
| Party Stats | Deltarune style: Kris, Susie and Ralsei's HP is your free CPU, RAM and disk |
| Annoying Dog | Wanders along your screen, naps, and barks when you click it |
| Mettaton Ratings | Your internet speed as Mettaton's TV ratings |
| Bullet Board | Music visualizer: bones rise to the beat, your soul hops |

Right-click any widget → **Edit skin** to change things like the Weather city or the shop items.

## App icons

In **ICONS+SOUNDS → App icons**, pick **Pixel** to give your apps pixel-art logos: on the
desktop, in the Start menu and on the taskbar. Covered so far: Chrome, File Explorer,
folders, Claude, VLC, Discord, Spotify, Roblox, DELTARUNE, UNDERTALE, Steam, Lively, Zoom,
Python, GitHub Desktop, Unity and Godot (as Undyne). Pick **Original** to put every icon back.

- Windows asks for permission once, for shortcuts shared by everyone and the folder icon.
- On Windows 11 with Windhawk's **Taskbar Styler** mod, the Start button (classic
  four-color logo), search and Task View get pixel icons too.
- Apps only change when they're **pinned** or have a shortcut. Pin an app, then click
  **Pixel** again.
- Some apps can't change: Store-style apps (like Claude), and app badges such as
  Discord's notification counter, which apps draw themselves.

You can also save your own themes, add your own wallpapers / videos / GIFs, and turn a
drawing into a theme (ART → THEME pulls the colors out of a PNG).

## Install

1. Download WinUx: the green **Code** button → **Download ZIP**, then unzip it somewhere
   it can stay (like `Documents\WinUx`). Or `git clone` it.
2. Double-click **`install.bat`**.
   It finds Python (or offers to install it), then asks about each helper app one by one.
   Say yes to the ones you want. Nothing is installed without asking.
3. WinUx opens in your browser at `http://127.0.0.1:7777`. That's it!

Next time, double-click **`Start WinUx.bat`** (or let it start with Windows).

### What gets installed

| App | What WinUx uses it for | Needed? |
|---|---|---|
| [Python 3.10+](https://www.python.org/) | Runs WinUx itself | Yes |
| [Lively Wallpaper](https://www.rocksdanister.com/lively/) | Live / animated wallpapers | For live walls |
| [TranslucentTB](https://github.com/TranslucentTB/TranslucentTB) | Clear or colored taskbar | Optional |
| [Rainmeter](https://www.rainmeter.net/) | Desktop widgets | Optional |
| [Windhawk](https://windhawk.net/) | Mod shop (taskbar / Start menu styles) | Optional |

The installer uses `winget` (built into Windows 11 and recent Windows 10). If you don't
have it, it shows you the download links instead.

## If something goes wrong

- **"Windows protected your PC"** when you open `install.bat`: click **More info**, then **Run anyway**.
  (Windows says this about any new file from the internet.)
- **Don't double-click `install.ps1`.** Windows just opens it in Notepad. Use `install.bat`.
- **The installer stopped with an error:** it saves everything it did in `install-log.txt`
  in the WinUx folder. Send that file on the GitHub page (Issues) and we'll fix it.
- **WinUx doesn't open:** run `Start WinUx.bat`. If WinUx can't start, it now shows why, and
  saves the details in `winux-error.log`. Send that file too.
- **Widgets are in odd places on a small screen:** just drag them where you like.
  Right-click a widget → **Settings** to lock it in place.

## Windows 10 vs 11

WinUx works on both. On Windows 10:

- The taskbar **icon position** switch (center / left) is hidden, since Windows 10 doesn't have it.
- The **ICON + LABEL** search style is hidden for the same reason.
- The mod shop only shows mods that work on Windows 10.
- Live walls need Microsoft's free **WebView2 Runtime**. The installer offers it if it's missing.

## Music themes

Snowdin and Forgotten Man play their songs. WinUx doesn't include any music files: it streams
the official uploads from YouTube, so WinUx needs to be running and you need internet.
Lively mutes it while windows cover your desktop. Right-click the wallpaper in Lively to turn
the music off or change the volume.

Own the soundtrack? Put the song in the theme's folder (for example
`live-walls/snowdin/music.mp3`) and it plays from your file instead.

## Uninstall

1. In WinUx, open **BACKUP** → **RESTORE** to put your original look back.
2. Double-click **`uninstall.bat`**.
3. Delete the WinUx folder.

## Is it safe?

- WinUx only runs on your own PC (`127.0.0.1`). Nothing is sent anywhere.
- It only changes your own user settings (colors, wallpaper, cursors...), never system files.
- Your original look is saved in `backups/` the first time it runs.

## Credits

- **DELTARUNE** and **UNDERTALE** are by Toby Fox. WinUx is a fan project and isn't
  connected to Toby Fox or his team. All the pixel art in WinUx is fan art drawn for it.
- Fonts: [VT323](https://fonts.google.com/specimen/VT323) and
  [Press Start 2P](https://fonts.google.com/specimen/Press+Start+2P), under the SIL Open Font License.
- The Sans art in Judgment Hall (battle, ketchup, silhouette and blue-eye) was drawn for WinUx by its creator.
- Built with [Claude Code](https://claude.com/claude-code).

## License

The WinUx code is under the [MIT License](LICENSE). The fonts keep their own license
(`widgets/WinUx/@Resources/Fonts/OFL.txt`).
