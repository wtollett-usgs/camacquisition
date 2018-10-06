#!/usr/bin/env python

import argparse
import json
import logging
import os
import requests
import shutil
import sys
import time

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
parser.add_argument('-l', '--logfile', type=str, required=False,
                    help='Logfile location')

# Logging
logger = logging.getLogger('CamAcq')
level = logging.getLevelName(os.getenv('LOGLEVEL', 'INFO'))
logger.setLevel(level)


def read_config(configfile):
    logger.debug('Reading configfile: {0}'.format(configfile))
    with open(configfile) as f:
        return json.load(f)


def set_logfile(path):
    fh = logging.FileHandler(path)
    logger.addHandler(fh)


def close_logs():
    handlers = logger.handlers[:]
    for handler in handlers:
        handler.close()
        logger.removeHandler(handler)


def get(url, auth):
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
            logger.info('Giving up at: %s' %
                        datetime.now().strftime(TFMT))
            sys.exit()
        else:
            time.sleep(5)
            return get(url, auth)


if __name__ == '__main__':
    args = parser.parse_args()
    if args.logfile:
        set_logfile(args.logfile)
    logger.info('Starting: %s' % NOW.strftime(TFMT))
    config = read_config(args.config)
    r = get(config['url'], config['auth'])
    logger.debug('Got image')

    # Set up variables based on config
    cam = config['cam']
    tmpfile = TMP.format(cam)
    tmpthumb = TMB.format(cam)
    tmpjs = JS.format(cam)
    path = ARCHPATH.format(cam, NOW.year, str(NOW.month).zfill(2),
                           str(NOW.day).zfill(2), str(NOW.hour).zfill(2))

    with open(tmpfile, 'wb') as f:
        f.write(r.content)

    # Add watermark, create thumbnail
    with Image.open(tmpfile) as im:
        with Image.open(WATERMARK) as wm:
            logger.debug('Adding watermark')
            w, h = im.size
            w2, h2 = wm.size
            im.paste(wm, (10, h - (h2 + 10)), wm)
            im.save(tmpfile)

        logger.debug('Creating thumbnail')
        im.thumbnail(config['t_size'])
        im.save(tmpthumb, 'JPEG')

    # Copy to archive
    if not os.path.exists(path):
        logger.debug('Creating new archive dir: {0}'.format(path))
        os.makedirs(path)
    logger.debug('Copying to archive')
    tm = datetime.now()
    shutil.copy2(tmpfile,
                 '{0}/{1}M.jpg'.format(path, tm.strftime('%Y%m%d%H%M%S')))

    # Make js.js
    logger.debug('Making js.js')
    with open(tmpjs, 'w') as f:
        f.write('var datetime = "%s (HST)";\n' %
                tm.strftime(TFMT))
        f.write('var frames   = new Array("M");')

    # Copy stuff to lamp
    logger.info('Copying to lamp')
    shutil.copy2(tmpfile, IMG.format(cam, 'M.jpg'))
    shutil.copy2(tmpthumb, IMG.format(cam, 'M.thumb.jpg'))
    shutil.copy2(tmpjs, IMG.format(cam, 'js.js'))

    # Delete from tmp
    logger.debug('Removing from tmp')
    os.remove(tmpfile)
    os.remove(tmpthumb)
    os.remove(tmpjs)

    logger.info('Finished at: %s' % datetime.now().strftime(TFMT))
    close_logs()
