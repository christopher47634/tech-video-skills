# Tech Video Skills

用 HTML/CSS 动画 + Playwright 逐帧截图 + FFmpeg 合成，程序化生产高质量技术科普视频。

不依赖 Premiere、After Effects、Remotion 或任何 npm 生态。纯 Python + Chromium + FFmpeg。

## 效果预览

适用于：产品介绍、技术科普、数据可视化、社媒短视频、教程演示。

支持的场景组件：终端窗口、代码编辑器、AI 对话、数据指标卡片、标题页、结尾 CTA。

---

## 目录

- [工作流总览](#工作流总览)
- [环境准备](#环境准备)
- [Step 1: 生成 TTS 语音 + 字幕](#step-1-生成-tts-语音--字幕)
- [Step 2: 编写 HTML 场景](#step-2-编写-html-场景)
- [Step 3: Playwright 逐帧截图](#step-3-playwright-逐帧截图)
- [Step 4: FFmpeg 合成视频](#step-4-ffmpeg-合成视频)
- [Step 5: SFX + BGM 音效层](#step-5-sfx--bgm-音效层)
- [Step 6: 最终混音 + 替换音轨](#step-6-最终混音--替换音轨)
- [动画设计原则](#动画设计原则)
- [组件库](#组件库)
- [字体渲染](#字体渲染)
- [踩坑记录](#踩坑记录)
- [定稿参数速查](#定稿参数速查)

---

## 工作流总览

```
稿子文本
   │
   ▼
edge-tts ──→ voiceover.mp3 + voiceover.vtt
   │
   ▼
HTML/CSS 场景文件 (scenes.html)
   │
   ▼
Playwright 逐帧截图 (frame_00000.png ~ frame_07049.png)
   │
   ▼
FFmpeg 编码视频流 (libx264, 30fps)
   │
   ▼
SFX 生成 (FFmpeg 合成) + BGM 素材
   │
   ▼
逐条叠加混音 (voiceover + SFX + BGM)
   │
   ▼
替换音轨 → 最终输出 MP4
```

**核心理念**：HTML 写场景，Playwright 截帧，FFmpeg 合成。不碰 npm，不碰 Remotion，不碰 After Effects。

---

## 环境准备

### 依赖

```bash
# Python 3.10+
pip install playwright

# Playwright 浏览器
playwright install chromium
# 或者用系统 Chromium（WSL 推荐）:
sudo snap install chromium

# TTS
pip install edge-tts

# FFmpeg
sudo apt install ffmpeg
```

### WSL 特殊配置

Playwright 自带的 Chromium 在 WSL 下路径会指向 Windows temp 目录导致报错。必须指定系统 Chromium：

```python
browser = p.chromium.launch(
    headless=True,
    executable_path='/snap/bin/chromium',  # WSL 必须指定
    args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
)
```

### 字体

中文字体用本地文件，不用 Google Fonts CDN（headless Chromium 会静默失败，中文变方块）。

推荐 [LXGW WenKai](https://github.com/lxgw/LxgwWenKai)：

```bash
# 下载字体
mkdir -p ~/.local/share/fonts
wget -O ~/.local/share/fonts/LXGWWenKai-Regular.ttf \
  "https://github.com/lxgw/LxgwWenKai/releases/download/v1.330/LXGWWenKai-Regular.ttf"
```

---

## Step 1: 生成 TTS 语音 + 字幕

```bash
edge-tts --voice zh-CN-XiaoxiaoNeural \
  --text "$(cat script.txt)" \
  --write-media voiceover.mp3 \
  --write-subtitles voiceover.vtt
```

`--write-subtitles` 同时生成精确的 VTT 时间戳，后续字幕和场景边界都依赖它。

**不要加 `--rate`**。原始语速最自然。如果用户要求快节奏才加 `--rate="+15%"`，此时必须同时重新生成 media 和 subtitles——两个文件的时间戳完全不同，不能混用。

### VTT 示例

```
WEBVTT

00:00:00.100 --> 00:00:03.587
Vibe Coding，是一种全新的编程方式

00:00:03.537 --> 00:00:08.075
你不需要写每一行代码，只需要描述你想要什么
```

解析为 Python 数组：

```python
SUBTITLES = [
    [0.100, 3.587, "Vibe Coding，是一种全新的编程方式"],
    [3.537, 8.075, "你不需要写每一行代码，只需要描述你想要什么"],
    # ...
]
```

---

## Step 2: 编写 HTML 场景

单个 HTML 文件包含所有场景，用 CSS 类控制显隐和动画。

### 基本结构

```html
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<style>
  /* 字体、变量、场景、动画 */
</style>
</head>
<body>

<!-- 背景网格 -->
<div class="bg-grid"></div>

<!-- HUD 叠加层 -->
<div class="hud">...</div>

<!-- 字幕层 -->
<div class="subtitle-bar">
  <div class="subtitle-text" id="subtitleText"></div>
</div>

<!-- 场景 -->
<div class="scene active" id="s0"><!-- 标题 --></div>
<div class="scene" id="s1"><!-- 终端 --></div>
<div class="scene" id="s2"><!-- 代码编辑器 --></div>
<div class="scene" id="s3"><!-- AI 对话 --></div>
<div class="scene" id="s4"><!-- 数据指标 --></div>
<div class="scene" id="s5"><!-- 结尾 --></div>

</body>
</html>
```

### CSS 变量

```css
:root {
  --bg: #FBF7F0;
  --surface: #FFFFFF;
  --text: #1F2937;
  --muted: #9CA3AF;
  --border: #E5E0D8;
  --cyan: #0891B2;
  --purple: #7C3AED;
  --green: #059669;
  --mono: 'JetBrains Mono', 'LXGW WenKai', monospace;
  --sans: 'LXGW WenKai', -apple-system, sans-serif;
}
```

**`--mono` 必须加 LXGW WenKai fallback**，否则 JetBrains Mono 下的中文会变方块。

### 场景显隐

```css
.scene {
  position: absolute;
  inset: 0;
  opacity: 0;
  pointer-events: none;
}
.scene.active {
  opacity: 1;
  pointer-events: auto;
}
```

### 字体加载

```css
@font-face {
  font-family: 'LXGW WenKai';
  src: url('file:///home/YOUR_USER/.local/share/fonts/LXGWWenKai-Regular.ttf') format('truetype');
}
```

**绝对不要用 `@import url('https://fonts.googleapis.com/...')`**。Headless Chromium 会静默加载失败，中文全部变方块。

---

## Step 3: Playwright 逐帧截图

```python
#!/usr/bin/env python3
"""capture.py — Playwright frame capture."""
import os, shutil, json
from playwright.sync_api import sync_playwright

HTML_PATH = "/path/to/scenes.html"
FRAMES_DIR = "/tmp/frames"
FPS = 30
DURATION = 23.5  # 秒
W, H = 1920, 1080
TOTAL_FRAMES = int(DURATION * FPS)

SUBTITLES = [
    [0.100, 3.587, "字幕文本1"],
    [3.537, 8.075, "字幕文本2"],
]

def main():
    if os.path.exists(FRAMES_DIR):
        shutil.rmtree(FRAMES_DIR)
    os.makedirs(FRAMES_DIR)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path='/snap/bin/chromium',
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        )
        page = browser.new_page(viewport={'width': W, 'height': H})
        page.goto(f'file://{HTML_PATH}')
        page.wait_for_load_state('networkidle')

        page.evaluate(f"window.SUBS = {json.dumps(SUBTITLES)};")

        update_js = """
        (time) => {
          // 场景切换
          document.querySelectorAll('.scene').forEach(s => s.classList.remove('active'));
          let sceneId = time < 4 ? 's0' : time < 9 ? 's1' : time < 14.5 ? 's2'
                      : time < 19 ? 's3' : time < 22 ? 's4' : 's5';
          document.getElementById(sceneId).classList.add('active');

          // HUD 时钟 + 进度条
          let m = Math.floor(time/60), s = Math.floor(time%60);
          document.getElementById('hudTime').textContent =
            String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
          document.getElementById('progressFill').style.width = (time/23.5*100)+'%';

          // 字幕
          let subEl = document.getElementById('subtitleText');
          let txt = '';
          for (let sub of window.SUBS) {
            if (time >= sub[0] && time <= sub[1]) { txt = sub[2]; break; }
          }
          if (txt) { subEl.textContent = txt; subEl.classList.add('visible'); }
          else { subEl.classList.remove('visible'); }

          // 各场景动画（见下方"动画控制"章节）
          // ...
        }
        """

        for i in range(TOTAL_FRAMES):
            t = i / FPS
            page.evaluate(update_js, t)
            page.wait_for_timeout(8)
            page.screenshot(
                path=os.path.join(FRAMES_DIR, f"frame_{i:05d}.png"),
                clip={'x': 0, 'y': 0, 'width': W, 'height': H}
            )

        browser.close()

if __name__ == "__main__":
    main()
```

### 动画控制

所有动画都在 `update_js` 中用 `classList.add('show')` 触发，CSS 负责过渡效果。

**子元素交错入场（Stagger）**：

```js
// Scene 1: 终端行，每 0.35s 出现一行
if (sceneId === 's1') {
    let t = time - 4;
    if (t > 0.2) document.querySelector('#s1 .terminal').classList.add('show');
    for (let i = 0; i <= 9; i++) {
        let e = document.getElementById('tl' + i);
        if (e && t > 0.5 + i * 0.35) e.classList.add('show');
    }
}

// Scene 2: 代码行，每 0.18s 出现一行
if (sceneId === 's2') {
    let t = time - 9;
    if (t > 0.2) document.querySelector('#s2 .editor-wrap').classList.add('show');
    for (let i = 0; i <= 14; i++) {
        let e = document.getElementById('cl' + i);
        if (e && t > 0.8 + i * 0.18) e.classList.add('show');
    }
}

// Scene 3: 对话气泡，每 0.9s 出现一条
if (sceneId === 's3') {
    let t = time - 14.5;
    for (let i = 0; i <= 3; i++) {
        let e = document.getElementById('msg' + i);
        if (e && t > 0.3 + i * 0.9) e.classList.add('show');
    }
}

// Scene 4: 指标卡片 + 数字滚动
if (sceneId === 's4') {
    let t = time - 19;
    for (let i = 0; i <= 2; i++) {
        let e = document.getElementById('mc' + i);
        if (e && t > 0.4 + i * 0.3) {
            e.classList.add('show');
            let p = Math.min(1, (t - 0.4 - i * 0.3) / 1.5);
            if (p > 0) {
                // 数字滚动
                document.getElementById('mv0').textContent = Math.round(p * 10) + 'x';
                document.getElementById('mv1').textContent = Math.round(p * 95) + '%';
                document.getElementById('mv2').textContent = Math.round(p * 5) + 'min';
                // 进度条填充
                document.getElementById('mb0').style.width = (p * 100) + '%';
                document.getElementById('mb1').style.width = (p * 100) + '%';
                document.getElementById('mb2').style.width = (p * 100) + '%';
            }
        }
    }
}
```

### 交错间隔参考值

| 组件 | 间隔 | 原因 |
|------|------|------|
| 终端行 | 0.35s | 需要阅读，不能太快 |
| 代码行 | 0.18s | 快速扫过，体现"AI 生成速度" |
| 侧边栏文件 | 0.15s | 装饰性，快速扫过 |
| 对话气泡 | 0.9s | 最慢，用户需要阅读内容 |
| 指标卡片 | 0.3s | 数字有滚动动画所以稍快 |

---

## Step 4: FFmpeg 合成视频

```bash
ffmpeg -y -framerate 30 -i /tmp/frames/frame_%05d.png -i voiceover.mp3 \
  -c:v libx264 -preset medium -crf 18 \
  -c:a aac -b:a 192k -pix_fmt yuv420p -shortest output.mp4
```

参数说明：
- `-crf 18`：视觉无损，文件大小适中
- `-pix_fmt yuv420p`：兼容性最好（浏览器、手机、社媒平台）
- `-b:a 192k`：音频比特率，128k 也行但 192k 更清晰
- `-shortest`：以最短流为准（视频和音频谁短用谁）

---

## Step 5: SFX + BGM 音效层

### SFX 生成（FFmpeg 纯合成，零外部依赖）

```python
import subprocess

def run(cmd):
    subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)

SFX_DIR = "./sfx"

# 场景切换音效
run(f"ffmpeg -y -f lavfi -i 'anoisesrc=d=0.5:c=white:a=0.6' "
    f"-af 'bandpass=f=2000:width_type=o:w=2,aecho=0.8:0.88:60:0.4,volume=3.0' "
    f"-ar 44100 {SFX_DIR}/whoosh.wav")

# 打字音效
run(f"ffmpeg -y -f lavfi -i 'anoisesrc=d=0.04:c=pink:a=0.8' "
    f"-af 'highpass=f=3000,lowpass=f=8000,volume=4.0' "
    f"-ar 44100 {SFX_DIR}/typing_key.wav")

# 气泡弹出
run(f"ffmpeg -y -f lavfi -i 'sine=f=1000:d=0.12' "
    f"-af 'volume=3.0' "
    f"-ar 44100 {SFX_DIR}/pop.wav")

# 代码行出现
run(f"ffmpeg -y -f lavfi -i 'sine=f=5000:d=0.03' "
    f"-af 'volume=3.0' "
    f"-ar 44100 {SFX_DIR}/tick.wav")

# 数据卡片
run(f"ffmpeg -y -f lavfi -i 'sine=f=1500:d=0.15' "
    f"-af 'volume=3.0' "
    f"-ar 44100 {SFX_DIR}/blip.wav")

# 结尾收束
run(f"ffmpeg -y -f lavfi -i 'sine=f=523:d=1.2' "
    f"-af 'volume=2.0' "
    f"-ar 44100 {SFX_DIR}/chime.wav")
```

### 音量验证（必须！）

每个 SFX 生成后必须检查音量：

```bash
for f in sfx/*.wav; do
  max=$(ffmpeg -i "$f" -af volumedetect -f null /dev/null 2>&1 \
    | grep max_volume | sed 's/.*max_volume: //')
  echo "$(basename $f): $max"
done
```

目标：SFX max > -10 dB。如果低于 -15 dB，说明 FFmpeg 合成源振幅太低，需要提高 `a=` 参数或加 `volume=` 滤镜。

### BGM 素材

推荐使用真实素材而非 FFmpeg 合成（合成 BGM 在低音量下无质感）。

免费素材站：
- [Mixkit](https://mixkit.co/music/) — 免费商用，无需署名
- [Pixabay Music](https://pixabay.com/music/) — 免费商用

下载后处理：

```bash
ffmpeg -y -i bgm-source.mp3 \
  -af "atrim=0:24,asetpts=PTS-STARTPTS,volume=0.08,afade=t=in:d=2,afade=t=out:st=21:d=3" \
  -ar 44100 -ac 1 bgm.wav
```

**不要删除 BGM 源文件**。混音脚本每次修改都需要重新生成，源文件丢了就得重新下载（可能下到不同版本）。

---

## Step 6: 最终混音 + 替换音轨

### 混音策略：逐条叠加（Incremental Overlay）

**不要用 amix 多路归一化**。amix 的 `normalize=0` 不是"不缩放"——它仍然按 1/N 缩放每个输入。N=45 时每个 SFX 被压到 1/45 ≈ 0.022 倍，等于静音。

正确方案：从静音底轨开始，每次只叠一条 SFX（2 路 amix）：

```python
import subprocess, os

DURATION = 23.352
SFX_DIR = "./sfx"
VOICEOVER = "voiceover.mp3"
SFX_VOL = 0.5

SCHEDULE = [
    (0.0, "whoosh.wav"),
    (4.0, "whoosh.wav"),
    (4.5, "typing_key.wav"), (4.9, "typing_key.wav"), (5.3, "typing_key.wav"),
    # ... 更多 SFX 事件
]

def run(cmd):
    subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)

# 1. 生成静音底轨
run(f"ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=mono -t {DURATION} -c:a pcm_s16le /tmp/silence.wav")

# 2. 逐条叠加 SFX
current = "/tmp/silence.wav"
for idx, (time, sfx) in enumerate(SCHEDULE):
    delay_ms = int(time * 1000)
    out = f"/tmp/sfx_step_{idx:03d}.wav"
    run(f"ffmpeg -y -i {current} -i {SFX_DIR}/{sfx} "
        f"-filter_complex "
        f"'[1]adelay={delay_ms}|{delay_ms},volume={SFX_VOL},apad=whole_dur={DURATION}[sfx];"
        f"[0][sfx]amix=inputs=2:duration=first:normalize=0' "
        f"-ar 44100 -ac 1 {out}")
    current = out

# 3. voiceover + BGM
run(f"ffmpeg -y -i {VOICEOVER} -i bgm.wav "
    f"-filter_complex "
    f"'[1]atrim=0:{DURATION},asetpts=PTS-STARTPTS,volume=0.08,aresample=44100[bgm];"
    f"[0]aresample=44100[vo];"
    f"[vo][bgm]amix=inputs=2:duration=first:normalize=0' "
    f"-ar 44100 -ac 1 /tmp/vo_bgm.wav")

# 4. 最终合并
run(f"ffmpeg -y -i /tmp/vo_bgm.wav -i {current} "
    f"-filter_complex "
    f"'[0][1]amix=inputs=2:duration=first:normalize=0,"
    f"alimiter=limit=0.9:attack=5:release=50' "
    f"-ar 44100 -ac 1 mixed-audio.wav")
```

### 音轨替换

```bash
ffmpeg -y -i output.mp4 -i mixed-audio.wav \
  -c:v copy -c:a aac -b:a 192k \
  -map 0:v:0 -map 1:a:0 final.mp4
```

**`-c:v copy` 不重新编码视频流**，只替换音频。如果重新编码会破坏已烘焙的中文字符渲染。

### 混音后验证

```bash
# 对比混音前后
ffmpeg -i mixed-audio.wav -af volumedetect -f null 2>&1 | grep max_volume
ffmpeg -i voiceover.mp3 -af volumedetect -f null 2>&1 | grep max_volume
# 差值 > 1 dB → SFX/BGM 成功混入
# 差值 < 0.1 dB → 混音失败，SFX/BGM 被 amix 吞了
```

---

## 动画设计原则

### 运动曲线

```css
/* 定稿默认：有弹性但不过头 */
cubic-bezier(0.16, 1, 0.3, 1)

/* 标准缓入缓出 */
cubic-bezier(0.25, 0.46, 0.45, 0.94)
```

### 容器入场用组合变换

```css
/* 好：translateY + scale，有重量感 */
.terminal { opacity: 0; transform: translateY(30px) scale(0.97); }
.terminal.show { animation: slideUp 0.7s cubic-bezier(0.16,1,0.3,1) forwards; }

/* 平：只有位移，像 PPT */
.terminal { opacity: 0; transform: translateY(30px); }
```

### 多阶段入场

```
阶段1 (t+0.2s): 容器整体入场
阶段2 (t+0.5s): 子元素交错入场
阶段3 (t+2.0s): 装饰元素延迟出现
```

### 应该用的效果

- 微妙的位移 + 透明度变化 — 专业感
- 固定元素 + 只动内容 — 稳定感
- HUD 叠加层 — 科技感
- 数字滚动 + 进度条同步 — 数据感

### 不要用的效果

- 弹跳（bounce）— 幼稚
- 旋转入场 — 像 PPT
- 过多同时动画 — 眼花缭乱
- 大面积纯色块动画 — 像儿童教育视频

---

## 组件库

### 终端窗口

```html
<div class="terminal">
  <div class="terminal-bar">
    <div class="dot dot-r"></div>
    <div class="dot dot-y"></div>
    <div class="dot dot-g"></div>
    <span class="terminal-title">~/project</span>
  </div>
  <div class="terminal-body">
    <div class="terminal-line" id="tl0">
      <span class="prompt">$</span> <span class="cmd">command here</span>
    </div>
    <div class="terminal-line" id="tl1">
      <span class="output">output text</span>
    </div>
    <div class="terminal-line" id="tl9">
      <span class="prompt">$</span> <span class="cursor-blink"></span>
    </div>
  </div>
</div>
```

```css
.terminal {
  background: #0D1117;
  border-radius: 12px;
  border: 1px solid #21262D;
  box-shadow: 0 8px 40px rgba(0,0,0,0.12);
}
.terminal-bar { background: #161B22; padding: 12px 16px; display: flex; gap: 8px; }
.dot { width: 12px; height: 12px; border-radius: 50%; }
.dot-r { background: #FF5F56; }
.dot-y { background: #FFBD2E; }
.dot-g { background: #27C93F; }
.prompt { color: #3FB950; }
.cmd { color: #E6EDF3; }
.output { color: #8B949E; }
.cursor-blink {
  display: inline-block; width: 10px; height: 20px;
  background: #58A6FF; animation: blink 0.7s step-end infinite;
}
.terminal-line { opacity: 0; transform: translateX(-10px); }
.terminal-line.show { animation: slideRight 0.3s forwards; }
```

### 代码编辑器

三栏布局：侧边栏(260px) + 编辑器(flex:1) + 预览面板(550px)。

```html
<div class="editor-wrap">
  <div class="sidebar">
    <div class="sidebar-header">Explorer</div>
    <div class="file-item active" id="fi0"><span class="file-icon">📄</span> main.tsx</div>
  </div>
  <div class="editor-main">
    <div class="editor-tabs">
      <div class="editor-tab active">main.tsx</div>
    </div>
    <div class="editor-content">
      <div class="code-line" id="cl0">
        <span class="line-num">1</span>
        <span class="line-content"><span class="kw">import</span> ...</span>
      </div>
    </div>
  </div>
  <div class="preview-panel">
    <div class="preview-bar">
      <div class="preview-dot"></div>
      <span>Live Preview — localhost:5173</span>
    </div>
    <div class="preview-content" id="previewContent">
      <div class="preview-card">...</div>
    </div>
  </div>
</div>
```

语法高亮色（米白主题）：

```css
.kw { color: #8B5CF6; }   /* keyword: 紫 */
.fn { color: #2563EB; }   /* function: 蓝 */
.str { color: #059669; }  /* string: 绿 */
.num { color: #D97706; }  /* number: 橙 */
.cmt { color: #9CA3AF; font-style: italic; }  /* comment: 灰 */
.op { color: #0891B2; }   /* operator: 青 */
.type { color: #DC2626; } /* type: 红 */
.var { color: #E11D48; }  /* variable: 玫红 */
```

### AI 对话气泡

```html
<div class="chat-container">
  <div class="msg user" id="msg0">
    <div class="msg-avatar">V</div>
    <div class="msg-bubble">用户消息</div>
  </div>
  <div class="msg ai" id="msg1">
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble">AI 回复</div>
  </div>
</div>
```

```css
.msg { display: flex; gap: 16px; max-width: 80%; opacity: 0; transform: translateY(20px); }
.msg.show { animation: slideUp 0.5s cubic-bezier(0.16,1,0.3,1) forwards; }
.msg.user { align-self: flex-end; flex-direction: row-reverse; }
.msg.ai { align-self: flex-start; }
.msg.user .msg-bubble { background: var(--purple); color: white; border-bottom-right-radius: 4px; }
.msg.ai .msg-bubble { background: var(--surface); border: 1px solid var(--border); border-bottom-left-radius: 4px; }
```

### 数据指标卡片

```html
<div class="metric-card" id="mc0">
  <div class="metric-icon">⚡</div>
  <div class="metric-value cyan" id="mv0">0x</div>
  <div class="metric-label">开发速度提升</div>
  <div class="metric-bar"><div class="metric-bar-fill cyan" id="mb0"></div></div>
</div>
```

数字从 0 滚动到目标值，进度条同步填充。JS 逐帧计算：

```js
let p = Math.min(1, (t - startTime) / 1.5);
document.getElementById('mv0').textContent = Math.round(p * 10) + 'x';
document.getElementById('mb0').style.width = (p * 100) + '%';
```

### HUD 叠加层

```html
<div class="hud">
  <div class="hud-corner hud-tl"></div>
  <div class="hud-corner hud-tr"></div>
  <div class="hud-corner hud-bl"></div>
  <div class="hud-corner hud-br"></div>
  <div class="hud-rec"><div class="rec-dot"></div><span class="rec-label">REC</span></div>
  <div class="hud-time" id="hudTime">00:00</div>
  <div class="hud-progress"><div class="hud-progress-fill" id="progressFill"></div></div>
</div>
```

四角用 80x80px border-only div 做 L 形装饰框：

```css
.hud-corner { position: absolute; width: 80px; height: 80px;
  border-color: rgba(8,145,178,0.15); border-style: solid; border-width: 0; }
.hud-tl { top:20px; left:20px; border-top-width:2px; border-left-width:2px; }
.hud-tr { top:20px; right:20px; border-top-width:2px; border-right-width:2px; }
.hud-bl { bottom:20px; left:20px; border-bottom-width:2px; border-left-width:2px; }
.hud-br { bottom:20px; right:20px; border-bottom-width:2px; border-right-width:2px; }
```

### 背景网格

```css
.bg-grid {
  position: fixed; inset: 0;
  background-image:
    linear-gradient(rgba(8,145,178,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(8,145,178,0.04) 1px, transparent 1px);
  background-size: 60px 60px;
  z-index: 0;
}
```

### 渐变文字

```css
.gradient-text {
  background: linear-gradient(135deg, var(--cyan), var(--purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
```

### CTA 脉冲发光

```css
.end-cta.show {
  animation: fadeIn 0.5s 0.8s forwards, pulse 2s 1.3s infinite;
}
@keyframes pulse {
  0%,100% { box-shadow: 0 0 0 0 rgba(8,145,178,0.3); }
  50% { box-shadow: 0 0 30px 10px rgba(8,145,178,0.15); }
}
```

### 常用 CSS 动画

```css
@keyframes slideUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes slideRight {
  from { opacity: 0; transform: translateX(-10px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.93); }
  to { opacity: 1; transform: scale(1); }
}
@keyframes blink {
  50% { opacity: 0; }
}
```

---

## 字体渲染

### 铁律 1：不用 Google Fonts CDN

```css
/* 错 — headless Chromium 静默失败，中文变方块 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC...');

/* 对 — 本地 @font-face */
@font-face {
  font-family: 'LXGW WenKai';
  src: url('file:///home/YOUR_USER/.local/share/fonts/LXGWWenKai-Regular.ttf') format('truetype');
}
```

### 铁律 2：--mono 必须加中文 fallback

```css
/* 错 — JetBrains Mono 不支持中文，变方块 */
--mono: 'JetBrains Mono', monospace;

/* 对 */
--mono: 'JetBrains Mono', 'LXGW WenKai', monospace;
```

---

## 踩坑记录

### 1. amix 1/N 缩放陷阱

`amix normalize=0` 不是"不缩放"。它禁用了自动防削波归一化，但仍然按 1/N 缩放每个输入。

| amix 输入数 | 每输入缩放 | 效果 |
|-------------|-----------|------|
| 2 | 1/2 = 0.50 | 可接受 |
| 5 | 1/5 = 0.20 | 偏安静 |
| 10 | 1/10 = 0.10 | 很安静 |
| 45 | 1/45 = 0.022 | 等于静音 |

**解决**：逐条叠加，每次 amix 只有 2 个输入。

### 2. FFmpeg 合成源默认极静

`sine` 和 `anoisesrc` 的 `a` 参数默认值产生的信号在 -30~-50 dB 范围。必须用高振幅（a≥0.6）+ volume=3.0+ 放大。

### 3. tremolo 频率下限 0.1

FFmpeg tremolo filter 的 `f` 参数最小值 0.1，低于此值报 `Numerical result out of range`。

### 4. 视频流比音频短

不要用 tpad 补。重新抓帧，让视频 DURATION >= 音频 DURATION。

### 5. 音频替换不重新编码

替换音轨时必须 `-c:v copy`。重新编码会破坏已烘焙的中文字符渲染。

### 6. 场景边界改变时 SFX 必须同步

改 capture 脚本的场景边界 → 同时改 mix 脚本的 SFX 时间表。不改 = 音效和画面不同步。

### 7. BGM 源文件不要删除

混音脚本每次修改 SFX 音量都需要重新生成 mixed-audio.wav。源文件丢了就得重新下载。

### 8. 混音后必须验证

对比 mixed-audio 和 voiceover 的 volumedetect 输出。如果 max_volume 差值 < 0.1 dB，说明 SFX/BGM 根本没混进去。

### 9. 改动隔离

用户说"在这个基础上改 X"时，只改 X，不动其他东西。即使逻辑上"顺便优化一下 Y"更合理。

### 10. npm 在 WSL + Windows 跨文件系统下极慢

不要在 /mnt/c/ 下运行 npm。用 Linux 原生文件系统（~/ 或 /tmp/）。

---

## 定稿参数速查

| 参数 | 值 |
|------|-----|
| 分辨率 | 1920x1080 |
| 帧率 | 30fps |
| 编码 | libx264 CRF 18, yuv420p, aac 192k |
| 中文字体 | LXGW WenKai（本地 @font-face） |
| 英文字体 | JetBrains Mono（代码） + ChakraPetch（标题） |
| 字幕 | 64px，底部居中，半透明黑底白字圆角气泡 |
| TTS | edge-tts zh-CN-XiaoxiaoNeural，不加 --rate |
| BGM | ambient electronic, volume=0.08, 2s fade-in 3s fade-out |
| SFX 音量 | volume=0.5 |
| 缓动函数 | cubic-bezier(0.16, 1, 0.3, 1) |
| 混音策略 | 逐条叠加（incremental overlay） |

---

## 许可证

MIT
