@echo off
chcp 65001
title Jar启动脚本

:: 默认端口
set PORT=8770

:: 如果传入了第一个参数，就覆盖端口
if not "%1"=="" (
    set PORT=%1
)

echo ======================================
echo 准备启动jar，端口：%PORT%
echo ======================================

:: 替换为你的jar包文件名
java -server -Xms512m -Xmx1024m -jar yzy-b-demo-1.0-SNAPSHOT.jar --server.port=%PORT%

pause