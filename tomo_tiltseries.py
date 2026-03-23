#! /usr/bin/env python3

from argparse import ArgumentParser
from subprocess import run
import os
import json

def main():
    parser = ArgumentParser(description='prepares unaligned tiltseries for all sets of tilt images')
    parser.add_argument('--apix', default=1.37, help='pixel spacing for raw tifs')
    parser.add_argument('--flip_gain', default=2, type=int,
                        help='how to flip the gain file. 0=none 1=flip-x 2=flip-y')
    parser.add_argument('--gain', default='gain.mrc', help='path to the gain file')
    parser.add_argument('--defects', default='defects.txt', help='path to the defect file')

    args=parser.parse_args()

    with open('./tomo_info/info.json', 'r') as j_file:
        info_dict = json.load(j_file)
    directories = info_dict['directory_paths']
    parent_directory = info_dict['parent_directory']

    gain = os.path.join(parent_directory, 'gain.mrc')
    if not os.path.isfile(gain):
        print('invalid gain file provided')
        exit()
    defect = os.path.join(parent_directory, 'defects.txt')
    if not os.path.isfile(defect):
        print('invalid defect file provided')
        exit()
    for directory in directories:
        base_name = directory.split('/')[-1]
        raw_tif_path = os.path.join(directory, 'raw_tif')
        mdoc_path = os.path.join(raw_tif_path, base_name + '.mdoc')
        run(['e2ddd_external.py', raw_tif_path, '--program=ucsf_motioncor2', '--device=gpu', '--mdoc=' + mdoc_path,
             '--apix=' + str(args.apix), '--gain=' + args.gain, '--defect_file=' + args.defects, '--mc2_rotgain=0',
             '--mc2_flipgain='+str(args.flip_gain), '--imod_rotflipgain=0', '--device_num=0', '--tomo'])
    print('process complete')
if __name__=='__main__':
    main()