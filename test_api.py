"""
Test the recommendation API for multiple users
"""
import requests
import json

def test_user_recommendations():
    """Test recommendations for multiple users"""
    print("\n" + "="*60)
    print("测试推荐系统 API")
    print("="*60)

    base_url = "http://127.0.0.1:8000/api/user"

    # Test users: 1, 100, 500, 1000
    test_users = [1, 100, 500, 1000]

    for user_id in test_users:
        url = f"{base_url}/{user_id}/recommendations/"
        params = {'limit': 3}

        try:
            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()

                print(f"\n{'='*60}")
                print(f"用户 {user_id} 的推荐 (Top 3)")
                print(f"{'='*60}")

                for i, rec in enumerate(data['recommendations'], 1):
                    print(f"{i}. {rec['title']}")
                    print(f"   预测评分: {rec['predicted_rating']} | 平均评分: {rec['avg_rating']} ({rec['rating_count']} 个评分)")
                    print(f"   类型: {rec['genres']}")
                    print()
            else:
                print(f"\n❌ 用户 {user_id} - API 错误: {response.status_code}")

        except Exception as e:
            print(f"\n❌ 用户 {user_id} - 请求失败: {str(e)}")

    print("\n" + "="*60)
    print("✅ API 测试完成")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_user_recommendations()
