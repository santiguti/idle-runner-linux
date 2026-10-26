# Next steps (handoff of 2026-10-22)

212 tests pass (`.venv/bin/python -m pytest -q`; 2026-10-26). Nothing is committed. A live session of about 90 minutes (auto-buy every minute, no auto-ascend) ended clean. Buying, claiming, Second Wind, restarting the game and the first-round equipment buy all worked live. The user wants every item fixed **correctly, without guessing**: if an item lacks data, measure first.

## Log review of 2026-10-25 (last run: 2026-10-23 19:15 – 10-24 00:14, about 5 h)

- **The user did the first Ultra Ascension** between 22:51 and 22:56 on 10-23, with 6 USP. Until the UA node
  (2M SP) is rebought, the ascension panel has only one Ascend button, centred (client x about 210-430).
  `auto_ascend` is on in the user's config (every 10 min).
- **First automatic ascension, 23:16:38: correct.** It was a normal Ascend (+19 SP, +19%), checked in the
  black box. The Ultra Ascend button didn't exist then, so the dangerous layout is still untested live.
- **55 minutes without a single buy (23:16 – 00:12; 43 "AutoUpgrade shop not open").** Root cause:
  - Right after the UA the shop has 5 tabs (Equipment, Upgrades, Jewels (purple drop), ⋮, X). There is
    no Quests tab until Permanent Quests / Training Quests is bought.
  - `claim_quests` clicked (1000, 690), which landed on the **Jewels shop (outfits bought with real
    jewels)**. `tab_shown("quests")` is a negative test ("no buying tab showing"), so it passed, and the
    loop wheeled there for 60 s ("stuck claim_quests"). It searched for green buttons the whole time and
    found none; an affordable outfit's green button would have been clicked.
  - After it closed that panel, a dark empty panel stayed over the shop area (client x 795-1280,
    y 108-720) from 23:18:09 until the user opened and closed the crafting panel at 00:12. Every shop
    click in between failed. With 4,489 coins, 5 green upgrades (10-1000) were never bought.
  - **FIXED 2026-10-25** (tests on 6 recorded tab bars, `tests/fixtures/shop_tabs/`):
    - `Shop.has_quests_tab` tells the bars apart by where the X tab starts (1200 vs 1184).
    - `claim_quests` logs "Claim quests: no Quests tab" and closes the shop without clicking (1000, 690).
    - `tab_shown("quests")` also needs the Jewels and ⋮ tabs unselected. The Quests tab turns gold, not
      darker, when something can be claimed, so its own shade can't be used.
    - Upgrades is checked at x = 915, inside it in both bars (897 was Equipment in the five-tab bar).
  - **The dark panel had another cause, reproduced live on 2026-10-25 (FIXED):**
    - It came back at 23:40:43, with six tabs and no Jewels click.
    - Both times, `claim_quests` closed the shop and `auto_upgrade`'s blind "close the shop if it's open"
      click hit the X tab 23 ms later, while the shop was still closing. The shop takes ~120 ms to close
      (measured at about 30 fps).
    - Reproduced on purpose: close, close again at +23 ms, open at +194 ms → dark panel. Close then open
      at +194 ms → fine.
    - The dark panel takes every click (shop button, its X). Opening and closing crafting doesn't clear
      it. **Escape does** (2 of 2 times).
    - **Escape without the dark panel opens "Exit Game — Are you sure?"** Its Yes (client 493-624 x
      525-578) is where the Ascend dialog's Yes is. So Escape is not used as a recovery.
    - Fix: `Shop.close_if_open` clicks the X only while the shop's white corner shows, then waits 300 ms
      (was 150). Used by `auto_upgrade` and `claim_quests`.
  - The claim trigger (shop-button glow) fired while no quests existed: the glow isn't only quests.
- **Ascend by % never ascended live (2026-10-25 23:32, FIXED):**
  - The bonus sample closes the panel, and `auto_ascend` clicked (95, 90) 21 ms later. That click was
    lost ("Ascend skipped: ascend button not found", twice).
  - `Shop.open_ascension_tab` now waits up to 2 s for the Ascend button and retries once. It clicks
    (95, 90) only while the panel's X tab (538, 681, AD1111) is not showing: on the tree tab, (95, 90)
    is the "Buy on Click" toggle.
- **Tree session 2026-10-25** (user's OK to buy in wiki order; the bot frozen with SIGSTOP meanwhile):
  - Tier 1 is complete.
  - Tier 2 bought: Red Ore, Boost Coin, Cheap Cooldown, Augmented Soul Gatherer, then **Slowmo Bonus
    (40) and Blue Ore (20)**, bought by Claude after one ascension (+53).
  - Next in order: Green Ore 35, Pink Ore 50, Soul Gem 25, Doesn't Matter to Me 150, Portals 20 (the wiki:
    as late as possible).
  - The user bought Stones of Time on 10-26 and ascended by hand at about 01:00. The old bot's % ascend
    had failed 11 times (00:30-00:57). The bot restarted with the fixed code at 01:03:58; its % ascend
    isn't seen live yet.
  - UI, measured:
    - The panel opens on the Ascension tab; the tree tab is client (197, 665).
    - **The tree keeps its last pan and zoom** (on 10-26 it opened where the user had left it).
    - **Minimum zoom is a fixed layout:** 10 or 20 wheel notches down, from any pan or zoom, give the
      same node positions (best alignment shift (0, 0); the rest is the rings' pulse). Use it.
      - min-zoom client = 0.5 × default-view client + (42.5, 34.5), checked on 5 nodes.
      - Nodes are ~25 px wide there, ~30 px apart.
    - Dragging pans, with ~30 px of inertia.
    - Hovering shows a tooltip (description, "Cost: N" red/green, or "Unlocked") after ~0.5 s.
    - A click with "Buy on Click" off opens a modal: name, cost, rarity (LEGENDARY gold, ULTRA blue),
      description. One pixel at client (460, 540) tells three states apart:
      - 00A400 green: **Buy** (526, 551) / Close (750, 551). **The prerequisites are met, not
        necessarily the SP**: Legendary Belt (350) showed Buy with 191 SP. Not yet measured: what Buy
        does without enough SP.
      - AF0000 red, one wide button, text "Can't buy yet" (white in x 556-600): a prerequisite is missing.
      - AF0000 red, one wide button, text "Close" ("Unlocked | N"): already bought.
      - The wide button (640, 551) closes either red modal.
    - Ring colours aren't a state: green = unlockable, gold = LEGENDARY rarity, blue = post-UA (ULTRA).
    - **(95, 90) on the tree tab is the "Buy on Click" toggle.** `collect_minions` clicks it blindly: never
      leave the tree open while the bot runs.
    - The wiki's v7.0.0 costs differ from the game's for some nodes.
  - **Min-zoom map** (client coords, surveyed 10-26 with 191 SP; B = Buy, C = Can't buy yet, U = bought):
    - Bought: Stones of Time (110, 152) U, Blue Ore (330, 177), Red Ore (270, 177), Slowmo (270, 257).
    - Buyable: Village Key 3 (110, 182) B, Dangerous While Alone 35 (110, 212) B, Idle Earrings I 20
      (140, 242) B, Money Laundering 25 (170, 122) B, Portals 20 (240, 122) B, Green Ore 35 (300, 217) B,
      Legendary Belt 350 (240, 302) B.
    - Locked: Idle Earrings II 25 (140, 272) C, Blessing of Cronus 50 (110, 272) C (path: Earrings I →
      II → Blessing, by the drawn links), Dagger Edge 75 (170, 272) C, Orange Ore 5 (260, 197) C,
      Yellow Ore 5 (340, 197) C, Soul Gem 25 (360, 217) C, Sacred Book of Projectiles (the Bow) 1,000
      (300, 302) C, Stocks Buyer 50 (200, 122) C, Portal Traveler 200 (270, 122) C, Pink Ore 50
      (330, 217) C.
    - Not located yet: Ancient Quests, Hot Desert (the wiki: "at the very top"), Stability, Triple Shot,
      Minions, Soul Slash.
  - **`buy_tree` routine: DONE 2026-10-26, not yet run live** (`idle_runner/tree.py`, tests in
    `tests/test_tree.py`). Setting `auto_buy_tree` (off by default).
    - It runs once at start, after each ascension by the bot, and after "Coins reached 6" (an ascension
      by hand).
    - It opens the tree and wheels down 20 notches. Then for each node in `ORDER` it clicks the node's
      min-zoom point and reads the modal:
      - bought → close and go on;
      - Buy → click it, wait for the modal to go, click the node again and expect "bought";
      - otherwise → stop.
    - Nodes seen bought are cached for the bot's run.
    - The user's order (10-26): Village Key, Idle Earrings I, Idle Earrings II, Blessing of Cronus,
      Portals (the user needs jellies now), Green Ore, Pink Ore, Soul Gem, Portal Traveler, Legendary
      Belt, Sacred Book of Projectiles, Dangerous While Alone, Orange Ore, Yellow Ore, Money Laundering.
      Ancient Quests and Hot Desert are still to locate: at minimum zoom they seem to sit under the
      header.
    - **Live 2026-10-26 02:10: bought 7 nodes in 13.5 s** (Idle Earrings I and II, Blessing of Cronus,
      Portals, Green Ore, Pink Ore, Soul Gem).
    - The 02:07 run bought Village Key, but its check click came 222 ms after Buy, while the modal's
      dimming was still fading, and was lost. The routine then stopped. Fix: `wait_modal_gone` waits
      until the panel's X tab is AD1111 again (150202 under the modal, 3C0606 while fading).
    - **Buy without enough SP opens a jewel offer** ("cover the missing amount with 💧5"). It has an
      "I understand" box (white at 583, 521), a jewel button (094309 at 468, 571) that works only once the
      box is ticked, and Close (758, 582). Jewels cost real money.
      - At 02:11:05 it opened for Portal Traveler (200 SP, 95 available).
      - Nothing was spent: no bot click lands on the box, and `close_all` closed the offer 0.3 s later
        (its AF0000 check matched the offer's Close).
    - Fix (FIXED 2026-10-26, tests incl. a lying tooltip): Buy is clicked only after the node's tooltip
      shows its cost in green.
      - The tooltip is a 262626 box from x + 43, centred on the pointer. Its cost digits are 11AA23 /
        AD1111 on the row with the SP icon (6A31CA).
      - "Unlocked" is 11AA23 too but has no SP icon.
      - Checked on 26 recorded tooltips: 16 costs read right, 10 "Unlocked" never read as affordable.
      - Red → stop without opening the modal. Not read → close the modal with Close and stop. A jewel
        offer anyway → its Close, stop.
  - **Full wiki order (2026-10-26, user: "respetemos lo que diga la wiki"):** `ORDER` holds 102 nodes.
    - The survey clicked 155 candidate points at minimum zoom and read each modal's name: no misses, no
      duplicates. Candidates came from a colour disc detector plus 23 points added by eye.
      - Recipe: the panel's background is saturated orange-brown (hue 10-50°, sat > 0.45). Score each point
        as non-background share within r 11 × background share within r 14-17, and take local maxima.
      - Static-pixel and edge-circle detectors failed: the panel is translucent and the rings pulse.
      - Scripts and the name → position map are in the session's scratchpad (`map/`). Re-survey with
        them if the tree changes.
    - Order: what's left of the UA guide (Portal Traveler, Legendary Belt, the Bow, Stability, Triple
      Shot), the cheap "First Ultra Ascension" nodes (Orange Ore, Yellow Ore, Dangerous While Alone), the
      tier list's tiers 1-10 in order, the rest of the "First Ultra Ascension" section, and the Ultra
      Ascension node last.
    - New rule: a node locked by a prerequisite ("Can't buy yet") is skipped and checked again after the
      next purchase, since the wiki's order doesn't follow the tree's links. A buyable node with the cost in
      red stops the run (SP is saved in order).
    - Not located (under the header at minimum zoom, or missed): Ancient Quests 5, Hot Desert 5, Bullet
      Time 250, Map 150, Portal Dominum, Land Lord, Astral Sword, Astral Blessing, Daily Silver Bonus.
    - Cost: after each purchase the locked nodes before the stop point are opened again, ~1.2 s each.
  - **`collect_minions` guarded (2026-10-26):**
    - After the UA its trigger still fired (00:08:38, 01:04:39) with no Minions tab.
    - Its claim clicks (318, 182) ×5 and (320, 280) ×5 then landed in the tree and opened modals; with
      "Buy on Click" on they would buy nodes.
    - It now opens the panel with `actions.open_ascension_tab`, shared with the shop and the tree. It
      claims only if the Minions tab shows selected at (332, 676); the empty bar there is 3E260A.
    - The selected Minions tab itself isn't measured (no Minions node yet). If minions stop being
      collected once the node is bought, measure it.
- **Ascend by %: DONE 2026-10-25.**
  - `idle_runner/ascend_bonus.py` reads the Ascend button's second line. The game shrinks the font to
    fit (14-16 px tall), so glyphs are area-averaged to 14x10 and compared by correlation.
  - Templates: `bonus_glyphs.py`, from the 39 readable samples (`logs/frames/*-ascend-bonus.png`).
  - Checked on all 50 samples: 50/50. In leave-one-out (each frame read without its own shapes) 44/50
    are right and the 6 misses are "7", which has a single shape: they read as None, never as a wrong
    number.
  - `sample_ascend_bonus` logs "Ascend bonus" with `percent`. "Ascend bonus unreadable" saves a frame
    and a black-box mark: add its glyphs then.
  - New setting `auto_ascend_percent` (0 = off) ascends at the first sample that reaches it, and
    `auto_ascend_minutes` stays as the cap. It needs `ascend_bonus_sample_minutes > 0`.
  - Post-UA curve: 0% → 3% (23:06) → 15% (23:11) → 19% (23:16).
- **Coin reader** after the UA: the counter shows "1,027", "4,489"; it read 7.0 / 6.0 and fired
  "Coins reached 6" every ~10 min. The comma isn't a glyph yet (extra buys only, harmless).
- **Minions Collect** fired 90 times in 20:21–23:18 (pre-UA), often 3–7 s apart: the (99, 113) trigger
  stays on after the routine. No frames kept (the black box only holds 23:13+). Irrelevant until the
  Minions node (1,200 SP) is rebought.
- **Ascension tree UI** (black box 10-24 00:12–00:14, the user buying): a zoomable, pannable node graph
  in the left panel (client x 0-630). The header reads "N available" and "Ascend to claim: +N". Nodes are
  about 50 px: magenta = bought, green ring = buyable, gold / grey / blue (new post-UA nodes) = other
  states. Clicking a node opens a modal with its name, cost and "Buy". A "Buy on Click" toggle sits at
  the top left. Tier list parsed from the wiki (301 rows incl. "First Ultra Ascension"); the wiki's
  Ultra_Ascension_Strategy reorders the early post-UA priorities (souls, Stones of Time, Blessing of
  Cronus; skip CpS; Portals late).

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

- `config.toml` (git-ignored) is the user's, edited in the window: auto-buy every 2 min, auto-ascend off, perfect chest hunt, `ascend_bonus_sample_minutes = 5`. Don't edit it while the window is open.
- Night of 2026-10-23 (00:17–01:44, 54 buys): 3 "Shop tab not shown" (upgrades, buy aborted; black-box marks kept), 5 "Shop click retried", 2 BS2 sync timeouts (s3, s4), 0 ascend-bonus samples (the setting had been lost).
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
