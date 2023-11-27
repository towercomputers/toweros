#!/usr/bin/env python3

import os

XDG_CATEGORIES = {
    'Development': 'Development',
    'Education': 'Education',
    'Game': 'Games',
    'Graphics': 'Graphics',
    'Internet': 'Internet',
    'Settings': 'Settings',
    'Screensaver': 'Settings',
    'System': 'System',
    'Emulator': 'System',
    'Network': 'Internet',
    'AudioVideo': 'Multimedia',
    'Audio': 'Multimedia',
    'Video': 'Multimedia',
    'Utility': 'Accessories',
    'Accessibility': 'Accessories',
    'Core': 'Accessories',
    'Office': 'Office'
}

APPLICATIONS_DIRS = [
    '/usr/share/applications/',
    '/usr/local/share/applications/',
    os.path.expanduser('~/.local/share/applications/')
]

def get_desktop_files():
    desktop_files = []
    for app_dir in APPLICATIONS_DIRS:
        for root, _, files in os.walk(app_dir):
            for file in files:
                if file.endswith(".desktop"):
                    desktop_files.append(os.path.join(root, file))
    return desktop_files

def clean_exec(desktop_file_info):
    if 'Exec' not in desktop_file_info:
        desktop_file_info['Exec'] = ''
        return desktop_file_info
    desktop_file_info['Icon'] = desktop_file_info.get('Icon', '')   
    exec_line = desktop_file_info['Exec']
    exec_line = exec_line.replace(' %f', '')
    exec_line = exec_line.replace(' %F', '')
    exec_line = exec_line.replace(' %u', '')
    exec_line = exec_line.replace(' %U', '')
    exec_line = exec_line.replace(' %c', f" {desktop_file_info['Name']}")
    exec_line = exec_line.replace( '%k', f" {desktop_file_info['Filename']}")
    exec_line = exec_line.replace(' %i', f" {desktop_file_info['Icon']}")
    desktop_file_info['Exec'] = exec_line
    return desktop_file_info

def clean_categories(desktop_file_info):
    if 'Categories' not in desktop_file_info:
        desktop_file_info["InHost"] = False
        desktop_file_info['Categories'] = 'Other'
        return desktop_file_info
    categories = desktop_file_info['Categories'].split(';')
    if categories[0].startswith('X-tower-'):
        desktop_file_info["InHost"] = True
        desktop_file_info['Categories'] = categories[0][8:].capitalize()
    else:
        desktop_file_info["InHost"] = False
        categories = [XDG_CATEGORIES[category] for category in categories if category in XDG_CATEGORIES]
        desktop_file_info['Categories'] = categories[0] if len(categories) > 0 else "Other"
    return desktop_file_info

def get_desktop_file_info(desktop_file):
    fields = ['Categories', 'Name', 'Icon', 'Exec', 'NoDisplay', 'Color']
    desktop_file_info = {
        "Filename": desktop_file,
    }
    with open(desktop_file, 'r', encoding="UTF-8") as fp:
        for line in fp.readlines():
            if '=' in line:
                key, value = line.split('=', 1)
                if key in fields and key not in desktop_file_info:
                    desktop_file_info[key] = value.strip()
    return clean_categories(clean_exec(desktop_file_info))

def get_desktop_applications():
    desktop_applications = []
    for desktop_file in get_desktop_files():
        desktop_file_info = get_desktop_file_info(desktop_file)
        if 'Name' not in desktop_file_info or 'Exec' not in desktop_file_info:
            continue
        if 'NoDisplay' in desktop_file_info and desktop_file_info['NoDisplay'].lower() == 'true':
            continue
        desktop_applications.append(desktop_file_info)
    return desktop_applications

def generate_menu_group(desktop_applications):
    menu = []
    categories = []
    color_by_category = {}
    desktop_applications.sort(key=lambda x: x['Name'])
    for desktop_file_info in desktop_applications:
        if desktop_file_info['Categories'] not in categories:
            categories.append(desktop_file_info['Categories'])
            if 'Color' in desktop_file_info and desktop_file_info['Categories'] not in color_by_category:
                color_by_category[desktop_file_info['Categories']] = desktop_file_info['Color']

    categories.sort()
    for category in categories:
        menu.append(f"MenuClear('Menugen_{category}')")
    for category in categories:
        if category in color_by_category:
            sub_icon = f"circle-{color_by_category[category].replace(' ', '-').lower()}"
        elif category.lower() == 'settings':
            sub_icon = "preferences-system"
        else:
            sub_icon = f"applications-{category.lower()}"
        menu.append(f"Menu('Menugen_Applications') {{ SubMenu('{category}%{sub_icon}', 'Menugen_{category}') }}")
    for desktop_file_info in desktop_applications:
        menu.append(f"Menu('Menugen_{desktop_file_info['Categories']}') {{ Item('{desktop_file_info['Name']}%{desktop_file_info['Icon']}',Exec '{desktop_file_info['Exec']}') }}")
    return menu

def generate_menu():
    desktop_applications = get_desktop_applications()
    menu = ["MenuClear('Menugen_Applications')"]
    in_host_apps = [info for info in desktop_applications if info["InHost"]]
    if len(in_host_apps) > 0:
        menu += generate_menu_group(in_host_apps)
        menu += ["Menu('Menugen_Applications') { Separator }"]
    no_in_host_apps = [info for info in desktop_applications if not info["InHost"]]
    menu += generate_menu_group(no_in_host_apps)
    menu += ["Menu('Menugen_Applications') { Separator }"]
    menu += ["Menu('Menugen_Applications') { Item('Exit',Exec 'labwc --exit') }"]
    menu += ["Menu('Menugen_Applications') { Item('Poweroff',Exec 'poweroff') }"]
    return "\n".join(menu)

if __name__ == '__main__':
    print(generate_menu())
