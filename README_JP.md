# CESMD V2ファイルコンバーター

*[English](README.md)*

Center for Engineering Strong Motion Data (CESMD)のV2形式ファイルをCSV、MAT、HDF5形式に変換するためのシンプルなGUIツールです。

## 機能

- V2ファイルから加速度、速度、変位データを直接抽出
- CSV、MAT（MATLAB）、HDF5形式への変換
- 使いやすいグラフィカルユーザーインターフェース
- バッチ処理によるフォルダ内の複数のV2ファイルの変換
- ドラッグ&ドロップによる入出力フォルダの指定（tkinterdnd2がインストールされている場合）
- 複数チャンネルを含むV2ファイルの自動分割処理
- カスタムアイコン（Pillowがインストールされている場合）

## クイックスタート（事前ビルド済みWindows実行ファイル）

GitHub Releases から、事前ビルド済みの Windows 実行ファイル（.exe）を利用できます。

- ダウンロードURL: [CESMD-Converter.exe](https://github.com/SaidaTaisei/CESMD-V2-File-Converter/releases/download/v0.3.1/CESMD-Converter.exe)

ダウンロード後は、`.exe` ファイルを直接実行してください。

## 依存関係

コアライブラリの依存関係：

* numpy>=1.20.0
* scipy>=1.7.0
* h5py>=3.1.0

GUI追加依存：

* Pillow>=9.0.0（オプション、アイコン表示のために必要）
* tkinterdnd2>=0.3.0（オプション、ドラッグ&ドロップ機能のために必要）

コア依存のインストール：

```bash
pip install -r requirements.txt
```

GUI依存のインストール：

```bash
pip install -r requirements-gui.txt
```

## データ抽出の仕組み

このコンバーターは、V2ファイルから以下のデータを直接抽出します：

- 加速度データ（"points of accel data"セクション）
- 速度データ（"points of veloc data"セクション、存在する場合）
- 変位データ（"points of displ data"セクション、存在する場合）
- メタデータ（ファイルヘッダーから）

V2ファイルには既に加速度、速度、変位のデータが含まれており、このツールはそれらを抽出して指定された形式に変換します。積分計算などの処理は行いません。

## インストール

### 必要条件

- Python 3.8以上
- 必要なパッケージ（ライブラリは`requirements.txt`、GUIは`requirements-gui.txt`）

### セットアップ

1. リポジトリをクローンまたはダウンロード
   ```
   git clone https://github.com/SaidaTaisei/CESMD-V2-File-Converter.git
   cd CESMD-V2-File-Converter
   ```

2. 依存関係をインストール
   ```
   # コアライブラリ依存
   pip install -r requirements.txt

   # 任意: GUI依存
   pip install -r requirements-gui.txt
   ```

## 使い方

1. スクリプトを実行
   ```
   python converter.py
   ```

2. GUIで以下の操作を行う
   - 「入力ディレクトリ」でV2ファイルが含まれるフォルダを選択（ドラッグ&ドロップも可能）
   - 「出力ディレクトリ」で変換ファイルの保存先を選択（ドラッグ&ドロップも可能）
   - 「出力形式」でCSV、MAT、HDF5のいずれかを選択
   - 「変換開始」ボタンをクリック

3. 変換処理が完了すると結果が表示されます

## ライブラリとしての使い方

このプロジェクトは Python ライブラリとしても利用できます。

### インストール（ローカルリポジトリ）

```bash
pip install .
```

### インストール（開発モード）

```bash
pip install -e .
```

### GitHub URL からインストール

```bash
pip install "git+https://github.com/SaidaTaisei/CESMD-V2-File-Converter.git"
```

```python
from cesmd_converter import parse_v2_file, to_csv, to_mat, to_hdf5

record = parse_v2_file("CHAN001.V2")
print(record.metadata.station_id)
print(record.acceleration[:5])

to_csv(record, "channel_1.csv")
to_mat(record, "channel_1.mat")
to_hdf5(record, "channel_1.h5")
```

## 出力ファイルの構造

### CSV形式
- コメント行にメタデータ
- 列：Time, Acceleration, Velocity（存在する場合）, Displacement（存在する場合）

### MAT形式
- time: 時間配列
- acceleration: 加速度データ
- velocity: 速度データ（V2ファイルに含まれる場合）
- displacement: 変位データ（V2ファイルに含まれる場合）
- metadata: メタデータ構造体

### HDF5形式
- /time: 時間データセット
- /acceleration: 加速度データセット
- /velocity: 速度データセット（V2ファイルに含まれる場合）
- /displacement: 変位データセット（V2ファイルに含まれる場合）
- /metadata: メタデータグループ（属性としてキー・値を格納）

## 複数チャンネルを含むファイルの処理

このツールは、複数のチャンネルを含むV2ファイルを自動的に検出し、チャンネルごとに分割して処理します。これにより、各チャンネルのデータを個別のファイルとして出力することができます。

## 注意事項

- V2ファイルのみ対応しています
- すべてのV2ファイルに速度と変位のデータが含まれているとは限りません
- 形式によっては一部のメタデータが失われる可能性があります
- HDF5を厳密比較する場合、環境差で `metadata.filepath` の区切り文字（`\\` / `/`）だけ差分になることがあります

## ライセンス

MIT License 