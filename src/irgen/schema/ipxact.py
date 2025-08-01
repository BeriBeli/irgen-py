from pydantic_xml import BaseXmlModel, attr, element


IEEE1685_2014_NS = "http://www.accellera.org/XMLSchema/IPXACT/1685-2014"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = "http://www.accellera.org/XMLSchema/IPXACT/1685-2014 http://www.accellera.org/XMLSchema/IPXACT/1685-2014/index.xsd"


class ResetType(BaseXmlModel):
    value: str = element(tag="ipxact:value")


class ResetsType(BaseXmlModel):
    reset: list[ResetType] = element(tag="ipxact:reset")


class FieldType(BaseXmlModel):
    name: str = element(tag="ipxact:name")
    description: str | None = element("ipxact:description", default=None)
    bit_offset: str = element(tag="ipxact:bitOffset")
    bit_width: str = element(tag="ipxact:bitWidth")
    access: str = element(tag="ipxact:access")
    modified_write_value: str | None = element(tag="ipxact:modifiedWriteValue", default=None)
    read_action: str | None = element(tag="ipxact:readAction", default=None)
    resets: ResetsType = element(tag="ipxact:resets")


class RegisterType(BaseXmlModel):
    name: str = element(tag="ipxact:name")
    description: str | None = element(tag="ipxact:description", default=None)
    address_offset: str = element(tag="ipxact:addressOffset")
    size: str = element(tag="ipxact:size")
    field: list[FieldType] = element(tag="ipxact:field")


class BlockType(BaseXmlModel):
    name: str = element(tag="ipxact:name")
    description: str | None = element(tag="ipxact:description", default=None)
    base_address: str = element(tag="ipxact:baseAddress")
    range: str = element(tag="ipxact:range")
    width: str = element(tag="ipxact:width")
    register: list[RegisterType] = element(tag="ipxact:register")


class MemoryMapType(BaseXmlModel):
    name: str = element(tag="ipxact:name")
    address_block: list[BlockType] = element(tag="ipxact:addressBlock")


class MemoryMapsType(BaseXmlModel):
    memory_map: list[MemoryMapType] = element(tag="ipxact:memoryMap")


class ComponentType(BaseXmlModel, tag="ipxact:component"):
    xmlns_ipxact: str = attr(name="xmlns:ipxact", default=IEEE1685_2014_NS)
    xmlns_xsi: str = attr(name="xmlns:xsi", default=XSI_NS)
    schema_location: str = attr(name="xsi:schemaLocation", default=SCHEMA_LOCATION)
    vendor: str = element(tag="ipxact:vendor")
    library: str = element(tag="ipxact:library")
    name: str = element(tag="ipxact:name")
    version: str = element(tag="ipxact:version")
    memory_maps: MemoryMapsType | None = element(tag="ipxact:memoryMaps")