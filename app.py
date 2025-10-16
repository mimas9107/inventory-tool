import pandas as pd
from flask import Flask, render_template, request, jsonify

# ----------------- 配置 (欄位名稱定義) -----------------
EXCEL_FILE = 'inventory.xlsx'
# 根據 Excel 檔案的標題列定義變數，確保程式碼與資料源的欄位名稱一致
COL_LOCATION_DESC = '所在位置'      
COL_PRODUCT_ID = '貨品編號'
COL_PRODUCT_NAME = '貨品名稱'
COL_UNIT = '貨品基本單位'          
COL_QTY = '庫存量'                 

# 指定要載入的欄位列表。由於使用欄位名稱，Excel中的順序不影響程式運行
COLUMNS_TO_LOAD = [COL_LOCATION_DESC, COL_PRODUCT_ID, COL_PRODUCT_NAME, COL_UNIT, COL_QTY]

app = Flask(__name__)

# 格式化庫存量 (小數點後四位) 的輔助函式
def format_qty(qty):
    """將庫存量格式化為小數點後四位的字串，用於前端顯示"""
    try:
        return f"{float(qty):.4f}"
    except (ValueError, TypeError):
        return "N/A" # 處理非數值或空值的情況

# ----------------- 資料載入區 (服務啟動時只執行一次) -----------------
try:
    # 讀取 Excel：使用 openpyxl 引擎，並僅載入 COLUMNS_TO_LOAD 中指定的欄位
    inventory_df = pd.read_excel(EXCEL_FILE, engine='openpyxl', usecols=COLUMNS_TO_LOAD)
    
    # 確保關鍵欄位為字串並清除前後空白，避免查詢匹配失敗
    inventory_df[COL_PRODUCT_ID] = inventory_df[COL_PRODUCT_ID].astype(str).str.strip()
    inventory_df[COL_PRODUCT_NAME] = inventory_df[COL_PRODUCT_NAME].astype(str).str.strip()
    inventory_df[COL_UNIT] = inventory_df[COL_UNIT].astype(str).str.strip()

    # 將庫存量轉換為數值 (float)，如果遇到非數值資料則設為 NaN (Not a Number)
    inventory_df[COL_QTY] = pd.to_numeric(inventory_df[COL_QTY], errors='coerce')

    # 設定 '貨品編號' 為 DataFrame 的索引，以便使用 .loc 進行快速、精確查詢
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
    """處理貨品編號精確查詢 (區塊 1)"""
    
    product_id = request.form.get('product_id', '').strip()
    if not product_id:
        return jsonify({'success': False, 'message': '請輸入貨品編號。'})
    
    try:
        # 使用索引 (loc) 進行精確查詢
        location_data = inventory_df.loc[product_id]
        
        # 檢查結果是單筆 (Series) 還是多筆 (DataFrame)
        if isinstance(location_data, pd.Series):
            # 單一匹配：直接整理成字典回傳
            result = {
                'success': True,
                'product_id': product_id,
                'location_desc': location_data[COL_LOCATION_DESC],
                'product_name': location_data[COL_PRODUCT_NAME],
                'product_unit': location_data[COL_UNIT],
                'current_qty': format_qty(location_data[COL_QTY]), # 格式化庫存量
                'is_multiple': False
            }
        elif isinstance(location_data, pd.DataFrame):
            # 多重匹配：整理成列表回傳給前端
            locations = location_data.apply(
                lambda row: {
                    'location_desc': row[COL_LOCATION_DESC],
                    'product_name': row[COL_PRODUCT_NAME],
                    'product_unit': row[COL_UNIT],
                    'current_qty': format_qty(row[COL_QTY])
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
        # 找不到該 ID 的錯誤處理
        return jsonify({'success': False, 'message': f"找不到貨品編號：{product_id} 的庫存記錄。"})


@app.route('/search_by_name', methods=['POST'])
def search_by_name():
    """處理貨品名稱關鍵字模糊查詢 (區塊 2)"""
    
    keyword = request.form.get('keyword', '').strip()
    if not keyword:
        return jsonify({'success': False, 'message': '請輸入貨品名稱的關鍵字。'})

    try:
        # 為了對 '貨品名稱' 欄位操作，需要暫時重置索引
        results_df = inventory_df.reset_index()
        
        # 核心：使用 str.contains 進行大小寫不敏感 (case=False) 的模糊比對
        matched_rows = results_df[
            results_df[COL_PRODUCT_NAME].str.contains(keyword, case=False, na=False)
        ]

        if matched_rows.empty:
            return jsonify({
                'success': False,
                'message': f"找不到包含關鍵字：'{keyword}' 的任何貨品。"
            })

        # 整理結果：將所有匹配的列轉換為 JSON 格式
        search_results = matched_rows.apply(
            lambda row: {
                'product_id': row[COL_PRODUCT_ID],
                'product_name': row[COL_PRODUCT_NAME],
                'location_desc': row[COL_LOCATION_DESC],
                'product_unit': row[COL_UNIT],         
                'current_qty': format_qty(row[COL_QTY]) 
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


# ----------------- 啟動服務 -----------------

if __name__ == '__main__':
    # host='0.0.0.0' 允許從外部網路訪問 (在公司內部網路部署時很有用)
    # debug=True 方便開發調試
    app.run(host='0.0.0.0', port=5000, debug=True)