#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import cv2
import json
import logging
import os
import shutil
import Util as my_utils

from datetime import datetime, timedelta
from glob import glob

logger = my_utils.setup_logging("DailyMovie Log")

# Argparse
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', type=str, required=False,
                    help='Config file. If no config file, GOES assumed.')
parser.add_argument('-d', '--date', type=str, required=False,
                    help="Datetime string (YYYYMMDD) or 'yesterday'")


def read_config(config_file):
    logger.debug(f'Reading config file: {config_file}')
    with open(config_file, 'r') as f:
        return json.load(f)


def parse_date(in_date=None):
    if in_date:
        if in_date == 'yesterday':
            now = datetime.now() - timedelta(1)
        else:
            now = datetime.strptime(in_date, '%Y%m%d')
    else:
        now = datetime.now()
    return str(now.year), str(now.month).zfill(2), str(now.day).zfill(2)


def get_files(rootdir):
    files = []
    for filename in glob(f'{rootdir}/**/*.jpg', recursive=True):
        files.append(filename)
    return sorted(files)


def create_and_copy_video(files, tmpmovie, moviedir, goes):
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    if goes:
        img = cv2.imread(files[0])
        h, w = img.shape[:2]
        size = [w, h]
    else:
        size = config['size']
    video = cv2.VideoWriter(tmpmovie, fourcc, 10, (size[0], size[1]))
    for img in files:
        video.write(cv2.imread(img))
    video.release()
    # Copy movie
    logger.info(f'Copying file to {moviedir}')
    shutil.copy2(tmpmovie, moviedir)
    # Delete tmp movie
    os.remove(tmpmovie)


def create_video(imagedir, tmpmovie, moviedir, goes=False):
    # Get file list
    files = get_files(imagedir)

    if len(files) > 0:
        # Create movie
        logger.debug(f'Found {len(files)} images. Starting encode.')
        create_and_copy_video(files, tmpmovie, moviedir, goes)
    else:
        logger.debug("No image files -- exiting")


def goes_video(in_date=None):
    year, month, day = parse_date(in_date)
    logger.info(f'Starting goes video creation for {year}-{month}-{day}')
    movie_name = f'goes{year}{month}{day}.avi'
    tmp_movie = f'/tmp/{movie_name}'
    moviedir = f'/data/www/remote_sensing/goes/movies/'
    imagedir = f'/data/www/remote_sensing/goes/images/{year}/{month}/{day}'
    create_video(imagedir, tmp_movie, moviedir, goes=True)


def cam_video(in_date=None):
    cam = config['cam']
    name = config['name']
    year, month, day = parse_date(in_date)
    logger.info('Starting video creation for %s, date = %s'
                % (cam, f'{year}-{month}-{day}'))
    movie_name = f'{cam}{year}{month}{day}{name}.avi'
    tmp_movie = f'/tmp/{movie_name}'
    moviedir = f'/data/cams/{cam}/movies/'
    imagedir = f'/data/cams/{cam}/images/archive/{year}/{month}/{day}'
    create_video(imagedir, tmp_movie, moviedir)


if __name__ == '__main__':
    if 'PYLOGLEVEL' in os.environ:
        level = logging.getLevelName(os.getenv('PYLOGLEVEL', 'DEBUG'))
        logger.setLevel(level)

    args = parser.parse_args()
    if args.config:
        global config
        config = read_config(args.config)
        cam_video(args.date)
    else:
        goes_video(args.date)
    logging.info('Finished creating video.')
    logging.shutdown()
