# DesktopPet Bug Report & Fix Log

Date: 2026-05-21

---

## Bug 1: 快捷键完全不响应（GC 回收 + 方案不可行 → 已放弃）

**严重程度:** Critical  
**现象:** 按 Ctrl+Shift+P 等任何快捷键都没有反应，无通知弹出  
**根因:** `_setup_shortcuts()` 中 `QShortcut` 对象是局部变量 `sc`，for 循环结束后 Python 垃圾回收器立即销毁了这些对象，快捷键注册随之失效

**尝试过的方案（均不可靠）：**

1. **QShortcut + parent=self** — 无效，macOS 后台应用（Tool 窗口）不接收键盘事件
2. **Carbon RegisterEventHotKey** — 注册成功但事件处理器从未被调用，Qt 的 NSApplication 事件循环与 Carbon 事件派发不兼容
3. **PyObjC NSEvent.addGlobalMonitorForEventsMatchingMask** — 模拟输入可通过，但真实键盘输入需要「输入监控」权限，用户难以配置
4. **CGEventTapCreate** — 可以创建但与 Qt 的 CFRunLoop 集成时崩溃 (SIGTRAP)
5. **pynput + 子线程** — 可以工作但需要「输入监控」权限才能捕获真实键盘

**最终决定：放弃全局快捷键，改用托盘菜单操作。**

所有功能（推迟久坐/喝水提醒、暂停提醒）通过托盘菜单可用，无需键盘快捷键。

---

## Bug 2: 托盘通知找不到 tray_icon

**严重程度:** Medium  
**现象:** 宠物触发提醒时（如久坐提醒），不弹出系统通知  
**根因:** `pet_window.py` 的 `_send_notification()` 通过 `self.window().tray_icon` 查找托盘图标，但 `self.window()` 返回的是 PetWindow 自身（顶层窗口），而 `tray_icon` 在 PetApp 上

```python
# BUG: self.window() 返回 PetWindow，PetWindow 没有 tray_icon
icon = self.window().tray_icon if hasattr(self.window(), 'tray_icon') else None
# icon 永远是 None → 通知永远不显示
```

**修复方案:** 遍历 `QApplication.topLevelWidgets()` 查找持有 `tray_icon` 的窗口：

```python
for widget in QApplication.topLevelWidgets():
    if hasattr(widget, 'tray_icon') and widget.tray_icon:
        widget.tray_icon.showMessage(...)
        return
```

**修复文件:** [pet_window.py](pet_window.py) `_send_notification()` 方法

---

## Bug 3: toggle_pause 在无宠物时无效

**严重程度:** Medium  
**现象:** 在上传宠物照片之前按 Ctrl+Shift+P 没有任何反应（托盘也不弹通知）  
**根因:** `_shortcut_toggle_pause()` 依赖 `self.pet_window` 存在才执行，首次启动未上传照片时 `pet_window` 为 None，整个函数被跳过

```python
# BUG: pet_window 为 None 时直接跳过
def _shortcut_toggle_pause(self):
    if self.pet_window and self.pet_window.settings:  # False → 整个函数什么都不做
        ...
```

**修复方案:** 直接操作 `self.settings`（主应用设置），`pet_window` 仅为可选的定时器重置：

```python
def _shortcut_toggle_pause(self):
    s = self.settings  # 直接用主应用设置
    both_paused = s.get("water_paused") and s.get("sit_paused")
    s["water_paused"] = not both_paused
    s["sit_paused"] = not both_paused
    if self.pet_window:
        self.pet_window._sit_timer = 0
        self.pet_window._water_timer = 0
    self._save_settings()
    if self.tray_icon:
        self.tray_icon.showMessage(...)
```

**修复文件:** [app.py](app.py) `_shortcut_toggle_pause()` 方法

---

## Bug 4: 玳瑁猫被识别为黑白双色

**严重程度:** Medium  
**现象:** 上传玳瑁猫（tortoiseshell）照片，识别结果为黑白双色（bicolor）  
**根因:**
1. `orange` 颜色桶亮度阈值（150）过高，玳瑁猫较暗的橙棕色区域无法被归类为暖色
2. `black + white` 合计 > 55% 时强制覆盖主色为黑或白，未检查暖色比例

**修复方案:**
1. 降低 `orange` 亮度阈值 150→100，`cream` 亮度阈值 200→140，扩大 hue 范围
2. 新增 `WARM_COLORS` 聚合集合，暖色比例 > 8% 时跳过黑白覆盖
3. 重写 `_detect_pattern()`：先检测 calico（暖+暗+白三色）和 tortie（暖+暗双色），再 fallback 到 bicolor

```python
WARM_COLORS = {"orange", "brown", "cream", "red", "chocolate"}

# 暖色保护：不覆盖为双色
if warm_pct > 8:
    pass  # 保留排序后的主色
elif black_pct + white_pct > 55:
    # 原来的黑白覆盖逻辑
```

**修复文件:** [vision/pet_recognizer.py](vision/pet_recognizer.py)

---

## Bug 5: AssetLoader 状态目录名不匹配

**严重程度:** Low  
**现象:** 部分动画状态（如鼠标靠近、跟随）加载不到帧，回退到默认动画  
**根因:** `STATE_DIR_MAP` 中的目录名与实际 assets 目录结构不一致

| PetState | 映射的目录名 | 实际目录名 |
|----------|-------------|-----------|
| MOUSE_NEAR | `mouse_near` | `near` |
| FOLLOW_MOUSE | `follow_mouse` | `follow` |

**修复方案:** 将映射改为实际目录名：

```python
PetState.MOUSE_NEAR: "near",      # was "mouse_near"
PetState.FOLLOW_MOUSE: "follow",  # was "follow_mouse"
```

**修复文件:** [utils/asset_loader.py](utils/asset_loader.py) `STATE_DIR_MAP`

---

## 自动化测试验证

所有修复均通过 [test_callback_direct.py](test_callback_direct.py) 和 [test_functional.py](test_functional.py) 验证：

```
Test 1: App imports and starts                       ✅
Test 2: 托盘菜单项完整 (7 items)                      ✅
Test 3: 暂停/恢复切换逻辑正确                          ✅
Test 4: 推迟提醒不崩溃 (无 pet_window 时)              ✅
Test 5: 设置对话框行为正确                              ✅
Test 6: 视觉识别 (玳瑁猫 = tortie)                    ✅
Test 7: 状态机转换正确                                 ✅
Test 8: 提醒定时器触发通知 (5秒间隔测试)                ✅
```
