#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import re
import shutil
import subprocess
import tomputils.util as tutil

from datetime import datetime, timedelta
from glob import glob

# Argparse
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', type=str, required=True,
                    help='Config file')
parser.add_argument('-d', '--date', type=str, required=False,
                    help="Datetime string (YYYYMMDD) or 'yesterday'")

movie_dir = '/data/cams/{}/movies/'
image_dir = '/data/cams/{}/images/archive/{}/{}/{}'


def read_config(config_file):
    logger.debug(f'Reading config file: {config_file}')
    camera_code = None
    name = None
    pattern = re.compile('[\t\n="()]')
    with open(config_file, 'r') as f:
        for line in f:
            line = pattern.sub('', line)
            spl = line.split(' ')
            if spl[1] == 'cameraCode':
                camera_code = spl[2]
            elif spl[1] == 'name':
                name = spl[2]
    logger.debug(f'Camera: {camera_code}, Name: {name}')
    return camera_code, name


def create_video(camera_code, name, in_date=None):
    if in_date:
        if in_date == 'yesterday':
            now = datetime.now() - timedelta(1)
        else:
            now = datetime.strptime(in_date, '%Y%m%d')
    else:
        now = datetime.now()
    logger.info('Starting video creation for %s, date = %s'
                % (camera_code, now.strftime('%Y-%m-%d')))
    year = str(now.year)
    month = str(now.month).zfill(2)
    day = str(now.day).zfill(2)
    movie_name = f'{camera_code}{year}{month}{day}{name}.avi'
    tmp_movie = f'/tmp/{movie_name}'
    filelist = f'{tmp_movie}.movie.txt'
    m_dir = movie_dir.format(camera_code)
    i_dir = image_dir.format(camera_code, year, month, day)

    # Get file list
    files = []
    for filename in glob(f'{i_dir}/**/*{name}.jpg', recursive=True):
        files.append(filename)
    with open(filelist, 'wb') as f:
        f.write(str.encode('\n'.join(sorted(files))))

    if len(files) > 0:
        # Create movie
        logger.debug(f'Found {len(files)} images. Starting encode.')
        cmd = ['mencoder', f'mf://@{filelist}', '-mf', 'fps=10', '-ovc',
               'lavc', '-lavcopts', 'vcodec=mjpeg:vbitrate=1000', '-o',
               tmp_movie]
        subprocess.call(cmd)
        # Copy movie
        logger.info(f'Copying file to {m_dir}')
        shutil.copy2(tmp_movie, m_dir)
        # Delete tmp movie
        os.remove(tmp_movie)
    else:
        logger.debug("No image files -- exiting")

    os.remove(filelist)


if __name__ == '__main__':
    global logger
    logger = tutil.setup_logging("DailyMovie")
    if 'PYLOGLEVEL' in os.environ:
        level = logging.getLevelName(os.getenv('PYLOGLEVEL', 'DEBUG'))
        logger.setLevel(level)

    args = parser.parse_args()
    camera_code, name = read_config(args.config)
    create_video(camera_code, name, args.date)
    logging.info('Finished creating video.')
    logging.shutdown()
