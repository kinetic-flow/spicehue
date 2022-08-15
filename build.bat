@echo off
pushd %~dp0
del /q dist\*
mkdir dist
copy default.ini dist\
echo Build with pyinstaller...
pyinstaller spicehue.py --onefile -n spicehue
powershell Compress-Archive -Path dist\* -DestinationPath dist\spicehue_release.zip
echo Create an archive...
popd