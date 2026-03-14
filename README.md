# house-cli

一行命令搜全平台房源，买房租房不用再四个 App 来回切。

支持贝壳/链家、自如、安居客、58同城、房天下、诸葛找房 6 个平台，数据自动归一化，终端内完成搜索、对比、月供计算。

## 安装

需要 Python 3.12+，推荐使用 [uv](https://docs.astral.sh/uv/)：

```bash
git clone https://github.com/luxuzhou/house-cli.git
cd house-cli
uv sync
```

## 使用

```bash
# 搜索上海浦东 500 万以内的两室
uv run house search --city 上海 --district 浦东 --max-price 500 --layout 2室

# 指定平台搜索
uv run house search --platform beike --city 杭州

# 查看房源详情
uv run house detail beike:abc123

# 对比两套房
uv run house compare beike:abc123 anjuke:def456

# 月供计算（总价 300 万，首付 30%，30 年）
uv run house mortgage --total 300 --down-payment 0.3 --years 30

# 导出搜索结果
uv run house export --format csv

# JSON 输出（可供其他工具消费）
uv run house search --city 上海 --output json
```

## 支持平台

| 平台 | 买房 | 租房 |
|------|:----:|:----:|
| 贝壳/链家 | ✅ | ✅ |
| 自如 | — | ✅ |
| 安居客 | ✅ | ✅ |
| 58同城 | ✅ | ✅ |
| 房天下 | ✅ | ✅ |
| 诸葛找房 | ✅ | ✅ |

## 命令一览

| 命令 | 说明 |
|------|------|
| `search` | 多平台聚合搜索 |
| `detail` | 查看房源详情 |
| `compare` | 并排对比多套房 |
| `analyze` | 区域房价分析 |
| `mortgage` | 月供计算器（等额本息/等额本金） |
| `watch` | 房源价格监控 |
| `export` | 导出搜索结果为 CSV/JSON |

## 项目背景

这个项目是多模型并行开发的实践案例——3 个 AI Agent（Claude Code + Codex CLI）通过 git worktree 同时开发不同模块，详见 [这篇文章](https://mp.weixin.qq.com/s/xxx)。

## License

MIT
