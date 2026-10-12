仓库Fork自https://github.com/Sophomoresty/qmdec

特性:

- 为`fast_decrypt`添加clang支持(Windows)
- 修复单曲下载时标题或歌手名中的 `/`、`\` 被识别为目录分隔符而导致下载失败的问题。生成文件名时将 `/`、`\`、`:` 替换为 `_`，显示和元数据中的原始名称保持不变。此处理覆盖直接下载、加密 FLAC 临时文件和 MP3 回退下载。
