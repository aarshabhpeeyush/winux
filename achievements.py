"""WinUx achievements: little goals for using WinUx, playing the live walls,
using your PC, plus a few secret ones.

Everything is counted from "events" (theme switched, dog petted, Sans fight
lost...). Progress lives in backups/achievements.json.
"""
import json
import threading
import time
from pathlib import Path

# id: (category, name, how to get it, icon, rule(stats) -> bool)
# categories: winux, walls, pc, secret (secret ones show "???" until you get them)


def count(name, n=1):
    return lambda s: s["counts"].get(name, 0) >= n


def many(key, n):
    return lambda s: len(s.get(key, [])) >= n


LIST = {
    # --- using WinUx
    "new-look": ("winux", "A NEW LOOK", "Switch to a theme.", "★", many("themes", 1)),
    "fashion": ("winux", "FASHION SHOW", "Try 10 different themes.", "♛", many("themes", 10)),
    "speedrun": ("winux", "SPEEDRUNNER", "Switch themes with Ctrl+Alt+T.", "»", count("hotkey")),
    "artist": ("winux", "PIXEL ARTIST", "Wear cursors you drew yourself.", "✎", count("cursors")),
    "decorator": ("winux", "INTERIOR DECORATOR", "Color 5 folders.", "▤", count("folder", 5)),
    "friends": ("winux", "FRIENDSHIP!", "Share a theme or your cursors as a file.", "♥", count("share")),
    "party": ("winux", "DESKTOP PARTY", "Have 5 widgets on at once.", "☺", lambda s: s.get("maxWidgets", 0) >= 5),
    "soul": ("winux", "SOUL SEARCHING", "Change your soul color.", "♡", count("soul")),
    "song": ("winux", "YOUR OWN SONG", "Use your own startup sound.", "♪", count("jingle-custom")),
    # --- playing the walls
    "bad-time": ("walls", "A BAD TIME", "Start the Sans fight in Judgment Hall.", "☠", count("sans-start")),
    "dunked": ("walls", "GET DUNKED ON", "Lose to Sans.", "✖", count("sans-lose")),
    "determined": ("walls", "DETERMINATION", "Lose to Sans 10 times. Keep going.", "♥", count("sans-lose", 10)),
    "ketchup": ("walls", "KETCHUP ENDING", "Make it to turn 25 and beat Sans.", "♨", count("sans-win")),
    "hands-on": ("walls", "HANDS ON", "Play a PLAYABLE wall (Soul or Cyber City).", "✚", count("wall-play")),
    "dj": ("walls", "DJ", "Turn on the music in a MUSIC wall.", "♫", count("music")),
    # --- using the PC
    "task": ("pc", "TASK DEFEATED", "Win a Focus Timer battle.", "⚔", count("timer-win")),
    "focus": ("pc", "FOCUS MASTER", "Win 10 Focus Timer battles.", "⚔", count("timer-win", 10)),
    "good-boy": ("pc", "GOOD BOY", "Pet the Annoying Dog.", "◕", count("dog-pet")),
    "annoying": ("pc", "ANNOYING", "Pet the Annoying Dog 50 times.", "◕", count("dog-pet", 50)),
    "hours-10": ("pc", "STAYING DETERMINED", "Use your PC for 10 hours with WinUx on.", "◷", lambda s: s.get("minutes", 0) >= 600),
    "hours-100": ("pc", "TRUE DEDICATION", "100 hours with WinUx on.", "◷", lambda s: s.get("minutes", 0) >= 6000),
    "night-owl": ("pc", "NIGHT OWL", "Use your PC between midnight and 4 AM.", "☾", count("night")),
    "every-day": ("pc", "EVERY DAY", "Use WinUx on 7 different days.", "▦", many("days", 7)),
    # --- secret
    "gaster": ("secret", "ENTRY NUMBER 17", "Switch to the Pirate Gaster theme.", "✋", count("gaster")),
    "logo": ("secret", "STOP CLICKING", "Click the WinUx logo 10 times.", "!", count("logo")),
    "rainbow": ("secret", "ALL SEVEN SOULS", "Try every soul color.", "❖", many("souls", 7)),
    "late-sans": ("secret", "IT'S LATE, KID", "Fight Sans after midnight.", "☾", count("sans-late")),
    "completionist": ("secret", "COMPLETIONIST", "Get every other achievement.", "♛",
                      lambda s: all(k in s["unlocked"] for k in LIST if k != "completionist")),
}

# events that walls / Rainmeter / the folder menu may send without the panel's password
PUBLIC_EVENTS = {"sans-start", "sans-lose", "sans-win", "wall-play", "music", "folder", "dog-pet", "timer-win"}
PANEL_EVENTS = PUBLIC_EVENTS | {"share", "logo"}


class Achievements:
    def __init__(self, path, notify=None, sound=None):
        self.path = Path(path)
        self.notify, self.sound = notify, sound
        self.lock = threading.Lock()
        self.last = {}          # event -> time, so spamming one event doesn't count 1000 times
        self.data = self._load()

    def _load(self):
        try:
            d = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            d = {}
        d.setdefault("counts", {})
        d.setdefault("unlocked", {})
        d.setdefault("unseen", [])
        for k in ("themes", "souls", "days"):
            d.setdefault(k, [])
        return d

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def _check(self):
        new = []
        for key, (_, name, desc, _, rule) in LIST.items():
            if key not in self.data["unlocked"]:
                try:
                    ok = rule(self.data)
                except Exception:
                    ok = False
                if ok:
                    self.data["unlocked"][key] = time.strftime("%Y-%m-%d %H:%M")
                    self.data["unseen"].append(key)
                    new.append(key)
        # completionist can only be checked after the others
        if new and "completionist" not in self.data["unlocked"] and LIST["completionist"][4](self.data):
            self.data["unlocked"]["completionist"] = time.strftime("%Y-%m-%d %H:%M")
            self.data["unseen"].append("completionist")
            new.append("completionist")
        return new

    def _announce(self, new):
        for key in new:
            _, name, desc, _, _ = LIST[key]
            if self.notify:
                try:
                    self.notify("★ ACHIEVEMENT GET!", f"{name}\n{desc}")
                except Exception:
                    pass
        if new and self.sound:
            try:
                self.sound()
            except Exception:
                pass

    def event(self, name, value=None, gap=0.4):
        """Count something that happened. `value` adds to a list (themes, souls...)."""
        with self.lock:
            now = time.time()
            if gap and now - self.last.get((name, value), 0) < gap:
                return []
            self.last[(name, value)] = now
            if name in ("themes", "souls", "days"):
                if value is None or value in self.data[name]:
                    return []
                self.data[name].append(value)
            elif name == "minute":
                self.data["minutes"] = self.data.get("minutes", 0) + 1
            elif name == "widgets":
                self.data["maxWidgets"] = max(self.data.get("maxWidgets", 0), int(value or 0))
            else:
                self.data["counts"][name] = self.data["counts"].get(name, 0) + 1
            new = self._check()
            self._save()
        self._announce(new)
        return new

    def seen(self):
        with self.lock:
            self.data["unseen"] = []
            self._save()

    def state(self):
        with self.lock:
            d = self.data
            out = []
            for key, (cat, name, desc, icon, _) in LIST.items():
                got = d["unlocked"].get(key)
                hide = cat == "secret" and not got
                out.append({"id": key, "cat": cat, "name": "???" if hide else name,
                            "desc": "It's a secret." if hide else desc, "icon": "?" if hide else icon, "got": got})
            return {"list": out, "unseen": list(d["unseen"]),
                    "got": len(d["unlocked"]), "total": len(LIST),
                    "stats": {"minutes": d.get("minutes", 0), "dogPets": d["counts"].get("dog-pet", 0),
                              "sansLosses": d["counts"].get("sans-lose", 0), "themes": len(d["themes"]),
                              "timerWins": d["counts"].get("timer-win", 0)}}
