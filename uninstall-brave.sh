#!/bin/bash

sudo rm -rf /Applications/Brave\ Browser.app
sudo rm -rf /Applications/Brave\ Browser\ Beta.app
sudo rm -rf /Applications/Brave\ Browser\ Nightly.app

sudo /Library/Application\ Support/BraveSoftware/BraveUpdater/Current/BraveUpdater.app/Contents/MacOS/BraveUpdater --uninstall --system
~/Library/Application\ Support/BraveSoftware/BraveUpdater/Current/BraveUpdater.app/Contents/MacOS/BraveUpdater --uninstall

