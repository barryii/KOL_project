# 執行計畫：導入「數位工坊 (The Digital Atelier)」設計系統

根據您提供的 `DESIGN.md`，這套 **「Curated Hearth (精心佈置的壁爐)」** 設計哲學非常獨特，強烈要求溫暖、有機的材質感，並排斥傳統冷硬的數據面板。為了達到這種宛如高級文具與灑滿陽光的工作室氛圍，我將對目前的儀表板進行徹底的基因改造。

## User Review Required

> [!IMPORTANT]  
> 這次的改版將會**徹底改變**所有卡片的形狀、字體與層次結構，請您確認以下實作方向是否符合期待。一旦批准，我將進行全檔重構。

## Proposed Changes

### 1. 色彩學注入：Terracotta 與溫暖大地色系
- **背景與圖層 (Tonal Layering)**：
  - 將純白與冷灰切換為溫暖的奶油色。最底層背景 `background` 設為 `#fffcf7`。
  - 主要卡片背景改為 `#ffffff` (`surface_container_lowest`)，創造出浮在奶油色上的輕盈感。
- **資料與品牌色 (Data Visualization)**：
  - YouTuber A：使用經典的 **Terracotta (赤陶色 `#a24a35`)** 到 Coral 的漸層色系。
  - YouTuber B：使用 **Sage (鼠尾草綠)** 或是 **Brown (暖棕色)** 來進行溫和的對比，徹底避免傳統的紅綠互補色（減少 Christmas effect）。
- **文字對比下降**：絕對禁止純黑 `#000000`，所有文字全數切換為 `#373831` (`on_surface`)。

### 2. The "No-Line" Rule 與 Ambient Depth
- **移除剛硬邊框**：移除儀表板中所有的 `border` 與 `border-outline-variant` 實心線條。區塊邊界將改由「背景色些微過渡」或是極淡的 15% `ghost border` 來暗示。
- **溫暖的環境光陰影 (Ambient Shadows)**：卡片與導覽列將套用 `box-shadow: 0 12px 40px rgba(162, 74, 53, 0.06)`，也就是帶有一點赤陶色調的柔和投影，捨棄原本黑色或藍色的剛硬陰影。

### 3. 字體切換：Plus Jakarta Sans
- 移除 `Manrope` 與 `Inter`，全域導入 `Plus Jakarta Sans`。這套字型擁有現代幾何的俐落與圓潤的曲線，能完美呼應極大的圓角設計。

### 4. 有機造型：超級大圓角
- 貫徹 `Intentional Softness`：
  - 所有的分析卡片圓角將從一般的 `8px` (`rounded-lg`) 大幅提升至 `2rem` (`32px`) 甚至是 `3rem` (`48px`)。
  - 按鈕全數改為 `rounded-full` (全圓角膠囊狀)。
  - 卡片內部的內邊距 (Padding) 將大幅放寬，使用 `p-8` 甚至是 `p-10` 來創造「奢侈的留白 (Space is a luxury)」。

### 5. Interaction 互動元素
- 左側選單的高亮狀態 (Active) 與主要按鈕，將應用 `135度` 從 Primary `#a24a35` 漸變至 Primary Container `#ffac99` 的專屬靈魂漸層。

---

如果這套「**溫暖、有機、帶有紙張與黏土質地**」的設計系統是您現在想要的最終面貌，請給我您的同意（或提供您想微調的想法），我馬上為您著手改寫！
