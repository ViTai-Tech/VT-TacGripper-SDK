# 🛠️ 使用指南

本页覆盖从安装到首次动作验证的完整流程：**安装 → 权限 → 发现设备 → 标定 → 验证**。

> 💡 **建议顺序**
> 新夹爪首次使用请按本页顺序执行；已标定且通信正常的夹爪可直接从“验证”开始。

---

## ✅ 开始前检查

| 检查项 | 要求 |
| --- | --- |
| Python | 3.10 或 3.12，与 wheel 的 cp310/cp312 匹配 |
| 适配器 | USB2CANFD 已连接，USB 线无松动 |
| 电机 | 已供电；新电机需完成通信配置 |
| 夹爪 | 已安装好夹头，行程内无遮挡 |
| 环境 | 标定时夹爪空载，机构牢固 |
| 软件 | 已安装 `VT-TacGripper-SDK` wheel |

---

## 📦 安装

从 [Releases](https://github.com/ViTai-Tech/VT-TacGripper-SDK/releases) 下载与 Python 版本匹配的 wheel：

- Python 3.10：`vt_tacgripper_sdk-1.1.0-cp310-cp310-linux_x86_64.whl`
- Python 3.12：`vt_tacgripper_sdk-1.1.0-cp312-cp312-linux_x86_64.whl`

```bash
# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装 wheel（按实际 Python 版本选择）
pip install ./vt_tacgripper_sdk-1.1.0-cp310-cp310-linux_x86_64.whl
```

验证安装：

```bash
python -c "import VT_TacGripper; print(VT_TacGripper.__version__)"
```

预期输出：

```text
1.1.0
```

> 💡 **说明**
> wheel 已自带运行库，不需要额外安装 Python 依赖。Python 3.11 或其他平台没有对应的 1.1.0 wheel。

---

## 🔐 设备权限（udev）

Linux 下普通用户需要 udev 规则才能访问 USB2CANFD 适配器。

```bash
# 查看当前权限规则
python -m VT_TacGripper.tools.install_udev --status

# 安装规则（需要 root）
sudo -E python -m VT_TacGripper.tools.install_udev --install
```

安装后**拔插适配器**，再确认：

```bash
python -m VT_TacGripper.tools.install_udev --status
python -m VT_TacGripper.tools.list_devices
```

> ⚠️ **注意**
> 安装 udev 规则只需一次。日常运行 SDK 和工具时不要使用 `sudo`。

卸载规则：

```bash
sudo -E python -m VT_TacGripper.tools.install_udev --uninstall
```

---

## 🔍 发现设备与首次配置

### 1. 枚举适配器

```bash
python -m VT_TacGripper.tools.list_devices
```

记下输出中的适配器 SN。后续命令中的 `<SN>` 都替换为这个值；只有一个适配器时部分工具可省略 `--sn`，但建议显式填写。

### 2. 检查电机通信参数

新电机或更换电机后，先只读检查：

```bash
python -m VT_TacGripper.tools.configure_motor --sn <SN> --check
```

- 如果提示**参数一致**：无需写入，直接进入标定。
- 如果提示**存在差异**：运行写入命令，确认后保存：

```bash
python -m VT_TacGripper.tools.configure_motor --sn <SN>
```

写入完成后按提示**断电至少 5 秒**，重新上电，再执行一次 `--check` 确认掉电保持。

### 3. 确认运行状态

```bash
python -m VT_TacGripper.tools.diagnose --sn <SN>
```

如果要看实时温度、位置、速度、力矩，需要加 `--enable`：

```bash
python -m VT_TacGripper.tools.diagnose --sn <SN> --enable
```

`--enable` 会在诊断期间使能并保持当前位置，读取后自动失能。温度来自反馈帧；未使能时显示“无反馈”，不是真实的 0 °C。

> 💡 **已有配置的夹爪**
> 如果夹爪已经能正常通信和运动，可跳过本节的通信配置，直接标定或验证。

---

## 🎯 标定

标定用于建立“行程单位 ↔ 电机弧度”的映射，并记录张开/闭合限位。

### 何时需要标定

- 首次使用夹爪
- 更换夹头、夹爪或机构
- 更换电机、重新安装电机
- 配置文件丢失或限位明显漂移
- 夹爪动作顶住机械限位、开合范围不正确

### 安全要求

> ⚠️ **标定会产生机械受力**
> 标定过程中夹爪会向两端机械限位缓慢顶住，并可能重设零点。请确保：
>
> - 夹爪**空载**，不要夹持工件；
> - 行程内**没有手、工具或遮挡物**；
> - 夹爪与机构固定牢固；
> - 电源稳定，急停/断电方式可用。

### 自动标定

```bash
python -m VT_TacGripper.tools.calibrate \
  --sn <SN> \
  --product-model VT-TacGripper-85-S \
  --config ./devices.json
```

首次注册时 `--product-model` 用于确定几何类型、行程单位和默认参数：

| 夹爪 | `--product-model` |
| --- | --- |
| VT-TacGripper-85-S | `VT-TacGripper-85-S` |
| VT-TacGripper-85-L | `VT-TacGripper-85-L` |
| VT-TacGripper-Slim | `VT-TacGripper-Slim` |

常用选项：

| 选项 | 说明 |
| --- | --- |
| `--force 3.0` | 标定扫描力（Nm）；默认 3.0 |
| `--dry-run` | 只扫描并打印结果，不写入配置 |
| `--yes` | 跳过确认提示 |
| `--no-center-zero` | 不把零点重设到行程中点 |
| `--margin-ratio 0.01` | 限位按跨度比例内缩；默认 1% |
| `--config ./devices.json` | 指定一机一码配置路径 |

预期输出会包含：

```text
张开限位: ...
闭合限位: ...
有效跨度: ...（安全边距 ...）
零点: ...
力上限: ... Nm  扫描速度: ... rad/s
已写入配置：.../devices.json
```

> 💡 **零点重设**
> 默认会把电机零点重设到行程中点，使全行程落在 ±π 内，降低断电后编码器别名错位导致行程失效的风险。这是正常行为，标定后的 `open_rad`/`close_rad` 会相应平移。

### 手动示教

自动标定后如需微调边界，使用 `teach`：

```bash
python -m VT_TacGripper.tools.teach \
  --sn <SN> \
  --config ./devices.json
```

启动时 `teach` 会显式使能并保持当前位置。退出时默认保持当前使能状态；需要退出失能请加 `--disable-on-exit`，或在交互中输入 `d`。常用命令：

| 命令 | 作用 |
| --- | --- |
| `p` | 打印位置、速度、力矩、使能状态、控制模式和行程 |
| `m 40` | 运动到 40 mm（圆弧夹爪为 40°） |
| `j 30` | 以 30% 速度向**张开**方向点动 |
| `j -30` | 以 30% 速度向**闭合**方向点动 |
| `s` | 停止并保持当前位置 |
| `o` | 把当前位置记录为**张开限位** |
| `c` | 把当前位置记录为**闭合限位** |
| `e` / `d` | 使能 / 失能 |
| `r` | 清除电机故障并重新使能 |
| `q` | 退出（默认保持使能；先 `d` 或使用 `--disable-on-exit` 可失能） |

> ⚠️ **谨慎使用 `o` / `c`**
> 这两个命令会覆盖当前标定限位。只有在确认当前位置正确时才记录；普通动作验证不要按 `o`/`c`。

手动示教只更新限位，不执行自动标定的零点重设和边距计算。建议先完成自动标定，再用 `teach` 微调。

---

## ✅ 验证

标定完成后，用以下两种方式验证。**建议至少执行一次代码验证**；现场调试可先用 `teach`。

### 🕹️ 方式一：`teach`

```bash
python -m VT_TacGripper.tools.teach \
  --sn <SN> \
  --config ./devices.json
```

按以下顺序操作：

| 步骤 | 输入 | 预期结果 |
| --- | --- | --- |
| 1 | `p` | 显示 `使能 是`、`模式 POS_FORCE`、位置和行程 |
| 2 | `m 40` | 夹爪运动到约 40 mm（85-S/L）或 40°（Slim） |
| 3 | `s` | 停止并保持当前位置 |
| 4 | `d` | 显示 `已失能`，`p` 显示 `使能 否` |
| 5 | `m 40` | 提示 `电机未使能，请先输入 e`，不会运动 |
| 6 | `e` | 显示 `已使能`，夹爪保持当前位置 |
| 7 | `r` | 清除故障并重新使能；无故障时也显示成功 |
| 8 | `q` | 退出；默认保持使能；先 `d` 或使用 `--disable-on-exit` 可失能 |

> 💡 **启动为什么直接锁死？**
> `teach` 启动时会显式使能并保持当前位置。因此即使没有输入 `e`，夹爪也会处于使能保持状态；退出默认也保持使能。这是预期行为。

### 🐍 方式二：Python 代码

```python
from VT_TacGripper import VTacGripper

SN = "<SN>"

g = VTacGripper(SN, config_path="./devices.json")
try:
    g.enable()  # 显式使能并保持当前位置
    print(f"SN={g.sn}  单位={g.unit}  已标定={g.is_calibrated}")
    print(f"初始: {g.position:.2f}{g.unit}  {g.torque:+.3f} Nm")

    g.open(block=True)
    print(f"张开: {g.position:.2f}{g.unit}")

    g.close(block=True)
    print(f"闭合: {g.position:.2f}{g.unit}")

    g.move(40, vel=50, force=50, block=True)
    print(f"中间: {g.position:.2f}{g.unit}  {g.torque:+.3f} Nm")
    print(f"状态: {g.error()}  故障={g.state.faulted}")
finally:
    g.disable()   # 想保持使能时省略这一行
    g.release()
```

预期结果：

- 位置能到达张开位、闭合位和中间位置；
- 不抛出异常；
- `g.state.faulted` 为 `False`；
- `g.position` 在 `0–travel` 范围内（圆弧夹爪为 `0–118°` 量级）；
- 重复开合 3 次仍稳定。

> 💡 **生命周期**
> 构造默认不使能；`enable()` 显式使能，`disable()` 显式失能。`release()` 只停止发送流并释放句柄，**不改变使能状态**。验证示例用实例化写法，便于看清 `enable/disable/release` 的调用顺序。

也可用示例脚本做快速验证：

```bash
python examples/check_devices.py --config ./devices.json
python examples/motion.py --sn <SN> --config ./devices.json --action cycle
```

### 🧪 判定标准

| 检查项 | 通过标准 |
| --- | --- |
| 张开/闭合 | 能稳定到达标定限位附近，无异常停顿 |
| 中间位置 | `move()` 能到达目标，位置误差在容差内 |
| 状态 | `error()` 为 `使能`，`state.faulted` 为 `False` |
| 重复性 | 连续开合 3 次位置和动作稳定 |
| 配置 | `--config` 指向的 `devices.json` 中存在该 SN 且 `calibrated=true` |

---

## 🧰 常用命令

```bash
# 枚举适配器
python -m VT_TacGripper.tools.list_devices

# 检查通信参数（只读）
python -m VT_TacGripper.tools.configure_motor --sn <SN> --check

# 自动标定
python -m VT_TacGripper.tools.calibrate \
  --sn <SN> --product-model VT-TacGripper-85-S --config ./devices.json

# 手动示教（退出默认保持使能；需退出失能加 --disable-on-exit）
python -m VT_TacGripper.tools.teach --sn <SN> --config ./devices.json

# 状态诊断
python -m VT_TacGripper.tools.diagnose --sn <SN>

# 设备权限
python -m VT_TacGripper.tools.install_udev --status
```

---

## 🧯 常见问题

| 现象 | 处理 |
| --- | --- |
| `未发现任何 U2CANFD 适配器` | 检查 USB、供电和 udev 权限；重新拔插后运行 `list_devices` |
| `配置中不存在 SN=...` | 首次使用需提供 `--product-model`，或使用 `auto_register=True` / `teach` 的自动注册 |
| `尚未标定开闭限位` | 先运行 `calibrate`，或手动 `teach` 记录 `o`/`c` |
| 标定未达到力阈值 | 检查机构是否卡住；必要时提高 `--force`；先用 `--dry-run` 观察 |
| `POS_VEL` 下 `force` 无效 | POS_VEL 协议没有力参数；需要力上限时使用 POS_FORCE |
| 同一进程关闭后无法重新打开 | 这是厂商运行库限制；重启进程 |
| 同时运行 `teach` 和程序失败 | 同一适配器不能被两个进程同时占用；只保留一个控制进程 |
| 程序退出后夹爪仍保持使能 | 这是显式生命周期设计；在 `teach` 中先 `d`，或代码中调用 `g.disable()`；`teach --disable-on-exit` 可退出失能 |
| 夹爪不动作但显示已使能 | 检查 `state.faulted`、供电、限位和 `diagnose` 输出；必要时 `r` 清错 |

更多错误文本、电机状态码和恢复步骤见 [错误码与异常](./04-errors.md)。
