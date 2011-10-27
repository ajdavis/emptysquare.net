#!/bin/bash

cd /Users/ajdavis/emptysquare.net
/Library/Frameworks/Python.framework/Versions/2.7/bin/python emptysquare.py emptysquare emptysquare.net
rsync -avz photography static squareempty@emptysquare.net:emptysquare.net/

