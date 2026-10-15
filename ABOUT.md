# Tech Video Skills

> 文档存档：后续维护已并入 [glassmotion](https://github.com/christopher47634/glassmotion)。

用 HTML/CSS 动画 + Playwright 逐帧截图 + FFmpeg 合成，程序化生产高质量技术科普视频。

## 快速开始

```bash
pip install -r examples/requirements.txt
playwright install chromium
sudo apt install ffmpeg   # 需要 FFmpeg >= 4.4（amix normalize 选项）
```

详细文档见 [README.md](README.md)，可运行脚本见 [examples/](examples/)。

## 内容

- 完整的 6 步工作流（TTS → HTML → Playwright → FFmpeg → SFX → 混音），每步对应 examples/ 下一个脚本
- 动画设计原则（seekTo 纯函数、stagger、多阶段入场、组合变换）
- 组件库（终端、代码编辑器、AI 对话、数据卡片、HUD）
- 10 个踩坑记录（amix normalize 行为已实测更正）
- 定稿参数速查表
