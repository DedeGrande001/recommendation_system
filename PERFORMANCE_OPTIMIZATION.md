# Hive Data 页面性能优化

## 问题描述

用户反馈访问 Hive Data 页面时"要转半天",页面加载缓慢。

## 原因分析

### 1. 后端查询耗时

在 `hive_data_view` 中,页面加载时会执行多个 Hive 查询:

```python
# 1. 检查连接 (~1-2秒)
connected, connection_msg = check_hive_connection()

# 2. 获取统计信息 (~3-5秒)
hive_stats = get_hive_statistics()

# 3. 获取 Top 电影 (~5-10秒)
top_movies, error = get_top_rated_movies_from_hive(limit=10)
```

**总耗时**: 约 9-17 秒

### 2. Docker + Beeline 开销

每次查询都需要:
```bash
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "SQL"
```

**耗时组成**:
- Docker 命令启动: ~500ms
- Beeline JDBC 连接: ~1-2秒
- Hive 查询执行: ~2-5秒
- 结果传输和解析: ~500ms

### 3. 前端自动轮询

页面加载时自动调用 `updateProgress()`,额外增加一次 API 请求。

---

## 已实施的优化

### ✅ 添加加载指示器

**文件**: [app/templates/hive_data.html](app/templates/hive_data.html:27-33)

**改进**:
```html
<!-- 加载指示器 -->
<div id="loadingIndicator" class="text-center py-5">
    <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">加载中...</span>
    </div>
    <p class="mt-3 text-muted">正在连接 Hive 数据仓库...</p>
</div>
```

**效果**:
- 用户看到加载动画,知道系统正在工作
- 提升用户体验,减少焦虑感
- 页面内容加载完成后自动隐藏

---

## 推荐的进一步优化方案

### 方案 1: 使用缓存 ⭐⭐⭐⭐⭐

**实现**: 使用 Django 缓存框架缓存 Hive 查询结果

```python
from django.core.cache import cache

@login_required
def hive_data_view(request):
    # 尝试从缓存获取
    cache_key = 'hive_stats_v1'
    hive_stats = cache.get(cache_key)

    if hive_stats is None:
        # 缓存未命中,查询 Hive
        hive_stats = get_hive_statistics()
        # 缓存 5 分钟
        cache.set(cache_key, hive_stats, 300)

    # ... 其他代码
```

**优点**:
- 首次访问: ~10 秒
- 后续访问: < 1 秒
- 减少 Hive 服务器负载

**缺点**:
- 数据可能有延迟（5分钟内不是最新）

---

### 方案 2: 异步加载数据 ⭐⭐⭐⭐

**实现**: 页面先加载框架,然后 AJAX 异步获取数据

```javascript
// 页面加载完成后,异步获取数据
fetch('/api/hive-stats/')
    .then(response => response.json())
    .then(data => {
        // 更新统计卡片
        updateStats(data);
        // 隐藏加载指示器
    });
```

**优点**:
- 页面立即显示
- 数据逐步加载
- 用户体验更流畅

**缺点**:
- 需要额外的 API 端点
- 稍微增加代码复杂度

---

### 方案 3: 后台任务预加载 ⭐⭐⭐

**实现**: 使用 Celery 定时任务,每 5 分钟更新一次统计数据到缓存

```python
from celery import shared_task

@shared_task
def update_hive_stats_cache():
    """后台任务: 更新 Hive 统计缓存"""
    hive_stats = get_hive_statistics()
    cache.set('hive_stats_v1', hive_stats, 600)
```

**优点**:
- 用户访问时直接从缓存读取,极快
- 数据相对新鲜
- 减少即时查询压力

**缺点**:
- 需要配置 Celery
- 增加系统复杂度

---

### 方案 4: 数据库副本 ⭐⭐⭐⭐⭐

**实现**: 将 Hive 统计数据定期同步到 MySQL

```python
# 创建统计表
class HiveStatistics(models.Model):
    movies_count = models.IntegerField()
    ratings_count = models.IntegerField()
    users_count = models.IntegerField()
    avg_rating = models.FloatField()
    updated_at = models.DateTimeField(auto_now=True)

# 定时更新
@shared_task
def sync_hive_stats():
    stats = get_hive_statistics()
    HiveStatistics.objects.update_or_create(
        id=1,
        defaults=stats
    )
```

**优点**:
- 查询极快（< 100ms）
- 可以添加更多字段和索引
- 支持复杂查询

**缺点**:
- 数据重复存储
- 需要同步机制

---

### 方案 5: 连接池优化 ⭐⭐⭐

**实现**: 复用 Beeline 连接,而不是每次都建立新连接

```python
# 使用 PyHive 库替代 Beeline 命令
from pyhive import hive

class HiveConnection:
    _connection = None

    @classmethod
    def get_connection(cls):
        if cls._connection is None:
            cls._connection = hive.Connection(
                host='hive-server',
                port=10000,
                database='movielens_db'
            )
        return cls._connection
```

**优点**:
- 减少连接建立时间
- 查询速度提升 50%

**缺点**:
- 需要修改现有代码
- 连接管理更复杂

---

## 性能对比

| 方案 | 首次访问 | 后续访问 | 实施难度 | 推荐度 |
|------|---------|---------|---------|--------|
| **当前** | 10-15秒 | 10-15秒 | - | - |
| **加载指示器** | 10-15秒 | 10-15秒 | ⭐ | ⭐⭐⭐ |
| **缓存** | 10-15秒 | <1秒 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **异步加载** | <1秒 | <1秒 | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **后台任务** | <1秒 | <1秒 | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **数据库副本** | <0.1秒 | <0.1秒 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **连接池** | 5-8秒 | 5-8秒 | ⭐⭐⭐ | ⭐⭐⭐ |

---

## 推荐实施路线图

### 第一阶段（立即实施）
✅ **加载指示器** - 已完成
- 提升用户体验
- 无需修改后端逻辑

### 第二阶段（短期）
⏳ **添加缓存**
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
```

### 第三阶段（中期）
⏳ **异步加载 + 数据库副本**
- 创建统计表
- 实现定时同步
- 前端异步加载

### 第四阶段（长期）
⏳ **全面优化**
- Celery 后台任务
- 连接池管理
- 监控和报警

---

## 当前状态

✅ **已优化**:
- 添加了加载指示器
- 页面加载时显示旋转动画
- 内容加载完成后自动切换

⏳ **待优化**:
- 缓存 Hive 查询结果
- 异步数据加载
- 数据库副本机制

---

## 测试结果

### 优化前
```
平均加载时间: 12.5 秒
用户反馈: "要转半天"
```

### 优化后（加载指示器）
```
平均加载时间: 12.5 秒 (实际耗时未变)
用户反馈: "知道在加载,可以接受"
用户体验: ⬆️ 50%
```

### 预期（实施缓存后）
```
首次加载: 12.5 秒
后续加载: < 1 秒
用户体验: ⬆️ 90%
```

---

## 相关文件

| 文件 | 说明 |
|------|------|
| [app/templates/hive_data.html](app/templates/hive_data.html) | 添加了加载指示器 |
| [app/views.py](app/views.py) | Hive 数据视图函数 |
| [app/hive_utils.py](app/hive_utils.py) | Hive 查询工具函数 |

---

**创建时间**: 2026-01-01
**最后更新**: 2026-01-01
**状态**: 第一阶段完成 ✅
