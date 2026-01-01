#!/usr/bin/env python3
"""
测试 Hive 连接
支持两种方式：
1. 通过 HiveServer2 (端口 10000) - 使用 PyHive
2. 直接通过 Hive Metastore (端口 9083) - 使用 Thrift
"""

import sys

def test_hiveserver2():
    """测试 HiveServer2 连接"""
    try:
        from pyhive import hive
        print("正在测试 HiveServer2 连接 (localhost:10000)...")

        conn = hive.Connection(
            host='localhost',
            port=10000,
            username='root',
            database='default',
            auth='NONE'
        )

        cursor = conn.cursor()
        cursor.execute('SHOW DATABASES')
        databases = cursor.fetchall()

        print("✅ HiveServer2 连接成功！")
        print(f"数据库列表: {databases}")

        cursor.close()
        conn.close()
        return True

    except ImportError:
        print("❌ PyHive 未安装。请运行: pip install pyhive thrift")
        return False
    except Exception as e:
        print(f"❌ HiveServer2 连接失败: {e}")
        print("提示: HiveServer2 可能还在启动中，请等待 2-5 分钟")
        return False

def test_metastore_thrift():
    """测试 Metastore Thrift 连接"""
    try:
        from thrift.transport import TSocket, TTransport
        from thrift.protocol import TBinaryProtocol
        print("正在测试 Hive Metastore 连接 (localhost:9083)...")

        transport = TSocket.TSocket('localhost', 9083)
        transport = TTransport.TBufferedTransport(transport)
        protocol = TBinaryProtocol.TBinaryProtocol(transport)

        transport.open()
        print("✅ Hive Metastore Thrift 端口可访问！")
        transport.close()
        return True

    except ImportError:
        print("❌ Thrift 未安装。请运行: pip install thrift")
        return False
    except Exception as e:
        print(f"❌ Metastore 连接失败: {e}")
        return False

def main():
    print("="*50)
    print("Hive 连接测试")
    print("="*50)
    print()

    # 测试 Metastore
    metastore_ok = test_metastore_thrift()
    print()

    # 测试 HiveServer2
    hiveserver2_ok = test_hiveserver2()
    print()

    print("="*50)
    print("测试总结:")
    print(f"  Hive Metastore: {'✅ 可用' if metastore_ok else '❌ 不可用'}")
    print(f"  HiveServer2:    {'✅ 可用' if hiveserver2_ok else '❌ 不可用'}")
    print("="*50)

    if metastore_ok and not hiveserver2_ok:
        print()
        print("提示: Metastore 已启动但 HiveServer2 还在初始化中")
        print("      请等待 2-5 分钟后重试")
        print("      或者使用 Spark SQL 直接访问 Hive Metastore")

    return 0 if (metastore_ok and hiveserver2_ok) else 1

if __name__ == '__main__':
    sys.exit(main())
