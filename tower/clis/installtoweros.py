from sh import Command

from rich.prompt import Confirm

def main():
    return Confirm.ask("Install TowerOS?")
