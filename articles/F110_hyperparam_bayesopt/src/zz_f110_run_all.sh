#!/bin/bash
# F110 の計算をまとめて実行（他の計算と並ぶので nice をつける）
cd "$(dirname "$0")"
nice -n 10 python3 03_探索.py power wide 40 0,1,2,3,4 grid,random,tpe,gp power_main
nice -n 10 python3 03_探索.py land wide 40 0,1,2 grid,random,tpe,gp land_main
nice -n 10 python3 03_探索.py power narrow 40 0,1,2,3,4 grid,random,tpe,gp power_narrow
nice -n 10 python3 03_探索.py power wide 100 10,11,12 random,tpe,gp power_long
nice -n 10 python3 03b_ばらつき.py
