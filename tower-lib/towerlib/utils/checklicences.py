#!/usr/bin/env python3

import os
import subprocess
import tomllib
import json

from sh import license_scanner

def scan_licenses():
    cwd = os.path.join(os.getcwd(), 'tower-lib')
    licenses_str = license_scanner(_cwd=cwd).strip()
    licenses = {}
    current_license = None
    for line in licenses_str.split('\n'):
        if line.strip().startswith('=====') or line == "":
            continue
        if line.startswith(' - ') and current_license:
           licenses[current_license].append(line[3:])
           continue
        current_license = line.strip()
        licenses[current_license] = []
    return licenses

def get_allowed():
    pyproject_path = os.path.join(os.getcwd(), 'tower-lib', "pyproject.toml")
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    allowed_licenses = data['tool']['license_scanner']['allowed-licences']
    allowed_packages = data['tool']['license_scanner']['allowed-packages']
    return allowed_licenses, allowed_packages

def generate_sarif(not_allowed_packages):
    results = []
    for license in not_allowed_packages:
        for package in not_allowed_packages[license]:
            results.append({
                "level": "error",
                "message": {
                    "text": f"Package {package} has license {license} which is not allowed"
                },
                "ruleId": "not-allowed-license",
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": f"https://pypi.org/project/{package}/"
                            }
                        }
                    }
                ]
            })
    sarif = {
        "version": "2.1.0",
        "$schema": "http://json.schemastore.org/sarif-2.1.0-rtm.4",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "license-scanner",
                        "notifications": [],
                        "rules": [
                            {
                                "id": "not-allowed-license",
                                "shortDescription": {
                                    "text": "License is not allowed"
                                },
                            }
                        ]
                    }
                },
                "results": results
            }
        ]
    }
    with open("license_scanner.sarif", "w") as outfile:
        outfile.write(json.dumps(sarif, indent=4))


def check_licenses():
    # Run the license scanner
    used_packages = scan_licenses()
    used_licenses = list(used_packages.keys())
    allowed_licenses, allowed_packages = get_allowed()
    not_allowed_packages = {}
    for license in used_licenses:
        if license not in allowed_licenses:
            for package in used_packages[license]:
                if package not in allowed_packages:
                    if license not in not_allowed_packages:
                        not_allowed_packages[license] = []
                    not_allowed_packages[license].append(package)
    generate_sarif(not_allowed_packages)
    

if __name__ == '__main__':
    check_licenses()
