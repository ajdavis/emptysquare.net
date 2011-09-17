#!/bin/bash

cd /Users/ajdavis/emptysquare.net
/Library/Frameworks/Python.framework/Versions/2.7/bin/python emptysquare.py emptysquare emptysquare.net
scp -r photography/ static/ squareempty@emptysquare.net:emptysquare.net/

