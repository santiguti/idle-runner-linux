# Changelog

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
