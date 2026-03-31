# Dashboard UX 改版計畫 (Sidebar 與分頁切換)

根據您的最新需求，我們將進一步向 `front.html` 的完整版面靠攏，並解決「畫面太長、全部擠在一起」的問題。

## User Review Required

> [!IMPORTANT]
> 請確認以下重構計畫是否符合您的期待：
> 1. **移除手動輸入框**：我會將頂部的「Channel ID 搜尋框」與「開始分析」按鈕全部移除，並將頻道 ID 寫死在背景自動載入，讓畫面更清爽。
> 2. **引入側邊欄 (SideNavBar)**：我會將 `front.html` 左側的黑色導覽列 (Dashboard, Channels, Content... 等目錄) 完整移植過來。
> 3. **實作「分頁切換」功能 (解決全擠在同一頁的問題)**：我會讓左側的側邊選單具備切換功能，將目前的圖表與資料拆分成三個不同的畫面 (Tabs)：
>    - 📊 **Dashboard (數據總覽)**：只顯示 4 張總覽卡片與觀看數走勢圖。
>    - 👥 **Audience (粉絲互動)**：只顯示按讚/留言互動圖表與「Top 10 鐵粉留言者」。
>    - 🎬 **Content (內容表現)**：只顯示發片頻率圖表與「Top 5 熱門影片清單」。
> 這樣可以確保不會把所有圖表跟表格硬塞在同一個捲動視窗中！

## Proposed Changes

### [MODIFY] [youtuber_comparison_dashboard.html](file:///c:/Users/a5020877/Documents/github/KOL_project/Barry/youtuber_comparison_dashboard.html)
- **HTML Layout 結構調整**：
  - 加入 `<aside>` 作為側邊欄，並與 `front.html` 共用相同的類別 (`h-screen w-64 fixed left-0 top-0...`)。
  - 主內容區加回 `lg:ml-64` 以留出側邊欄空間。
- **UI 移除**：刪除 Header 中的 `<div class="glass-panel p-4... search form">`。
- **Javascript 邏輯擴充**：
  - 進入網頁時自動執行 `fetchAndRenderDashboard()` 取得所有資料。
  - 新增 `switchTab(tabId)` 函數，透過點擊側邊欄來隱藏/顯示對應區塊 (Dashboard / Audience / Content)。

## Open Questions

> [!QUESTION]
> 這個「引入側邊欄並透過點擊來切換不同圖表頁面」的作法，就是您所期望的『不要全部都在同個畫面』嗎？確認後我馬上動手改寫！

## Verification Plan
1. 修改 `youtuber_comparison_dashboard.html` 的 HTML 與 JS。
2. 讓您重新開啟網頁，測試點擊側邊欄選單是否能順利切換不同的數據頁面。
