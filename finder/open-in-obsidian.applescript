-- "Open in Obsidian" — Finder toolbar button and URL handler (source of ~/Applications/Open in Obsidian.app).
-- Opens the Obsidian vault at a folder's git repository root (or the folder itself), creating the vault
-- first if it is not one yet: whole plugin roster installed, profile core-only (nothing switched on).
-- Two entry points:
--   on run            Finder toolbar click: the selected folder, else the front window's folder.
--   on open location  obsidian-vault-setup://open?path=<url-encoded absolute path>  (a clickable link,
--                     e.g. from a terminal status line). The path must be inside the home folder.
-- Built by `obsidian-vault-setup install-finder-button` with osacompile, which also registers the URL
-- scheme. Log: ~/Library/Logs/obsidian-vault-setup.log

on openFolder(targetPath)
	set cmd to "export PATH=\"$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin\"; " & ¬
		"obsidian-vault-setup open --launch --notify " & quoted form of targetPath & ¬
		" >> \"$HOME/Library/Logs/obsidian-vault-setup.log\" 2>&1 &"
	do shell script cmd
end openFolder

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
	openFolder(targetPath)
end run

on open location theURL
	-- Decode and validate with the tool itself (`url --decode`, tested in tests/): scheme and host
	-- must match and the path must be an existing directory under $HOME. A refused link prints
	-- nothing, so a crafted link cannot point the tool at an arbitrary folder.
	set targetPath to ""
	try
		set targetPath to do shell script "export PATH=\"$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin\"; " & ¬
			"obsidian-vault-setup url --decode " & quoted form of theURL
	end try
	if targetPath is "" then
		display notification "Refused: " & theURL with title "Obsidian"
		return
	end if
	openFolder(targetPath)
end open location
