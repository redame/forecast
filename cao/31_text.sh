#!/bin/sh

# www5.cao.go.jp/keizai3/getsurei/2014/1125getsurei/main.pdf

for ff in txt/*txt;do
  f=`basename $ff`
  yyyy=${f:0:4}
  mm=${f:4:2}
  echo $yyyy $mm
  python 31_text.py txt/${yyyy}${mm}.txt txt/${yyyy}${mm}.txt.conv
  uniq txt/${yyyy}${mm}.txt.conv > /tmp/$$.txt
  mv /tmp/$$.txt txt/${yyyy}${mm}.txt.conv
done
