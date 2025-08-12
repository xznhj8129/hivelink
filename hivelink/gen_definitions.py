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

    # Generate Messages class with nested enums
    messages_code = "class Messages:\n"
    for category in categories:
        messages_code += f"    class {category}:\n"
        for subcategory in message_dict[category]:
            messages_code += f"        class {subcategory}(Enum):\n"
            for message in message_dict[category][subcategory]:
                messages_code += f"            {message} = auto()\n"

    # Assign values and strings to categories and subcategories
    values_code = "\n\n"
    for category in categories:
        subcategories = list(message_dict[category].keys())
        for i, subcategory in enumerate(subcategories, start=1):
            values_code += f"Messages.{category}.{subcategory}.value_subcat = {i}\n"
            values_code += f"Messages.{category}.{subcategory}.str = {subcategory!r}\n"
    for i, category in enumerate(categories, start=1):
        values_code += f"Messages.{category}.value_cat = {i}\n"
        values_code += f"Messages.{category}.str = {category!r}\n"

    # Assign payload definitions
    payload_code = ""
    for category in categories:
        for subcategory in message_dict[category]:
            for message in message_dict[category][subcategory]:
                payload = message_dict[category][subcategory][message]
                payload_code += f"Messages.{category}.{subcategory}.{message}.payload_def = {repr(payload)}\n"

    # NEW: static introspection so enum_member.category works without any runtime helpers
    introspection_code = "\n"
    for i, category in enumerate(categories, start=1):
        for j, subcategory in enumerate(message_dict[category].keys(), start=1):
            introspection_code += (
                f"Messages.{category}.{subcategory}.category = Messages.{category}\n"
                f"Messages.{category}.{subcategory}.category_name = {category!r}\n"
                f"Messages.{category}.{subcategory}.category_value = {i}\n"
                f"Messages.{category}.{subcategory}.subcategory_name = {subcategory!r}\n"
                f"Messages.{category}.{subcategory}.subcategory_value = {j}\n"
            )

    # Combine all parts
    code = "from enum import Enum, IntEnum, auto\n\n"
    code += category_code + "\n"
    code += messages_code
    code += values_code
    code += payload_code
    code += introspection_code

    return code


def generate_message_definitions(csvfile="message_definitions.csv", payloads="protocol/payload_enums.csv", name="default",ver=1, outfile="protocol/protocol.json"):
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

    edict, estr = gen_payload_enums(payloads=payloads)

    enumspy = generate_enums_file(messages)
    f = f'PROTOCOL_VERSION = {ver}\nPROTOCOL_NAME = "{name}"\n\n' + enumspy + '\n\n' + estr

    with open("hivelink/protocol.py", "w") as file:
        file.write(f)

    pdict = {
        "PROTOCOL_NAME": name,
        "PROTOCOL_VERSION": ver,
        "messages": messages,
        "payloads": edict
    }
    f2 = json.dumps(pdict, indent=4)# + '\n\n' + 
    with open(outfile, "w") as file:
        file.write(f2)
    
def gen_payload_enums(payloads="protocol/payload_enums.csv"): 
    """Reads the CSV, builds the message dictionary, writes it to JSON, and generates enums."""
    enum_dict = {}
    with open(payloads, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        current_message = None
        for row in reader:
            row = {k: (v.strip() if v is not None else "") for k, v in row.items()}
            #print(current_message, row)
            if row["Payload"]:
                current_message = row["Payload"]
                if current_message not in enum_dict:
                    enum_dict[current_message] = {}
            else:
                if current_message is None:
                    continue
                payload_field = row["Field"]
                if payload_field:
                    field_value = row["Value"]
                    if payload_field!="_info":
                        field_value = int(field_value)
                    enum_dict[current_message][payload_field] = field_value

    #f2 = json.dumps(enum_dict, indent=4)# + '\n\n' + 
    #with open("protocol/payload_enums.json", "w") as file:
    #    file.write(f2)

    # Generate class with nested enums
    enum_dict_code = "class PayloadEnum:\n"
    for payload in enum_dict:
        enum_dict_code += f"    class {payload}(IntEnum):\n"
        #print(payload)
        for field in enum_dict[payload]:
            #print(field, enum_dict[payload][field])
            if field!="_info":
                enum_dict_code += f"        {field} = {enum_dict[payload][field]}\n"
            else:
                enum_dict_code += f"        # {enum_dict[payload][field]}\n"
        enum_dict_code += "\n"

    #code = "from enum import Enum, IntEnum, auto\n\n"
    #code += enum_dict_code

    # Debug: Print the generated code
    #print("Generated code:")
    #print(enum_dict_code)

    return (enum_dict, enum_dict_code)
    #with open("protocol/payload_enums.py", "w") as file:
    #    file.write(code)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate message protocol definition")
    parser.add_argument("--csvfile", default="message_definitions.csv", help="Message definition file")
    parser.add_argument("--name", default="default", help="Protocol name")
    parser.add_argument("--version", default=1, help="Protocol version int")
    parser.add_argument("--out", default="protocol/protocol.json", help="Output JSON file")
    args = parser.parse_args()

    generate_message_definitions(csvfile=args.csvfile,name=args.name, ver=args.version, outfile=args.out)
    
    # Test the generated enums
    from hivelink.protocol import Messages
    print("\nTesting enum values:")
    print("Status.System.FLIGHT:", Messages.Status.System.FLIGHT.value)
    print("Status.System.POSITION:", Messages.Status.System.POSITION.value)
    print("System value:", Messages.Status.System.value_subcat)