#! /usr/bin/env python3

import os
from argparse import ArgumentParser

def replace_decimal(dir_path):
    """
    Replaces the tilt angle decimal in the file names with an underscore
    :param dir_path: Description
    """
    for file in os.listdir(dir_path):
        if file.endswith('.tif') or file.endswith('.tif.mdoc'):
            tmp_file = file.split('.')
            if tmp_file[1] == '0':
                corrected_file = '_'.join(tmp_file[0:2]) + '.' + '.'.join(tmp_file[2:])
                print(os.path.join(dir_path, file) + " -> " + os.path.join(dir_path, corrected_file))
                os.rename(os.path.join(dir_path, file), os.path.join(dir_path, corrected_file))
            else:
                print("no file names in need of correction were found")
                break


def main():
    parser = ArgumentParser(description="Removes decimals from tilt angle in raw tif tomo file names")
    parser.add_argument('--raw_tif_dir', '-r', required=True, help='Absolute path to raw tif directory')

    args = parser.parse_args()

    replace_decimal(args.raw_tif_dir)

if __name__ == "__main__":
    main()