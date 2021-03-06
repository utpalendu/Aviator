#!/usr/bin/env python
#
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=C0301
"""Package resources into an apk.

See https://android.googlesource.com/platform/tools/base/+/master/legacy/ant-tasks/src/main/java/com/android/ant/AaptExecTask.java
and
https://android.googlesource.com/platform/sdk/+/master/files/ant/build.xml
"""
# pylint: enable=C0301

import optparse
import os
import shutil

from util import build_utils

def ParseArgs():
  """Parses command line options.

  Returns:
    An options object as from optparse.OptionsParser.parse_args()
  """
  parser = optparse.OptionParser()
  parser.add_option('--android-sdk', help='path to the Android SDK folder')
  parser.add_option('--android-sdk-tools',
                    help='path to the Android SDK build tools folder')

  parser.add_option('--configuration-name',
                    help='Gyp\'s configuration name (Debug or Release).')

  parser.add_option('--android-manifest', help='AndroidManifest.xml path')
  parser.add_option('--version-code', help='Version code for apk.')
  parser.add_option('--version-name', help='Version name for apk.')
  parser.add_option('--resource-zips',
                    help='zip files containing resources to be packaged')
  parser.add_option('--asset-dir',
                    help='directories containing assets to be packaged')

  parser.add_option('--apk-path',
                    help='Path to output (partial) apk.')

  (options, args) = parser.parse_args()

  if args:
    parser.error('No positional arguments should be given.')

  # Check that required options have been provided.
  required_options = ('android_sdk', 'android_sdk_tools', 'configuration_name',
                      'android_manifest', 'version_code', 'version_name',
                      'resource_zips', 'asset_dir', 'apk_path')

  build_utils.CheckOptions(options, parser, required=required_options)

  return options


def MoveImagesToNonMdpiFolders(res_root):
  """Move images from drawable-*-mdpi-* folders to drawable-* folders.

  Why? http://crbug.com/289843
  """
  for src_dir_name in os.listdir(res_root):
    src_components = src_dir_name.split('-')
    if src_components[0] != 'drawable' or 'mdpi' not in src_components:
      continue
    src_dir = os.path.join(res_root, src_dir_name)
    if not os.path.isdir(src_dir):
      continue
    dst_components = [c for c in src_components if c != 'mdpi']
    assert dst_components != src_components
    dst_dir_name = '-'.join(dst_components)
    dst_dir = os.path.join(res_root, dst_dir_name)
    build_utils.MakeDirectory(dst_dir)
    for src_file_name in os.listdir(src_dir):
      if not src_file_name.endswith('.png'):
        continue
      src_file = os.path.join(src_dir, src_file_name)
      dst_file = os.path.join(dst_dir, src_file_name)
      assert not os.path.lexists(dst_file)
      shutil.move(src_file, dst_file)


def main():
  options = ParseArgs()
  android_jar = os.path.join(options.android_sdk, 'android.jar')
  aapt = os.path.join(options.android_sdk_tools, 'aapt')

  with build_utils.TempDir() as temp_dir:
    package_command = [aapt,
                       'package',
                       '--version-code', options.version_code,
                       '--version-name', options.version_name,
                       '-M', options.android_manifest,
                       '--no-crunch',
                       '-f',
                       '--auto-add-overlay',

                       '-I', android_jar,
                       '-F', options.apk_path,
                       ]

    if os.path.exists(options.asset_dir):
      package_command += ['-A', options.asset_dir]

    dep_zips = build_utils.ParseGypList(options.resource_zips)
    for z in dep_zips:
      subdir = os.path.join(temp_dir, os.path.basename(z))
      if os.path.exists(subdir):
        raise Exception('Resource zip name conflict: ' + os.path.basename(z))
      build_utils.ExtractAll(z, path=subdir)
      MoveImagesToNonMdpiFolders(subdir)
      package_command += ['-S', subdir]

    if 'Debug' in options.configuration_name:
      package_command += ['--debug-mode']

    build_utils.CheckOutput(
        package_command, print_stdout=False, print_stderr=False)


if __name__ == '__main__':
  main()
