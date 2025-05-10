# 多交易所提币助手

## 功能特点

- 支持多交易所（Binance、OKX）批量**随机数量、随机时间、随机地址**提币
- 支持多币种（ETH、USDT、USDC、SUI、G、SOL）和多网络
- OKX特殊地址格式（如SOL、SUI等）自动处理（**请配置好label，详见下方截图**）
- 实时显示提币金额的美元估值
- 支持Excel/CSV格式地址列表导入，支持多列（EVM/SOL/SUI）
- 自动验证地址格式
- 支持批量提币，可设置**提币间隔和大额阈值预警**
- 保存多交易所提币历史记录
- 支持大额提币二次确认

## 软件截图
N
    <img src="https://github.com/user-attachments/assets/f61c4c88-baa8-4dbf-8647-599fcebbf9a7" alt="image" width="200"/>
    <img src="https://github.com/user-attachments/assets/df73399c-a697-430c-9f98-a77f1945e8a7" alt="image" width="200"/>
    <img src="https://github.com/user-attachments/assets/4403f22d-3f7c-45a2-a319-360d3037a69f" alt="image" width="200"/>
    <img src="https://github.com/user-attachments/assets/5b91a5fa-f008-4566-b3ed-4ccc3b06fd68" alt="image" width="200"/>
    <img src="https://github.com/user-attachments/assets/a83c727b-5a68-4061-8b75-4a8f3e90e5a1" alt="image" width="200"/>
    <img src="https://github.com/user-attachments/assets/18e32401-a4bf-4271-a24a-e11475766860" alt="image" width="300"/>
    <img src="https://github.com/user-attachments/assets/bbc026aa-7d25-4220-ae5d-92f73a07f6ad" alt="image" width="300"/>

## 如果您觉得这个工具对您有帮助，欢迎打赏支持开发者继续改进和分享更多小工具。
![image](https://github.com/user-attachments/assets/b7810000-78d3-4c6b-a10d-cee4d22d6845)
![image](https://github.com/user-attachments/assets/11952997-dd5d-4311-a085-8145acdb4950)
## 联系方式
https://x.com/StayrealLoL https://t.me/MONSTERJANE0331
![image](https://github.com/user-attachments/assets/60ef9967-420f-4fab-a220-7292939fc31e)

## 系统要求

- Windows 10/11
- Python 3.12.5 (用于构建可执行文件，建议使用此版本以获得最佳兼容性)
- 交易所API密钥（需开启提币权限）

## 使用方式 (通过源代码构建并运行)

为了确保代码的透明性和安全性，推荐您通过以下步骤自行构建并运行本工具：

1.  **克隆或下载项目源代码**
    *   您可以从本 GitHub 仓库下载最新的源代码压缩包，或使用 Git 克隆：
      ```bash
      git clone https://github.com/l445698714/Multi-withdrawl-helper.git
      cd Multi-withdrawl-helper
      ```

2.  **安装 Python 环境**
    *   确保您已安装 Python。**强烈建议使用 Python 3.12.5 版本进行构建**，这是经过测试并成功打包的版本。您可以从 [Python官网](https://www.python.org/downloads/) 下载。
    *   安装 Python 时，请确保勾选 "Add Python to PATH" (将 Python 添加到环境变量)。

3.  **关于项目依赖**
    *   在您执行第 4 步通过 `python build.py` 构建可执行文件时，脚本会自动尝试从 `requirements.txt` 文件安装所有必需的项目依赖项（包括 PyInstaller）。
    *   因此，通常情况下，您**无需手动执行**下面的 `pip install` 命令，可以直接进行到第 4 步。
    *   **可选操作**：如果您希望在运行 `build.py` 之前预先安装依赖，或者如果在 `build.py` 自动安装依赖的过程中遇到网络问题或错误，您可以手动打开命令行工具 (如 Command Prompt 或 PowerShell)，进入项目根目录，然后运行：
      ```bash
      pip install -r requirements.txt
      ```
    *   如果手动安装时下载速度较慢，可以尝试使用国内镜像源：
      ```bash
      pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
      ```

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
   - 支持Excel/CSV格式，支持单列（address）或多列（EVM/SOL/SUI）
   - 系统自动识别地址类型，无需手动选择
   - 点击"导入地址"按钮选择文件
   - 可设置提币地址范围

3. 设置提币参数：
   - 选择提币币种和网络
   - 设置提币金额范围

4. 进度与历史：
   - 进度条和左下角进度标签显示
   - 可随时点击"停止"按钮中断操作
   - 支持多交易所历史记录查询

5. 其他：
   
   - 支持大额提币二次确认，安全性高

## 注意事项

- 请确保API密钥安全，不要泄露给他人
- 建议先使用小额测试提币功能
- 提币前请仔细核对地址和金额
- 大额提币需要二次确认
- 请确保网络稳定，**提币时的ip需与交易所设置的ip白名单（建议设置）一致**，避免提币失败
- OKX部分币种（如SOL、SUI）需使用"地址:标签"格式，请提前配置

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


