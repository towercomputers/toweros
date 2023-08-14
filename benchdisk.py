
#!/usr/bin/env python3

import json
import re
import subprocess

from rich.console import Console
from rich.table import Table


def run_cmd(cmd, to_json=False):
    out = subprocess.run(cmd, capture_output=True, encoding="UTF-8").stdout.strip()
    if to_json:
        return json.loads(out)
    return out

def get_disk_bench():
    cmd = "iozone -e -I -a -s 100M -r 4k -i 0 -i 1 -i 2 -R"
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

def display_bench(values): 
    table = Table(
        title="\nTest with 100M file and 4k record size\n", 
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

display_bench(parse_bench(get_disk_bench()))