#!/usr/bin/env python3

import sys
import subprocess

from rich import print as rprint
from rich.text import Text
from rich.console import Console


def main():
    Console().clear()
    title = subprocess.run(
        ['figlet', '-w', '160', 'TowerOS-ThinClient'],
        capture_output=True, encoding="UTF-8"
    ).stdout
    print(title)
    print("\n")
    rprint(Text("Congratulations, toweros is correctly installed!", style="green bold"))
    print("\n")
    rprint(Text("Make sure to remove the drive that contains the installation image, then press Enter to reboot.", style="purple bold"))
    input()

if __name__ == '__main__':
    sys.exit(main())
