# ATMB 地址爬取与验证工具 | ATMB Address Scraper & Verifier

[English](#english) | [中文](#chinese)

---

<a name="chinese"></a>
## 🇨🇳 中文 (Chinese)

### 简介
本仓库包含一套用于抓取、补全和验证 Anytime Mailbox (ATMB) 美国地址的工具。工作流主要包含三个步骤：爬取基础地址信息、提取详细单元号/房间号信息，以及使用 Smarty API 验证地址性质（住宅/商业状态）。

### 特性
*   **自动爬取:** 支持按州或全美范围自动爬取地址点位。
*   **详情提取:** 智能从详情页提取 Suite/Apartment（单元/公寓）编号。
*   **地址验证:** 集成 Smarty API，验证地址有效性并判断 RDI（住宅投递标识）和 CMRA（商业邮件接收代理）状态。
*   **断点续传:** 脚本支持从上次中断的地方继续运行，适合处理大量数据。

### 准备工作
*   Python 3.x
*   安装依赖库:
    ```bash
    pip install requests beautifulsoup4
    ```
*   **Smarty API 密钥:** 验证步骤需要 Smarty.com 的 API 密钥。请在根目录创建一个名为 `smarty_api_key.txt` 的文件，内容格式如下：
    ```text
    auth_id=你的AUTH_ID
    auth_token=你的AUTH_TOKEN
    ```

### 如何使用

#### 1. 爬取基本地址信息
运行 `ATMB_scrape.py` 从网站抓取基础地址信息（街道、城市、州、邮编）。

*   **命令:**
    ```bash
    python ATMB_scrape.py --input <state_slug|us>
    ```
*   **示例:**
    *   爬取纽约州地址: `python ATMB_scrape.py --input new-york`
    *   爬取全美所有州: `python ATMB_scrape.py --input us`
*   **输出:** CSV 文件将保存在 `Public/` 文件夹中（例如 `Public/new-york.csv`）。

#### 2. 补充单元号信息（可选）
运行 `ATMB_detail.py` 访问详情链接，为每个地址提取 Suite/Unit 信息。

*   **命令:**
    ```bash
    python ATMB_detail.py --input <CSV文件路径>
    # 或者 处理整个文件夹
    python ATMB_detail.py --folder <文件夹路径>
    ```
*   **示例:**
    ```bash
    python ATMB_detail.py --input Public/new-york.csv
    ```
*   **输出:** 生成带有 `_detailed` 后缀的新文件（例如 `Public/new-york_detailed.csv`），其中包含新增的 `Suite/Apartment` 列。

#### 3. 验证地址性质
运行 `ATMB_verify.py` 使用 Smarty API 验证地址并检查 RDI/CMRA 状态。

*   **命令:**
    ```bash
    python ATMB_verify.py --input <CSV文件路径>
    ```
*   **逻辑说明:**
    *   如果输入文件名以 `_detailed.csv` 结尾，脚本将验证**包含具体单元号**的完整地址。
    *   否则，脚本仅验证**街道地址**。
*   **示例:**
    ```bash
    python ATMB_verify.py --input Public/new-york_detailed.csv
    ```
*   **输出:** 生成带有 `_verified` 后缀的新文件（例如 `Public/new-york_detailed_verified.csv`），其中包含 `RDI` 和 `CMRA` 列。

---

<a name="english"></a>
## 🇬🇧 English

### Introduction
This repository contains a set of tools designed to scrape, enrich, and verify US addresses from Anytime Mailbox (ATMB). The workflow consists of three main steps: scraping basic address information, extracting detailed unit/suite numbers, and verifying the address properties (Residential/Commercial status) using the Smarty API.

### Features
*   **Scraping:** Automated scraping of address locations by state or for the entire US.
*   **Detail Extraction:** Intelligent extraction of suite/apartment numbers from detail pages.
*   **Verification:** Integration with Smarty API to validate addresses and determine RDI (Residential Delivery Indicator) and CMRA (Commercial Mail Receiving Agency) status.
*   **Resume Capability:** Scripts support resuming from where they left off to handle large datasets.

### Prerequisites
*   Python 3.x
*   Required Python packages:
    ```bash
    pip install requests beautifulsoup4
    ```
*   **Smarty API Key:** For the verification step, you need a Smarty.com API key. Create a file named `smarty_api_key.txt` in the root directory with the following format:
    ```text
    auth_id=YOUR_AUTH_ID
    auth_token=YOUR_AUTH_TOKEN
    ```

### usage

#### 1. Scrape Basic Addresses
Run `ATMB_scrape.py` to crawl basic address information (Street, City, State, Zip) from the website.

*   **Command:**
    ```bash
    python ATMB_scrape.py --input <state_slug|us>
    ```
*   **Examples:**
    *   Scrape detailed addresses for New York: `python ATMB_scrape.py --input new-york`
    *   Scrape all US states: `python ATMB_scrape.py --input us`
*   **Output:** CSV files will be saved in the `Public/` folder (e.g., `Public/new-york.csv`).

#### 2. Supplement Unit Information (Optional)
Run `ATMB_detail.py` to visit detail URLs and extract Suite/Unit information for each address.

*   **Command:**
    ```bash
    python ATMB_detail.py --input <path_to_input_csv>
    # OR process an entire folder
    python ATMB_detail.py --folder <path_to_folder>
    ```
*   **Example:**
    ```bash
    python ATMB_detail.py --input Public/new-york.csv
    ```
*   **Output:** Generates a new file with `_detailed` suffix (e.g., `Public/new-york_detailed.csv`) containing the new `Suite/Apartment` column.

#### 3. Verify Address Properties
Run `ATMB_verify.py` to validate the address and check RDI/CMRA status using Smarty API.

*   **Command:**
    ```bash
    python ATMB_verify.py --input <path_to_csv>
    ```
*   **Logic:**
    *   If the input filename ends with `_detailed.csv`, it verifies the address **highlighting the specific unit**.
    *   Otherwise, it verifies the **street address only**.
*   **Example:**
    ```bash
    python ATMB_verify.py --input Public/new-york_detailed.csv
    ```
*   **Output:** Generates a new file with `_verified` suffix (e.g., `Public/new-york_detailed_verified.csv`) containing `RDI` and `CMRA` columns.
