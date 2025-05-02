#!/bin/bash

# This script removes Brave browser configuration, bookmarks, extensions and residual files.
# Usage: ./brave-clean-slate.sh

sudo rm -rf /Library/Application\ Support/BraveSoftware
rm -rf ~/Library/Application\ Support/BraveSoftware

# Residual files
rm -rf /Library/Saved Application State/com.brave.Browser.savedState
rm -rf /Library/Caches/BraveSoftware
rm -rf /Library/Preferences/com.brave.Browser.plist
