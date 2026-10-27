Idle Runner - an Idle Slayer bot for Windows and Linux
https://github.com/santiguti/idle-slayer-bot

HOW TO START
1. Unzip this folder anywhere (a normal folder like Downloads is fine; don't run it from inside the zip).
2. Start Idle Slayer in a 1280x720 window and keep it in front.
3. Double-click IdleRunner.exe, check the settings, and press Start.

Your settings (config.toml) and the logs are saved in this same folder.
config.example.toml explains every setting.

WINDOWS SAYS "Windows protected your PC" OR AN ANTIVIRUS COMPLAINS
The exe is not code-signed (a certificate costs money), and any program that sends mouse and keyboard
input can look suspicious to antivirus software. In SmartScreen choose "More info" > "Run anyway".
To check the download, compare the SHA-256 of the zip with the .sha256 file next to it on the release page
(PowerShell: Get-FileHash IdleRunner-*.zip). The source code is on GitHub; you can also run it from source.

The bot only looks at the pixels of the game window and sends keys and mouse clicks. It never reads or
changes the game's memory, files or network traffic, and it never spends jewels.
