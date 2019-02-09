#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import tomputils.util as tutil

from datetime import datetime
from glob import glob

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--cam', type=str, required=True, help='Camera code')


def prune_data(cam):
    now = datetime.now()
    year = str(now.year)
    month = str(now.month).zfill(2)
    day = str(now.day).zfill(2)
    ten_days_ago = now.timestamp() - 10 * 86400
    camdir = f'/data/cams/{cam}'
    idir = f'{camdir}/images/archive/{year}/{month}/{day}'
    cdir = f'{camdir}/composites/{year}/{month}'
    mdir = f'{camdir}/movies'

    # Delete empty images files from hours folders
    for filename in glob(f'{idir}/*/*.jpg', recursive=True):
        if os.stat(filename).st_size == 0:
            logger.info(f'Removing empty file: {filename}')
            os.remove(filename)

    # Delete empty composites from month
    for filename in glob(f'{cdir}/*.jpg'):
        if os.stat(filename).st_size == 0:
            logger.info(f'Removing empty composite: {filename}')
            os.remove(filename)

    # Delete movies > 10 days old
    for filename in glob(f'{mdir}/*.avi'):
        if os.stat(filename).st_mtime < ten_days_ago:
            logger.info(f'Removing old video: {filename}')
            os.remove(filename)


if __name__ == '__main__':
    global logger
    logger = tutil.setup_logging("PruneData")
    if 'PYLOGLEVEL' in os.environ:
        level = logging.getLevelName(os.getenv('PYLOGLEVEL', 'DEBUG'))
        logger.setLevel(level)

    args = parser.parse_args()
    logger.info('Starting')
    prune_data(args.cam)
    logger.info('Finished')
    logging.shutdown()
