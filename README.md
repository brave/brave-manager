# Brave Manager

A tool for managing installed Brave versions on macOS and Windows.

## Installation

Download [this repository's Zip file](https://github.com/brave/brave-manager/archive/refs/heads/main.zip)
and unpack it. Open a terminal in the unpacked folder and execute the
following command. On macOS:

```
python3 install.py
```

On Windows:

```
python install.py
```

The script asks whether it should add Brave Manager to your `PATH`.

## Usage

After installation, open a new terminal window. Then you can launch Brave
Manager by typing the following command:

```
bm
```

If you did not add Brave Manager to your `PATH`, run `bin/bm` (macOS) or
`bin\bm.bat` (Windows) in the unpacked folder instead.

Brave Manager can also be driven non-interactively, for instance from CI. The
following uninstalls all installed architectures and levels of a channel, then
all installed updaters:

```
bm uninstall origin nightly --delete-profile
bm uninstall updater
```

Run `bm --help` for the full list of commands.

## Development

To run tests, execute the following in this directory:

```
python3 -m unittest
```

To update the Zip file of historic releases that's included in this repository,
follow the instructions in `update_historic_releases.py`.
