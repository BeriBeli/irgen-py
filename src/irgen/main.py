import sys
import logging
import argparse
from pathlib import Path

import polars as pl
import fastexcel

from .__version__ import __version__
from .parser import (
    process_vendor_sheet,
    process_address_map_sheet,
    process_register_sheet,
)
from .template import generate_template
from .config import (
    DEBUG,
    LOG_FILE,
    DEFAULT_VENDOR_SHEET,
    DEFAULT_ADDRESS_SHEET,
)
from .schema.ipxact import (
    MemoryMapsType,
    MemoryMapType,
    BlockType,
    RegisterType
)


def setup_logger_level(debug: bool):
    """Configures logging based on the debug flag."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(levelname)s - %(filename)s - %(lineno)d] %(message)s",
        filename=LOG_FILE if debug else None,
        filemode="w",
    )


def setup_arg_parser() -> argparse.ArgumentParser:
    """Set up and return the argument parser."""
    parser = argparse.ArgumentParser(
        description="Convert spreadsheets register maps to IP-XACT XML files."
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Version",
    )
    parser.add_argument(
        "-d",
        "--debug",
        default=DEBUG,
        action="store_true",
        help="Enable debug logging.",
    )
    parser.add_argument(
        "-t",
        "--template",
        action="store_true",
        help="Generate a template excel for an example.",
    )
    parser.add_argument(
        "-i",
        "--input",
        help="Path to the input excel file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Path for the output XML file.",
    )
    parser.add_argument(
        "--vendor-sheet",
        default=DEFAULT_VENDOR_SHEET,
        help="Name of the vendor sheet.",
    )
    parser.add_argument(
        "--address-sheet",
        default=DEFAULT_ADDRESS_SHEET,
        help="Name of the address map sheet.",
    )
    return parser


def process_args() -> argparse.Namespace:
    parser = setup_arg_parser()
    args = parser.parse_args()

    setup_logger_level(args.debug)

    if args.version:
        print(__version__)
        sys.exit(0)

    if args.template:
        try:
            generate_template()
        except Exception as e:
            logging.error(f"Failed to generate template: {e}")
        sys.exit(0)

    if not args.input:
        parser.error(
            "the --excel argument is REQUIRED in this context.\n"
            "Hint: Use -t or --template to generate an example Excel file."
        )

    if not args.output:
        args.output = f"{Path(args.input).stem}.xml"

    return args


def get_sheet_names(excel_name: str) -> list[str]:
    try:
        sheet_names = fastexcel.read_excel(excel_name).sheet_names
    except (fastexcel.FastExcelError, FileNotFoundError) as e:
        logging.critical(f"Could not read Excel file '{excel_name}': {e}")
        sys.exit(1)
    return sheet_names


def main():
    args = process_args()

    excel_name = str(args.input)
    xml_path = str(f"{Path(args.input).stem}.xml")
    vendor_sheet = str(args.vendor_sheet)
    address_sheet = str(args.address_sheet)

    sheet_names = get_sheet_names(excel_name)

    try:
        component = None
        address_blocks: list[BlockType] = []
        all_registers: dict[str, list[RegisterType]] = {}

        logging.info(f"Processing sheets: {sheet_names}")

        for sheet_name in sheet_names:

            logging.info(f"--- Reading sheet: {sheet_name} ---")

            df = pl.read_excel(excel_name, sheet_name=sheet_name)

            if sheet_name == vendor_sheet:
                component = process_vendor_sheet(df)
            elif sheet_name == address_sheet:
                address_blocks = process_address_map_sheet(df)
            else:
                all_registers[sheet_name] = process_register_sheet(df)

        if not component:
            logging.critical("Failed to parse vendor information. Aborting.")
            sys.exit(1)
        if not address_blocks:
            logging.critical("Failed to parse address blocks. Aborting.")
            sys.exit(1)

        # Assemble the final component data structure
        logging.info("Assembling final component structure...")
        for block in address_blocks:
            if block.name in all_registers:
                for reg in all_registers[block.name]:
                    block.registers.append(reg)
                logging.info(
                    f"Mapped {len(block.registers)} registers to address block "
                    f"'{block.name}'."
                )
            else:
                logging.warning(
                    f"No register block sheet found for address block "
                    f"'{block.name}'."
                )

        memory_map = MemoryMapType(
            name=component.name,
            address_block=[],
        )
        for block in address_blocks:
            memory_map.address_block.append(block)
        memory_maps = MemoryMapsType(
            memory_map=[]
        )
        memory_maps.memory_map.append(memory_map)
        component.memory_maps = memory_maps

        logging.info(f"XML file will be generated at: {xml_path}")

        with open(xml_path, "wb") as f:
            component_xml = component.to_xml(exclude_none=True)
            if isinstance(component_xml, bytes):
                f.write(component_xml)
            else:
                f.write(component_xml.encode())

    except Exception as e:
        logging.critical(f"An error occurred during processing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
