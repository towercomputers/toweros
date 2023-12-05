import re

def clean_usage(usage):
    cleaned_usage = usage.replace('usage: ', '')
    cleaned_usage = cleaned_usage.replace('\n', ' ')
    return re.sub(' +', ' ', cleaned_usage)

def get_cli_help(parser):
    cli_help = {
        'name': parser.prog,
        'synopsis': clean_usage(parser.format_usage().strip()),
        'description': parser.description,
        'commands': [],
        'options': [],
    }
    commands = parser._get_positional_actions()[0].choices
    for command_name in commands:
        action = commands[command_name]
        if not action.description:
            continue
        cmd_info = {
            'name': command_name,
            'usage': clean_usage(action.format_usage().strip()),
            'help': action.description,
            'positional_arguments': [],
            'optional_arguments': [],
        }
        for arg in action._get_positional_actions():
            cmd_info['positional_arguments'].append({
                'name': arg.dest,
                'help': arg.help,
            })
        for opt in action._option_string_actions:
            class_name = str(action._option_string_actions[opt].__class__).split('._')[1].replace("'>", "")
            if class_name == 'HelpAction':
                continue
            cmd_info['optional_arguments'].append( {
                'name': opt,
                'help': action._option_string_actions[opt].help,
                'class': str(action._option_string_actions[opt].__class__).split('._')[1].replace("'>", ""),
            })
        cli_help['commands'].append(cmd_info)
    options = parser._option_string_actions
    for opt in options:
        class_name = str(options[opt].__class__).split('._')[1].replace("'>", "")
        if class_name == 'HelpAction':
            continue
        cli_help['options'].append({
            'name': opt,
            'help': options[opt].help,
            'class': str(options[opt].__class__).split('._')[1].replace("'>", ""),
        })
    return cli_help

def md_div(text):
    return f'<div style="margin:0 50px">{text}</div>'

def md_div_courrier(text):
    return f'<div style="margin:0 50px; font-family:Courier">{text}</div>'

def gen_md_help(parser):
    cli_help = get_cli_help(parser)
    md = []
    open_div = '<div style="margin:0 50px">'
    close_div = '</div>'
    md.append('<!--Do not edit manually. Generated with `[tower-cli]$ hatch run tower mdhelp > ../docs/src/manual.md`.-->')
    # global information
    md.append('## NAME')
    md.append(md_div(cli_help['name']))
    md.append('## SYNOPSIS')
    md.append(md_div_courrier(cli_help['synopsis']))
    md.append('## DESCRIPTION')
    md.append(md_div(cli_help['description']))
    # commands list
    md.append('## COMMANDS')
    md.append(open_div)
    for cmd in cli_help['commands']:
        md.append(f'<b>tower</b> <u><a href="#tower-{cmd["name"]}">{cmd["name"]}</a></u><br />{md_div(cmd["help"])}<br />')
    md.append(close_div)
    # commands details
    for cmd in cli_help['commands']:
        # command name
        md.append(f"### `tower {cmd['name']}`")
        # usage
        md.append(md_div_courrier(f"usage: {cmd['usage']}"))
        # required arguments
        if len(cmd['positional_arguments']) > 0:
            md.append(f'{open_div}<br />')
            for pos_arg in cmd['positional_arguments']:
                md.append(f'<b>{pos_arg["name"]}</b><br />{md_div(pos_arg["help"])}<br />')
            md.append(close_div)
        # optional flags
        if len(cmd['optional_arguments']) > 0:
            md.append(f"Options:")
            md.append(open_div)
            for opt in cmd['optional_arguments']:
                md.append(f"<b>{opt['name']}</b><br />{md_div(opt['help'])}<br />")
            md.append(close_div)
    # global options
    md.append('## OPTIONS')
    md.append(open_div)
    for opt in cli_help['options']:
        md.append(f"<b>{opt['name']}</b><br />{md_div(opt['help'])}<br />")
    md.append(close_div)
    return "\n".join(md)
