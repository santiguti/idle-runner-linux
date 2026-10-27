# Changelog

## v1.3.0 (2026-10-26)

Groundwork for the Windows version. Nothing changes in how the bot plays.

### New
- **`idle-runner` command.** After `pipx install` (or `pip install -e .`) the bot is the `idle-runner` command. With no arguments it opens the window, and `idle-runner --version` prints the version.

### Changed
- The package is now called `idle-slayer-bot`, the name the repository will get on GitHub. The version comes from `idle_runner.__version__`.

### Under the hood
- The game window is opened through `open_backend()`, which will pick X11 or Windows. `python-xlib` is only installed on Linux. There is no Windows backend yet.
- A build made with PyInstaller works from its own folder, where it keeps `config.toml` and `logs/`.
- Automated tests run on GitHub for Linux and Windows, with Python 3.12 and 3.14.
- A release workflow that builds the Windows zip. It runs from the v2.0.0 tag on, so v1.x tags stay Linux source releases.
- An update check against the latest GitHub release. The window doesn't use it yet.

## v1.2.1 (2026-10-26)

### Fixed
- **Coin counter after an Ultra Ascension.** The counter shows thousands with a comma ("1,251"). The bot read them as small numbers (7.0) and announced "Coins reached 6" about every 10 minutes. It now reads the comma and the digit 9, which it had never seen. Re-reading 3,600 recorded frames changed only the readings that used to fail.
- **"Swipe to Start" in bonus stages.** If the swipe didn't take, the bot was supposed to try again, but it waited for a white pixel this version of the game never shows. It now swipes again while the green handle is still showing in any of its four places (seen in all 30 recorded stage starts).
- **A shop that doesn't open is tried again 15 seconds later**, for example right after a minigame, while its results screen still covers the shop. Before, the bot waited for the next buy interval. It retries once: if the shop stays shut, the normal interval takes over again.

## v1.2.0 (2026-10-26)

### New
- **Choose which Ascension Tree nodes the bot buys, and in what order.** List them under `tree_order` in a new `[tree]` section of `config.toml`. A name the bot doesn't know, or a name listed twice, is reported as an error. Without the list the bot uses the recommended order: 110 nodes, now including the first ones (Village Key, Idle Earrings I and II, Blessing of Cronus, Portals, the ores and Soul Gem) for players who haven't bought them yet. Saving settings from the window keeps your list.
- **Orange Random Box.** The box with a sword is now seen like the silver one, so a buy stops for it and the jumper can grab it. It shows up often and in every zone: in 19,181 recorded frames, at 126 different minutes. Its colour appears in only one other place, the Ascension Tree panel, where the bot never looks for boxes.

## v1.1.2 (2026-10-26)

### Fixed
- **Slow check of nodes already bought.** After each restart the bot went over every bought node: it hovered over each one for 1.5 seconds and opened it. It now recognises "Unlocked" in the tooltip and moves on in under a second, without opening the node. Checked on 34 recorded tooltips, all read right.

## v1.1.1 (2026-10-26)

A safety fix for Ascension Tree buying, which is now seen working live.

### Fixed
- **Jewel offer when Slayer Points weren't enough.**
  - Pressing Buy on a node you can't afford doesn't just fail. The game offers to cover the difference with jewels, which are bought with real money.
  - The bot pressed Buy on Portal Traveler (200 SP, with 95 available) and that offer showed. Nothing was spent: its jewel button works only after you tick "I understand", and the bot never clicks that box.
  - Now the bot hovers over each node first and presses Buy only when the tooltip shows the cost in green (enough SP).
  - With the cost in red, it stops there without opening the node. If it can't read the cost, it closes the node without buying. If a jewel offer still shows up, the bot presses only its Close.
- **Tree buying stopped after the first node.** After a purchase the bot clicks the node again to check it was bought. That click came while the node's window was still fading out, so the game ignored it and the bot stopped. It now waits for the fade to finish.

### Seen working live
- Ascension Tree buying: 7 nodes in order in 13 seconds (Idle Earrings I and II, Blessing of Cronus, Portals, Green Ore, Pink Ore, Soul Gem). It stopped at the first one it couldn't afford.

Covered by automated tests (210 of them), including one where the tooltip says there is enough SP and the game opens the jewel offer anyway.

## v1.1.0 (2026-10-26)

Idle Runner for Linux is now its own project. This release teaches it to ascend at the right moment, to spend Slayer Points on the Ascension Tree, and to keep working after an Ultra Ascension.

### New
- **Ascend by percentage.** Every `ascend_bonus_sample_minutes` the bot reads the Ascend button's "+X% CpS bonus" and logs it. With `auto_ascend_percent` set, it ascends at the first reading that reaches it, and `auto_ascend_minutes` stays as the upper limit. A bonus it can't read is logged with a screenshot, never guessed.
- **Ascension Tree buying** (`auto_buy_tree`, off by default). Buys nodes in the order listed in `idle_runner/tree.py`, at start and after every ascension, the bot's or yours. It skips nodes already bought and stops at the first one it can't buy.
- The ascension panel is opened with a check: the bot waits for the Ascend button and clicks again if the first click was lost.
- The black box also keeps the moments around an unreadable ascend bonus and a tree node that wasn't bought.

### Fixed
- **No buys for almost an hour.** Closing the shop twice in a row, while it was still closing, left an empty dark panel over it that blocked every click. The bot now closes the shop only while it shows, and waits for it to finish.
- **Jewels shop opened by mistake.** After an Ultra Ascension the shop has no Quests tab, and claiming quests clicked the Jewels shop instead. The bot now checks that the Quests tab is there first.
- The Upgrades tab is recognised in both shop layouts (with and without the Quests tab).
- **Ascend by percentage never ascended.** The click that opened the ascension panel came right after the bonus reading closed it, and was lost.
- **Minion claims landing in the Ascension Tree.** After an Ultra Ascension there is no Minions tab, but the bot still clicked where the claim buttons used to be. It now claims only when the Minions tab shows.

### Everything that works
Verified live on Fedora 44 with KDE Plasma 6 (Wayland, game on XWayland) and the native Linux build of Idle Slayer:
- Jumping and boosting nonstop, at the rate you choose.
- Silver boxes, rage at Megahordes (with or without Soul Bonus) and rage during Soul Bonus.
- Buying upgrades and equipment, including the first round of equipment. The Vertical Magnet and Special Vertical Magnet are never bought, and blue event-quest rows are bought only once claimed.
- Stopping a purchase for a floating Random Box so the jumper can grab it, then buying again.
- Buying as soon as the counter shows 6 coins after an ascension (the bot's or yours), then waiting longer between buys until `auto_buy_minutes`.
- Claiming quest rewards.
- Collecting minions and the daily bonus (before an Ultra Ascension).
- Chest hunts, including the life saver.
- Bonus Stage 2, including Second Wind.
- Ascending on a timer and by percentage (on 2026-10-26 it ascended at +12.1% with a 10% target). Every bonus reading since 2026-10-25 was readable.
- Pausing when the game loses focus or the window isn't 1280x720, and resuming afterwards. Finding the game again after it is closed and restarted.
- Logging errors and stuck screens with a screenshot and carrying on.
- The black box, **Mark problem** and the settings window.

Covered by automated tests (208 of them), not yet seen live:
- Ascension Tree buying.
- Ascending while both the Ascend and Ultra Ascend buttons show: every automatic ascension so far happened with the single button shown right after an Ultra Ascension.
- The minion fix above (the Minions node isn't bought again yet).
- Portals, Ascending Heights, the Victor boss fight and crafting (Souls Compass, Rage Pill, Dimensional and Bidimensional staffs).

### Known limitations
- Bonus Stage 2 can still fall out of step in some sections (`Sync timeout` in the log); it carries on and finishes the stage.
- The tree order lives in `idle_runner/tree.py`, not in the settings window. Restart the bot after an Ultra Ascension done by hand.
- Linux only (X11 or XWayland). The Knight boss fight stays disabled.

## v0.1.0 (2026-10-23)

First public release: a Linux port of [Devil4ngle's Idle Runner](https://github.com/Devil4ngle/Idle_Slayer_Script) for the native Linux build of Idle Slayer.

### Same as the original
- Jumps and boosts, collects silver boxes, rages at Megahordes, takes portals, buys upgrades and equipment, claims quest rewards, collects minions and can ascend on a timer.
- Plays chest hunts, bonus stages, Ascending Heights and the Victor boss fight.
- Uses the original's coordinates, colours and timings, so it behaves the same way.

### Better than the original
- No blind spots: the original paused 2 seconds out of every 5, so 40% of the time it couldn't see Megahordes, chest hunts, quests or silver boxes. That pause is gone.
- Safe auto-ascend: it can no longer hit the new **Ultra Ascend** button by accident.
- Easier to control: it plays while the game is focused and pauses as soon as you switch windows. No hotkeys and no focus stealing.
- Recovers on its own: unexpected errors and stuck loops are logged and skipped instead of freezing the bot.
- Black box recorder: it keeps the last hour of gameplay, so you can see exactly what happened while you were away.
- Faster buying right after an ascension.
- Small window with Start/Stop, settings and a **Mark problem** button.

### Known limitations
- Linux only (X11 or XWayland). On Windows, use the original.
- The Knight boss fight stays disabled, as in the original.
