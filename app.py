import pandas as pd
from flask import Flask, render_template, request, jsonify

# ----------------- 配置 (新增欄位配置) -----------------
EXCEL_FILE = 'inventory.xlsx'
COL_PRODUCT_ID = '貨品編號'
COL_PRODUCT_NAME = '貨品名稱' # 新增：貨品名稱欄位
COL_LOCATION_FLOOR = '所在樓層'
COL_LOCATION_DESC = '具體位置描述 (中文)'
COLUMNS_TO_LOAD = [COL_PRODUCT_ID, COL_PRODUCT_NAME, COL_LOCATION_FLOOR, COL_LOCATION_DESC]

app = Flask(__name__)
try:
    inventory_df = pd.read_excel(EXCEL_FILE, engine='openpyxl', usecols=COLUMNS_TO_LOAD)
    
    # 清理資料：確保 ID 是字串，且去除前後空白
    inventory_df[COL_PRODUCT_ID] = inventory_df[COL_PRODUCT_ID].astype(str).str.strip()
    
    # 清理資料：確保名稱也是字串，並在搜尋時使用
    inventory_df[COL_PRODUCT_NAME] = inventory_df[COL_PRODUCT_NAME].astype(str).str.strip()
    
    # 設定 ID 為索引供快速查詢 ( /query )
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
    return render_template('index.html')

# (原有的 /query 路由不變，用於 ID 精確搜尋)
@app.route('/query', methods=['POST'])
def query_inventory():
    """處理貨品編號精確查詢請求"""
    # 略... (此處代碼與您原先的 app.py 相同)
    if inventory_df.empty:
        return jsonify({'success': False, 'message': '資料庫載入失敗或為空。'})

    product_id = request.form.get('product_id', '').strip()

    if not product_id:
        return jsonify({'success': False, 'message': '請輸入貨品編號。'})
    
    try:
        location_data = inventory_df.loc[product_id]
        
        # 處理單一或多個匹配項的邏輯...
        if isinstance(location_data, pd.Series):
            result = {
                'success': True,
                'product_id': product_id,
                'location_floor': location_data[COL_LOCATION_FLOOR],
                'location_desc': location_data[COL_LOCATION_DESC],
                'product_name': location_data[COL_PRODUCT_NAME], # 新增回傳名稱
                'is_multiple': False
            }
        elif isinstance(location_data, pd.DataFrame):
            locations = location_data.apply(
                lambda row: {
                    'location_floor': row[COL_LOCATION_FLOOR],
                    'location_desc': row[COL_LOCATION_DESC],
                    'product_name': row[COL_PRODUCT_NAME]
                },
                axis=1
            ).tolist()
            
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
    """處理貨品名稱關鍵字模糊查詢請求 (新增功能)"""
    if inventory_df.empty:
        return jsonify({'success': False, 'message': '資料庫載入失敗或為空。'})

    # 取得關鍵字
    keyword = request.form.get('keyword', '').strip()
    if not keyword:
        return jsonify({'success': False, 'message': '請輸入貨品名稱的關鍵字。'})

    try:
        # 關鍵字模糊比對 (使用 pandas.Series.str.contains 進行大小寫不敏感的模糊搜尋)
        # inventory_df.reset_index() 是因為索引是貨品編號，所以需要重置才能對 "貨品名稱" 欄位操作
        results_df = inventory_df.reset_index()
        
        # 使用 str.contains 進行模糊搜尋，設置 case=False 忽略大小寫
        matched_rows = results_df[
            results_df[COL_PRODUCT_NAME].str.contains(keyword, case=False, na=False)
        ]

        if matched_rows.empty:
            return jsonify({
                'success': False,
                'message': f"找不到包含關鍵字：'{keyword}' 的任何貨品。"
            })

        # 整理結果 (將 DataFrame 轉換為 JSON 列表)
        search_results = matched_rows.apply(
            lambda row: {
                'product_id': row[COL_PRODUCT_ID],
                'product_name': row[COL_PRODUCT_NAME],
                'location_floor': row[COL_LOCATION_FLOOR],
                'location_desc': row[COL_LOCATION_DESC]
            },
            axis=1
        ).tolist()
        
        # 返回找到的所有結果
        return jsonify({
            'success': True,
            'keyword': keyword,
            'count': len(search_results),
            'results': search_results
        })

    except Exception as e:
        print(f"關鍵字搜尋時發生錯誤：{e}")
        return jsonify({'success': False, 'message': '伺服器內部關鍵字搜尋錯誤，請聯繫管理員。'})


# ----------------- 啟動服務 -----------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)