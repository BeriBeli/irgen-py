import logging

import polars as pl

from .attribute import (
    get_access_value,
    get_modified_write_value,
    get_read_action_value,
)
from .schema.ipxact import (
    ComponentType,
    BlockType,
    RegisterType,
    FieldType,
    ResetsType,
    ResetType
)


def parse_dataframe(df: pl.DataFrame) -> pl.DataFrame:
    try:
        parsed_df = (
            df.with_columns(
                REG_WIDTH = pl.col("WIDTH").cast(pl.Int32).sum().over("ADDR"),
                BYTES = (pl.col("WIDTH").cast(pl.Int32).sum().over("ADDR") // 8),
                BASE_REG = pl.coalesce(
                    pl.col("REG").first().over("ADDR").str.extract(r"(.*?)\{n\}"), pl.lit("")
                ),
                IS_EXPANDABLE = pl.col("REG").first().over("ADDR").str.contains(r"\{n\}"),
                START = pl.col("REG").first().over("ADDR").str.extract(r"n\s*=\s*(\d+)").cast(pl.Int32),
                END = pl.col("REG").first().over("ADDR").str.extract(r"~\s*(\d+)").cast(pl.Int32),
                BASE_ADDR = pl.col("ADDR").first().over("ADDR").str.extract("0x([0-9a-fA-F]+)").str.to_integer(base=16, strict=False),
                BIT_OFFSET = pl.col("BIT").over("ADDR").str.extract(r"\[(?:\d+:)?(\d+)]"),
            )
            .with_columns(
                N_SERIES=pl.when(
                    pl.col("IS_EXPANDABLE")
                    & pl.col("START").is_not_null()
                    & pl.col("END").is_not_null()
                )
                .then(pl.int_ranges(pl.col("START"), pl.col("END") + 1))
                .otherwise(pl.lit(None))
            )
            .explode("N_SERIES")
            .filter(
                (pl.col("IS_EXPANDABLE") & pl.col("N_SERIES").is_not_null())
                | (
                    ~pl.col("IS_EXPANDABLE")
                    & pl.col("FIELD").is_not_null()
                    & (pl.col("FIELD") != "")
                )
            )
            .with_columns(
                ADDR=pl.when(pl.col("IS_EXPANDABLE"))
                .then(
                    (
                        pl.col("BASE_ADDR") + pl.col("N_SERIES") * pl.col("BYTES")
                    ).map_elements(lambda x: f"0x{x:X}", return_dtype=pl.String)
                )
                .otherwise(pl.col("ADDR")),
                REG=pl.when(pl.col("IS_EXPANDABLE"))
                .then(pl.col("BASE_REG") + "_" + pl.col("N_SERIES").cast(pl.String))
                .otherwise(pl.col("REG")),
            )
            .filter(
                ~pl.col("FIELD")
                .str
                .contains(r"^(rsvd|reserved)\d*$")
            )
        )
    except pl.exceptions.PolarsError as e:
        logging.error(f"Failed to process register sheet: {e}")
        raise

    return parsed_df


def process_vendor_sheet(df: pl.DataFrame) -> ComponentType:
    """Process the Sheet<vendor> to create an IP-XACT Component object"""
    try:
        component = ComponentType(
            vendor = df["VENDOR"][0],
            library = df["LIBRARY"][0],
            name = df["NAME"][0],
            version = df["VERSION"][0],
            memory_maps=None,
        )
        return component
    except (pl.exceptions.PolarsError, ValueError, KeyError) as e:
        logging.error(f"Failed to process the Sheet<vendor>: {e}")
        raise
    except Exception as e:
        logging.error(
            f"An unexpected error occurred while processing the Sheet<vendor>: {e}"
        )
        raise


def process_address_map_sheet(
    df: pl.DataFrame
) -> list[BlockType]:
    """Process the Sheet<address_map> to create a list of IP-XACT AddressBlock objects."""

    address_blocks = []
    for row in df.iter_rows(named=True):
        try:
            address_block = BlockType(
                name = str(row["BLOCK"]),
                base_address = str(row["OFFSET"]),
                range = str(row["RANGE"]),
                width = "32",
                registers=[],
            )

            address_blocks.append(address_block)
        except KeyError as e:
            logging.error(
                f"Missing expected column in address_map sheet: {e}. Skipping row: {row}"
            )
            raise
    return address_blocks


def process_register_sheet(
    df: pl.DataFrame
) -> list[RegisterType]:
    """Process a single register block sheet into a list of Register objects."""

    try:
        # Pre-process the dataframe
        filled_df = df.select(pl.all().forward_fill())
        logging.debug(f"filled_df is {filled_df}")
        parsed_df = parse_dataframe(filled_df)
        logging.debug(f"parsed_df is {parsed_df}")
    except pl.exceptions.PolarsError as e:
        logging.error(f"Polars error during pre-processing of a register sheet: {e}")
        raise

    registers = []
    # Group by register to process all its fields together
    for reg_name, group in parsed_df.group_by("REG", maintain_order=True):
        if not reg_name:
            logging.warning("Skipping rows with no register name.")
            continue

        fields: list[FieldType] = []
        first_row = group.row(0, named=True)

        for field_row in group.iter_rows(named=True):
            try:

                field = FieldType(
                    bit_offset=str(field_row["BIT_OFFSET"]),
                    bit_width=str(field_row["WIDTH"]),
                    name=str(field_row["FIELD"]),
                    access=get_access_value(str(field_row["ATTRIBUTE"])),
                    modified_write_value=get_modified_write_value(str(field_row["ATTRIBUTE"])),
                    read_action=get_read_action_value(str(field_row["ATTRIBUTE"])),
                    resets=ResetsType(reset = [
                        ResetType(
                            value=str(field_row["DEFAULT"])
                        )
                    ]),
                )

                fields.append(field)

            except (KeyError, ValueError, TypeError) as e:
                logging.error(
                    f"Skipping invalid field '{field_row.get('FIELD', 'N/A')}' in register '{reg_name[0]}': {e}"
                )
                raise

        if fields:
            register = RegisterType(
                address_offset = str(first_row["ADDR"]),
                size = str(first_row["REG_WIDTH"]),
                name = str(reg_name[0]),
                field = fields,
            )
            registers.append(register)
    return registers
