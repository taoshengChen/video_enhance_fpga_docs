---
name: fpga-design-spec-generator
description: 为 FPGA 视频增强项目生成标准化的 Design Specification 目录和文档结构。当用户需要创建新的显示器视频处理方案设计文档时使用。
---

# FPGA Design Specification Generator

此技能通过引导式询问获取规格参数，并自动化生成符合公司标准的 FPGA 视频处理项目设计文档结构。

## 工作流程

### 1. 规格收集
在使用此技能前，必须使用 `ask_user` 询问用户以下关键参数：
- **项目代号/名称** (如: `video_enhance_pro_tv_box`)
- **显示分辨率** (如: `3840x2160`)
- **屏幕尺寸** (如: `50 inch`)
- **帧率范围** (如: `24Hz-120Hz`)
- **色深** (如: `8bit/10bit`)
- **硬件接口** (如: `8-lane V-by-One` 或 `4-lane eDP`)
- **目标 FPGA 型号** (如: `PH1A90SEG324`)
- **支持色深** (如: 8-bit, 10-bit, 8/10-bit, 8/10/12-bit)
- **是否支持 IIC 从机接口** (Yes/No)
- **是否支持 AHB 接口配置** (Yes/No)
- **是否支持时间滤波** (Yes/No)
- **是否支持 VRR 模式** (Yes/No)

### 2. 目录结构创建
根据项目代号创建根目录 `{project_name}_design_specification/`，并包含以下子项：
- `images/`: 存放文档图片
- `.gitignore`: 从 `assets/.gitignore_template` 复制
- `{project_name}_design_specification.md`: 主设计文档，基于 `references/SPEC_TEMPLATE.md` 生成
- `{project_name}_design_specification.drawio`: 占位文件

### 3. 文档生成逻辑
- **替换模板变量**: 将 `SPEC_TEMPLATE.md` 中的占位符（如 `{resolution}`, `{fpga_model}` 等）替换为用户提供的参数。
- **条件内容处理**:
  - **色深支持**: 
    - `{bit_depth_description}`: 将用户选择的位深格式化为“兼容 X 比特和 Y 比特色深”。
    - `{bit_depth_feature}`: 格式化为“支持 X 比特和 Y 比特色深”。
    - `{bit_depth_spec_vibrance}`/`{bit_depth_spec_skin}`/`{bit_depth_spec_clahe}`/`{bit_depth_spec_sharpen}`/`{bit_depth_spec_guide}`/`{bit_depth_spec_temporal}`: 
      - 如果包含 10-bit，生成：“**支持8比特和10比特色深:** 算法的内部数据路径和计算逻辑均支持 **8比特** 和 **10比特** 两种色深。”
      - 否则根据用户选择生成对应的“支持X比特色深”描述。
  - **肤色检测 2.1 支持**:
    - 如果支持肤色检测 2.1，将参考文档 3.6 节的详细描述（包含 Stage 1-3 架构）替换到 `{skin_detection_21_block}`。
    - 否则，将 `{skin_detection_21_block}` 替换为空白。
  - **IIC 支持**:
    - 如果支持 IIC，将以下内容替换到 `{iic_feature_block}`：
      ```markdown
      * 内建 IIC 从机接口，用于 SoC 与 FPGA 通讯及 PQE 参数配置
      ```
      并将 `{comm_intro_text}` 替换为 `SPI 或 IIC`。
      并将 `{comm_interfaces}` 替换为 `SPI/IIC`。
      并将 `{protocol_layer_title}` 替换为 `SPI和IIC协议层`。
      将参考文档 4.2 节（IIC 物理层）及 4.7 节（IIC 时序要求）的内容替换到 `{iic_content_block}`。
      将参考文档 5.1.2 节（IIC 物理层功能点与接口表）替换到 `{iic_integration_functional_block}`。
      将参考文档 5.1 节中关于 IIC 物理层的描述插入到 `{iic_integration_details_block}`。
    - 否则，将 `{iic_feature_block}`、`{iic_content_block}`、`{iic_integration_details_block}`、`{iic_integration_functional_block}` 替换为空白。
  - **AHB 支持**:
    - 如果支持 AHB，将以下内容替换到 `{ahb_feature_block}`：
      ```markdown
      * 支持通过AHB接口配置视频参数
      ```
      将参考文档 4.9 节（时间滤波参数更新及 AHB 地址累加机制）的内容替换到 `{ahb_content_block}`。
      将参考文档 5.1.4 节中关于 AHB 的功能点及 16-bit AHB-Lite 接口列表替换到 `{ahb_integration_details_block}`。
    - 否则，将 `{ahb_feature_block}`、`{ahb_content_block}`、`{ahb_integration_details_block}` 替换为空白。
  - **时间滤波支持**: 
    - 如果支持时间滤波，将以下内容替换到 `{temporal_filter_feature}`：
      ```markdown
        * 可选时间滤波：平滑连续视频帧间的统计特性，有效抑制时域噪声并消除画面闪烁（Flicker），提升视觉稳定性
      ```
      并将参考文档 3.5 节的完整描述（规格、公式、硬件、LUT 机制）替换到 `{temporal_filter_content_block}`。
    - 否则，将 `{temporal_filter_feature}` 和 `{temporal_filter_content_block}` 替换为空白。
  - **VRR 支持**: 如果用户回答支持 VRR，将以下内容替换到 `{vrr_feature_block}`：
    ```markdown
    * 支持跟随刷新率变换
      * **VRR 模式 (流畅切换)**：优化时序握手协议，实现切换分辨率时的“零感”过渡，确保显示不中断。
      * **固定模式 (同步重启)**：采用完整的链路初始化机制，切换分辨率时重新启动显示系统，确保高可靠性的信号锁定。
    ```
    否则，将 `{vrr_feature_block}` 替换为空白（删除该行）。
- **算法细节**: 根据用户选择的 Pro 或 Base 版本，从参考项目 (`video_enhance_hkc_monitor_27inch_design_specification`) 中提取相应的算法描述填充到第 3 章节。

## 参考规范
- 文档风格应严格参照 `video_enhance_hkc_monitor_27inch_design_specification.md`。
- 图题和表题必须使用 `<small><b>标题内容</b></small>` 格式。
- 公式使用 `$$` 作为定界符。
- 始终使用中文回复。
