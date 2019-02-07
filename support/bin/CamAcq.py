#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import os
import requests
import shutil
import sys
import time
import tomputils.util as tutil

from datetime import datetime, timedelta
from PIL import Image

NOW = datetime.now()
TMP = '/tmp/img{0}.jpg'
TMB = '/tmp/img{0}.thumb.jpg'
JS = '/tmp/js{0}.js'
ARCHPATH = '/data/cams/{0}/images/archive/{1}/{2}/{3}/{4}'
IMG = '/data/cams/{0}/images/{1}'
WATERMARK = '/app/camacquisition/bin/usgs_watermark_wht.png'
TFMT = '%Y-%m-%d %H:%M:%S'

# Argparse
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', type=str, required=True,
                    help='Config file')

# ToDo:
# 1. Reset logfiles every hour
# 3. Email errors to defined email list


def read_config(configfile):
    logger.debug(f'Reading configfile: {configfile}')
    with open(configfile) as f:
        return json.load(f)


def get(url, auth=None):
    with requests.session() as s:
        s.keep_alive = False
        try:
            if auth:
                mauth = None
                if auth['type'] == 'digest':
                    mauth = requests.auth.HTTPDigestAuth(auth['user'],
                                                         auth['passwd'])
                else:
                    mauth = requests.auth.HTTPBasicAuth(auth['user'],
                                                        auth['passwd'])
                return requests.get(url, auth=mauth, timeout=20)
            else:
                return requests.get(url, timeout=20)
        except Exception:
            if datetime.now() > NOW + timedelta(seconds=50):
                logger.info('Giving up.')
                sys.exit()
            else:
                time.sleep(5)
                return get(url, auth)
        finally:
            s.close()


if __name__ == '__main__':
    global logger
    logger = tutil.setup_logging("CamAcq")
    if 'PYLOGLEVEL' in os.environ:
        level = logging.getLevelName(os.getenv('PYLOGLEVEL', 'DEBUG'))
        logger.setLevel(level)

    args = parser.parse_args()
    logger.info('Starting')
    config = read_config(args.config)
    if 'auth' in config:
        r = get(config['url'], config['auth'])
    else:
        r = get(config['url'])
    logger.debug('Got image')

    # Set up variables based on config
    cam = config['cam']
    iname = config['name']
    tmpfile = TMP.format(cam)
    tmpthumb = TMB.format(cam)
    tmpjs = JS.format(cam)
    path = ARCHPATH.format(cam, NOW.year, str(NOW.month).zfill(2),
                           str(NOW.day).zfill(2), str(NOW.hour).zfill(2))

    with open(tmpfile, 'wb') as f:
        f.write(r.content)

    # Crop KI and M1 cams
    if cam in ['KIcam', 'M1cam']:
        logger.debug(f'Cropping {cam} image.')
        with Image.open(tmpfile) as im:
            w, h = im.size
            im = im.crop((0, 0, w, h-config['crop']))
            im.save(tmpfile)

    # Add watermark, create thumbnail
    with Image.open(tmpfile) as im:
        w, h = im.size
        with Image.open(WATERMARK) as wm:
            logger.debug('Adding watermark')
            w2, h2 = wm.size
            im.paste(wm, (10, h - (h2 + 10)), wm)
            im.save(tmpfile)

        logger.debug('Creating thumbnail')
        im.thumbnail((w * 0.3, h * 0.3))
        im.save(tmpthumb, 'JPEG')

    # Copy to archive
    if not os.path.exists(path):
        logger.debug(f'Creating new archive dir: {path}')
        os.makedirs(path)
    logger.debug('Copying to archive')
    tm = datetime.now()
    shutil.copy2(tmpfile, f"{path}/{tm.strftime('%Y%m%d%H%M%S')}{iname}.jpg")

    # Make js.js
    logger.debug('Making js.js')
    with open(tmpjs, 'w') as f:
        f.write(f'var datetime = "{tm.strftime(TFMT)} (HST)";\n')
        f.write(f'var frames   = new Array("{iname}");')

    # Copy stuff to lamp
    logger.info('Copying to lamp')
    shutil.copy2(tmpfile, IMG.format(cam, f'{iname}.jpg'))
    shutil.copy2(tmpthumb, IMG.format(cam, f'{iname}.thumb.jpg'))
    shutil.copy2(tmpjs, IMG.format(cam, 'js.js'))

    # Delete from tmp
    logger.debug('Removing from tmp')
    os.remove(tmpfile)
    os.remove(tmpthumb)
    os.remove(tmpjs)

    logger.info('Finished')
    logging.shutdown()
