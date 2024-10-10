#!/bin/sh
DIRECTORY=`dirname $0`

if [ $# -eq -0 ]
then
     $DIRECTORY/P2PP.py
else
     $DIRECTORY/P2PP.py -i "$1"
fi