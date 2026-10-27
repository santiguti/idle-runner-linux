Idle Runner - an Idle Slayer bot for Windows and Linux
https://github.com/santiguti/idle-slayer-bot

HOW TO START
1. Extract the archive anywhere (a normal folder like Downloads is fine):
       tar xzf IdleRunner-*-linux-x64.tar.gz
2. Optional: run ./install.sh from the extracted IdleRunner folder. It copies the program to
   ~/.local/share/idle-runner and adds "Idle Runner" to your application menu.
   Without it, just run ./IdleRunner from the extracted folder.
3. Start Idle Slayer in a 1280x720 window and keep it in front.
4. Open Idle Runner, check the settings, and press Start.

Your settings (config.toml) and the logs are saved in the folder the program runs from: the extracted folder,
or ~/.local/share/idle-runner if you used install.sh (installing again keeps both).
config.example.toml explains every setting.

REQUIREMENTS
- A distro with glibc 2.35 or newer (Ubuntu 22.04, Fedora 36 or newer).
- The game in a 1280x720 window under X11 or XWayland.

TO CHECK THE DOWNLOAD
Put the .sha256 file next to the archive and run:
    sha256sum -c IdleRunner-*-linux-x64.tar.gz.sha256
The source code is on GitHub; you can also run it from source.

The bot only looks at the pixels of the game window and sends keys and mouse clicks. It never reads or
changes the game's memory, files or network traffic, and it never spends jewels.
