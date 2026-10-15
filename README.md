# Tech Video Skills

> **维护状态：文档存档。** 后续维护已并入 [glassmotion](https://github.com/christopher47634/glassmotion)（截帧、混音脚本与踩坑文档见其 `docs/`）。本仓库保留为早期文档版存档，只修正确性问题，不再加新功能。

用 HTML/CSS 动画 + Playwright 逐帧截图 + FFmpeg 合成，程序化生产高质量技术科普视频。

渲染管线不需要 Premiere、After Effects 或 Remotion，只用 Python + Chromium + FFmpeg；视频生产本身不需要 Node.js / npm（仓库里的 `scripts/*.mjs` 只是清单校验工具，用 Node 运行，与出片无关）。

所有步骤都有可直接运行的脚本，见 [`examples/`](examples/)（下文的代码块与之一一对应）。

## 适用场景

适用于：产品介绍、技术科普、数据可视化、社媒短视频、教程演示。

支持的场景组件：终端窗口、代码编辑器、AI 对话、数据指标卡片、标题页、结尾 CTA。

---

## 目录

- [工作流总览](#工作流总览)
- [可运行示例](#可运行示例)
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

**核心理念**：HTML 写场景，Playwright 截帧，FFmpeg 合成。不用 Remotion，不用 After Effects。

---

## 可运行示例

| 脚本 | 对应步骤 |
|------|---------|
| `examples/tts.py` | Step 1：edge-tts 生成配音 + 字幕（`--file` 传稿子） |
| `examples/scenes.example.html` + `scenes.example.json` | Step 2：场景 HTML（`seekTo(t)` 纯函数）与场景时间配置 |
| `examples/capture.py` | Step 3：Playwright 逐帧截图，场景时间从 JSON 读，任一帧失败即非零退出 |
| `examples/encode.py` | Step 4：帧序列 + 配音编码 MP4 |
| `examples/gen_sfx.py` | Step 5：合成 SFX 并用 volumedetect 校验 |
| `examples/mix.py` + `sfx_schedule.example.json` | Step 6：单次 amix（normalize=0）混音 |
| `examples/volume.py` | 读取任意音频的 max_volume |

所有外部命令都以参数列表调用（不经 shell）并 `check=True`，任何一步 ffmpeg 失败都会直接报错退出。

```bash
cd examples
pip install -r requirements.txt && playwright install chromium
python tts.py script.txt --out-dir build
python capture.py scenes.example.html --scenes scenes.example.json --vtt build/voiceover.vtt --out build/frames
python encode.py build/frames build/voiceover.mp3 build/output.mp4
python gen_sfx.py --out-dir sfx
python mix.py build/voiceover.mp3 --schedule sfx_schedule.example.json --bgm bgm.wav -o build/mixed-audio.wav
python volume.py build/voiceover.mp3 build/mixed-audio.wav
```

CI 会对 `examples/*.py` 做 `py_compile`、跑单测，并实际合成一遍 SFX。

---

## 环境准备

### 依赖

```bash
# Python 3.10+，版本已在 examples/requirements.txt 固定（playwright、edge-tts）
pip install -r examples/requirements.txt

# Playwright 自带的 Chromium（默认使用这个）
playwright install chromium

# FFmpeg ≥ 4.4（amix 的 normalize 选项从 4.4 起才有，见 Step 6）
sudo apt install ffmpeg
ffmpeg -version | head -1
```

edge-tts 调用的是微软在线服务，**没有离线回退**：断网或服务端拒绝（实测会出现 HTTP 403）时 `tts.py` 会非零退出，不会产出空文件。需要离线时请换本地 TTS，再按同样格式提供 `voiceover.mp3` + `voiceover.vtt`。

### 指定浏览器（可选）

默认用 `playwright install chromium` 下载的浏览器。如果某个环境里它不可用（例如个别 WSL 配置下启动失败），用参数或环境变量指定系统 Chromium，不要在代码里写死路径：

```bash
python examples/capture.py scenes.html --scenes scenes.json --chromium "$(command -v chromium)"
# 或
export CHROMIUM_PATH=/usr/bin/chromium
```

### 字体

中文字体用本地文件，不用 Google Fonts CDN（headless Chromium 会静默失败，中文变方块）。

推荐 [LXGW WenKai](https://github.com/lxgw/LxgwWenKai)：

```bash
# 下载字体到场景 HTML 旁边的 fonts/ 目录，HTML 里用相对路径引用（不写个人绝对路径）
mkdir -p fonts
wget -O fonts/LXGWWenKai-Regular.ttf \
  "https://github.com/lxgw/LxgwWenKai/releases/download/v1.330/LXGWWenKai-Regular.ttf"
```

---

## Step 1: 生成 TTS 语音 + 字幕

```bash
edge-tts --voice zh-CN-XiaoxiaoNeural \
  --file script.txt \
  --write-media voiceover.mp3 \
  --write-subtitles voiceover.vtt
```

用 `--file` 传稿子，**不要用 `--text "$(cat script.txt)"`**：稿子以 `-` 开头会被当成命令行选项，含引号、`$`、反引号时还会被 shell 再解释一遍。对应脚本 `examples/tts.py`（它还会校验生成的字幕没有时间重叠）。

`--write-subtitles` 同时生成精确的 VTT 时间戳，后续字幕和场景边界都依赖它。

**不要加 `--rate`**。原始语速最自然。如果用户要求快节奏才加 `--rate=+15%`（用 `=` 连写，避免 `-10%` 这类负值被当成选项），此时必须同时重新生成 media 和 subtitles——两个文件的时间戳完全不同，不能混用。

### VTT 示例

```
WEBVTT

00:00:00.100 --> 00:00:03.537
Vibe Coding，是一种全新的编程方式

00:00:03.537 --> 00:00:08.075
你不需要写每一行代码，只需要描述你想要什么
```

解析为 Python 数组：

```python
SUBTITLES = [
    [0.100, 3.537, "Vibe Coding，是一种全新的编程方式"],
    [3.537, 8.075, "你不需要写每一行代码，只需要描述你想要什么"],
    # ...
]
```

相邻两条字幕必须满足「下一条开始 ≥ 上一条结束」，否则两条会同时满足 `start <= t <= end`，画面上字幕闪烁或取错。`examples/common.py` 的 `parse_vtt` 遇到重叠会直接报错。

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
  src: url('fonts/LXGWWenKai-Regular.ttf') format('truetype');  /* 相对于 scenes.html */
}
```

**绝对不要用 `@import url('https://fonts.googleapis.com/...')`**。Headless Chromium 会静默加载失败，中文全部变方块。

---

## Step 3: Playwright 逐帧截图

完整脚本：[`examples/capture.py`](examples/capture.py)。要点：

- **场景时间不写在代码里**，统一放在 `scenes.json`（示例 `examples/scenes.example.json`），截图脚本、HTML、SFX 时间表都从这一份读：

```json
{
  "width": 1920, "height": 1080, "fps": 30,
  "scenes": [
    {"id": "s0", "start": 0.0, "end": 4.0},
    {"id": "s1", "start": 4.0, "end": 9.0}
  ]
}
```

- 总时长 = 最后一个场景的 `end`，总帧数 = `round(时长 × fps)`；
- 脚本把 `scenes` 注入 `window.SCENES`、把 VTT 注入 `window.SUBS`，然后对每一帧调用 `window.seekTo(i / fps)` 再截图；
- 浏览器优先级：`--chromium` 参数 > 环境变量 `CHROMIUM_PATH` > Playwright 自带 Chromium；
- **任何一帧失败都会以非零状态退出并列出失败帧**，不会留下序号断档的帧序列让 FFmpeg 悄悄合成出跳帧视频。

```bash
python examples/capture.py scenes.html --scenes scenes.json --vtt build/voiceover.vtt --out build/frames
```

核心循环：

```python
page.evaluate("([s, u]) => { window.SCENES = s; window.SUBS = u; }", [cfg["scenes"], subs])
page.evaluate("document.fonts.ready")
for i in range(total):
    try:
        page.evaluate("t => window.seekTo(t)", i / FPS)
        page.screenshot(path=str(out / f"frame_{i:05d}.png"))
    except Exception as e:
        failed.append((i, str(e).splitlines()[0]))
# 结束后 failed 非空 -> 打印失败帧并 sys.exit(1)
```

### 动画控制：seekTo(t) 必须是 t 的纯函数

逐帧截图时浏览器的真实时钟和视频时间毫无关系。凡是依赖真实时间的东西——CSS `animation`/`transition`、`setTimeout`、`requestAnimationFrame`、`infinite` 循环——截出来的帧都取决于截图速度，不可复现。

所以场景里的每个状态都要由 `t` 直接算出来：同一个 `t` 无论调用几次、以什么顺序调用，画面都一样（可以倒着截、跳着截、只重截某一段）。

```js
// 通用：进度 0→1，带缓动
const clamp01 = x => Math.min(1, Math.max(0, x));
const easeOut = p => 1 - Math.pow(1 - p, 3);
function reveal(el, p, dy = 30) {          // p: 0..1
  const e = easeOut(clamp01(p));
  el.style.opacity = e;
  el.style.transform = `translateY(${dy * (1 - e)}px)`;
}

function seekTo(t) {
  const cur = window.SCENES.find(s => t >= s.start && t < s.end) || window.SCENES.at(-1);
  document.querySelectorAll('.scene').forEach(el => el.classList.toggle('active', el.id === cur.id));
  const local = t - cur.start;               // 场景内时间，不再硬编码 4 / 9 / 14.5

  if (cur.id === 's1') {                     // 终端行，每 0.35s 一行
    document.querySelectorAll('#s1 .terminal-line').forEach((el, i) =>
      reveal(el, (local - 0.5 - i * 0.35) / 0.3, 0));
  }
  if (cur.id === 's4') {                     // 指标卡片 + 数字滚动
    document.querySelectorAll('#s4 .metric-card').forEach((el, i) => {
      const p = clamp01((local - 0.4 - i * 0.3) / 1.5);
      reveal(el, p * 3);
      el.querySelector('.metric-value').textContent = Math.round(p * el.dataset.target) + el.dataset.unit;
      el.querySelector('.metric-bar-fill').style.width = (p * 100) + '%';
    });
  }

  const total = window.SCENES.at(-1).end;    // HUD 进度条，总时长来自配置
  document.getElementById('progressFill').style.width = (t / total * 100) + '%';
  const sub = window.SUBS.find(s => t >= s[0] && t < s[1]);   // 半开区间，避免相邻字幕同时命中
  document.getElementById('subtitleText').textContent = sub ? sub[2] : '';
}
window.seekTo = seekTo;
```

可直接打开运行的最小例子见 `examples/scenes.example.html`。

> 早期版本用 `classList.add('show')` 触发 CSS `animation`，再 `wait_for_timeout(8)` 等它跑——这样每帧截到的是「动画实际跑了多少毫秒」，和 t 无关，截图快慢不同结果就不同。已改为上面的写法。下文组件库里的 `.show { animation: ... }` 仅用于浏览器里预览，出片时用 `reveal()` 这类函数按 t 设置样式。

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

脚本：`examples/encode.py`。

```bash
ffmpeg -y -framerate 30 -i build/frames/frame_%05d.png -i build/voiceover.mp3 \
  -c:v libx264 -preset medium -crf 18 \
  -c:a aac -b:a 192k -pix_fmt yuv420p -shortest build/output.mp4
```

参数说明：
- `-crf 18`：视觉无损，文件大小适中
- `-pix_fmt yuv420p`：兼容性最好（浏览器、手机、社媒平台）
- `-b:a 192k`：音频比特率，128k 也行但 192k 更清晰
- `-shortest`：以最短流为准（视频和音频谁短用谁）

---

## Step 5: SFX + BGM 音效层

### SFX 生成（FFmpeg 纯合成，零外部依赖）

脚本：[`examples/gen_sfx.py`](examples/gen_sfx.py)。所有 ffmpeg 调用都是参数列表（不经 shell）+ `check=True`，合成失败会直接抛错，不会留下缺失或空的 wav。

| 名称 | lavfi 源 | 滤镜 | 用途 |
|------|---------|------|------|
| whoosh | `anoisesrc=d=0.5:c=white:a=0.6` | `bandpass=f=2000:width_type=o:w=2,aecho=0.8:0.88:60:0.4,volume=3.0` | 场景切换 |
| typing_key | `anoisesrc=d=0.04:c=pink:a=0.8` | `highpass=f=3000,lowpass=f=8000,volume=4.0` | 打字 |
| pop | `sine=f=1000:d=0.12` | `volume=3.0` | 气泡弹出 |
| tick | `sine=f=5000:d=0.03` | `volume=3.0` | 代码行出现 |
| blip | `sine=f=1500:d=0.15` | `volume=3.0` | 数据卡片 |
| chime | `sine=f=523:d=1.2` | `volume=2.0` | 结尾收束 |

```python
from common import ffmpeg   # ffmpeg(*args) = subprocess.run(["ffmpeg", "-y", ...], check=True)

ffmpeg("-f", "lavfi", "-i", "sine=f=1000:d=0.12", "-af", "volume=3.0", "-ar", "44100", "sfx/pop.wav")
```

实测（FFmpeg 8.0.1）max_volume：whoosh 0.0 dB、typing_key 约 -3～-5 dB（噪声源随机）、pop/tick/blip -8.5 dB、chime -12.0 dB。

### 音量验证（必须！）

`gen_sfx.py` 生成后自动检查，单独检查用 `examples/volume.py`，或：

```bash
for f in sfx/*.wav; do
  max=$(ffmpeg -hide_banner -i "$f" -af volumedetect -f null - 2>&1 \
    | grep max_volume | sed 's/.*max_volume: //')
  echo "$(basename "$f"): $max"
done
```

注意输出目标 `-f null -` 末尾的 `-` 不能省：省掉后 ffmpeg 报 `At least one output file must be specified`，grep 什么也拿不到，验证形同虚设。

目标：SFX max > -15 dB（最好 > -10 dB）。低于 -15 dB 说明合成源振幅太低，需要提高 `a=` 参数或加 `volume=` 滤镜。

### BGM 素材

推荐使用真实素材而非 FFmpeg 合成（合成 BGM 在低音量下无质感）。

免费素材站：
- [Mixkit](https://mixkit.co/music/) — 免费商用，无需署名
- [Pixabay Music](https://pixabay.com/music/) — 免费商用

下载后处理（时长按 `scenes.json` 的总时长替换 24 / 21）：

```bash
ffmpeg -y -i bgm-source.mp3 \
  -af "atrim=0:24,asetpts=PTS-STARTPTS,afade=t=in:d=2,afade=t=out:st=21:d=3" \
  -ar 44100 -ac 2 bgm.wav
```

BGM 的音量（默认 0.08）在 `mix.py --bgm-vol` 里统一调，这里不再乘 `volume=`，避免两处叠乘。

**不要删除 BGM 源文件**。混音脚本每次修改都需要重新生成，源文件丢了就得重新下载（可能下到不同版本）。

---

## Step 6: 最终混音 + 替换音轨

### amix 的 normalize 到底做了什么（实测）

用 1 kHz 测试音（单独 max_volume -24.1 dB）与 N-1 路静音做 amix，再用 volumedetect 量（FFmpeg 8.0.1，脚本见下）：

| 输入数 N | `normalize=1`（默认） | `normalize=0` |
|---------|----------------------|---------------|
| 2 | -30.1 dB（×1/2） | -24.1 dB（不变） |
| 5 | -38.1 dB（×1/5） | -24.1 dB（不变） |
| 10 | -44.1 dB（×1/10） | -24.1 dB（不变） |
| 45 | -57.1 dB（×1/45） | -24.1 dB（不变） |

再测串联：2 路 amix 连续叠 45 次，`normalize=0` 结果仍为 -24.1 dB；而 `normalize=1` 只串 10 次就掉到 -84.3 dB（每次 -6 dB）。

结论：

- **`normalize=0` 完全不缩放**，各路直接相加。早期版本文档说它「仍按 1/N 缩放」是错的；1/N 缩放是默认的 `normalize=1`，以及 **FFmpeg 4.4 之前**的 amix（那时没有 `normalize` 选项，无法关闭缩放）。
- `normalize` 选项从 **FFmpeg 4.4** 起才有（4.3 源码中没有）。最低要求 FFmpeg ≥ 4.4；`examples/mix.py` 启动时会用 `ffmpeg -h filter=amix` 检查，没有就直接报错退出。
- 因此不需要「逐条叠加」：**一次 amix 把配音、BGM、全部 SFX 混起来，`normalize=0`，最后接 `alimiter` 防削波**即可。这比逐条叠加少 N 次中间文件读写，也不会出现「旧文档里每步都用 2 路 amix 却又声称会被 1/N 压扁」的自相矛盾。
- 不要在没有 `normalize=0` 的旧版本上用逐条 2 路 amix：每叠一次整条轨道就被减半，最先叠进去的 SFX 会被压到 2^-N。

复现脚本（造测试音 → 混音 → volumedetect）：

```bash
ffmpeg -y -f lavfi -i "sine=f=1000:d=1,volume=0.5" -ar 44100 tone.wav
ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=mono -t 1 sil.wav
for n in 0 1; do
  ffmpeg -y -i tone.wav -i sil.wav -i sil.wav -i sil.wav -i sil.wav \
    -filter_complex "amix=inputs=5:duration=first:normalize=$n" out_$n.wav
  ffmpeg -hide_banner -i out_$n.wav -af volumedetect -f null - 2>&1 | grep max_volume
done
```

### 混音实现

脚本：[`examples/mix.py`](examples/mix.py)。SFX 时间表放在 JSON 里（`examples/sfx_schedule.example.json`），和 `scenes.json` 一起维护：

```json
[[0.0, "whoosh"], [4.0, "whoosh"], [4.5, "typing_key"], [19.4, "blip"], [22.0, "chime"]]
```

生成的 filter_complex 结构（同一个 SFX 用多次时先 `asplit`）：

```
[0:a]aresample=44100[vo];
[1:a]asplit=2[sp1_0][sp1_1];
[sp1_0]aresample=44100,adelay=0:all=1,volume=0.5[x0];
[sp1_1]aresample=44100,adelay=4000:all=1,volume=0.5[x1];
...
[N:a]atrim=0:<配音时长>,asetpts=PTS-STARTPTS,volume=0.08,aresample=44100[bgm];
[vo][x0][x1]...[bgm]amix=inputs=K:duration=first:normalize=0,alimiter=limit=0.9:attack=5:release=50[out]
```

```bash
python examples/mix.py build/voiceover.mp3 --schedule sfx_schedule.json --bgm bgm.wav -o build/mixed-audio.wav
```

### 声道：默认立体声

早期版本最终混音用 `-ac 1`（单声道），原因只是 edge-tts 输出单声道、合成 SFX 也是单声道，省事省体积。但 BGM 素材通常是立体声，`-ac 1` 会把它折叠成单声道，部分素材左右声道相位相反时还会互相抵消变小声。

现在 `mix.py` 默认输出立体声（`-ac 2`）：单声道配音和 SFX 自动复制到左右声道，听感与单声道一致，BGM 保留立体声。确实需要单声道（比如极端在意体积）时加 `--mono`。

### 音轨替换

```bash
ffmpeg -y -i build/output.mp4 -i build/mixed-audio.wav \
  -c:v copy -c:a aac -b:a 192k \
  -map 0:v:0 -map 1:a:0 build/final.mp4
```

**`-c:v copy` 不重新编码视频流**，只替换音频。如果重新编码会破坏已烘焙的中文字符渲染。

### 混音后验证

```bash
# 对比混音前后（注意 -f null - 末尾的 -）
ffmpeg -hide_banner -i build/mixed-audio.wav -af volumedetect -f null - 2>&1 | grep max_volume
ffmpeg -hide_banner -i build/voiceover.mp3  -af volumedetect -f null - 2>&1 | grep max_volume
# 或：python examples/volume.py build/voiceover.mp3 build/mixed-audio.wav
# 差值 > 1 dB → SFX/BGM 成功混入
# 差值 < 0.1 dB → 混音失败，SFX/BGM 没进去（检查时间表、文件路径）
```

实测（合成配音 -24.5 dB + 示例 SFX 时间表）：mixed-audio -7.2 dB，SFX 确实混入。

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

> 下面的 CSS `animation`（`.show`、`cursor-blink`、`pulse` 等 `infinite` 循环）只适合在浏览器里预览样式。逐帧出片时它们跟真实时钟走、不可复现，必须改成在 `seekTo(t)` 里按 t 计算（入场用 Step 3 的 `reveal()`；光标闪烁用 `Math.floor(t / 0.35) % 2`；脉冲用 `Math.sin(2 * Math.PI * t / 2)` 算 box-shadow）。

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

数字从 0 滚动到目标值，进度条同步填充。在 `seekTo(t)` 里按 t 计算（`startTime` 为卡片在场景内的出现时刻）：

```js
let p = Math.min(1, Math.max(0, (t - startTime) / 1.5));
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

/* 对 — 本地 @font-face，相对 HTML 的路径 */
@font-face {
  font-family: 'LXGW WenKai';
  src: url('fonts/LXGWWenKai-Regular.ttf') format('truetype');
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

amix **默认**（`normalize=1`，以及 FFmpeg 4.4 之前没有该选项的版本）按 1/N 缩放每个输入：45 路时每路只剩 1/45 ≈ -33 dB，SFX 基本听不见。

**解决**：FFmpeg ≥ 4.4，单次 amix 加 `normalize=0`（实测完全不缩放，见 Step 6 的测试表），末尾接 `alimiter` 防削波。旧文档说「`normalize=0` 仍按 1/N 缩放」是错误结论，已按实测更正。

### 2. FFmpeg 合成源默认极静

`sine` 和 `anoisesrc` 的 `a` 参数默认值产生的信号在 -30~-50 dB 范围。必须用高振幅（a≥0.6）+ volume=3.0+ 放大。

### 3. tremolo 频率下限 0.1

FFmpeg tremolo filter 的 `f` 参数最小值 0.1，低于此值报 `Numerical result out of range`。

### 4. 视频流比音频短

不要用 tpad 补。重新抓帧，让视频 DURATION >= 音频 DURATION。

### 5. 音频替换不重新编码

替换音轨时必须 `-c:v copy`。重新编码会破坏已烘焙的中文字符渲染。

### 6. 场景边界改变时 SFX 必须同步

场景边界只在 `scenes.json` 里改，`capture.py` 和 HTML 都从它读；SFX 时间表（`sfx_schedule.json`）要跟着同步改。不改 = 音效和画面不同步。

### 7. BGM 源文件不要删除

混音脚本每次修改 SFX 音量都需要重新生成 mixed-audio.wav。源文件丢了就得重新下载。

### 8. 混音后必须验证

对比 mixed-audio 和 voiceover 的 volumedetect 输出（命令必须是 `-f null -`，缺了末尾的 `-` ffmpeg 直接报错，什么都量不到）。如果 max_volume 差值 < 0.1 dB，说明 SFX/BGM 根本没混进去。

### 9. 改动隔离

用户说"在这个基础上改 X"时，只改 X，不动其他东西。即使逻辑上"顺便优化一下 Y"更合理。

### 10. WSL 跨文件系统 IO 极慢

本流程本身不用 npm，但截帧会写几千个 PNG。在 WSL 里不要把工作目录或帧输出放在 `/mnt/c/` 这类 Windows 盘上（npm、pip 安装同理），用 Linux 原生文件系统（`~/` 或 `/tmp/`），最后只把成片拷回 Windows。

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
| TTS | edge-tts zh-CN-XiaoxiaoNeural，`--file` 传稿，不加 --rate |
| BGM | ambient electronic, volume=0.08, 2s fade-in 3s fade-out |
| SFX 音量 | volume=0.5 |
| 缓动函数 | cubic-bezier(0.16, 1, 0.3, 1) |
| 混音策略 | 单次 amix `normalize=0` + `alimiter=limit=0.9`（FFmpeg ≥ 4.4） |
| 混音声道 | 立体声 `-ac 2`（`--mono` 可选） |
| 场景时间 | `scenes.json` 单一来源 |

---

## 技能清单与校验

`skills-manifest.json` 登记本仓库发布的技能/文档条目（id、title、type、path、description）。`type: "skill"` 的条目必须指向带 YAML frontmatter（`name`、`description`）的 `SKILL.md`；新增的 `SKILL.md` 必须登记进清单。

```bash
node scripts/validate-manifest.mjs   # 校验清单结构、文件存在性、frontmatter
node --test test/*.test.mjs          # 校验脚本自身的单测
```

CI（`.github/workflows/validate.yml`）在每次推送时自动运行：校验清单，并对 `examples/*.py` 做 `py_compile`、单测和 SFX 冒烟测试。第三方依赖与授权说明见 [NOTICE.md](NOTICE.md)。

---

## 许可证

MIT
