#! /usr/bin/env python3

import os
from argparse import ArgumentParser

def replace_decimal(dir_path, verbose):
    """
    Replaces the tilt angle decimal in the file names with an underscore
    :param dir_path: Description
    :param quiet: whether to suppress the output of the command
    """
    for file in os.listdir(dir_path):
        if file.endswith('.tif') or file.endswith('.tif.mdoc') or file.endswith('.mrc') or file.endswith('.txt'):
            tmp_file = file.split('.')
            if tmp_file[1] == '0':
                corrected_file = '_'.join(tmp_file[0:2]) + '.' + '.'.join(tmp_file[2:])
                if verbose:
                    print(os.path.join(dir_path, file) + " -> " + os.path.join(dir_path, corrected_file))
                os.rename(os.path.join(dir_path, file), os.path.join(dir_path, corrected_file))
            else:
                print("no file names in need of correction were found")
                break
    print('file name modification completed')


def main():
    parser = ArgumentParser(description="Removes decimals from tilt angle in raw tif tomo file names")
    parser.add_argument('--raw_tif_dir', '-r', required=True, help='Absolute path to raw tif directory')
    parser.add_argument('--verbose', '-v', action='store_true', help='suppress output from the command')

    args = parser.parse_args()

    print("modifying file names...")
    replace_decimal(args.raw_tif_dir, args.verbose)

if __name__ == "__main__":
    main()