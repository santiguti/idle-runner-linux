"""How each setting appears on the Settings page: label, help, panel, widget and limits (Settings has the
values and config.check_ranges the rules; tests keep these limits in line with it)."""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    label: str
    help: str
    card: str
    kind: str  # "toggle", "int", "float", "slider", "choice" or "text"
    unit: str = ""
    minimum: float | None = None
    maximum: float | None = None
    step: float = 1
    choices: tuple[str, ...] = ()  # "choice": the labels; an int setting stores the label's position, from 1
    depends_on: str | None = None  # a toggle that has to be on for this field to matter
    warning: str = ""


CARDS = ("Playing", "Shopping", "Ascending", "Ascension Tree", "Minions", "Minigames", "Crafting", "Advanced")
ZONES = ("Hills", "Hot Desert", "Jungle", "Frozen Fields", "Funky", "Modern City", "Factory", "Valley", "Castle")

FIELDS: dict[str, Field] = {
    # Playing
    "jump_interval_ms": Field("Time between jumps", "How often the bot jumps and boosts.", "Playing", "slider",
                              "ms", 0, 300, 10),
    "circle_portals": Field("Travel through portals", "Takes the next zone whenever the portal is ready.",
                            "Playing", "toggle"),
    "circle_portals_count": Field("First zone", "Where the trip through the zones starts.", "Playing", "choice",
                                  minimum=1, maximum=9, choices=ZONES, depends_on="circle_portals"),
    "disable_rage_without_soul_bonus": Field(
        "Rage at Megahordes only with Soul Bonus", "Saves the rage for a Megahorde that gives more souls.",
        "Playing", "toggle"),
    # Shopping
    "auto_buy_upgrades": Field(
        "Buy upgrades and equipment",
        "Opens the shop on a timer and buys everything affordable, except the Vertical Magnet and Electric "
        "Worms. Also claims quest rewards.", "Shopping", "toggle"),
    "auto_buy_minutes": Field("Buy every", "", "Shopping", "float", "minutes", 0.5, 120, 0.5,
                              depends_on="auto_buy_upgrades"),
    "post_ascend_first_buy_seconds": Field(
        "First buy after ascending", "Then the wait doubles until it reaches the interval above. 0 waits the "
        "full interval.", "Shopping", "int", "seconds", 0, 600, 5, depends_on="auto_buy_upgrades"),
    # Ascending
    "auto_ascend": Field("Ascend automatically", "", "Ascending", "toggle",
                         warning="Ascending resets your run. It can't be undone. The bot never Ultra Ascends."),
    "auto_ascend_percent": Field(
        "Ascend at this bonus", "As soon as the Ascend button shows at least this \"+X% CpS bonus\". The wiki "
        "suggests about 20 % mid game and 10 % late. 0 ascends on the timer only.", "Ascending", "float", "%",
        0, 100, 0.5, depends_on="auto_ascend"),
    "auto_ascend_minutes": Field("Or at the latest every", "", "Ascending", "float", "minutes", 1, 600, 1,
                                 depends_on="auto_ascend"),
    "ascend_bonus_sample_minutes": Field(
        "Check the bonus every", "Reads the Ascend button and logs the bonus. 0 never checks it, so ascending "
        "at a bonus is off too.", "Ascending", "float", "minutes", 0, 60, 1),
    # Ascension Tree
    "auto_buy_tree": Field("Buy Ascension Tree nodes",
                           "At start and after every ascension, in the order of the Tree order page.",
                           "Ascension Tree", "toggle", warning="Spends your Slayer Points."),
    # Minions
    "work_benefits": Field("I have Work Benefits", "The Divinity that makes missions 15% faster: the bot "
                           "checks the minions back sooner.", "Minions", "toggle"),
    "improved_work_conditions": Field("I have Improved Work Conditions", "The Divinity that makes missions 20% "
                                      "faster.", "Minions", "toggle"),
    "greeks_blessing": Field("I have Greeks Blessing", "The Divinity that makes missions 25% faster.", "Minions",
                             "toggle"),
    # Minigames
    "skip_bonus_stage": Field("Skip bonus stages", "Waits for them to end instead of playing.", "Minigames",
                              "toggle"),
    "no_lockpicking": Field("I don't have Lockpicking 100",
                            "The Divinity that lets chest hunts open more chests.", "Minigames", "toggle"),
    "no_reinforced_crystal_saver": Field(
        "I don't have the Reinforced Crystal Saver", "Then the life saver opens right after the first chest, "
        "even with Perfect Chest Hunts on.", "Minigames", "toggle"),
    "perfect_chest_hunt": Field(
        "Go for Perfect Chest Hunts", "Riskier: ignores the life saver until a 2x shows. Turn the 2x2x Dark "
        "Divinity off.", "Minigames", "toggle"),
    # Crafting
    "craft_soul_bonus": Field("Craft a Souls Compass", "At a Megahorde with Soul Bonus.", "Crafting", "toggle"),
    "craft_rage_pill": Field("Craft a Rage Pill", "At a Megahorde with Soul Bonus.", "Crafting", "toggle"),
    "craft_dimensional_staff": Field("Craft the Dimensional Staff once", "At the first Megahorde after Start.",
                                     "Crafting", "toggle"),
    "craft_bidimensional_staff": Field("Craft the Bidimensional Staff once", "At the first Megahorde after Start.",
                                       "Crafting", "toggle"),
    # Advanced
    "window_name": Field("Game window title", "", "Advanced", "text"),
    "offset_x": Field("Frame offset X", "Between the original's coordinates and the game's picture.", "Advanced",
                      "int", "px"),
    "offset_y": Field("Frame offset Y", "", "Advanced", "int", "px"),
    "color_tolerance": Field("Colour tolerance", "0 matches colours exactly, like the original.", "Advanced",
                             "int", "", 0, 255),
    "log_dir": Field("Logs folder", "Logs, screenshots and the black box.", "Advanced", "text"),
    "log_level": Field("Log detail", "DEBUG also logs every pixel check.", "Advanced", "choice",
                       choices=("INFO", "DEBUG", "WARNING")),
    "save_frames": Field("Save screenshots", "At minigames, timeouts and errors.", "Advanced", "toggle"),
    "blackbox_fps": Field("Black box frames per second",
                          "Keeps the last minutes of play to look at problems later. 0 turns it off.",
                          "Advanced", "float", "", 0, 30),
    "blackbox_minutes": Field("Black box keeps", "About 1.4 GB per hour at 4 frames per second.", "Advanced",
                              "float", "minutes", 1, 600, 5),
}


def friendly(problem: str) -> str:
    """A config.check_ranges message with labels instead of setting names, and without the file name."""
    problem = problem.split(": ", 1)[-1]  # every message starts with the config file's path
    return re.sub(r"\b(" + "|".join(FIELDS) + r")\b", lambda m: f"“{FIELDS[m[1]].label}”", problem)
