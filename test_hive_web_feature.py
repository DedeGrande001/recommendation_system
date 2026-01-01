"""
测试 Hive 数据清洗 Web 功能
"""
import requests
import time

def test_hive_page_access():
    """测试 Hive 数据页面访问"""
    print("\n" + "="*60)
    print("测试 1: 访问 Hive 数据页面")
    print("="*60)

    url = "http://127.0.0.1:8000/hive-data/"

    try:
        response = requests.get(url, timeout=5)

        # 检查是否重定向到登录页
        if 'login' in response.url:
            print("⚠ 需要登录才能访问")
            print(f"重定向到: {response.url}")
            return False
        elif response.status_code == 200:
            print("✓ 页面访问成功")
            print(f"状态码: {response.status_code}")

            # 检查关键元素
            content = response.text
            checks = {
                '运行数据清洗': 'runCleaningBtn' in content,
                '刷新按钮': 'refreshBtn' in content,
                '数据统计': 'hive_stats' in content,
            }

            print("\n页面元素检查:")
            for name, present in checks.items():
                status = "✓" if present else "✗"
                print(f"  {status} {name}: {'存在' if present else '缺失'}")

            return all(checks.values())
        else:
            print(f"✗ 访问失败: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到服务器，请确保 Django 正在运行")
        print("  运行命令: python manage.py runserver")
        return False
    except Exception as e:
        print(f"✗ 错误: {str(e)}")
        return False


def test_run_cleaning_endpoint():
    """测试运行清洗端点（需要登录）"""
    print("\n" + "="*60)
    print("测试 2: 运行数据清洗端点")
    print("="*60)

    url = "http://127.0.0.1:8000/run-hive-cleaning/"

    try:
        # 不带认证的请求（应该被重定向）
        response = requests.post(url, timeout=5)

        if 'login' in response.url or response.status_code == 302:
            print("✓ 端点需要认证（符合预期）")
            return True
        else:
            print(f"⚠ 端点状态: {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ 错误: {str(e)}")
        return False


def test_hive_utils():
    """测试 Hive 工具函数"""
    print("\n" + "="*60)
    print("测试 3: Hive 工具函数")
    print("="*60)

    try:
        from app.hive_utils import check_hive_connection, get_hive_statistics

        # 测试连接
        print("\n检查 Hive 连接...")
        connected, message = check_hive_connection()

        if connected:
            print(f"✓ Hive 连接成功: {message}")

            # 获取统计
            print("\n获取统计信息...")
            stats = get_hive_statistics()

            if stats['available']:
                print("✓ 数据可用")
                print(f"  - 电影数: {stats['movies_count']:,}")
                print(f"  - 评分数: {stats['ratings_count']:,}")
                print(f"  - 用户数: {stats['users_count']:,}")
                print(f"  - 平均评分: {stats['avg_rating']:.2f}")
                return True
            else:
                print("⚠ 数据不可用（表可能为空）")
                if stats['error']:
                    print(f"  错误: {stats['error']}")
                return False
        else:
            print(f"✗ Hive 连接失败: {message}")
            print("\n请确保:")
            print("  1. Docker 容器正在运行: docker-compose up -d")
            print("  2. Hive 服务已启动: docker logs hive-server")
            return False

    except ImportError as e:
        print(f"✗ 导入错误: {str(e)}")
        print("  请确保在项目根目录运行此脚本")
        return False
    except Exception as e:
        print(f"✗ 错误: {str(e)}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Hive Web 功能测试套件")
    print("="*60)

    results = []

    # 测试 1: 页面访问
    results.append(("页面访问", test_hive_page_access()))

    # 等待一下
    time.sleep(1)

    # 测试 2: 清洗端点
    results.append(("清洗端点", test_run_cleaning_endpoint()))

    # 等待一下
    time.sleep(1)

    # 测试 3: Hive 工具
    results.append(("Hive 工具", test_hive_utils()))

    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    passed = 0
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status} - {name}")
        if result:
            passed += 1

    print("\n" + "="*60)
    print(f"总计: {passed}/{total} 测试通过")
    print("="*60)

    if passed == total:
        print("\n✅ 所有测试通过！")
        print("\n可以访问页面测试完整功能:")
        print("  http://127.0.0.1:8000/hive-data/")
        return True
    else:
        print("\n⚠ 部分测试失败，请检查上述错误信息")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
