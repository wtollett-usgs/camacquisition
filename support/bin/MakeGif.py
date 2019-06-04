#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import shutil
import subprocess
import Util as my_utils

from datetime import datetime, timedelta
from glob import glob

TM_FORMAT = '%Y-%m-%d %H:%M:%S'
DIR = os.getenv('CAMSDIR', '/data/cams')
YR_PATH = '{}/{}/images/archive/{}'
TMP = '/tmp/gif'

logger = my_utils.setup_logging('MakeGif')

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', type=str, required=True,
                    help='Config file')


def get_hours(st, et):
    hours = {}
    if et.day == st.day:
        hours[str(et.day).zfill(2)] = [str(x).zfill(2)
                                       for x in range(st.hour, et.hour + 1)]
    else:
        hours[str(st.day).zfill(2)] = [str(x).zfill(2)
                                       for x in range(st.hour, 24)]
        hours[str(et.day).zfill(2)] = [str(x).zfill(2)
                                       for x in range(0, et.hour + 1)]
    return hours


def gather_images():
    cam = config['cam']
    now = datetime.now()
    st = now - timedelta(days=1)
    logger.info(f'Gather images for {cam}.')
    months = {}
    if now.month == st.month:
        months[str(now.month).zfill(2)] = get_hours(st, now)
    else:
        months[str(st.month).zfill(2)] = get_hours(st,
                                                   datetime(st.year,
                                                            st.month,
                                                            st.day, 23, 30))
        months[str(now.month).zfill(2)] = get_hours(datetime(now.year,
                                                             now.month,
                                                             now.day, 00,
                                                             30), now)
    count = 0
    ypath = YR_PATH.format(DIR, cam, now.year)
    if not os.path.exists(f'{TMP}/{cam}'):
        os.makedirs(f'{TMP}/{cam}')
    for mkey, mval in months.items():
        for dkey, dval in mval.items():
            for h in dval:
                p = f'{ypath}/{mkey.zfill(2)}/{dkey.zfill(2)}/{h.zfill(0)}'
                if os.path.exists(p):
                    os.chdir(p)
                    logger.info(f'Grabbing files from {os.getcwd()}')
                    imgs = glob('*.jpg')
                    if imgs:
                        shutil.copy2(sorted(imgs)[0], f'{TMP}/{cam}')
                        count += 1
                    else:
                        logger.info('No images in directory.')
                else:
                    logger.info('Directory doesn\'t exist.')
    return count


def create_gif():
    os.chdir(f'{TMP}/{config["cam"]}')
    imgs = sorted(glob('*.jpg'))
    if imgs:
        if config['size'][0] > 1920:
            logger.info('Downsizing large images.')
            cmd = ['mogrify', '-resize', '1920', '*.jpg']
            subprocess.call(cmd)
        logger.info('Creating gif')
        cmd = ['convert', '+dither', '-layers', 'Optimize', '-delay', '15',
               '*.jpg', f'{config["cam"]}.gif']
        subprocess.call(cmd)
    else:
        logger.info('No images, quitting')


def copy_to_server():
    logger.info('Copying to lamp')
    cam = config['cam']
    shutil.copy2(f'{TMP}/{cam}/{cam}.gif', f'{DIR}/{cam}/images')


def cleanup():
    os.chdir(f'{TMP}/{config["cam"]}')
    logger.info('Cleaning up')
    os.remove(f'{config["cam"]}.gif')
    files = glob('*.jpg*')
    for f in files:
        os.remove(f)


if __name__ == '__main__':
    if 'PYLOGLEVEL' in os.environ:
        level = logging.getLevelName(os.getenv('PYLOGLEVEL', 'DEBUG'))
        logger.setLevel(level)

    args = parser.parse_args()
    logger.info('Starting')
    global config
    config = my_utils.read_json_config(args.config)
    count = gather_images()
    if count > 0:
        create_gif()
        copy_to_server()
        cleanup()
    else:
        logger.info('No images collected.')
    logger.info('Finished')
    logging.shutdown()
