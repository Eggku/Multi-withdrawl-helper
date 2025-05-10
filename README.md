# 多交易所提币助手

## 功能特点

- 支持多交易所（Binance、OKX）批量**随机数量、随机时间、随机地址**提币
- 支持多币种（ETH、USDT、USDC、SUI、G、SOL）和多网络
- 自动识别地址类型，无需手动选择
- OKX特殊地址格式（如SOL、SUI等）自动处理（**请配置好label，详见下方截图**）
- 实时显示提币金额的美元估值
- 支持Excel/CSV格式地址列表导入，支持多列（EVM/SOL/SUI等）
- 自动验证地址格式
- 支持批量提币，可设置**提币间隔和大额阈值预警**
- 实时显示等待时间
- 保存多交易所提币历史记录
- 支持大额提币二次确认
- 自动保存上次使用的地址文件

## 系统要求

- Windows 10/11
- Python 3.12.5 (用于构建可执行文件，建议使用此版本以获得最佳兼容性)
- 交易所API密钥（需开启提币权限）

## 使用方式 (通过源代码构建并运行)

为了确保代码的透明性和安全性，我们推荐您通过以下步骤自行构建并运行本工具：

1.  **克隆或下载项目源代码**
    *   您可以从本 GitHub 仓库下载最新的源代码压缩包，或使用 Git 克隆：
      ```bash
      git clone https://github.com/l445698714/Multi-withdrawl-helper.git
      cd Multi-withdrawl-helper
      ```

2.  **安装 Python 环境**
    *   确保您已安装 Python。**强烈建议使用 Python 3.12.5 版本进行构建**，这是经过测试并成功打包的版本。您可以从 [Python官网](https://www.python.org/downloads/) 下载。
    *   安装 Python 时，请确保勾选 "Add Python to PATH" (将 Python 添加到环境变量)。

3.  **安装项目依赖**
    *   打开命令行工具 (如 Command Prompt 或 PowerShell)，进入项目根目录。
    *   运行以下命令安装所需的依赖包：
      ```bash
      pip install -r requirements.txt
      ```
    *   如果安装速度慢或遇到问题，可以尝试使用国内镜像源：
      ```bash
      pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
      ```
    *   `build.py` 脚本也会在构建前尝试检查并安装 PyInstaller。

4.  **构建可执行文件 (.exe)**
    *   在项目根目录下，运行 `build.py` 脚本：
      ```bash
      python build.py
      ```
    *   构建成功后，可执行文件 `MultiWithdrawalHelper.exe` 将会生成在项目根目录下的 `dist_packages/MultiWithdrawalHelper_vX.X.X/` 文件夹内 (X.X.X 代表当前版本号)。

5.  **运行程序**
    *   进入上述 `dist_packages/MultiWithdrawalHelper_vX.X.X/` 文件夹。
    *   双击运行 `MultiWithdrawalHelper.exe` 文件。

## 使用说明

1. 配置API密钥：
   - 点击"设置"按钮，输入API Key和Secret Key
   - 支持Binance、OKX等主流交易所
   - 确保API具有提币权限

2. 导入提币地址：
   - 支持Excel/CSV格式，支持单列（address）或多列（EVM/SOL/SUI等）
   - 系统自动识别地址类型，无需手动选择
   - 点击"导入地址"按钮选择文件
   - 可设置提币地址范围

3. 设置提币参数：
   - 选择提币币种和网络
   - 设置提币金额范围
   - 可查看提币费用和最小提币数量

4. 进度与历史：
   - 进度条和左下角进度标签均采用N/N格式显示（如12/100）
   - 可随时点击"停止"按钮中断操作
   - 支持多交易所历史记录查询

5. 其他：
   - "支持开发者"按钮字体为蓝色，与估值风格一致
   - 支持大额提币二次确认，安全性高

## 注意事项

- 请确保API密钥安全，不要泄露给他人
- 建议先使用小额测试提币功能
- 提币前请仔细核对地址和金额
- 大额提币需要二次确认
- 请确保网络稳定，避免提币失败
- OKX部分币种（如SOL、SUI）需使用"地址:标签"格式，系统已自动处理
- ![image](https://github.com/user-attachments/assets/bbc026aa-7d25-4220-ae5d-92f73a07f6ad)


## 更新日志

### v1.1.0 (2024.06)
- 支持多交易所（Binance、OKX）
- 自动识别地址类型，移除手动选择
- 进度条与标签N/N显示
- OKX特殊地址格式自动处理
- UI细节优化与风格统一

### v1.0.0
- 初始版本发布
- 支持基本提币功能
- 支持地址验证
- 支持历史记录

## 免责声明

1. 本工具仅供学习和研究使用，不构成任何投资建议。
2. 使用本工具进行提币操作时，请确保遵守各交易所平台的相关规则和政策。
3. 由于网络延迟、API限制等原因，提币操作可能失败，本工具不保证100%成功率。
4. 使用本工具造成的任何损失（包括但不限于资金损失、账户限制等），开发者不承担任何责任。
5. 请勿将本工具用于任何非法用途，包括但不限于洗钱、逃税等违法行为。
6. 使用本工具即表示您同意承担所有相关风险和责任。

## 许可证

MIT License

## 联系方式

https://t.me/Monsterjane 
