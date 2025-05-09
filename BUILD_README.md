# 币安提币助手打包说明

## 打包概述

本项目提供了三种不同的打包方式，可以将币安提币助手Python程序打包成独立的Windows可执行文件(.exe)，无需用户安装Python环境即可运行。

打包后的程序会整合所有必要的依赖，生成一个单独的可执行文件，方便在Windows系统上分发和使用。

## 隐私与安全

**重要提示**：打包过程已优化，确保不会包含任何个人信息：

- 打包时使用干净的配置文件模板，不包含API密钥
- 不会包含钱包地址或其他敏感信息
- 程序首次运行时会自动创建一个全新的配置文件

## 打包前准备

1. **确保已安装Python环境**
   - 推荐Python 3.7或更高版本
   - 确保pip可用

2. **安装必要的依赖**
   - 运行 `pip install -r requirements.txt`
   - 安装PyInstaller: `pip install pyinstaller`

## 打包方式

### 方式一：使用批处理文件（推荐）

最简单的方式是直接运行批处理文件，它会引导你完成整个打包流程：

1. 双击运行 `build.bat`
2. 根据提示选择打包方式
3. 等待打包完成

### 方式二：使用Python脚本

如果你更习惯使用Python脚本：

1. 运行 `python build.py`
2. 等待打包完成

### 方式三：使用PyInstaller命令

如果你需要自定义打包配置：

1. 使用干净配置模板和PyInstaller命令：
   ```
   python -c "import configparser; config = configparser.ConfigParser(); config['BINANCE'] = {'api_key': '', 'api_secret': ''}; config['WITHDRAWAL'] = {'min_interval': '60', 'max_interval': '600', 'warning_threshold': '1000.0', 'enable_warning': 'True', 'last_address_file': ''}; f = open('config_template.ini', 'w', encoding='utf-8'); config.write(f); f.close()"
   
   pyinstaller --name "币安提币助手" --icon=app.ico --windowed --onefile --clean --add-data "app.ico;." --add-data "config_template.ini;config.ini" main_qt.py
   ```

2. 或者使用spec文件（更灵活）：
   ```
   pyinstaller binance_withdrawal_helper.spec
   ```

## 打包输出

打包完成后，会在 `dist` 目录下生成可执行文件：
- 文件名称：`币安提币助手.exe`
- 大小：约30-40MB（取决于打包方式和包含的依赖）

## 使用注意事项

1. **配置文件**
   - 程序首次运行时会自动创建干净的配置文件
   - 配置文件不会预先包含任何个人API密钥或地址信息

2. **运行环境**
   - 打包后的程序可在大多数Windows系统上运行（Windows 7/8/10/11）
   - 不需要管理员权限（除非访问受限目录）

3. **常见问题**
   - 如果运行时提示缺少DLL文件，可能需要安装Visual C++ Redistributable
   - 如果提示"应用无法正常启动"，可能是打包过程中缺少某些依赖项

## 高级定制

如果需要定制打包过程，可以编辑以下文件：

1. **binance_withdrawal_helper.spec**
   - 调整隐藏导入模块
   - 排除不必要的库
   - 修改数据文件

2. **build.py**
   - 调整打包参数
   - 添加额外的文件

## 打包流程技术说明

打包过程主要包含以下步骤：

1. **创建干净配置**：生成不包含任何个人信息的配置模板
2. **收集依赖**：PyInstaller分析代码，收集所有必要的Python模块和库
3. **打包资源**：将图标、配置模板等资源文件包含在内
4. **创建可执行文件**：将所有文件打包为单一的.exe文件

## 隐私与数据安全

打包程序在以下几个方面保护您的隐私：

1. **不包含API密钥**：打包时使用的配置文件不包含任何API密钥
2. **不包含地址信息**：打包程序不会包含任何提币地址
3. **临时文件清理**：打包过程中创建的临时文件会在完成后自动删除
4. **数据本地存储**：程序运行时生成的所有数据都只存储在本地

## 问题排查

如果在打包过程中遇到问题：

1. 检查Python环境和依赖项是否正确安装
2. 尝试使用不同的打包方式
3. 检查日志输出，查找错误信息

## 联系与支持

如有问题或需要帮助，请联系开发者。 