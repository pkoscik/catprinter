import asyncio
import contextlib
import sys
import uuid
from typing import Optional, Generator

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends.bluezdbus.client import BleakClientBlueZDBus

from catprinter import logger
from catprinter.cmds import cmds_print_img, prepare, finish
from catprinter.img import text_to_image

POSSIBLE_SERVICE_UUIDS = [
    "0000ae30-0000-1000-8000-00805f9b34fb",
    "0000af30-0000-1000-8000-00805f9b34fb",
]

TX_CHARACTERISTIC_UUID = "0000ae01-0000-1000-8000-00805f9b34fb"
SCAN_TIMEOUT_S = 10
WAIT_AFTER_EACH_CHUNK_S = 0.02



async def scan(name: Optional[str], timeout: int) -> BLEDevice:
    """Scan for a printer by name or UUID."""
    autodiscover = not name
    msg = "⏳ Auto-discovering printer..." if autodiscover else f"⏳ Searching for {name}..."
    logger.info(msg)

    def matches(device: BLEDevice, adv: AdvertisementData) -> bool:
        if autodiscover:
            return any(uuid in adv.service_uuids for uuid in POSSIBLE_SERVICE_UUIDS)
        return device.name == name

    device = await BleakScanner.find_device_by_filter(matches, timeout=timeout)
    if not device:
        raise RuntimeError("Printer not found. Ensure it is powered on and nearby.")

    logger.info(f"✅ Found printer: {device}")
    return device


async def get_device_address(device: Optional[str]) -> str:
    """Return BLE address or scan if needed."""
    if device:
        with contextlib.suppress(ValueError):
            return str(uuid.UUID(device))
        if device.count(":") == 5 and device.replace(":", "").isalnum():
            return device

    return await scan(device, timeout=SCAN_TIMEOUT_S)


def chunkify(data: bytes, size: int) -> Generator[bytes, None, None]:
    for i in range(0, len(data), size):
        yield data[i:i + size]


def get_input_lines() -> Generator[str, None, None]:
    """Yield input lines either from stdin or user typing."""
    if not sys.stdin.isatty():
        for line in sys.stdin:
            yield line.rstrip("\n")
        return

    print("Enter text (type 'exit' or 'quit' to stop):")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit"):
            break
        yield line


# --- Main BLE Loop ------------------------------------------------------------

async def run_ble(device: Optional[str]):
    try:
        address = await get_device_address(device)
    except RuntimeError as e:
        logger.error(f"🛑 {e}")
        return

    logger.info(f"⏳ Connecting to {address}...")
    async with BleakClient(address) as client:
        if isinstance(client, BleakClientBlueZDBus):
            await client._acquire_mtu()

        logger.info(f"✅ Connected. MTU: {client.mtu_size}")
        chunk_size = client.mtu_size - 3

        await client.write_gatt_char(TX_CHARACTERISTIC_UUID, prepare())

        for text in get_input_lines():
            if not text:
                continue

            bin_img = text_to_image(text)

            piped = not sys.stdin.isatty()
            data = cmds_print_img(bin_img, skip_flush=piped)

            logger.debug(f"🖨️ Printing {len(data)} bytes ({bin_img.shape[1]}x{bin_img.shape[0]} pixels)")

            for chunk in chunkify(data, chunk_size):
                await client.write_gatt_char(TX_CHARACTERISTIC_UUID, chunk)
                await asyncio.sleep(WAIT_AFTER_EACH_CHUNK_S)

        await client.write_gatt_char(TX_CHARACTERISTIC_UUID, finish())
                
        logger.info("✅ Done printing.")
