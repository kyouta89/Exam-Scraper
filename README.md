# ServiceNow Exam Scraper (CIS-CSM) 🛠️

ExamTopicsの学習コンテンツを効率的に学習するための、Python製スクレイピング＆教材生成ツールセットです。
Web上の問題を自動収集し、「日英併記のHTML教科書」と「学習記録用のExcel」をワンクリックで生成します。

## 📦 機能

1. **URL収集:** 指定したカテゴリ（CIS-CSM等）の問題ページURLを全ページから自動収集
2. **データ取得:** Seleniumを使用し、Cloudflare等のBot対策を回避しながら問題を安全にスクレイピング
3. **教材生成:**
   - **HTML教科書:** Google翻訳APIを用いた日英併記、学習に特化した見やすいデザイン（JSによる言語切替機能付き）
   - **管理Excel:** 学習進捗やメモを記録できる管理表（HTMLへのリンク機能付き）

## 🛠 動作環境

- Python 3.x
- Google Chrome

## 🚀 使い方

このツールは、以下の3ステップで実行します。

### 0. 準備

必要なライブラリをインストールします。

```bash
pip install -r requirements.txt
```

### 1. URLの収集

ExamTopicsから対象試験のURLリストを作成します。

```bash
python3 01_fetch_urls.py
```

- **出力:** `ServiceNow_CIS-CSM_links.txt`

### 2. 生データの取得

収集したURLリストを元に、問題文と解答データを取得します。
（※サーバー負荷を考慮し、待機時間を設けているため時間がかかります）

```bash
python3 02_scrape_raw.py
```

- **出力:** `CIS-CSM_Complete_Questions.html` (原材料データ)

### 3. 教材の生成

取得したデータを解析・翻訳し、学習用のHTMLとExcelを生成します。

```bash
python3 03_generate_study_kit.py
```

- **出力1:** `CIS-CSM_Master_Textbook.html` (閲覧用・日英切替機能付き)
- **出力2:** `CIS-CSM_My_Notebook.xlsx` (記録用・判定ステータス付き)

---

## 📖 学習の進め方

生成された **HTML** と **Excel** を並べて学習することをお勧めします。

1. **HTML** で問題を解く（デフォルトは日本語、ボタンで英語原文を確認）
2. **Excel** の「自分の結論」列に解答を入力
3. 意見が割れている問題（⚠️マーク）は重点的にチェックし、メモを残す

## ⚠️ 免責事項

- 本ツールは個人の学習効率化を目的として作成されています。
- スクレイピングを行う際は、対象サイトの利用規約を遵守し、サーバーに過度な負荷をかけないようご注意ください。
- 生成されたコンテンツの商用利用や再配布は推奨されません。
