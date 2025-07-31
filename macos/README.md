# Brave Manager on macOS

## Installation

Download [this repository's Zip file](https://github.com/brave/brave-manager/archive/refs/heads/main.zip)
and unpack it. Let's say this gives you the folder `brave-manager` in your home
directory.

Open a Terminal window and execute the following command:

```
python3 ~/brave-manager/macos/install.py
```

## Usage

After installation, you should be able to launch Brave Manager by typing the
following command into a Terminal window:

```
bm
```

## Development

To run tests, execute the following in this directory:

```
python3 -m unittest
```

To update the Zip file of historic releases that's included in this repository,
follow the instructions in `update_historic_releases.py`.
