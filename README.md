# Brave Manager

A tool for managing installed Brave versions on Windows and macOS. Please see
the [windows](windows) and [macos](macos) subdirectories for instructions on
the two operating systems.

## Installation

Download [this repository's Zip file](https://github.com/brave/brave-manager/archive/refs/heads/main.zip)
and unpack it.

## Usage

### Windows

Right-click on `Uninstall Brave.bat` and pick "Run as Administrator.
If you encounter any issues, try first right-clicking `Stop BraveUpdate.bat`.

### macOS

Run `uninstall-brave.sh` from a Terminal. For example, by entering the
following:

```
~/Downloads/uninstall-brave.sh
```

If `uninstall-brave.sh` is in the current directory, then you need to prefix it
with `./` to execute it:

```
./uninstall-brave.sh
```

The command will likely prompt for your password.