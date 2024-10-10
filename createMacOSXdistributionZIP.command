#!/bin/sh


#remove previous distributions if existing
rm -rf p2pp_dist
mkdir p2pp_dist

#copy all from main folder
cp *py p2pp_dist/
cp p2pp.command p2pp_dist/
cp *ic* p2pp_dist/

#make the scripts executable
chmod 755 p2pp_dist/P2PP.py
chmod 755 p2pp_dist/p2pp.command
 
#copy p2pp packages in subfolder to dist

mkdir p2pp_dist/p2pp
cp p2pp/*py p2pp_dist/p2pp/
cp p2pp/*ppm p2pp_dist/p2pp/


#create zip file

rm -rf p2pp_mac.zip

/usr/bin/zip -r p2pp_mac.zip p2pp_dist/*


rm -rf p2pp_dist
