@echo off
chcp 65001 >nul
echo =========================================
echo Hive 环境状态检查
echo =========================================
echo.

echo 1. 检查所有容器状态：
docker-compose ps
echo.

echo 2. 检查 Hive Metastore (端口 9083)：
docker exec hive-metastore bash -c "ss -tulnp 2>/dev/null | grep 9083" >nul 2>&1 && (
    echo ✅ Metastore 正在运行
) || (
    echo ❌ Metastore 未运行
)
echo.

echo 3. 检查 HiveServer2 (端口 10000)：
docker exec hive-server bash -c "ss -tulnp 2>/dev/null | grep 10000" >nul 2>&1 && (
    echo ✅ HiveServer2 正在运行
) || (
    echo ❌ HiveServer2 还在启动中...
)
echo.

echo 4. 测试 Hive 连接（10秒超时）：
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "SHOW DATABASES;" 2>&1 | findstr /C:"default" >nul && (
    echo ✅ Hive 连接成功！
) || (
    echo ❌ Hive 连接失败，HiveServer2 可能还在启动中，请等待2-3分钟后重试
)
echo.

echo 5. 查看 HiveServer2 最近日志：
docker logs hive-server --tail 10 2>&1
echo.

echo =========================================
echo 检查完成
echo
echo 提示：如果 HiveServer2 还未启动完成，请等待 2-5 分钟后再次运行此脚本
echo =========================================
pause
