@echo off
cd /d E:\sageishere\SAGE_SMART_TRADE

git add .
git commit -m "Auto update %date% %time%"
git push origin main
