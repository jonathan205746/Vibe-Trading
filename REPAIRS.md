# Vibe-Trading 修复报告

## 迁移完成 ✅
项目已从 `~/.openclaw/workspace/Vibe-Trading/` 迁移到 `~/.openclaw/workspace/projects/Vibe-Trading/`

## 已修复的问题

### 1. 数据源修复 ✅
**问题**: `investment_committee` 预设使用 `yfinance` 技能，A股数据被墙，bull代理全部失败
**修复**: 将 `yfinance` 替换为 `akshare`（免费A股数据源）
**文件**: `agent/src/swarm/presets/investment_committee.yaml`

### 2. CLI 变量映射修复 ✅
**问题**: 用户传 `{"topic": "..."}` 但预设期望 `{"target": "...", "market": "..."}`，导致 bear 代理分析 NVDA 而不是远程股份
**修复**: 在 CLI 中添加自动映射逻辑
- `topic` → `target`
- `goal` → `target`  
- 自动检测 market（A股/港股/美股/加密）
**文件**: `agent/cli.py`（cmd_swarm_run_live 和 cmd_swarm_run 函数）

### 3. A股预设优化 ✅
**优化内容**:
- 每个代理的 system_prompt 内置 akshare 代码模板
- 明确指示代理使用 bash 工具运行 Python + akshare 获取数据
- 禁用回测（代码生成不稳定，浪费迭代）
- 减少最大迭代次数：bull/bear 从 50→30，risk 从 50→20，PM 从 50→25
- 超时时间统一为 300 秒

### 4. load_skill 健壮性修复 ✅
**问题**: DeepSeek 调用 `load_skill` 时偶尔不传 `name` 参数，导致 KeyError
**修复**: `load_skill_tool.py` 已包含兼容逻辑（回退到遍历 kwargs 找字符串值）
**状态**: 代码已修复，但运行时可能还有旧缓存问题

## 还存在的问题

### 1. Python 模块路径问题 ⚠️
**症状**: `ModuleNotFoundError: No module named 'src'`
**原因**: 项目使用相对导入 `from src.agent.tools import ...`，但 PYTHONPATH 设置不正确
**影响**: 直接运行 Python 测试脚本失败，但通过 `vibe-trading` 命令可以正常工作（因为它设置了正确的路径）

### 2. 回测代码生成不稳定 ⚠️
**症状**: PM 代理尝试自动生成回测代码，但代码质量不稳定：
- "SignalEngine class not found"
- "'SignalEngine' object has no attribute 'generate'"
- "Columns must be same length as key"
**解决**: 已在预设中禁用回测（"DO NOT run backtests"），但如果代理忽略指示仍会尝试

## 测试建议

运行以下命令测试修复效果：

```bash
cd ~/.openclaw/workspace/projects/Vibe-Trading
source .venv/bin/activate

# 测试1: 使用正确的变量格式
vibe-trading --swarm-run investment_committee '{"target":"远程股份002692.SZ","market":"A-shares"}'

# 测试2: 使用 topic 变量（验证自动映射）
vibe-trading --swarm-run investment_committee '{"topic":"远程股份002692.SZ"}'

# 测试3: 查看预设列表
vibe-trading --swarm-presets
```

## 下一步可选优化

1. **创建 A股专用预设**: 可以新建 `a_share_investment_committee.yaml`，完全针对A股特性设计
2. **修复 PYTHONPATH**: 在 `pyproject.toml` 或启动脚本中正确设置 PYTHONPATH
3. **添加数据缓存**: 让代理之间共享已下载的数据，避免重复调用 akshare
4. **集成 LubyQuant 数据源**: 让 Vibe-Trading 能直接读取本地 MySQL 数据库的股票数据

---
*报告生成时间: 2026-05-03*
*位置: ~/.openclaw/workspace/projects/Vibe-Trading/REPAIRS.md*
