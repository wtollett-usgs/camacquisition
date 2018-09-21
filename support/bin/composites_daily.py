from imread import imread, imsave

import datetime
import fnmatch
import numpy as np
import os
import sys
import traceback

from PIL import Image

IMAGE_ARCHIVE = '/data/cams'

def composites_daily(camCode, frameName, imageWidth, imageHeight, imageDate, tmpDir):
    # Prepare the variables
    camCode     = camCode.strip()
    frameName   = frameName.strip()
    imageWidth  = imageWidth.strip()
    imageHeight = imageHeight.strip()
    imageDate   = imageDate.strip()
    tmpDir      = tmpDir.strip()

    # Validate the variables have values
    if not camCode:
        print('camCode is empty')
        return
    elif not frameName:
        print('frameName is empty')
        return
    elif not imageWidth:
        print('imageWidth is empty')
        return
    elif not imageHeight:
        print('imageHeight is empty')
        return
    elif not tmpDir:
        print('tmpDir is empty')
        return

    # Validate image sizes are numbers
    try:
        imageWidth  = int(imageWidth)
        imageHeight = int(imageHeight)
    except ValueError as e:
        print('imageWidth and imageHeight must be numbers')
        return

    # Validate the date
    if len(imageDate) > 0:
        if len(imageDate) != 8:
            print('imageDate is not 8 characters (yyyymmdd)')
            return
        else:
            try:
                int(imageDate)
            except ValueError as e:
                print('imageDate is not numeric (yyyymmdd)')
                return
        # User-defined imageDate
        endDate = datetime.datetime.strptime(imageDate, '%Y%m%d').date()
    else:
        # Use today's date as the end date (default)
        endDate = datetime.date.today()

    # Set date/time variables
    startDate  = endDate - datetime.timedelta(days=1)
    startYear  = startDate.year
    startMonth = '%02d' % startDate.month
    startDay   = '%02d' % startDate.day
    endYear    = endDate.year
    endMonth   = '%02d' % endDate.month
    endDay     = '%02d' % endDate.day

    # Echo the variables we will use for this run
    print('camCode: ' + camCode)
    print('frameName: ' + frameName)
    print('imageWidth: ' + str(imageWidth))
    print('imageHeight: ' + str(imageHeight))
    print('startDate: ' + datetime.datetime.strftime(startDate, '%Y-%m-%d'))
    print('endDate: ' + datetime.datetime.strftime(endDate, '%Y-%m-%d'))
    print('tmpDir: ' + tmpDir)
    print(' ')

    # Create an empty space for the composite image
    Amax = np.zeros((imageHeight, imageWidth, 3))

    # Go through the previous and current day
    for day in range(2):
        # This is defining the applicable nighttime hours
        if day == 0:
            dayDir     = '/'.join([IMAGE_ARCHIVE, camCode, 'images/archive', str(startYear), str(startMonth), str(startDay)])
            hoursArray = [i for i in range(20, 24)]
        elif day == 1:
            dayDir     = '/'.join([IMAGE_ARCHIVE, camCode, 'images/archive', str(endYear), str(endMonth), str(endDay)])
            hoursArray = [i for i in range(0,5)]

        # Check to see if the day directory exists
        if not os.path.isdir(dayDir):
            print(dayDir + ' does not exist')
            return

        # For each hour of this day
        for hour in hoursArray:
            # Pad the hour with a 0 if less than 10
            currentHour = '%02d' % hour

            # Check if correct hour directory exists
            currentDir = '/'.join([dayDir, currentHour])
            if not os.path.isdir(currentDir):
                break

            # Get file list for directory
            matchname = ''.join(['*', frameName, '.jpg'])
            filelist  = [n for n in os.listdir(currentDir) if fnmatch.fnmatch(n, matchname)]
            for file in filelist:
                # Skip images that are empty
                try:
                    # Log message
                    print(file)

                    # Use image class to test file for corruption
                    pilImage = Image.open('/'.join([currentDir, file]))
                    pilImage.getdata()
                    pilImage.close()

                    # Do the composite image calculation
                    A     = imread('/'.join([currentDir, file]))
                    A     = A.astype(float)
                    A2    = 0.299 * A[:,:,0] + 0.587 * A[:,:,1] + 0.114 * A[:,:,2]
                    A2    = A2.astype(float)
                    A2max = 0.299 * Amax[:,:,0] + 0.587 * Amax[:,:,1] + 0.114 * Amax[:,:,2]
                    A2max = A2max.astype(float)

                    # Detect and ignore bad pixels
                    Atest  = np.logical_and(A2 > 127, A2 < 129)
                    badsum = sum(sum(Atest))
                    if badsum > 5000:
                        for r in range(A2.shape[0]):
                            for c in range(A2.shape[1]):
                                if np.logical_and(A2[r,c] > 127, A2[r,c] < 129):
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
                                    Atest2 = np.logical_and(Acut > 127, Acut < 129)
                                    badsum2 = sum(sum(Atest2))
                                    if badsum2 > 10:
                                        A2[r,c] = 0

                    m1 = (A2max >= A2) * Amax[:,:,0]
                    m2 = (A2max >= A2) * Amax[:,:,1]
                    m3 = (A2max >= A2) * Amax[:,:,2]
                    n1 = (A2 > A2max) * A[:,:,0]
                    n2 = (A2 > A2max) * A[:,:,1]
                    n3 = (A2 > A2max) * A[:,:,2]
                    p1 = m1 + n1
                    p2 = m2 + n2
                    p3 = m3 + n3
                    Amax[:,:,0] = p1
                    Amax[:,:,1] = p2
                    Amax[:,:,2] = p3
                except Exception as e:
                    print(str(e))
                    continue

    Amax = Amax.astype('uint8')

    # Write the composite image to a file
    compositeImageName = ''.join([camCode, str(endYear), str(endMonth), str(endDay), str(frameName), '.jpg'])
    filelocation       = '/'.join([tmpDir, compositeImageName])
    imsave(filelocation, Amax)

if __name__ == '__main__':
    n = len(sys.argv) - 1
    if n != 6:
        print('Expected Usage:')
        print('  $ python composites_daily.py <cameraCode> <frameName> <imageWidth> <imageHeight> <date> <tmpDir>')
    else:
        composites_daily(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
