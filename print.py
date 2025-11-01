#!/usr/bin/env python
import argparse
import asyncio
import logging
import sys

from catprinter import logger
from catprinter.ble import run_ble


def parse_args():
    args = argparse.ArgumentParser(
        description='prints an image on your cat thermal printer')
    args.add_argument('-l', '--log-level', type=str,
                      choices=['debug', 'info', 'warn', 'error'], default='info')
    args.add_argument('-d', '--device', type=str, default='',
                      help=(
                          'The printer\'s Bluetooth Low Energy (BLE) address '
                          '(MAC address on Linux; UUID on macOS) '
                          'or advertisement name (e.g.: "GT01", "GB02", "GB03"). '
                          'If omitted, the the script will try to auto discover '
                          'the printer based on its advertised BLE services.'
                      ))
    return args.parse_args()


def configure_logger(log_level):
    logger.setLevel(log_level)
    h = logging.StreamHandler(sys.stdout)
    h.setLevel(log_level)
    logger.addHandler(h)


def main():
    args = parse_args()

    log_level = getattr(logging, args.log_level.upper())
    configure_logger(log_level)

    # Try to autodiscover a printer if --device is not specified.
    asyncio.run(run_ble(device=args.device))


if __name__ == '__main__':
    main()
