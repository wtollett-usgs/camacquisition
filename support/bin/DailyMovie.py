#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import os
import shutil
import subprocess
import tomputils.util as tutil

from datetime import datetime, timedelta
from glob import glob

# Argparse
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', type=str, required=False,
                    help='Config file. If no config file, GOES assumed.')
parser.add_argument('-d', '--date', type=str, required=False,
                    help="Datetime string (YYYYMMDD) or 'yesterday'")


def read_config(config_file):
    logger.debug(f'Reading config file: {config_file}')
    with open(config_file, 'r') as f:
        j = json.load(f)
        return j['cam'], j['name']


def parse_date(in_date=None):
    if in_date:
        if in_date == 'yesterday':
            now = datetime.now() - timedelta(1)
        else:
            now = datetime.strptime(in_date, '%Y%m%d')
    else:
        now = datetime.now()
    return str(now.year), str(now.month).zfill(2), str(now.day).zfill(2)


def get_files(rootdir, filelist):
    files = []
    for filename in glob(f'{rootdir}/**/*.jpg', recursive=True):
        files.append(filename)
    with open(filelist, 'wb') as f:
        f.write(str.encode('\n'.join(sorted(files))))
    return files


def create_and_copy_video(filelist, tmpmovie, moviedir):
    # Create movie
    cmd = ['mencoder', f'mf://@{filelist}', '-mf', 'fps=10', '-ovc',
           'lavc', '-lavcopts', 'vcodec=mjpeg:vbitrate=1000', '-o',
           tmpmovie]
    subprocess.call(cmd)
    # Copy movie
    logger.info(f'Copying file to {moviedir}')
    shutil.copy2(tmpmovie, moviedir)
    # Delete tmp movie
    os.remove(tmpmovie)


def create_video(imagedir, filelist, tmpmovie, moviedir):
    # Get file list
    files = get_files(imagedir, filelist)

    if len(files) > 0:
        # Create movie
        logger.debug(f'Found {len(files)} images. Starting encode.')
        create_and_copy_video(filelist, tmpmovie, moviedir)
    else:
        logger.debug("No image files -- exiting")

    os.remove(filelist)


def goes_video(in_date=None):
    year, month, day = parse_date(in_date)
    logger.info(f'Starting goes video creation for {year}-{month}-{day}')
    movie_name = f'goes{year}{month}{day}.avi'
    tmp_movie = f'/tmp/{movie_name}'
    filelist = f'{tmp_movie}.movie.txt'
    moviedir = f'/data/www/remote_sensing/goes/movies/'
    imagedir = f'/data/www/remote_sensing/goes/images/{year}/{month}/{day}'
    create_video(imagedir, filelist, tmp_movie, moviedir)


def cam_video(camera_code, name, in_date=None):
    year, month, day = parse_date(in_date)
    logger.info('Starting video creation for %s, date = %s'
                % (camera_code, f'{year}-{month}-{day}'))
    movie_name = f'{camera_code}{year}{month}{day}{name}.avi'
    tmp_movie = f'/tmp/{movie_name}'
    filelist = f'{tmp_movie}.movie.txt'
    moviedir = f'/data/cams/{camera_code}/movies/'
    imagedir = f'/data/cams/{camera_code}/images/archive/{year}/{month}/{day}'
    create_video(imagedir, filelist, tmp_movie, moviedir)


if __name__ == '__main__':
    global logger
    logger = tutil.setup_logging("DailyMovie")
    if 'PYLOGLEVEL' in os.environ:
        level = logging.getLevelName(os.getenv('PYLOGLEVEL', 'DEBUG'))
        logger.setLevel(level)

    args = parser.parse_args()
    if args.config:
        camera_code, name = read_config(args.config)
        cam_video(camera_code, name, args.date)
    else:
        goes_video(args.date)
    logging.info('Finished creating video.')
    logging.shutdown()
