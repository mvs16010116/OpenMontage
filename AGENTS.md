# OpenMontage

**MANDATORY: Read `AGENT_GUIDE.md` before responding to ANY user message.**

Do not act on the user's request until you have read AGENT_GUIDE.md.
It contains routing rules that determine your first action based on what the user asked.
Skipping it WILL cause you to take the wrong action.

There are no instructions in this file. All instructions are in AGENT_GUIDE.md.

**每次代码 / 配置 / 文档改动，必须依次走五步链，缺步即违规：**

1. **grill-me（推敲）**——需求/方案先审问、钉死目标与约束。
2. **to-spec（成文）**——把结论合成单份 spec，落 `issues/<NNN>-<slug>.md`。
   - 若推敲已在先前会话完成（决策已拍板），**直接从对话合成 spec，不重复审问**。
   - spec 必须含三区：**目标与约束** / **方案与决策点（含被否掉的替代方案）** / **验收标准**。
3. **to-tickets（拆票）**——把 spec 拆成追踪弹票，一张票一个文件 `issues/<NNN>-<slug>.md`，每票**声明阻塞边**（`Blocking: <票号>` 依赖谁 / 被谁依赖）。
   - 禁止大改动合成一张巨型票；每票可独立实现、独立验证。
   - 当前无外部 tracker，边写成文本即满足契约。
4. **implement（落地）**——按票实现，**一票一改一验一提交**。
   - 实现顺序由阻塞边决定；票完成 = 有验证证据（`npm test` 全绿 / 该票小样 / 抽查帧）。
   - 提交消息引用票号（如 `issues/026-xxx`）；保持每步可 `git revert` 回滚；**同一提交不混票**。
   - 改代码前必须先确认：对应 spec/票据已存在；越过未开票项 = 违规。
5. **handoff（交接）**——会话结束 / 上下文紧张 / 里程碑达成时，刷新仓库根 `HANDOFF.md`（压缩：目标、进度、决策、下一步、踩坑），供下一个 agent 接手。

**豁免**：仅纯注释 / 改名 / 常量调整 / 清理（无行为变化）可跳过 2/3，但仍须走 4/5 并在提交说明中注明豁免理由。

**执行细节**：每步动手前，先用 skill 工具加载对应技能并按参考执行（grill-me / to-spec / to-tickets / implement / handoff）。被判定违规时：停下补流程，不硬闯。