echo --------------------------------
echo IMPORTANT: type altscr when Soft
echo ICE is on the second screen
echo --------------------------------

rm hdd.img.lock
MDA_PIPE=/tmp/mda_pipe ~/_DEV/bochs-dual-monitor/bochs/bochs -q
