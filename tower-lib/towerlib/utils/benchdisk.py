
#!/usr/bin/env python3

import json
import re
import subprocess # nosec B404
import sys

from rich.console import Console
from rich.table import Table

def run_cmd(cmd, to_json=False):
    out = subprocess.run(cmd, capture_output=True, encoding="UTF-8", check=False).stdout.strip() # nosec B603
    if to_json:
        return json.loads(out)
    return out

def get_disk_bench(record_size, file_size, fast=True):
    opt = "-a" if fast else "-e -I -a"
    cmd = f"sudo iozone {opt} -s {file_size} -r {record_size} -i 0 -i 1 -i 2 -R"
    benchmark = run_cmd(cmd.split(" "))
    return benchmark.split("Excel output is below:")[1].strip()

def to_mbps(value):
    return f"{int(int(value) / 1024)}Mbps"

def parse_bench(benchmark):
    lines = "_".join([
        re.sub(' +', ' ', line.strip().replace('"', ""))
        if line != '' else '_'
        for line in benchmark.split('\n')
    ]).split("___")
    lines = [line.split("_") for line in lines]
    lines = [[line[0], to_mbps(line[2].split(" ")[1])] for line in lines]
    return {line[0]: line[1] for line in lines}

def display_bench():
    record_size = sys.argv[1] if len(sys.argv) > 1 else '4k'
    file_size = sys.argv[2] if len(sys.argv) > 2 else '100M'
    slow = len(sys.argv) > 3

    values = parse_bench(get_disk_bench(record_size, file_size, not slow))

    table = Table(
        title=f"\nTest with: {record_size} record size, {file_size} file\n",
        show_header=False,
        title_style="bold magenta"
    )

    table.add_column("Title", justify="Left", style="cyan", no_wrap=True)
    table.add_column("Read", justify="right", style="green")
    table.add_column("Write", justify="right", style="green")

    table.add_row("Read / Write: ", values['Reader report'], values['Writer report'])
    table.add_row("Re-read / Re-write: ", values['Re-Reader report'], values['Re-writer report'])
    table.add_row("Random read / Random write: ", values['Random read report'], values['Random write report'])

    console = Console()
    console.print(table)

if __name__ == '__main__':
    CMD = "sudo apk --repository=http://dl-cdn.alpinelinux.org/alpine/edge/testing add python3 py3-rich iozone"
    run_cmd(CMD.split(" "))
    display_bench()
