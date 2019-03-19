# CamAcquisition

[![Build Status](https://travis-ci.com/wtollett-usgs/camacquisition.svg?branch=master)](https://travis-ci.com/wtollett-usgs/camacquisition)

## Usage
---
Expected volume mounts:
1. Camera conf files and geod.cron to /app/camacquisition/etc
2. Location to save images to /data
3. If you want to view the logs outside the container, mount something to /var/log/cams
