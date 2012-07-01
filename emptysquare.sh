#!/bin/bash

python2.7 emptysquare.py emptysquare emptysquare.net
rsync -avz photography static es2:emptysquare.net/

