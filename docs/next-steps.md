# Next steps (handoff of 2026-10-22)

167 tests pass (`.venv/bin/python -m pytest -q`). Nothing is committed. A live session of about 90 minutes (auto-buy every minute, no auto-ascend) ended clean. Buying, claiming, Second Wind, restarting the game and the first-round equipment buy all worked live. The user wants every item fixed **correctly, without guessing**: if an item lacks data, measure first.

## 0. Plan agreed with the user on 2026-10-22 (evening), in this order

The user now runs the bot alone (KDE menu → Idle Runner, or `python -m idle_runner run`). The inherited
architecture was reviewed: the layers (x11 → game → runner, the fake backend) are sound. What hurts is the
original's "click, fixed sleep, assume it worked" style and single-pixel detection: about 10 of the 18 bugs
listed below came from it, 5 from game changes and 3 from Linux. Decision: no rewrite. Fix it routine by
routine with verified waits.

1. **Unattended debugging. DONE 2026-10-22:**
   - The 2 s sleep in `close_all` is removed (it blinded the fast checks 40% of the time).
   - Every click, wheel notch and hold goes to `idle_runner.log`.
   - Black box (`idle_runner/blackbox.py`, own process, 4 fps, last 60 min). Measured: 22–27 ms and
     about 100 KB per frame.
   - Automatic marks around anomalies; `mark` command.

   To debug a user's run, start from `logs/marks/`.
2. **GUI. DONE 2026-10-22:** `idle_runner/gui.py` (tkinter, English labels as the user asked) and the KDE
   menu entry. Start/Stop was checked with a missing window (bot exits, error shown); the user hasn't run it
   live yet.
3. **Ascend by CpS bonus %** (user's idea, matches the wiki's rule). The Ascend button reads
   "+10.6% CpS bonus.", which is gained SP / earned SP. The wiki ascends at about 20% mid game and about 10%
   late game; the user suggested 5%. Plan:
   - read the % every few minutes and log it as an event (the curve tells which threshold maximizes SP/hour);
   - setting: ascend after N minutes OR at X%, whichever comes first.

   Progress 2026-10-23:
   - A manual recording of the user's panel and one manual ascension are kept in
     `logs/marks/20261023-000700-ascension-panel/`. It only showed "+0%" (right after an ascension).
   - The text is pure white FFFFFF and the button's twinkling stars never are, so it can be read the
     same way as `coins.py`.
   - `Shop.sample_ascend_bonus` (setting `ascend_bonus_sample_minutes`; 5 in the user's config) opens the
     Ascension tab, saves a frame labelled `ascend-bonus` to `logs/frames/` and closes the panel.

   Next: once those frames cover the digits 0-9 and the decimal point, build the glyph templates, read
   the % (log it as an event every sample) and add the threshold setting.
4. **Verified clicks:** one `Game` helper that clicks, waits for the screen to change and retries,
   generalizing `open_shop`/`select_tab`. Move the routines that are still blind to it when they are next
   touched: `collect_minions` (6 blind clicks, one at (691, 680) unexplained), `auto_ascend` (checks y=480,
   clicks y=600), `buy_temp_item`, the claim loop (item 4 below).
5. The list below. The wiki says the bonus stage "is largely unhelpful" mid game, so BS2 calibration moves
   down. Rage: 147 rages at megahordes, 0 with Soul Bonus; once step 3 measures SP/hour, compare
   `disable_rage_without_soul_bonus = true`.

**Ultra Ascension (user, 2026-10-22):**
- The UA node is bought; the game says 5 USP.
- The user has Wind Waker, Ultra Instinct, Magic Bag and Temporary Hammer. The tree isn't complete.
- The wiki recommends the first UA at 6 USP (about 6.4M total SP).
- The bot must never ultra-ascend.
- **FIXED 2026-10-23: `auto_ascend` could Ultra Ascend.**
  - Since the node purchase, the panel shows Ascend (client x 92-307) and **Ultra Ascend (client x
    332-549)** side by side.
  - The original's confirm click (550, 580) is client (542, 549), inside Ultra Ascend whenever the
    "Are you sure?" dialog isn't up yet or the Ascend click got lost.
  - The confirm click is now (598, 581): Yes / Close in the dialogs, empty panel otherwise.
  - It is only sent once a dialog with the magenta Ascension icon shows.
  - Tests include the three recorded states (`tests/fixtures/ascend/`).
  - Not yet run live by the bot.
- The HUD's top-right bar now shows the USP in blue (it was the purple SP bar).

## How to resume

- `config.toml` (git-ignored) is still the live-test config: the defaults plus `auto_buy_upgrades = true` and `auto_buy_minutes = 1`. Auto-ascend is off.
- Live tests: don't ask the user questions mid-run, because every switch to VS Code unfocuses the game and aborts the running minigame. Get consent first, then act and report. **Ascending is irreversible: ask before the session starts.**
- If KDE shows a "remote control" permission dialog, the bot pauses; the user accepts it and refocuses the game.
- Recordings and measuring scripts are in `logs/recordings/2026-10-22/` (git-ignored):
  - `ascension-counter-and-shop/`: counter and shop button at 10 fps for 3 minutes after a manual ascension.
  - `bonus-stage-2/`: a full BS2 at 4 fps.
  - `shop-tour-1/` and `shop-tour-2-quests/`: the user scrolling through every shop tab.
  - `shop-opens/`: 2 s at 10 fps after each AutoUpgrade, including the late-opening shop and the Vertical Magnet purchase window.
  - `tools/`:
    - `record.py OUT SECONDS INTERVAL_MS [X Y W H]`: read-only recorder.
    - `watch_record.py`: records automatically when the bot logs certain events.
    - `e_record.py`: the post-ascension recorder.
    - `frames.py`: reads our PNGs and builds contact sheets.
    - `wheel_test.py`: sends XTEST wheel notches.
    - `pointer_probe.py`: shows what is under the pointer.

## 1. Pending, in priority order

1. **Six-coin buy (E): VERIFIED LIVE 2026-10-23 19:33** — one ascension by the bot's routine (user's OK); counter read 0, then "Coins reached 6" at 7.5 (8.7 s after the bot started) → AutoUpgrade → the sword was the first buy (Lv 55 a second later), then 143 upgrades + 130 equipment in 6 rounds. Remaining: add the digit-9 samples. Original item: It needs an ascension, so ask first. Expect "Coins reached 6" right after the counter passes 6, then an equipment buy. No sample of the digit "9" exists yet, so it reads as unknown. Save one when it shows up and add it to `idle_runner/coin_glyphs.py`.
2. **Lost clicks.** Sometimes a click never reaches the game: the shop stayed closed for 2.3 s with nothing in the way. The 2026-10-21 keyboard test also lost its first press. `open_shop`/`select_tab` now retry once and log "Shop click retried". Count those in the next run. If they are frequent, investigate the XTEST → XWayland/libei path; the cause is unknown.
3. **Bonus Stage 2 (C9).**
   - (a) The "Swipe to Start" retry never fires. The original retries while (775, 448) is white, but that pixel is 141416 on this version even with the dialog up. Measure a reliable "dialog still showing" pixel in `bonus-stage-2/` (the green slider, 007E00 at (443, 620), is a candidate).
   - (b) The intro got longer: after the swipe, "Golden Invasion appeared!" plus about 10 s of walking before "Go!". The first section's sync (CFBCB8 at (220, 465)) then has to arrive within its 15 s window. In one of two runs it timed out. Calibrate from more recordings.
   - (c) Hold timings (C9 proper): calibrate with `Sync timeout` events and frames from real runs.
3b. **2026-10-23 findings (live).**
   - Buy-loop fix DONE (tests incl. one that reproduces the magnet purchase with a list scrolled by one notch; verified on real frames: VM/SVM rows found over their whole band, a bouncing row is skipped): `Shop.row_around` (row = 93 px under the separator found going up from the click point, must be fully visible and contain y + 10) and `Shop.row_changed` (wait until the bought row is gone, 2 s cap, else "Upgrade click had no effect"). Live: every buy is recorded (`logs/recordings/2026-10-23-buys/`, shop panel, 4 fps, 30 s); the VM rows only show once coins reach ~1 De after an ascension. **Verified live 19:38–19:48**: VM (1 De) and Special VM (10 De) were green (affordable) in 8 recorded buys and were never bought, while the rows around them were (e.g. Augmented Soul Grabber).
   - **Vertical Magnet bought again**, between 19:12 and 19:19 (unrecorded: the shop recorder wasn't running). Two mechanisms fit:
     - (i) the list moves between check and click: the bot waits 50 ms, the game answers in 110–210 ms;
     - (ii) the list is misaligned after scrolling, so the 72 px exclusion box misses the icon.

     Fix in progress: before each click, find the real row around the click point by its black separators (x=1180) and check the exclusion colours over that whole row (no click if a separator isn't visible). After each click, wait until that row actually changes.
   - **Floating silver Random Box** (from the top-centre bonus, 5 in a row): slate frame 5F6D95 (117–508 px; other objects ≤ 52), about 41 px square, flies in from the right, then hovers over the player (x 125–166, y 276–317) for about 3 s until hit. While the bot shopped, the jumper was paused, so the box was lost. Fired live once (20:43:56): the buy stopped after 6 equipment and the retry 17 s later bought 9 more; whether the jumper got the box wasn't recorded (the shop recorder only captures the panel). Implementation: `actions.box_on_screen` and `Shop.stop_for_box` stop the buy, close the shop and log "Shopping stopped for a Random Box"; `Runner.buy` retries 15 s later. Orange boxes: no sample yet (`logs/recordings/2026-10-23-boxes/` has a 15 min play-area recording to scan). With the Vertical Magnet the box adjusts its height, which breaks blind jumping (user); jumping by box position would be needed.
   - **BS2 played live** by the bot's routine (`logs/recordings/2026-10-23-bs2`, 5 fps):
     - Second Wind was taken ("BonusStage2 Retry").
     - The sync timed out in s1 (twice), s2 and s3; all 4 sections then "completed" unsynchronized.
     - S1 cause, measured: the player runs into the first block and stops before the bot acts. The block's light edge (CFBCB8, 3–4 px wide, on y=465) came to rest at x 162–165 / 178–181 / 240–242 today and at 204–207 / **220–223** on 2026-10-22, so the single pixel (220, 465) matched only on 10-22. DONE 2026-10-23 (test with the 3 measured rest positions; a third live run also stopped at 162-181): `S1_SYNC` now spans x 151-220 on y=465, the span the original uses for the same block in section 3. Reading of the 3 runs: the exact colour CFBCB8 only shows while the block stands still. **Verified live 19:57–21:05: 5 BS2 runs, zero sync timeouts**; 4 finished all 4 sections, 1 ended by a focus loss; Second Wind was taken 3 times.
     - S2 (BB26DF, a 400 px platform) never appeared while it waited (the stage was already out of step).
   - **Post-ascension claim trigger**: right after the ascension the shop button glowed, but the Quests tab didn't (nothing to claim). The glow isn't only quests. One wasted claim was seen; watch for repeats and gate on the in-shop Quests tab glow if they happen.
   - **Digit 9** samples found (69.5, 109, 209, 390); add them to `coin_glyphs.py`.
3c. **Buy right after a minigame** (minor, live 2026-10-23): when the buy timer runs out during a bonus stage, the buy fires as soon as it ends, while the results screen still covers the shop. It retries the click, then logs "AutoUpgrade shop not open" (3.4 s lost, 5 times in 70 min); the next minute's buy works.
4. **Claim loop clicks the same button 2–3 times** about 21 ms apart: the original doesn't pause after a click. Harmless, but each click logs "Quest Claimed". Fix: after clicking, wait until that pixel stops being green (short cap).
5. **C8, click guard.** Measured with the pointer over different windows:
   - Over the game, `root.query_pointer().child` is the game's client window (no frame).
   - With Steam over the game, it is Steam's id.
   - Over Wayland windows it is 0 (as far as seen).

   Still unknown: whether `child` is updated right after an XTEST move. If not, the guard would block legitimate clicks. Measuring it needs input, so ask first; then implement "don't click unless `child` is the game".
6. **Quest Reward rows: DONE 2026-10-23.**
   - The user marked it (`logs/marks/20261023-013214/`): a claimed event reward ("Dracula's Tooth") stays
     blue but gets a green "Unlock 200 Sx" button, and the bot never bought it.
   - `first_row_after_quest_rewards` now skips only blue rows with the grey (7A7A7A) "Quest Reward"
     button. Blue rows with a buy button are bought like any other row.
   - Tests use both recorded frames (`tests/fixtures/quest_rewards/`).
   - Unknown: whether claimed rewards are sorted by price or pinned at the top. If pinned, an
     unaffordable (red) one would stop the buy loop above affordable rows. Watch for
     "AutoUpgrade Done upgrades=0" while green rows show below a blue one.
7. **F.** At start-up, check the in-game settings the original requires and warn, or set them. The list is in the original's README and `Libraries/Log.au3:180-212`. Later.
8. **H, efficiency** (after the script works):
   - Use the timings from the game's wiki, https://idleslayer.fandom.com/wiki/Idle_Slayer_Wiki, for buying and ascending.
   - Inside the open shop the Quests tab blinks gold when something can be claimed. AutoUpgrade could claim in the same visit.

## 2. Done on 2026-10-22 (each with a test written first and watched failing)

- **A1–A6:**
  - Config: unknown sections and keys in the wrong section are errors.
  - "Game unavailable" is logged once per state change.
  - "Bot started" carries the effective settings.
  - The chest-hunt text is the original's exact text.
  - A skipped bonus stage saves its end frame.
  - The repeater test no longer depends on timing.
- **B7:** a restarted game is found again (`WindowGone` → "Game window lost" → lookup by name every 2 s → "Game window found"). Verified live twice: a graceful close plus a relaunch through Steam (window found after 18 s), and the user closing the game.
- **Claim trigger:** the shop button pulses at 144 FPS, and the original's exact CBCB4C lasts about 7 ms. It now matches with ±16. Verified live.
- **Shop opening:** the shop can open 110–210 ms after the click, so the bot waits up to 1 s and then retries the click once.
- **Wrong-tab clicks** (these bought "Random Box Vertical Magnet"): equipment's "Max" lands on "Buy all available" in Upgrades, and the claim's green search finds "Unlock" buttons. `Shop.tab_shown` now checks the tab's selected shade and the "Buy all" bar before any buying or claiming click.
- **Exclusions:** Vertical Magnet / Electric Worms rows are skipped in any order, where the original skipped one of each in a fixed order.
- **Scrollbar colours changed:** the track is A0A0A0 and the thumb B7B7B7 at x=1254. Quests now checks the thumb's top end (1254, 160), which stays covered while the list bounces. This fixed the blank Quests panel.
- **Event quests:** `first_row_after_quest_rewards` scrolls past blue "Quest Reward" rows in Upgrades. The game setting "Hide locked quest rewards", which the original requires, also hides the locked ones.
- **Second Wind in Bonus Stage 2** (user's request): taken once per stage, and the failed section is rerun, as the original did only in BS3.
- **Equipment:** every AutoUpgrade now runs one equipment round. The original bought equipment only after an upgrade, so right after an ascension it bought nothing. Verified live: 0 upgrades + 28 equipment.
- **Six coins (E):** `coins.read_coins` reads the counter by glyph templates. `Runner.buy_at_six_coins` buys at the first reading ≥ 6 after a reading < 6, with a 2-minute fallback. Not yet seen live.
- `claim_quests` and every shop failure now save frames.

## 3. Measured facts (game and desktop as of 2026-10-22; AutoIt coordinates)

| What | Value |
|---|---|
| Wheel notch (XTEST, both lists) | 50 px, usually drawn within 30 ms; the game sometimes stalls drawing for >1 s, then catches up |
| Upgrades rows | 96 px apart; first separator y=153 at the top; black separators at x=1180 |
| Quest Reward rows | background 0B6BA1 at x=1130, grey button 7A7A7A |
| Buy / claim green | 11A622 (equipment buy 11AA23); unaffordable red A91111 |
| Scrollbar | x=1254: track A0A0A0, thumb B7B7B7. x=1260: track D6D6D6, thumb F5F5F5 |
| Selected shop tab | 5A251A–62271C (fades) at (820, 700) Equipment / (897, 700) Upgrades; unselected 85–8E red; Quests tab 431C13, gold when claimable |
| (1180, 636) | Upgrades "Buy all available" bar A1–A8 grey; Equipment "Max" FFFFFF / 898989 |
| Shop button glow (1130, 610) | pulses 989898 → CFCF46 when a quest can be claimed |
| After an ascension | counter "0" for about 43 s, no shop button until the first coins; then 3 → 7.5 → 11.3 …; the shop button appears already glowing |
| Coin counter digits | AutoIt (488, 69)–(807, 97), white fill FFFFFF |
| Bonus Stage 2 start | "Swipe to Start" slider 007E00 at (443, 620); then "Golden Invasion appeared!" and about 10 s before "Go!" |
| Second Wind | green 00A400 at (615, 590), click (560, 600); Close red AF0000 at (716, 600) |
| Desktop | KDE asks for remote-control permission on the first XTEST input after XWayland starts; the game stops drawing while fully covered; a destroyed window gives BadDrawable/BadWindow; a relaunched game reused window id 0x3a00008 |

## 4. Notes from 2026-10-23

- **Chest hunt strategy "did nothing":** `no_reinforced_crystal_saver = true` (set by the user in the
  window at 00:45) makes the original open the life saver right after the 1st chest, ahead of
  `perfect_chest_hunt`. This is the original's GetUpdatedState, not a port bug. The wiki: Crystal Saver
  = 1st chest safe, Reinforced = 2nd chest safe too. The hints in `config.example.toml` now say so. The
  user wants the aggressive strategy, so their config has it false.
- **The window overwrote an outside edit of `config.toml`** (the `ascend_bonus_sample_minutes = 5` set by
  Claude was lost). The window now asks before overwriting a file changed since it opened. Don't edit
  `config.toml` while the window is open; ask the user to change it there.
- Three hunts in a row (00:39, 00:50, 00:59) gave the identical sequence R R R R R M R, ending at chest 7.
  Unexplained; check the black-box frames if it repeats.
