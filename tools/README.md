# tools/

sync 基建(建设中):source.json(脱敏变换规则)+ sync 脚本(拉活体 → 变换 → diff 过目 → 写入 skills/)。
开发者本地活体源与本仓库发布快照分离;本仓库 `skills/` 是经过检查后提交的公开快照。

## 照片Skill分发校验

`check_cool_chibi_package.py` 检查照片Skill的文本分发文件、个人路径/凭据、内部链接、JSON和脚本默认值，并核对SHA-256清单。不读取用户照片、不调用生图或外部API。

```bash
python tools/check_cool_chibi_package.py
# 修改分发文件并审查后更新哈希：
python tools/check_cool_chibi_package.py --write-manifest
```
