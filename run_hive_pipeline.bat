@echo off
REM ====================================================
REM Hive 数据清洗管道 - 快速启动脚本 (Windows)
REM ====================================================

echo.
echo ========================================
echo   Hive 数据清洗管道启动器
echo ========================================
echo.

REM 检查 Docker 服务
echo [1/5] 检查 Docker 服务状态...
docker-compose ps > nul 2>&1
if errorlevel 1 (
    echo [错误] Docker 服务未运行，请先启动 Docker Desktop
    pause
    exit /b 1
)
echo [完成] Docker 服务运行正常

REM 检查关键服务
echo.
echo [2/5] 检查 Hive 服务...
docker exec hive-server echo "HiveServer2 is running" > nul 2>&1
if errorlevel 1 (
    echo [错误] HiveServer2 未运行
    echo 请运行: docker-compose up -d
    pause
    exit /b 1
)
echo [完成] HiveServer2 运行正常

REM 检查数据文件
echo.
echo [3/5] 检查数据文件...
if not exist "data\movies.csv" (
    echo [警告] data\movies.csv 不存在
    echo 请从 MovieLens 下载数据集
    pause
    exit /b 1
)
if not exist "data\ratings.csv" (
    echo [警告] data\ratings.csv 不存在
    echo 请从 MovieLens 下载数据集
    pause
    exit /b 1
)
echo [完成] 数据文件检查通过

REM 创建 movielens_db 数据库
echo.
echo [4/5] 创建 movielens_db 数据库...
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "CREATE DATABASE IF NOT EXISTS movielens_db;" > nul 2>&1
echo [完成] 数据库已创建

REM 运行管道
echo.
echo [5/5] 开始运行 Hive 数据清洗管道...
echo ========================================
echo.

python hive_data_pipeline.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo [失败] 管道执行出错
    echo ========================================
    pause
    exit /b 1
) else (
    echo.
    echo ========================================
    echo [成功] 管道执行完成！
    echo ========================================
    echo.
    echo 验证数据:
    echo   docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "USE movielens_db; SHOW TABLES;"
    echo.
    pause
)
