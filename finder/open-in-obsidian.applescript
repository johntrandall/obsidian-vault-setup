-- "Open in Obsidian" — Finder toolbar button (source of ~/Applications/Open in Obsidian.app).
-- Opens the Obsidian vault at the front Finder window's git repository root (or the folder itself),
-- creating the vault first if it is not one yet: whole plugin roster installed, profile core-only
-- (nothing switched on). Built by ../install.sh with osacompile. Log: ~/Library/Logs/obsidian-vault-setup.log
on run
	set targetPath to ""
	tell application "Finder"
		if (count of selection) is 1 and class of item 1 of (get selection) is folder then
			set targetPath to POSIX path of (item 1 of (get selection) as alias)
		else if (count of Finder windows) > 0 then
			set targetPath to POSIX path of (target of front Finder window as alias)
		end if
	end tell
	if targetPath is "" then
		display notification "Open a Finder window on the folder first." with title "Obsidian"
		return
	end if
	set cmd to "export PATH=\"$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin\"; " & ¬
		"obsidian-vault-setup open --launch --notify " & quoted form of targetPath & ¬
		" >> \"$HOME/Library/Logs/obsidian-vault-setup.log\" 2>&1 &"
	do shell script cmd
end run
