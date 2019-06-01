#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import shutil
import Util as my_utils

from datetime import datetime, timedelta
from glob import glob
from PIL import Image

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
    pth = YR_PATH.format(DIR, cam, now.year)
    if not os.path.exists(f'{TMP}/{cam}'):
        os.makedirs(f'{TMP}/{cam}')
    for mkey, mval in months.items():
        for dkey, dval in mval.items():
            for h in dval:
                os.chdir(f'{pth}/{mkey.zfill(2)}/{dkey.zfill(2)}/{h.zfill(0)}')
                logger.info(f'Grabbing files from {os.getcwd()}')
                imgs = glob('*.jpg')
                shutil.copy2(sorted(imgs)[0], f'{TMP}/{cam}')


def create_gif():
    logger.info('Creating gif')
    os.chdir(f'{TMP}/{config["cam"]}')
    imgs = sorted(glob('*.jpg'))
    img = Image.open(imgs[0])
    otherimgs = [Image.open(i) for i in imgs[1:]]
    img.save(f'{config["cam"]}.gif', save_all=True,
             append_images=otherimgs, duration=300, loop=1)
    img.close()
    for i in otherimgs:
        i.close()


def copy_to_server():
    logger.info('Copying to lamp')
    cam = config['cam']
    shutil.copy2(f'{TMP}/{cam}/{cam}.gif', f'{DIR}/{cam}/images')


def cleanup():
    os.chdir(f'{TMP}/{config["cam"]}')
    logger.info('Cleaning up')
    os.remove(f'{config["cam"]}.gif')
    files = glob('*.jpg')
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
    gather_images()
    create_gif()
    copy_to_server()
    cleanup()
    logger.info('Finished')
    logging.shutdown()
