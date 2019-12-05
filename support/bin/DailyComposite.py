#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import fnmatch
import json
import logging
import numpy as np
import os
import shutil
import Util as my_utils

from datetime import date, datetime, timedelta
from cv2 import imread, imwrite
from PIL import Image

ARCHIVE = '/data/cams'
COMPLOC = '/data/cams/{}/composites'
COMPARCH = '{}/archive/{}/{}'
TMPDIR = '/tmp'
TFMT = '%Y-%m-%d %H:%M'

logger = my_utils.setup_logging("DailyComposite Log")

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', type=str, required=True,
                    help='Config file')
parser.add_argument('-d', '--date', type=str, required=False, help="yyyymmdd")
parser.add_argument('-w', '--webcopy', type=bool, required=False, default=True,
                    help='Whether or not to copy to the web (default: true)')


def read_config(configfile):
    logger.debug(f'Reading configfile: {configfile}')
    with open(configfile) as f:
        return json.load(f)


def copy_to_archive(tmpfile, path, imgname):
    if not os.path.exists(path):
        logger.debug(f'Creating new directory: {path}')
        os.makedirs(path, 2775)
    logger.info(f'Copying {tmpfile} to {path}')
    shutil.copy2(tmpfile, f'{path}/{imgname}')


def create_composite(cam, name, size, webcopy, idate=None):
    logger.info('Creating composite')
    # Validate the date
    if idate and len(idate) > 0:
        if len(idate) != 8:
            return 'Date is not 8 characters (yyyymmdd)'
        else:
            try:
                int(idate)
            except ValueError as e:
                return f'imageDate is not numeric (yyyymmdd): {e}'
        # User-defined imageDate
        edate = datetime.strptime(idate, '%Y%m%d').date()
    else:
        # Use today's date as the end date (default)
        edate = date.today()

    # Set date/time variables
    sdate = edate - timedelta(days=1)
    syear = sdate.year
    smonth = '%02d' % sdate.month
    sday = '%02d' % sdate.day
    eyear = edate.year
    emonth = '%02d' % edate.month
    eday = '%02d' % edate.day

    # Other variable
    width = size[0]
    height = size[1]

    # Echo the variables we will use for this run
    logger.debug(f'cam: {cam}')
    logger.debug(f'frameName: {name}')
    logger.debug(f'imageWidth: {width}')
    logger.debug(f'imageHeight: {height}')
    logger.debug(f'startDate: {datetime.strftime(sdate, "%Y-%m-%d")}')
    logger.debug(f'endDate: {datetime.strftime(edate, "%Y-%m-%d")}')
    logger.debug(f'tmpDir: {TMPDIR}')

    # Create an empty space for the composite image
    Amax = np.zeros((height, width, 3))

    # Go through the previous and current day
    for day in range(2):
        # This is defining the applicable nighttime hours
        if day == 0:
            daydir = f'{ARCHIVE}/{cam}/images/archive/{syear}/{smonth}/{sday}'
            hours_array = [i for i in range(20, 24)]
        elif day == 1:
            daydir = f'{ARCHIVE}/{cam}/images/archive/{eyear}/{emonth}/{eday}'
            hours_array = [i for i in range(0, 5)]

        # Check to see if the day directory exists
        if not os.path.isdir(daydir):
            return f'{daydir} does not exist'

        # For each hour of this day
        for hour in hours_array:
            # Pad the hour with a 0 if less than 10
            currenthour = '%02d' % hour

            # Check if correct hour directory exists
            currentdir = f'{daydir}/{currenthour}'
            if not os.path.isdir(currentdir):
                break

            # Get file list for directory
            matchname = f'*{name}.jpg'
            filelist = [n for n in os.listdir(currentdir)
                        if fnmatch.fnmatch(n, matchname)]
            for filename in filelist:
                # Skip images that are empty
                try:
                    # Log message
                    logger.debug(filename)

                    # Use image class to test file for corruption
                    with Image.open(f'{currentdir}/{filename}') as test_img:
                        test_img.getdata()

                    # Do the composite image calculation
                    A = imread(f'{currentdir}/{filename}')
                    A = A.astype(float)
                    A2 = 0.299 * A[:, :, 0] + 0.587 * A[:, :, 1] \
                        + 0.114 * A[:, :, 2]
                    A2 = A2.astype(float)
                    A2max = 0.299 * Amax[:, :, 0] + 0.587 * Amax[:, :, 1] \
                        + 0.114 * Amax[:, :, 2]
                    A2max = A2max.astype(float)

                    # Detect and ignore bad pixels
                    Atest = np.logical_and(A2 > 127, A2 < 129)
                    badsum = sum(sum(Atest))
                    if badsum > 5000:
                        for r in range(A2.shape[0]):
                            for c in range(A2.shape[1]):
                                if np.logical_and(A2[r, c] > 127,
                                                  A2[r, c] < 129):
                                    rmin = r - 5
                                    if rmin < 0:
                                        rmin = 0
                                    rmax = r + 5
                                    if rmax >= A2.shape[0]:
                                        rmax = A2.shape[0] - 1
                                    cmin = c - 5
                                    if cmin < 0:
                                        cmin = 0
                                    cmax = c + 5
                                    if cmax >= A2.shape[1]:
                                        rmax = A2.shape[1] - 1
                                    Acut = A2[rmin:rmax, cmin:cmax]
                                    Atest2 = np.logical_and(Acut > 127,
                                                            Acut < 129)
                                    badsum2 = sum(sum(Atest2))
                                    if badsum2 > 10:
                                        A2[r, c] = 0

                    m1 = (A2max >= A2) * Amax[:, :, 0]
                    m2 = (A2max >= A2) * Amax[:, :, 1]
                    m3 = (A2max >= A2) * Amax[:, :, 2]
                    n1 = (A2 > A2max) * A[:, :, 0]
                    n2 = (A2 > A2max) * A[:, :, 1]
                    n3 = (A2 > A2max) * A[:, :, 2]
                    p1 = m1 + n1
                    p2 = m2 + n2
                    p3 = m3 + n3
                    Amax[:, :, 0] = p1
                    Amax[:, :, 1] = p2
                    Amax[:, :, 2] = p3
                except Exception as e:
                    logger.debug('OOPS!!!')
                    logger.debug(str(e))
                    continue

    Amax = Amax.astype('uint8')

    # Write the composite image to a file
    composite_name = f'{cam}{eyear}{emonth}{eday}{name}.jpg'
    filelocation = f'{TMPDIR}/{composite_name}'
    imwrite(filelocation, Amax)

    # Copy to various places
    if webcopy:
        cpath = COMPLOC.format(cam)
        copy_to_archive(filelocation, cpath, "M.jpg")
        apath = COMPARCH.format(cpath, eyear, emonth)
        copy_to_archive(filelocation, apath, composite_name)

        # Create js.js
        with open(f'{TMPDIR}/js.js', 'w') as f:
            f.write(f'var datetime = {datetime.now().strftime(TFMT)} (HST);\n')
            f.write(f'var frames   = new Array("{name}");')

        # Copy js.js to composites
        copy_to_archive(f'{TMPDIR}/js.js', cpath, 'js.js')

    # Delete tmp files
    logger.debug('Deleting temp files')
    os.remove(filelocation)
    os.remove(f'{TMPDIR}/js.js')


if __name__ == '__main__':
    if 'PYLOGLEVEL' in os.environ:
        level = logging.getLevelName(os.getenv('PYLOGLEVEL', 'DEBUG'))
        logger.setLevel(level)

    args = parser.parse_args()
    config = read_config(args.config)
    logger.info('Starting')
    # Create composite
    msg = create_composite(config['cam'], config['name'], config['size'],
                           args.webcopy, args.date)
    if msg:
        logger.info(f'Error: {msg}')
    logger.info('Finished')
    logging.shutdown()
