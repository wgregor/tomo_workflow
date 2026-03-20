#! /usr/bin/env python3
import json
from argparse import ArgumentParser
from subprocess import check_output, run, CalledProcessError
import os
import re

def build_tree(parent_directory, set_nums, prefix):
    """
    builds the directory tree for a tomography data processing workflow
    :param parent_directory: the directory where the file tree is built
    :param set_nums: list of group numbers for sets of raw tilts
    :param prefix: the prefix to be used for directory creation
    :return: None
    """

    directory_paths = []

    #Check if the parent directory exists and, if not, builds it
    if not os.path.isdir(parent_directory):
        os.mkdir(parent_directory)
    if not os.path.isdir(os.path.join(parent_directory, 'eman2_process')):
        os.mkdir(os.path.join(parent_directory, 'eman2_process'))
    if not os.path.isdir(os.path.join(parent_directory, 'tomo_info')):
        os.mkdir(os.path.join(parent_directory, 'tomo_info'))
    # loops through the tilt set numbers and creates directory trees for each set of raw data to process
    for set_num in set_nums:
        sub_dir = prefix + '_' + set_num
        try:
            directory_path = os.path.join(parent_directory, sub_dir)
            os.mkdir(directory_path)
            os.mkdir(os.path.join(str(directory_path), 'raw_tif'))
            directory_paths.append(directory_path)
            print('created directory ' + str(directory_path))
        except FileExistsError:
            print('the directory ' + str(os.path.join(parent_directory, sub_dir)) + ' already exists.')
    return directory_paths

def get_set_nums(server_credentials, server_dir):
    """
    creates a list of group numbers corresponding to the sets of raw tilts
    :param server_credentials: the username and ip for connecting to the target server (username@ip)
    :param server_dir: path to the rew tilt directory on the server
    :return: a list of numbers corresponding to groups of raw tilts
    """
    try:
        files = str(check_output(['ssh', server_credentials, 'ls',
                                  '--sort=time', server_dir]))[2:-1].split('\\n')[:-1]
    except CalledProcessError:
        exit()
    set_num = []
    gain = ''
    defect = ''
    gain_defect_names = ['gain','CountRef','defect','defects']
    for file in files:
        if file.endswith('.tif'):
            file_info = re.search(r"_[0-9]+_[0-9]{5}_-*[0-9]{1,2}", file)
            file_num = file_info.group().split('_')[1]
            if not file_num in set_num:
                set_num.append(file_num)
        elif file.endswith('.mrc')  and (file.startswith('CountRef') or file.startswith('gain')):
            if gain == '':
                gain = file
            else:
                continue
        elif file.endswith('.txt') and file.startswith('defects'):
            if defect == '':
                defect = file
            else:
                continue
    if not len(set_num)==0:
        print('finished initial query\nfound: ' + str(len(set_num)) + ' groups of tilt files')
    else:
        print('not tif files found')
        exit()
    print('found gain: ' + gain +'\nfound defect: ' + defect + '\n')
    return set_num, gain, defect

def transfer_tifs(server_credentials, server_dir, set_nums, prefix, gain, defect, parent_directory):
    """
    transfers raw tif files from the server to the local machine, grouped by the set numbers
    :param server_credentials: the username and ip for connecting to the target server (username@ip)
    :param server_dir: path to the rew tilt directory on the server
    :param set_nums: list of group numbers for sets of raw tilts
    :param prefix: the prefix to be used for directory creation
    :param gain:
    :param defect:
    :param parent_directory:
    :return: None
    """
    print('\ninitiating file transfer...')
    print('\ntransferring gain and defect files')
    if not gain == '' and not defect == '':
        run(['rsync', '-au', '--info=progress2', server_credentials + ':' +
            os.path.join(server_dir, gain),
            os.path.join(parent_directory)])
        run(['rsync', '-au', '--info=progress2', server_credentials + ':' +
             os.path.join(server_dir, defect),
             os.path.join(parent_directory)])
    for set_num in set_nums:
        print('\n' + '#'*10 + '[transferring group ' + set_num + ']' + '#'*10)
        run(['rsync', '-au', '--info=progress2', server_credentials + ':' +
             os.path.join(server_dir, '*' + set_num + '*.tif*'),
             os.path.join(prefix+'_'+set_num, 'raw_tif')])

def prepare_files(parent_directory, prefix, set_nums):
    for num in set_nums:
        raw_tif_path = os.path.join(parent_directory,prefix+'_'+num,'raw_tif')
        run(['tomo_prepare_files.py', '-r', parent_directory])
        run(['tomo_prepare_files.py', '-r', raw_tif_path])
        run(['tomo_combine_mdoc.py', raw_tif_path, '-o',os.path.join(str(raw_tif_path),prefix+'_'+num+'.mdoc'),'--fix-paths'])

def main():
    parser=ArgumentParser(description='retrieves list of files in a directory and creates a new '
                                      'directory tree based on information from the file list')
    parser.add_argument('--server_credentials', '-c', 
                        help='the username and ip of the server being accessed')
    parser.add_argument('--server_dir', '-d', help='path to directory in server')
    parser.add_argument('--parent_directory', '-p', default='./', 
                        help='path to directory where directory tree will be made')
    parser.add_argument('--prefix', default='raw_tifs', 
                        help='prefix to use when naming files and directories')

    args=parser.parse_args()

    info = {}

    if args.parent_directory == './':
        args.parent_directory = os.getcwd()

    set_nums, gain, defect = get_set_nums(args.server_credentials, args.server_dir)
    #fix gain so that there are underscores instead of decimals
    info['original_gain'] = os.path.join(args.parent_directory, gain)
    info['original_defect'] = os.path.join(args.parent_directory, defect)

    directory_paths = build_tree(args.parent_directory, set_nums, args.prefix)

    info['directory_paths'] = directory_paths

    transfer_tifs(args.server_credentials, args.server_dir, set_nums, args.prefix, gain, defect, args.parent_directory)

    os.rename(info['original_gain'],os.path.join(args.parent_directory,'gain.mrc'))
    os.rename(info['original_defect'], os.path.join(args.parent_directory,'defects.txt'))

    prepare_files(args.parent_directory, args.prefix, set_nums)

    j_file = json.dumps(info, indent=4)
    with open(os.path.join(args.parent_directory,'tomo_info','info.json'), 'w') as fp:
        fp.write(j_file)

if __name__=='__main__':
    main()