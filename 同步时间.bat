@echo off
echo 正在重置Windows时间服务...
net stop w32time
w32tm /unregister
w32tm /register

echo 配置时间服务器(使用多个备选服务器)...
w32tm /config /manualpeerlist:"time.windows.com,ntp.aliyun.com,cn.pool.ntp.org,time.nist.gov" /syncfromflags:manual /reliable:yes /update

echo 启动Windows时间服务...
net start w32time

echo 设置更新间隔...
w32tm /config /update /syncfromflags:manual

echo 尝试同步时间...
w32tm /resync /rediscover /nowarn

echo 检查同步状态...
w32tm /query /status

echo 完成!