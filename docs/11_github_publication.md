# GitHub发布记录

日期：2026-11-15。目标：https://github.com/bluebluehh/taobao-ad-data-warehouse 。用户已创建公开仓库并授权推送。

## 已准备

- 整理根README、文档导航、当前成果与验收范围。
- 项目源码、SQL、Windows启动入口、前端回归检查。
- examples包含汇总快照、离线HTML、必要检查证据；机器路径在发布副本中清理，行为日志原始预览行从发布副本删除。
- .gitignore仅允许已整理的项目目录，排除原始CSV、SQLite、压缩包、日志、临时目录及第三方材料。
- 本地Git已初始化为main，origin配置为上述仓库。
- 源码结构、JS语法、真实快照回归检查通过。选入文件的密钥模式与个人机器路径扫描未发现问题。

## 尚未上传的原因

GitHub连接的内容创建请求返回403 Resource not accessible by integration；本机Git在执行环境内无法解析github.com，且后续写入.git/index.lock受到权限限制。未创建远端提交，不能将本地暂存状态描述为推送成功。

## 本机完成发布

双击 scripts/publish_github.cmd。它会检查目标分支与远端、执行现有检查、重新暂存已整理的文件、提交并正常推送main；使用GitHub noreply邮箱，避免公开个人邮箱。不强推、不覆盖远端历史。

如果提示登录，在Git正常打开的浏览器中登录。若远端已出现其他提交，脚本会保留失败信息，不自动覆盖，需要先检查远端再整合。

必须看到git push成功或GitHub仓库出现文件后，才能将发布状态改为完成。

## 推送连接补充

用户已创建本地提交03068b4，仍停留于推送阶段。检查发现Windows系统代理启用，但Git与代理环境变量未设置。这是待验证的连接原因，尚不能认定根因。推送入口改用scripts/push_github.py：保留显式Git代理优先级，否则仅本次使用当前系统代理，不改全局配置；--diagnose只展示连接方式，不发起推送。尚未取得远端成功证据。
