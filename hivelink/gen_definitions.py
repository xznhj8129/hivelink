from typing import List, Dict
import csv
import json
import pprint
import os
import argparse
from pprint import pformat

def generate_enums_file(message_dict):
    
    # Generate MessageCategory enum
    category_code = "# This file is auto generated, refer to gen_definitions.py\n\nclass MessageCategory(Enum):\n"
    categories = list(message_dict.keys())
    for i, category in enumerate(categories, start=1):
        category_code += f"    {category} = {i}\n"

    # Assign values and strings to categories and subcategories
    values_code = "\n\n"
    for category in categories:
        subcategories = list(message_dict[category].keys())
        for i, subcategory in enumerate(subcategories, start=1):
            values_code += f"Messages.{category}.{subcategory}.value_subcat = {i}\n"
            values_code += f'Messages.{category}.{subcategory}.str = {subcategory!r}\n'
    for i, category in enumerate(categories, start=1):
        values_code += f"Messages.{category}.value_cat = {i}\n"
        values_code += f'Messages.{category}.str = {category!r}\n'

    # Generate Messages class with nested enums
    messages_code = "class Messages:\n"
    for category in categories:
        messages_code += f"    class {category}:\n"
        for subcategory in message_dict[category]:
            messages_code += f"        class {subcategory}(Enum):\n"
            for message in message_dict[category][subcategory]:
                messages_code += f"            {message} = auto()\n"

    # Assign payload definitions
    payload_code = ""
    for category in categories:
        for subcategory in message_dict[category]:
            for message in message_dict[category][subcategory]:
                payload = message_dict[category][subcategory][message]
                payload_code += f"Messages.{category}.{subcategory}.{message}.payload_def = {repr(payload)}\n"

    # Combine all parts
    code = "from enum import Enum, IntEnum, auto\n\n"
    code += category_code + "\n"
    code += messages_code
    code += values_code
    code += payload_code

    # Debug: Print the generated code
    #print("Generated code:")
    #print(code)
    return code
    # Write to file
    #with open("message_structure.py", "w") as f:
    #    f.write(code)

def generate_message_definitions(csvfile="message_definitions.csv", payloads="protocol/payload_enums.py", name="default",ver=1): #TODO: relative path import problem
    """Reads the CSV, builds the message dictionary, writes it to JSON, and generates enums."""
    messages = {}
    with open(csvfile, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        current_message = None
        for row in reader:
            row = {k: (v.strip() if v is not None else "") for k, v in row.items()}
            if row["Category"]:
                current_category = row["Category"]
                current_type = row["Type"] if row["Type"] else None
                current_subtype = row["Subtype"] if row["Subtype"] else None
                if current_category not in messages:
                    messages[current_category] = {}
                if current_type:
                    if current_type not in messages[current_category]:
                        messages[current_category][current_type] = {}
                if current_subtype:
                    messages[current_category][current_type][current_subtype] = []
                current_message = (current_category, current_type, current_subtype)
            else:
                if current_message is None:
                    continue
                payload_field = row["FieldName"]
                if payload_field:
                    payload_field_type = row["FieldType"]
                    payload_field_bitmask = row["FieldBitmask"]
                    payload_field_bitmask_bool = payload_field_bitmask.upper() == "TRUE"
                    payload = {
                        "name": payload_field,
                        "datatype": payload_field_type,
                        "bitmask": payload_field_bitmask_bool
                    }
                    cat, typ, sub = current_message
                    messages[cat][typ][sub].append(payload)
    
    pname = f"protocol_{name}_v{ver}"

    with open(payloads,'r') as file:
        pe = file.read()

    enumspy = generate_enums_file(messages)
    f = f'PROTOCOL_VERSION = {ver}\nPROTOCOL_NAME = "{name}"\n\n' + enumspy + '\n\n' + pe

    with open("hivelink/protocol.py", "w") as file:
        file.write(f)

    f2 = json.dumps(messages, indent=4)# + '\n\n' + 
    with open("protocol/protocol.json", "w") as file:
        file.write(f2)
    
    # Generate enums

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate message protocol definition")
    parser.add_argument("--csvfile", default="message_definitions.csv", help="Message definition file")
    parser.add_argument("--name", default="default", help="Protocol name")
    parser.add_argument("--version", default=1, help="Protocol version int")
    parser.add_argument("--out", default="message_definitions.json", help="Output JSON file")
    args = parser.parse_args()

    generate_message_definitions(csvfile=args.csvfile,name=args.name, ver=args.version)
    
    #TODO:     from .message_structure import * #leave as *
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #ImportError: attempted relative import with no known parent package
    #from msglib import MessageDefinitions
    #protodefs = MessageDefinitions()
    #print("Structure:")
    #pprint.pprint(protodefs.messages)
    
    # Test the generated enums
    from hivelink.protocol import Messages
    print("\nTesting enum values:")
    print("Status.System.FLIGHT:", Messages.Status.System.FLIGHT.value)
    print("Status.System.POSITION:", Messages.Status.System.POSITION.value)
    print("System value:", Messages.Status.System.value_subcat)