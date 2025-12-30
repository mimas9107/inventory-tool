# ----布疋與成品-倉儲位置與庫存查詢（動態地圖版）----
import pandas as pd
from flask import Flask, render_template, request, jsonify
import json
import os

# ----------------- 配置與常量 -----------------
EXCEL_FILE = 'inventory.xlsx'
AREA_CONFIG_FILE = 'location_areas.json'
MAP_RULES = {}

# Excel 欄位定義 (應與您的 Excel 標題列一致)
COL_LOCATION_DESC = '詳細位置'
COL_PRODUCT_ID = '貨品編號'
COL_PRODUCT_NAME = '貨品名稱'
COL_UNIT = '貨品基本單位'
COL_QTY = '庫存量'

COLUMNS_TO_LOAD = [COL_LOCATION_DESC, COL_PRODUCT_ID, COL_PRODUCT_NAME, COL_UNIT, COL_QTY]

app = Flask(__name__)

# ----------------- 數據處理函式 -----------------

def format_qty(qty):
    """將庫存量格式化為小數點後四位的字串，用於前端顯示"""
    try:
        return f"{float(qty):.4f}"
    except (ValueError, TypeError):
        return "N/A"

def load_area_config():
    """載入倉儲區域定義配置檔 (location_areas.json)"""
    global MAP_RULES
    try:
        with open(AREA_CONFIG_FILE, 'r', encoding='utf-8') as f:
            MAP_RULES = json.load(f)
        print(f"成功載入地圖配置檔：{AREA_CONFIG_FILE}")
    except FileNotFoundError:
        print(f"錯誤：找不到配置檔 {AREA_CONFIG_FILE}。地圖功能將無法使用。")
    except Exception as e:
        print(f"載入配置檔時發生錯誤：{e}")
load_area_config() # 服務啟動時載入配置

def get_map_info_dynamic(location_desc):
    """
    根據「所在位置」名稱動態判斷並回傳地圖資訊。
    這是應對 I 區儲位變動的核心彈性區塊。
    """
    location_desc = str(location_desc).upper().strip()
    result = {
        'area_name': '未定義區域',           # 區域的文字名稱 (例如: I區 2樓)
        'area_map_filename': '',         # 總覽地圖檔名 (例如: Map_I2F_Area.png)
        'detail_map_filename': ''        # 局部細節地圖檔名 (例如: I2-03.png)
    }
    
    if not location_desc:
        return result

    # 遍歷配置中的所有區域，尋找匹配項
    for config in MAP_RULES.values():
        if isinstance(config.get('prefix'), list):
            for prefix in config['prefix']:
                if location_desc.startswith(prefix.upper()):
                    # 匹配成功，設置區域總覽地圖資訊
                    result['area_name'] = config.get('area_name', '未知區域')
                    result['area_map_filename'] = config.get('area_map_filename', '')
                    
                    # 根據使用者需求：局部地圖檔名就是精確的儲位編號 + .png
                    # (例如 I2-03 會對應到 I2-03.png)
                    result['detail_map_filename'] = f"{location_desc}.png"
                    return result
    
    # 找不到匹配的前綴
    return result


# ----------------- 資料載入與初始化 -----------------

try:
    # 假設 Excel 檔案存在，且欄位名稱正確
    inventory_df = pd.read_excel(EXCEL_FILE, engine='openpyxl', usecols=COLUMNS_TO_LOAD)

    # 確保關鍵欄位為字串並清除前後空白
    inventory_df[COL_PRODUCT_ID] = inventory_df[COL_PRODUCT_ID].astype(str).str.strip()
    inventory_df[COL_PRODUCT_NAME] = inventory_df[COL_PRODUCT_NAME].astype(str).str.strip()
    inventory_df[COL_UNIT] = inventory_df[COL_UNIT].astype(str).str.strip()
    inventory_df[COL_LOCATION_DESC] = inventory_df[COL_LOCATION_DESC].astype(str).str.strip()
    inventory_df[COL_QTY] = pd.to_numeric(inventory_df[COL_QTY], errors='coerce')

    inventory_df.set_index(COL_PRODUCT_ID, inplace=True)
    print(f"成功載入資料：{EXCEL_FILE}，總筆數：{len(inventory_df)}")
except FileNotFoundError:
    print(f"錯誤：找不到檔案 {EXCEL_FILE}。請確認檔案是否存在。")
    inventory_df = pd.DataFrame()
except Exception as e:
    print(f"載入 Excel 檔案時發生錯誤：{e}")
    inventory_df = pd.DataFrame()


# ----------------- 路由定義 -----------------

@app.route('/')
def index():
    """首頁路由：返回前端 HTML 查詢介面"""
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query_inventory():
    """處理貨品編號精確查詢"""
    if inventory_df.empty: return jsonify({'success': False, 'message': '資料庫載入失敗或為空。'})
    product_id = request.form.get('product_id', '').strip()
    if not product_id: return jsonify({'success': False, 'message': '請輸入貨品編號。'})

    try:
        location_data = inventory_df.loc[product_id]

        def format_result_data(data):
            """輔助函式：統一整理結果的資料格式，並計算地圖檔名"""
            location_desc = data[COL_LOCATION_DESC]
            map_info = get_map_info_dynamic(location_desc) # 動態獲取地圖資訊
            print(location_desc)
            return {
                'location_desc': location_desc,
                'product_name': data[COL_PRODUCT_NAME],
                'product_unit': data[COL_UNIT],
                'current_qty': format_qty(data[COL_QTY]),
                'area_name': map_info['area_name'],
                'area_map_filename': map_info['area_map_filename'],
                'detail_map_filename': map_info['detail_map_filename']
            }

        if isinstance(location_data, pd.Series):
            # 單筆匹配
            result = {
                'success': True,
                'product_id': product_id,
                **format_result_data(location_data), # 展開所有欄位
                'is_multiple': False
            }
        elif isinstance(location_data, pd.DataFrame):
            # 多重匹配 (多個位置)
            locations = location_data.apply(format_result_data, axis=1).tolist()
            result = {
                'success': True,
                'product_id': product_id,
                'locations': locations,
                'is_multiple': True
            }
        else:
             raise KeyError()

        return jsonify(result)

    except KeyError:
        return jsonify({'success': False, 'message': f"找不到貨品編號：{product_id} 的庫存記錄。"})
    except Exception as e:
        print(f"查詢時發生錯誤：{e}")
        return jsonify({'success': False, 'message': '伺服器內部查詢錯誤，請聯繫管理員。'})


@app.route('/search_by_name', methods=['POST'])
def search_by_name():
    """處理貨品名稱關鍵字模糊查詢"""
    if inventory_df.empty: return jsonify({'success': False, 'message': '資料庫載入失敗或為空。'})
    keyword = request.form.get('keyword', '').strip()
    if not keyword: return jsonify({'success': False, 'message': '請輸入貨品名稱的關鍵字。'})

    try:
        results_df = inventory_df.reset_index()
        matched_rows = results_df[
            results_df[COL_PRODUCT_NAME].str.contains(keyword, case=False, na=False)
        ]

        if matched_rows.empty:
            return jsonify({'success': False, 'message': f"找不到包含關鍵字：'{keyword}' 的任何貨品。"
            })

        # 整理結果 (包含地圖資訊)
        search_results = matched_rows.apply(
            lambda row: {
                'product_id': row[COL_PRODUCT_ID],
                'product_name': row[COL_PRODUCT_NAME],
                'product_unit': row[COL_UNIT],
                'current_qty': format_qty(row[COL_QTY]),
                'location_desc': row[COL_LOCATION_DESC],
                # 將地圖資訊直接附加到每一筆結果中
                **get_map_info_dynamic(row[COL_LOCATION_DESC])
            },
            axis=1
        ).tolist()

        return jsonify({
            'success': True,
            'keyword': keyword,
            'count': len(search_results),
            'results': search_results
        })

    except Exception as e:
        print(f"關鍵字搜尋時發生錯誤：{e}")
        return jsonify({'success': False, 'message': '伺服器內部關鍵字搜尋錯誤，請聯繫管理員。'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
