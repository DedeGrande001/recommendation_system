#!/bin/bash

echo "========================================="
echo "Hive 环境状态检查"
echo "========================================="
echo ""

echo "1. 检查所有容器状态："
docker-compose ps
echo ""

echo "2. 检查 Hive Metastore (端口 9083)："
docker exec hive-metastore bash -c "ss -tulnp 2>/dev/null | grep 9083" && echo "✅ Metastore 正在运行" || echo "❌ Metastore 未运行"
echo ""

echo "3. 检查 HiveServer2 (端口 10000)："
docker exec hive-server bash -c "ss -tulnp 2>/dev/null | grep 10000" && echo "✅ HiveServer2 正在运行" || echo "❌ HiveServer2 还在启动中..."
echo ""

echo "4. 检查 HiveServer2 进程："
docker exec hive-server bash -c "ps aux | grep -i hiveserver2 | grep -v grep | wc -l" | {
    read count
    if [ "$count" -gt 0 ]; then
        echo "✅ HiveServer2 进程存在 ($count 个)"
    else
        echo "❌ HiveServer2 进程不存在"
    fi
}
echo ""

echo "5. 测试 Hive 连接："
timeout 10 docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "SHOW DATABASES;" 2>&1 | grep -q "default" && echo "✅ Hive 连接成功！" || echo "❌ Hive 连接失败，请稍后重试"
echo ""

echo "6. 查看 HiveServer2 最近日志："
docker logs hive-server --tail 5 2>&1
echo ""

echo "========================================="
echo "检查完成"
echo "========================================="
