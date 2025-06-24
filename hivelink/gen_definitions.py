from typing import List, Dict
import csv
import json
import pprint
import os

def generate_enums_file(message_dict):
    # Remove old file to ensure fresh generation
    if os.path.exists("message_structure.py"):
        os.remove("message_structure.py")
    
    # Generate MessageCategory enum
    category_code = "# This file is auto generated, refer to definitions.py\n\nclass MessageCategory(Enum):\n"
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
    code = "from enum import Enum, auto\n\n"
    code += category_code + "\n"
    code += messages_code
    code += values_code
    code += payload_code

    # Debug: Print the generated code
    print("Generated code:")
    print(code)

    # Write to file
    with open("message_structure.py", "w") as f:
        f.write(code)

def generate_message_definitions():
    """Reads the CSV, builds the message dictionary, writes it to JSON, and generates enums."""
    messages = {}
    with open("message_definitions.csv", newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
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
    
    # Remove old JSON and write new
    if os.path.exists("message_definitions.json"):
        os.remove("message_definitions.json")
    with open("message_definitions.json", "w") as file:
        file.write(json.dumps(messages, indent=4))
    
    # Generate enums
    generate_enums_file(messages)

if __name__ == '__main__':
    generate_message_definitions()
    from protocol import MessageDefinitions
    protodefs = MessageDefinitions()
    print("Structure:")
    pprint.pprint(protodefs.messages)
    
    # Test the generated enums
    from message_structure import Messages
    print("\nTesting enum values:")
    print("Status.System.FLIGHT:", Messages.Status.System.FLIGHT.value)
    print("Status.System.POSITION:", Messages.Status.System.POSITION.value)
    print("System value:", Messages.Status.System.value_subcat)