#!/usr/bin/env python3
"""
merge_mdocs.py

Merge individual per-tilt .tif.mdoc files (from SerialEM) into a single
tilt-series .mdoc file compatible with EMAN2's e2ddd_external.py.

Usage:
    python merge_mdocs.py /path/to/raw_tiff/ -o output_tiltseries.mdoc

The script will:
  1. Find all *.tif.mdoc files in the specified directory
  2. Parse each one for tilt angle and metadata
  3. Sort by tilt angle
  4. Write a combined mdoc with sequential [ZValue = N] sections

Author: Generated for cryo-ET processing workflow
"""

import os
import re
import glob
import argparse
from pathlib import Path


def parse_single_mdoc(filepath):
    """Parse a per-tilt mdoc file and return header lines and section key-value pairs."""
    header_lines = []
    section_data = {}
    in_section = False

    with open(filepath, 'r') as f:
        for line in f:
            line = line.rstrip('\n')

            # Check if this is a section header like [FrameSet = 0]
            if re.match(r'\[.+=.+\]', line):
                in_section = True
                continue

            if not in_section:
                # These are header lines (T = ..., Voltage = ..., etc.)
                if line.strip():
                    header_lines.append(line)
            else:
                # Key = Value pairs within the section
                if '=' in line and line.strip():
                    key, _, value = line.partition('=')
                    section_data[key.strip()] = value.strip()

    return header_lines, section_data


def extract_tilt_angle(section_data, filename):
    """Extract tilt angle from section data, falling back to filename parsing."""
    if 'TiltAngle' in section_data:
        return float(section_data['TiltAngle'])

    # Fallback: try to parse from filename (e.g., _00000_30.0.tif.mdoc)
    match = re.search(r'_(-?\d+\.?\d*)\.tif\.mdoc$', filename)
    if match:
        return float(match.group(1))

    raise ValueError(f"Cannot determine tilt angle for {filename}")


def merge_mdocs(input_dir, output_file, fix_subframepath=False):
    """
    Merge all per-tilt mdoc files in input_dir into a single tilt-series mdoc.

    Parameters
    ----------
    input_dir : str
        Directory containing *.tif.mdoc files
    output_file : str
        Path for the output merged mdoc file
    fix_subframepath : bool
        If True, rewrite SubFramePath to use the local directory
        (useful if data was moved from the collection computer)
    """
    # Find all per-tilt mdoc files
    mdoc_pattern = os.path.join(input_dir, '*.tif.mdoc')
    mdoc_files = sorted(glob.glob(mdoc_pattern))

    if not mdoc_files:
        print(f"ERROR: No *.tif.mdoc files found in {input_dir}")
        return

    print(f"Found {len(mdoc_files)} per-tilt mdoc files")

    # Parse all mdoc files
    all_tilts = []
    global_header = None

    for mdoc_file in mdoc_files:
        header_lines, section_data = parse_single_mdoc(mdoc_file)
        tilt_angle = extract_tilt_angle(section_data, os.path.basename(mdoc_file))

        # Use the header from the first file (they should all be the same)
        if global_header is None:
            global_header = header_lines

        # Optionally fix SubFramePath to point to the local directory
        if fix_subframepath and 'SubFramePath' in section_data:
            original_path = section_data['SubFramePath']
            tif_filename = os.path.basename(original_path.replace('\\', '/'))
            # Replace period in tilt angle with underscore (e.g. _27.0.tif -> _27_0.tif)
            tif_filename = re.sub(r'_(-?\d+)\.(\d+\.tif)', r'_\1_\2', tif_filename)
            local_path = tif_filename
            section_data['SubFramePath'] = local_path

        all_tilts.append({
            'tilt_angle': tilt_angle,
            'section_data': section_data,
            'source_file': os.path.basename(mdoc_file),
        })

    # Sort by tilt angle (ascending)
    all_tilts.sort(key=lambda x: x['tilt_angle'])

    print(f"Tilt range: {all_tilts[0]['tilt_angle']:.1f} to {all_tilts[-1]['tilt_angle']:.1f} degrees")
    print(f"Writing merged mdoc to: {output_file}")

    # Write the merged mdoc file
    with open(output_file, 'w') as f:
        # Write global header
        for line in global_header:
            f.write(line + '\n')
        f.write('\n')

        # Write each tilt as a [ZValue = N] section
        for zvalue, tilt in enumerate(all_tilts):
            f.write(f'[ZValue = {zvalue}]\n')

            # Write all key-value pairs from the section
            for key, value in tilt['section_data'].items():
                f.write(f'{key} = {value}\n')

            f.write('\n')

    print(f"Successfully wrote {len(all_tilts)} tilt sections")
    print(f"\nTilt order (by angle):")
    for i, tilt in enumerate(all_tilts):
        print(f"  ZValue {i:3d} -> {tilt['tilt_angle']:7.2f} deg  ({tilt['source_file']})")


def main():
    parser = argparse.ArgumentParser(
        description='Merge per-tilt SerialEM .tif.mdoc files into a single tilt-series mdoc.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - merge all mdocs in the raw_tiff directory
  python merge_mdocs.py /data1/Tomo/PqiABC/pqiabc_46/raw_tiff/

  # Specify output filename
  python merge_mdocs.py /data1/Tomo/PqiABC/pqiabc_46/raw_tiff/ -o pqiabc_46.mrc.mdoc

  # Fix SubFramePath to point to local tiff directory
  python merge_mdocs.py /data1/Tomo/PqiABC/pqiabc_46/raw_tiff/ --fix-paths
        """
    )

    parser.add_argument('input_dir',
                        help='Directory containing the per-tilt *.tif.mdoc files')
    parser.add_argument('-o', '--output',
                        default=None,
                        help='Output mdoc filename (default: tiltseries.mdoc in input dir)')
    parser.add_argument('--fix-paths', action='store_true',
                        help='Rewrite SubFramePath entries to use local absolute paths '
                             '(useful if data was moved from the collection computer)')

    args = parser.parse_args()

    input_dir = os.path.abspath(args.input_dir)

    if not os.path.isdir(input_dir):
        print(f"ERROR: {input_dir} is not a directory")
        return

    if args.output:
        output_file = args.output
    else:
        # Default: place the merged mdoc in the input directory
        # Try to derive a sensible name from the directory or filenames
        mdoc_files = glob.glob(os.path.join(input_dir, '*.tif.mdoc'))
        if mdoc_files:
            # Extract base name: pqiabc_Lamella_20260310_46_00000_30.0.tif.mdoc
            # -> pqiabc_Lamella_20260310_46
            basename = os.path.basename(mdoc_files[0])
            # Remove the _NNNNN_angle.tif.mdoc suffix
            match = re.match(r'(.+?)_\d{5}_-?\d+\.?\d*\.tif\.mdoc$', basename)
            if match:
                series_name = match.group(1)
                output_file = os.path.join(input_dir, f'{series_name}.mrc.mdoc')
            else:
                output_file = os.path.join(input_dir, 'tiltseries.mdoc')
        else:
            output_file = os.path.join(input_dir, 'tiltseries.mdoc')

    merge_mdocs(input_dir, output_file, fix_subframepath=args.fix_paths)


if __name__ == '__main__':
    main()
