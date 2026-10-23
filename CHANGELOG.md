# Changelog

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
