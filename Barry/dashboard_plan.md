# 執行計畫：鐵粉排行榜 API 重構與動態篩選功能

為了解決動態計算的效能問題，並提供更多元的排行檢視方式，我規劃了以下的前後端整合修改方案。

## User Review Required

> [!IMPORTANT]  
> 這次修改會異動到 FastAPI 的端點與回傳結構，並在儀表板增加連動控制項。請確認篩選器的設計方向是否符合您的需求。

## Proposed Changes

### [API 端點重構]
#### [MODIFY] `front_app.py`
為了加速讀取並簡化邏輯，我們將：
1. **捨棄原有的動態 Group By 查詢**：移除以 `video_comments` 即時計算留言數的方法。
2. **新增單一端點 `/api/top_fans`**：
   - 直接從預先算好的 `topN_comments` 表格中，以 `channel_id` 撈取資料。
   - 回傳統一格式：`{ channel_id_A: [ {name, comment_count, total_likes}, ... ], channel_id_B: ... }`。
3. 這樣就不用再分兩個 API (`top_commenters` 和 `top_commenters_by_likes`)，全部交由前端快速重排。

### [UI 操作介面實作]
#### [MODIFY] `youtuber_comparison_dashboard.html`
1. **新增排序與篩選下拉選單**：
   在「互動常客榜單」區塊右上角新增兩個 `<select>`，採用符合目前設計系統的樣式：
   - **頻道篩選**：可選擇看「全部綜合」、「YTer A 的粉絲」或「YTer B 的粉絲」。
   - **排序切換**：可選擇依「留言數」或依「獲讚數」精準排序。
2. **JavaScript 邏輯擴充**：
   - 建立全域變數 `globalFansData` 緩存後端傳來的資料。
   - 新增 `renderTopCommentersUI()` 函數：根據下拉選單的選擇，動態過濾對應的頻道數據，並使用原生的 `Array.sort` 切換排序邏輯，最後即時渲染清單。
   - 當切換為「獲讚數」排序時，榜單上的數據亮點會自動從「則留言」切換為「顆愛心 ❤️」顯示。

## Verification Plan

### Manual Verification
1. 重啟 uvicorn，並刷新儀表板頁面。
2. 觀察 "互動常客榜單" 區塊。
3. 測試切換「全部/頻道A/頻道B」看是否成功篩選。
4. 測試切換「留言數/獲愛心數」看數值、文字與排序是否正確對應。
