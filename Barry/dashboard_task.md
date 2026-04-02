# 🎨 數位工坊 (Digital Atelier) 設計重構

- `[x]` **字型替換**：全面導入 Plus Jakarta Sans。
- `[x]` **色彩基礎建設**：於 Tailwind 設定 `background: #fffcf7`、`primary: #a24a35` (Terracotta) 與相關的 Tonal Layering 奶油底色。
- `[x]` **材質與深度**：
  - 取代 1px 剛性邊界，改用 15% 透明度 Ghost Border。
  - 將所有環境陰影覆寫為溫暖的 `rgba(162, 74, 53, 0.06)` 投影。
  - 定義 `rounded-lg` 為 `2rem` (32px)、`rounded-xl` 為 `3rem` (48px) 大圓角。
- `[x]` **UI 元件打磨**：側邊導覽、主按鈕套用 135 度專屬漸層與 `rounded-full` 膠囊設計。
- `[x]` **資料視覺化**：Chart.js 配色置換為「Terracotta」vs「Sage (鼠尾草綠)」。
