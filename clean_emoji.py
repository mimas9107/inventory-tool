import argparse
import demoji
import os
import sys

def remove_emojis_from_file(input_path, output_path):
    """
    讀取檔案，移除所有 emoji，並寫入新檔案。
    """
    # 檢查輸入檔案是否存在
    if not os.path.exists(input_path):
        print(f"❌ 錯誤: 找不到檔案 '{input_path}'")
        return

    try:
        print(f"🔄 正在讀取檔案: {input_path} ...")
        
        # 使用 utf-8 編碼讀取，避免編碼錯誤
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 使用 demoji 替換掉 emoji (預設替換為空字串 "")
        clean_content = demoji.replace(content, "")
        
        # 計算移除前後的長度差異（僅供參考）
        removed_count = len(content) - len(clean_content)

        # 寫入輸出檔案
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(clean_content)

        print(f"✅ 成功! 已移除 emoji。")
        print(f"📂 輸出檔案: {output_path}")
        
    except Exception as e:
        print(f"❌ 發生未預期的錯誤: {e}")

def main():
    # 初始化 ArgumentParser
    parser = argparse.ArgumentParser(
        description="一個用來移除文字檔案中 Emoji 的 CLI 小工具。"
    )

    # 設定參數
    parser.add_argument(
        "input_file", 
        help="要處理的目標文字檔案路徑 (例如: data.txt)"
    )
    
    parser.add_argument(
        "-o", "--output", 
        help="輸出檔案的路徑 (選填)。如果不填，預設會在原檔名後加上 '_cleaned'。"
    )

    # 解析參數
    args = parser.parse_args()

    # 處理輸出檔名邏輯
    if args.output:
        output_file = args.output
    else:
        # 如果沒有指定輸出檔名，自動產生 (例如 test.txt -> test_cleaned.txt)
        filename, ext = os.path.splitext(args.input_file)
        output_file = f"{filename}_cleaned{ext}"

    # 執行主功能
    remove_emojis_from_file(args.input_file, output_file)

if __name__ == "__main__":
    main()