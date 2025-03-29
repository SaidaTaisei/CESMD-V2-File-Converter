#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CESMD V2ファイルコンバーター
Center for Engineering Strong Motion Data (CESMD)のV2形式のファイルを
CSV、MAT、HDF5形式に変換するためのGUIツール
"""

import os
import sys
import re
import glob
import numpy as np
import pandas as pd
from scipy import io as sio
import h5py
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from threading import Thread
import traceback

# TkDNDライブラリのインポートを試みる（インストールされていない場合はスキップ）
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    ENABLE_DND = True
except ImportError:
    ENABLE_DND = False
    print("ドラッグアンドドロップ機能を有効にするには、以下のコマンドを実行してください:")
    print("pip install tkinterdnd2")

class CESMDConverter:
    """CESMDのV2ファイルを処理するためのコンバータークラス"""
    
    def __init__(self):
        """コンバーターを初期化"""
        self.metadata = {}
        self.acceleration = None
        self.velocity = None
        self.displacement = None
        self.sampling_rate = None
        self.time_array = None
    
    def parse_v2_file(self, filepath):
        """V2ファイルを解析して必要なデータを抽出する"""
        try:
            with open(filepath, 'r') as f:
                content = f.readlines()
            
            # メタデータを抽出
            self.metadata = {
                'filename': os.path.basename(filepath),
                'filepath': filepath,
            }
            
            # チャンネル番号の初期化（デフォルト値）
            channel_num = 0
            
            # 基本情報の抽出（ヘッダーから）
            for i, line in enumerate(content[:30]):
                # チャンネル番号を検索
                chan_match = re.search(r'Chan\s+(\d+)', line, re.IGNORECASE)
                if chan_match:
                    channel_num = int(chan_match.group(1))
                    self.metadata['channel_number'] = channel_num
                
                # 観測日時を検索
                date_match = re.search(r'Rcrd of ([A-Za-z]+) ([A-Za-z]+) (\d+), (\d+) (\d+):(\d+):(\d+\.\d+)', line, re.IGNORECASE)
                if date_match:
                    observation_time = date_match.group(0)
                    self.metadata['observation_time'] = observation_time
                    
                    # 日時を個別に格納
                    self.metadata['obs_month'] = date_match.group(2)    # 月名
                    self.metadata['obs_day'] = int(date_match.group(3)) # 日
                    self.metadata['obs_year'] = int(date_match.group(4)) # 年
                    self.metadata['obs_hour'] = int(date_match.group(5)) # 時
                    self.metadata['obs_minute'] = int(date_match.group(6)) # 分
                    self.metadata['obs_second'] = float(date_match.group(7)) # 秒
                
                # UTC時間を検索
                utc_match = re.search(r'Start time:\s+(\d+)/(\d+)/(\d+),\s+(\d+):(\d+):(\d+\.\d+)\s+UTC', line, re.IGNORECASE)
                if utc_match:
                    utc_time = utc_match.group(0)
                    self.metadata['utc_time'] = utc_time
                    
                    # UTC日時を個別に格納
                    self.metadata['utc_month'] = int(utc_match.group(1))  # 月
                    self.metadata['utc_day'] = int(utc_match.group(2))    # 日
                    
                    # 年（2桁から4桁に変換）- 1990年代と2000年代の両方に対応
                    year_2digit = int(utc_match.group(3))
                    if year_2digit >= 90:  # 1990年代
                        full_year = 1900 + year_2digit
                    else:  # 2000年代
                        full_year = 2000 + year_2digit
                    self.metadata['utc_year'] = full_year
                    
                    self.metadata['utc_hour'] = int(utc_match.group(4))   # 時
                    self.metadata['utc_minute'] = int(utc_match.group(5)) # 分
                    self.metadata['utc_second'] = float(utc_match.group(6)) # 秒
                
                if re.search(r'Station No\.', line, re.IGNORECASE):
                    station_info = re.search(r'Station No\.\s+(\d+)\s+([\d\.]+)([NS])\s*,\s*([\d\.]+)([EW])', line, re.IGNORECASE)
                    if station_info:
                        self.metadata['station_id'] = station_info.group(1)
                        self.metadata['latitude'] = float(station_info.group(2)) * (1 if station_info.group(3) == 'N' else -1)
                        self.metadata['longitude'] = float(station_info.group(4)) * (1 if station_info.group(5) == 'E' else -1)
                
                # 地震情報を検索
                if re.search(r'Hypocenter:', line, re.IGNORECASE):
                    hypocenter_info = line.strip()
                    self.metadata['hypocenter_info'] = hypocenter_info
                
                # マグニチュード情報を検索
                magnitude_match = re.search(r'ML:\s+(.+)', line, re.IGNORECASE)
                if magnitude_match:
                    magnitude_info = magnitude_match.group(1)
                    self.metadata['magnitude_info'] = magnitude_info
                
                if re.search(r'Instr(ument)?\s+Period', line, re.IGNORECASE):
                    period_info = re.search(r'Instr(ument)?\s+Period\s*=\s*([\d\.]+)\s*sec', line, re.IGNORECASE)
                    if period_info:
                        self.metadata['instrument_period'] = float(period_info.group(2))
                
                if re.search(r'At equally-spaced intervals of', line, re.IGNORECASE):
                    interval_info = re.search(r'At equally-spaced intervals of\s*([\d\.]+)\s*sec', line, re.IGNORECASE)
                    if interval_info:
                        interval = float(interval_info.group(1))
                        self.sampling_rate = 1.0 / interval
                        self.metadata['sampling_rate'] = self.sampling_rate
                        self.metadata['time_interval'] = interval
                
                if re.search(r'Peak acceleration', line, re.IGNORECASE):
                    acc_info = re.search(r'Peak acceleration\s*=\s*([\d\.\-]+)', line, re.IGNORECASE)
                    if acc_info:
                        self.metadata['peak_acceleration'] = float(acc_info.group(1))
                
                if re.search(r'Peak\s+velocity', line, re.IGNORECASE):
                    vel_info = re.search(r'Peak\s+velocity\s*=\s*([\d\.\-]+)', line, re.IGNORECASE)
                    if vel_info:
                        self.metadata['peak_velocity'] = float(vel_info.group(1))
                
                if re.search(r'Peak displacement', line, re.IGNORECASE):
                    disp_info = re.search(r'Peak displacement\s*=\s*([\d\.\-]+)', line, re.IGNORECASE)
                    if disp_info:
                        self.metadata['peak_displacement'] = float(disp_info.group(1))
            
            # データセクションを探索
            accel_start_line = None
            velocity_start_line = None
            displ_start_line = None
            end_of_data_line = None
            
            for i, line in enumerate(content):
                if 'points of accel data equally spaced' in line.lower():
                    accel_start_line = i + 1
                elif 'points of veloc data equally spaced' in line.lower():
                    velocity_start_line = i + 1
                elif 'points of displ data equally spaced' in line.lower():
                    displ_start_line = i + 1
                elif 'End of data for channel' in line or 'end of data for channel' in line.lower():
                    end_of_data_line = i
            
            if accel_start_line is None:
                raise ValueError("加速度データセクションが見つかりません")
            
            # 加速度データセクションの終了位置を決定
            accel_end_line = velocity_start_line - 1 if velocity_start_line else end_of_data_line
            
            # 速度データセクションの終了位置を決定
            velocity_end_line = displ_start_line - 1 if displ_start_line else end_of_data_line
            
            # 変位データセクションの終了位置を決定
            displ_end_line = end_of_data_line
            
            # 加速度データを抽出
            acceleration_data = []
            for i in range(accel_start_line, accel_end_line):
                # line = content[i].strip()
                # if not line:
                #     continue
                
                # 10文字単位で数値を抽出
                try:
                    # values = [float(line[10*j:10*(j+1)].strip()) for j in range(len(line)//10) if line[10*j:10*(j+1)].strip()]
                    line = content[i]
                    # print(line)
                    values = [float(line[10*j:10*(j+1)]) for j in range(8) if len(line[10*j:10+10*j])>3]
                    acceleration_data.extend(values)
                except ValueError:
                    # 数値でない行はスキップ
                    pass
            # print(acceleration_data)
            self.acceleration = np.array(acceleration_data)
            
            # 速度データを抽出（存在する場合）
            self.velocity = None
            if velocity_start_line and velocity_end_line:
                velocity_data = []
                for i in range(velocity_start_line, velocity_end_line):
                    # line = content[i].strip()
                    # if not line:
                    #     continue
                    
                    # 10文字単位で数値を抽出
                    try:
                        # values = [float(line[10*j:10*(j+1)].strip()) for j in range(len(line)//10) if line[10*j:10*(j+1)].strip()]
                        line = content[i]
                        values = [float(line[10*j:10*(j+1)]) for j in range(8) if len(line[10*j:10+10*j])>3]
                        velocity_data.extend(values)
                    except ValueError:
                        # 数値でない行はスキップ
                        pass
                
                self.velocity = np.array(velocity_data)
            else:
                print("速度データセクションが見つかりません")
            
            # 変位データを抽出（存在する場合）
            self.displacement = None
            if displ_start_line and displ_end_line:
                displacement_data = []
                for i in range(displ_start_line, displ_end_line):
                    # line = content[i].strip()
                    # if not line:
                    #     continue
                    
                    # 10文字単位で数値を抽出
                    try:
                        # values = [float(line[10*j:10*(j+1)].strip()) for j in range(len(line)//10) if line[10*j:10*(j+1)].strip()]
                        line = content[i]
                        values = [float(line[10*j:10*(j+1)]) for j in range(8) if len(line[10*j:10+10*j])>3]
                        displacement_data.extend(values)
                    except ValueError:
                        # 数値でない行はスキップ
                        pass
                
                self.displacement = np.array(displacement_data)
            else:
                print("変位データセクションが見つかりません")
            
            # 時間配列を生成
            if self.sampling_rate is not None:
                dt = 1.0 / self.sampling_rate
                n = len(self.acceleration)
                self.time_array = np.arange(0, n * dt, dt)[:n]
            
            return True
        
        except Exception as e:
            print(f"ファイルの解析エラー: {e}")
            return False
    
    def to_csv(self, output_path):
        """データをCSV形式で保存"""
        if self.acceleration is None or self.time_array is None:
            raise ValueError("データがロードされていません")
        
        # DataFrameを作成
        data = {
            'Time': self.time_array,
            'Acceleration': self.acceleration
        }
        
        # 速度と変位データが存在する場合は追加
        if self.velocity is not None:
            if len(self.velocity) == len(self.time_array):
                data['Velocity'] = self.velocity
            else:
                print(f"警告: 速度データの長さが時間配列と一致しません。({len(self.velocity)} != {len(self.time_array)})")
        
        if self.displacement is not None:
            if len(self.displacement) == len(self.time_array):
                data['Displacement'] = self.displacement
            else:
                print(f"警告: 変位データの長さが時間配列と一致しません。({len(self.displacement)} != {len(self.time_array)})")
        
        df = pd.DataFrame(data)
        
        # メタデータをヘッダーとして追加（コメント行として）
        # 数値の精度を維持するためにフォーマットを調整
        metadata_items = []
        for k, v in self.metadata.items():
            if isinstance(v, float):
                # 浮動小数点数の場合、科学表記法を避けて完全な精度で出力
                metadata_items.append(f"{k}: {v:.16g}")
            else:
                metadata_items.append(f"{k}: {v}")
        
        metadata_str = "# " + ", ".join(metadata_items)
        
        # CSVに保存 - line_terminatorを指定して空行を防止
        with open(output_path, 'w') as f:
            f.write(metadata_str + "\n")
            df.to_csv(f, index=False, lineterminator='\n')
        
        return True
    
    def to_mat(self, output_path):
        """データをMAT形式で保存"""
        if self.acceleration is None or self.time_array is None:
            raise ValueError("データがロードされていません")
        
        # MATLABで使用するための辞書を作成
        mat_dict = {
            'time': self.time_array,
            'acceleration': self.acceleration,
            'metadata': self.metadata
        }
        
        # 速度と変位データが存在する場合は追加
        if self.velocity is not None:
            mat_dict['velocity'] = self.velocity
        
        if self.displacement is not None:
            mat_dict['displacement'] = self.displacement
        
        # MATファイルに保存
        sio.savemat(output_path, mat_dict)
        
        return True
    
    def to_hdf5(self, output_path):
        """データをHDF5形式で保存"""
        if self.acceleration is None or self.time_array is None:
            raise ValueError("データがロードされていません")
        
        with h5py.File(output_path, 'w') as h5f:
            # データセットを作成
            h5f.create_dataset('time', data=self.time_array)
            h5f.create_dataset('acceleration', data=self.acceleration)
            
            # 速度と変位データが存在する場合は追加
            if self.velocity is not None:
                h5f.create_dataset('velocity', data=self.velocity)
            
            if self.displacement is not None:
                h5f.create_dataset('displacement', data=self.displacement)
            
            # メタデータを属性として追加
            meta_group = h5f.create_group('metadata')
            for key, value in self.metadata.items():
                if isinstance(value, (int, float, str)):
                    meta_group.attrs[key] = value
        
        return True

    @staticmethod
    def has_multiple_channels(input_v2_filepath):
        """
        指定された V2 ファイルに複数チャンネルが含まれている可能性が高いか判定する。
        ファイル内の "Corrected accelerogram" の出現回数に基づきます。

        Args:
            input_v2_filepath (str): 判定する V2 ファイルのパス。

        Returns:
            bool: "Corrected accelerogram" が4回以上出現する場合は True、
                  それ以外の場合 (2回以下、ファイルが見つからない、エラー) は False。
        """
        print(f"複数チャンネルチェック: {input_v2_filepath}")
        if not os.path.exists(input_v2_filepath):
            print(f"エラー: ファイルが見つかりません: {input_v2_filepath}")
            return False

        try:
            with open(input_v2_filepath, 'r', encoding='utf-8', errors='ignore') as f:
                # ファイル全体を読み込むか、大きなファイルの場合は行ごとに処理することも検討
                file_content = f.read()

            # 大文字小文字を区別せずに "Corrected accelerogram" の出現回数を数える
            # 行頭にあることを前提とするなら正規表現を使う方がより正確かもしれないが、
            # まずは単純な文字列カウントで実装
            count = file_content.lower().count('corrected accelerogram')

            print(f" -> 'Corrected accelerogram' の出現回数: {count}")
            # 出現回数が2より大きい場合に True を返す
            return count > 2

        except FileNotFoundError:
            # ここには到達しないはずだが念のため
            print(f"エラー: ファイル読み込み中にエラー発生 (FileNotFound): {input_v2_filepath}")
            return False
        except Exception as e:
            print(f"ファイル読み込みまたは処理中に予期せぬエラー ({input_v2_filepath}): {e}")
            traceback.print_exc()
            return False

    @staticmethod
    def split_v2_file_by_channel(input_v2_filepath):
        """
        複数チャンネルを含む可能性のある V2 ファイルをチャンネルごとに分割し、
        入力ファイルと同じディレクトリに個別の V2 ファイルとして保存する。

        Args:
            input_v2_filepath (str): 入力となる V2 ファイルのパス。

        Returns:
            list[str]: 正常に作成された出力 V2 ファイルのパスのリスト。
                       エラーが発生した場合やチャンネルが見つからない場合は空のリストを返す。
        """
        output_filepaths = []
        print(f"チャンネル分割処理開始: {input_v2_filepath}")

        if not os.path.exists(input_v2_filepath):
            print(f"エラー: 入力ファイルが見つかりません: {input_v2_filepath}")
            return output_filepaths # 空リストを返す

        output_directory = os.path.dirname(input_v2_filepath)
        base_filename = os.path.basename(input_v2_filepath)
        base_name_without_ext = os.path.splitext(base_filename)[0]

        try:
            # ファイル全体を読み込む
            with open(input_v2_filepath, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()

            if not file_content.strip():
                print(f"警告: 入力ファイルが空です: {input_v2_filepath}")
                return output_filepaths # 空リストを返す

            # チャンネルヘッダーのパターン
            header_pattern = re.compile(r'^Corrected accelerogram.*?Chan\s+(\d+):', re.IGNORECASE | re.MULTILINE)
            matches = list(header_pattern.finditer(file_content))

            if not matches:
                # ヘッダーが見つからない場合、単一チャンネルファイルとして扱うか、警告のみとする
                print(f"情報: {base_filename} で複数チャンネルのヘッダーが見つかりませんでした。分割は行われません。")
                # 元のファイルパスをリストに入れて返すことも考えられるが、
                # 「分割されたファイル」ではないため、ここでは空リストを返す仕様とする。
                # もし単一チャンネルでもリストに含めたい場合は、 return [input_v2_filepath] とする
                return output_filepaths

            # ヘッダーに基づいてブロックを分割・保存
            num_blocks_processed = 0 # 処理したブロック数（ヘッダー前のブロックも含む可能性）
            for i, match in enumerate(matches):
                block_start = match.start()
                block_end = matches[i+1].start() if i + 1 < len(matches) else len(file_content)
                channel_block = file_content[block_start:block_end]
                num_blocks_processed += 1

                # ブロック内のヘッダーからチャンネル番号を再取得
                header_in_block_match = header_pattern.search(channel_block)
                if header_in_block_match:
                    channel_num = int(header_in_block_match.group(1))
                    # 出力ファイル名: 元ファイル名_chan_XXX.V2
                    output_filename = f"{base_name_without_ext}_chan_{channel_num}.V2"
                    output_filepath = os.path.join(output_directory, output_filename)

                    try:
                        with open(output_filepath, 'w', encoding='utf-8') as outfile:
                            outfile.write(channel_block)
                        output_filepaths.append(output_filepath) # 成功したパスをリストに追加
                        print(f" -> チャンネル {channel_num} を {output_filepath} に保存しました。")
                    except Exception as e:
                        print(f"エラー: チャンネル {channel_num} のファイル書き込み中にエラー: {output_filepath}, {e}")
                        traceback.print_exc()
                        # エラーが発生したファイルはリストに追加しない
                else:
                     print(f"警告: {base_filename} のブロック {i+1} でヘッダー再確認不可。スキップ。")

            # 最初のヘッダーより前の部分 (プリアンブルなど) の扱い
            if matches[0].start() > 0:
                 pre_header_block = file_content[:matches[0].start()]
                 if pre_header_block.strip():
                     num_blocks_processed += 1
                     # このブロックは特定のチャンネル番号を持たないため、別のファイル名で保存するか、
                     # あるいは無視するかを決定する必要がある。
                     # ここでは警告を出力し、分割ファイルリストには含めない。
                     print(f"警告: {base_filename} の先頭にヘッダー外ブロック検出。この部分は分割ファイルとして保存されません。")
                     # もし保存したい場合は、別途ファイル名を決めて書き込み、リストに追加する。
                     # 例: output_filename = f"{base_name_without_ext}_preamble.V2" ...

            if output_filepaths:
                 print(f"処理完了: {base_filename} から {len(output_filepaths)} 個のチャンネルファイルを分割しました。")
            else:
                 print(f"情報: {base_filename} は処理されましたが、有効なチャンネルブロックが見つからなかったか、書き込みに失敗しました。")

            return output_filepaths

        except FileNotFoundError:
             # このパスは関数の冒頭でチェック済みだが、念のため
             print(f"エラー: 入力ファイル処理中にエラー発生 (FileNotFound): {input_v2_filepath}")
             return []
        except Exception as e:
            print(f"予期せぬエラーが発生しました ({input_v2_filepath}): {e}")
            traceback.print_exc()
            return [] # エラー時は空リスト


class ConverterGUI:
    """コンバーターのGUIインターフェース"""
    
    def __init__(self, root):
        """GUIの初期化"""
        self.root = root
        self.root.title("CESMD V2ファイルコンバーター")
        self.root.geometry("600x400")
        self.root.resizable(True, True)
        
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.output_format = tk.StringVar(value="csv")  # デフォルト値
        
        # 入力ディレクトリが変更されたときのコールバックを設定
        self.input_dir.trace_add("write", self.on_input_dir_changed)
        
        # 入力ディレクトリの自動更新を許可するフラグ
        self.allow_output_sync = True
        
        # ドラッグ&ドロップの設定（利用可能な場合）
        self.dnd_enabled = ENABLE_DND
        
        self.setup_ui()
    
    def on_input_dir_changed(self, *args):
        """入力ディレクトリが変更されたときのコールバック"""
        # 自動更新が許可されていて、出力ディレクトリが空または前回の入力ディレクトリと同じだった場合のみ更新
        if self.allow_output_sync and (not self.output_dir.get() or self.output_dir.get() == self._previous_input_dir):
            input_dir = self.input_dir.get()
            if input_dir:
                self.output_dir.set(input_dir)
        
        # 現在の入力ディレクトリを記憶
        if hasattr(self, '_previous_input_dir'):
            self._previous_input_dir = self.input_dir.get()
    
    def setup_ui(self):
        """UIコンポーネントのセットアップ"""
        # 入力ディレクトリの初期値を記録
        self._previous_input_dir = self.input_dir.get()
        
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 入力ディレクトリ選択
        input_frame_text = "入力ディレクトリ"
        if self.dnd_enabled:
            input_frame_text += "（ドラッグ&ドロップ可能）"
        
        input_frame = ttk.LabelFrame(main_frame, text=input_frame_text, padding=5)
        input_frame.pack(fill=tk.X, pady=5)
        
        self.input_entry = ttk.Entry(input_frame, textvariable=self.input_dir, width=50)
        self.input_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(input_frame, text="選択", command=self.browse_input_dir).pack(side=tk.RIGHT, padx=5)
        
        # 出力ディレクトリ選択
        output_frame_text = "出力ディレクトリ"
        if self.dnd_enabled:
            output_frame_text += "（ドラッグ&ドロップ可能）"
            
        output_frame = ttk.LabelFrame(main_frame, text=output_frame_text, padding=5)
        output_frame.pack(fill=tk.X, pady=5)
        
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_dir, width=50)
        self.output_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="選択", command=self.browse_output_dir).pack(side=tk.RIGHT, padx=5)
        
        # ドラッグ&ドロップの設定（利用可能な場合）
        if self.dnd_enabled:
            self.input_entry.drop_target_register(DND_FILES)
            self.input_entry.dnd_bind('<<Drop>>', self.handle_input_drop)
            
            self.output_entry.drop_target_register(DND_FILES)
            self.output_entry.dnd_bind('<<Drop>>', self.handle_output_drop)
        
        # 出力形式選択
        format_frame = ttk.LabelFrame(main_frame, text="出力形式", padding=5)
        format_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(format_frame, text="CSV", variable=self.output_format, value="csv").pack(side=tk.LEFT, padx=20)
        ttk.Radiobutton(format_frame, text="MAT", variable=self.output_format, value="mat").pack(side=tk.LEFT, padx=20)
        ttk.Radiobutton(format_frame, text="HDF5", variable=self.output_format, value="h5").pack(side=tk.LEFT, padx=20)
        
        # 実行ボタン
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(action_frame, text="変換開始", command=self.start_conversion).pack(padx=5, pady=5)
        
        # 進捗表示
        progress_frame = ttk.LabelFrame(main_frame, text="進捗状況", padding=5)
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_var = tk.StringVar(value="待機中...")
        ttk.Label(progress_frame, textvariable=self.status_var).pack(padx=5, pady=5, anchor=tk.W)
    
    def handle_input_drop(self, event):
        """入力ディレクトリエントリーへのドロップイベントハンドラ"""
        path = event.data
        # Windowsパスの場合、{} を削除
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        # ディレクトリならそのまま、ファイルならディレクトリ部分を抽出
        directory = path if os.path.isdir(path) else os.path.dirname(path)
        
        # 入力ディレクトリをセット（trace_add経由で出力ディレクトリも更新される）
        self.input_dir.set(directory)
    
    def handle_output_drop(self, event):
        """出力ディレクトリエントリーへのドロップイベントハンドラ"""
        path = event.data
        # Windowsパスの場合、{} を削除
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        # ディレクトリならそのまま、ファイルならディレクトリ部分を抽出
        directory = path if os.path.isdir(path) else os.path.dirname(path)
        
        # ユーザーが明示的に出力ディレクトリを設定した場合は、入力ディレクトリとの自動同期を一時的に無効化
        self.allow_output_sync = False
        self.output_dir.set(directory)
    
    def browse_input_dir(self):
        """入力ディレクトリを選択"""
        directory = filedialog.askdirectory(title="入力ディレクトリを選択")
        if directory:
            # 入力ディレクトリをセット（trace_add経由で出力ディレクトリも更新される）
            self.input_dir.set(directory)
    
    def browse_output_dir(self):
        """出力ディレクトリを選択"""
        directory = filedialog.askdirectory(title="出力ディレクトリを選択")
        if directory:
            # ユーザーが明示的に出力ディレクトリを設定した場合は、入力ディレクトリとの自動同期を一時的に無効化
            self.allow_output_sync = False
            self.output_dir.set(directory)
    
    def start_conversion(self):
        """変換処理を開始"""
        input_dir = self.input_dir.get()
        output_dir = self.output_dir.get()
        output_format = self.output_format.get()
        
        if not input_dir or not output_dir:
            messagebox.showerror("エラー", "入力ディレクトリと出力ディレクトリを選択してください")
            return
        
        if not os.path.exists(input_dir):
            messagebox.showerror("エラー", "入力ディレクトリが存在しません")
            return
        
        if not os.path.exists(output_dir):
            response = messagebox.askyesno("確認", "出力ディレクトリが存在しません。作成しますか？")
            if response:
                os.makedirs(output_dir)
            else:
                return
        
        # 変換処理をバックグラウンドで実行
        thread = Thread(target=self.convert_files, args=(input_dir, output_dir, output_format))
        thread.daemon = True
        thread.start()
    
    def convert_files(self, input_dir, output_dir, output_format):
        """ディレクトリ内のすべてのV2ファイルを変換"""
        self.status_var.set("ファイルを検索中...")
        self.progress_var.set(0)
        
        # V2ファイルを検索
        v2_files = glob.glob(os.path.join(input_dir, "*.V2"))
        
        if not v2_files:
            self.status_var.set("V2ファイルが見つかりません")
            messagebox.showinfo("情報", "指定されたディレクトリにV2ファイルが見つかりません")
            return
        
        total_files = len(v2_files)
        self.status_var.set(f"{total_files}個のファイルを処理します...")
        
        # 各ファイルを処理
        success_count = 0
        error_count = 0
        
        for i, file_path in enumerate(v2_files):
            try:
                file_name = os.path.basename(file_path)
                
                self.status_var.set(f"処理中: {file_name} ({i+1}/{total_files})")
                
                # 複数チャンネルがあるかどうか
                if CESMDConverter.has_multiple_channels(file_path):
                    file_paths = CESMDConverter.split_v2_file_by_channel(file_path)
                    for _file_path in file_paths:
                        # ファイルを解析して変換
                        converter = CESMDConverter()
                        if converter.parse_v2_file(_file_path):
                            # チャンネル番号があれば使用、なければファイル名から推測
                            channel_num = converter.metadata.get('channel_number', 0)
                            if channel_num == 0:
                                # ファイル名からチャンネル番号を探す試み
                                chan_match = re.search(r'CHAN(\d+)', file_name, re.IGNORECASE)
                                if chan_match:
                                    channel_num = int(chan_match.group(1))
                            
                            # 出力ファイル名を生成（channel_XXX.拡張子 形式）
                            output_file_name = f"channel_{channel_num:03d}.{output_format}"
                            output_file = os.path.join(output_dir, output_file_name)
                            
                            # 選択された形式で保存
                            if output_format == "csv":
                                converter.to_csv(output_file)
                            elif output_format == "mat":
                                converter.to_mat(output_file)
                            elif output_format == "h5":
                                converter.to_hdf5(output_file)
                            
                            success_count += 1
                        else:
                            error_count += 1
                else:
                    # ファイルを解析して変換
                    converter = CESMDConverter()
                    if converter.parse_v2_file(file_path):
                        # チャンネル番号があれば使用、なければファイル名から推測
                        channel_num = converter.metadata.get('channel_number', 0)
                        if channel_num == 0:
                            # ファイル名からチャンネル番号を探す試み
                            chan_match = re.search(r'CHAN(\d+)', file_name, re.IGNORECASE)
                            if chan_match:
                                channel_num = int(chan_match.group(1))
                        
                        # 出力ファイル名を生成（channel_XXX.拡張子 形式）
                        output_file_name = f"channel_{channel_num:03d}.{output_format}"
                        output_file = os.path.join(output_dir, output_file_name)
                        
                        # 選択された形式で保存
                        if output_format == "csv":
                            converter.to_csv(output_file)
                        elif output_format == "mat":
                            converter.to_mat(output_file)
                        elif output_format == "h5":
                            converter.to_hdf5(output_file)
                        
                        success_count += 1
                    else:
                        error_count += 1
                
                # 進捗を更新
                progress = (i + 1) / total_files * 100
                self.progress_var.set(progress)
            
            except Exception as e:
                error_count += 1
                print(f"ファイル処理エラー: {file_path}, {e}")
        
        # 完了メッセージ
        if error_count == 0:
            self.status_var.set(f"完了: {success_count}個のファイルを変換しました")
            messagebox.showinfo("完了", f"{success_count}個のファイルを変換しました")
        else:
            self.status_var.set(f"完了: {success_count}個のファイルを変換しました（{error_count}個のエラー）")
            messagebox.showwarning("警告", f"{success_count}個のファイルを変換しました（{error_count}個のエラー）")


if __name__ == "__main__":
    # tkinterdnd2が利用可能な場合、TkinterDnDを使用
    if ENABLE_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = ConverterGUI(root)
    root.mainloop()
