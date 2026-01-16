# Formal Verification với SymbiYosys (SBY)

Tài liệu này tổng hợp kiến thức về các chế độ hoạt động và các bộ giải (engines) trong hệ sinh thái SymbiYosys. Tài liệu được tối ưu hóa cho quy trình xác minh các khối logic phức tạp trong thiết kế **AI Chip (6nm)**.

---

## I. Các Chế độ Hoạt động (Modes)

Việc lựa chọn `mode` đúng là bước then chốt để xác định mục tiêu kiểm thử.

| Chế độ | Ý nghĩa | Ưu điểm | Trường hợp sử dụng |
| :--- | :--- | :--- | :--- |
| **`mode bmc`** | Bounded Model Checking | Tìm lỗi cực nhanh trong $N$ chu kỳ đầu tiên. | Dùng hàng ngày khi viết code RTL để bắt lỗi logic sớm. |
| **`mode prove`** | Unbounded Verification | Chứng minh mạch **an toàn vĩnh viễn** bằng toán học. | Sign-off các bộ điều khiển (Arbiter, FSM) trước khi Tape-out. |
| **`mode cover`** | Reachability Analysis | Kiểm tra xem một trạng thái/luồng dữ liệu có thể chạm tới không. | Đảm bảo luồng dữ liệu thông suốt qua các lớp xử lý AI. |
| **`mode live`** | Liveness Checking | Đảm bảo một sự kiện "sớm muộn gì cũng phải xảy ra". | Kiểm tra lỗi treo mạch (Livelock) hoặc bỏ đói (Starvation) trong NoC. |

---

## II. Phân tích chi tiết các Engine

Mỗi engine sử dụng các thuật toán khác nhau (SMT, IC3, Interpolation) dẫn đến hiệu quả khác biệt trên từng loại logic.

### 1. Nhóm SMT-Based (Xử lý Word-level)
*Phù hợp nhất cho: `mode bmc`, `mode cover`.*

| Engine | Ưu điểm | Nhược điểm | Use Case tốt nhất |
| :--- | :--- | :--- | :--- |
| **smtbmc boolector** | "Tiêu chuẩn vàng" cho RTL, cực nhanh với logic Bit-vector. | Ngừng phát triển tính năng mới (chuyển sang Bitwuzla). | Logic điều khiển thông thường, FSM. |
| **smtbmc bitwuzla** | Xử lý vượt trội các **Mảng (Memory)** và **Số thực (FP)**. | Có thể chậm hơn Boolector với logic tổ hợp đơn giản. | **Chip AI**, Memory Controllers, các khối tích toán ma trận. |
| **smtbmc yices** | Tốc độ giải (solve time) rất nhanh, hay thắng các giải đấu SMT. | Đôi khi khó cấu hình thư viện trên một số OS cũ. | Khi các engine khác bị "kẹt" không ra kết quả. |
| **smtbmc z3** | Đa năng, hỗ trợ mọi lý thuyết toán học phức tạp. | Tốc độ chậm nhất khi áp dụng vào phần cứng thuần túy. | Làm phương án dự phòng (fallback) hoặc bài toán phi tuyến. |

### 2. Nhóm Bit-level & Unbounded (AIGER/ABC)
*Phù hợp nhất cho: `mode prove`, `mode live`.*

| Engine | Ưu điểm | Nhược điểm | Use Case tốt nhất |
| :--- | :--- | :--- | :--- |
| **abc pdr** | Thuật toán PDR/IC3 mạnh mẽ nhất để chứng minh vĩnh viễn. | Tốn nhiều RAM khi mạch quá lớn (do phải trải mạch ra cổng). | Chứng minh mạch **không bao giờ Deadlock**. |
| **aiger avy** | Hiệu quả với các thiết kế lớn nhờ kỹ thuật Nội suy (Interpolation). | Chỉ hỗ trợ duy nhất `mode prove`. | Khi PDR chạy mãi không hội tụ được kết quả. |
| **aiger suprove** | Engine mạnh nhất hiện nay cho bài toán **Liveness**. | Yêu cầu tài nguyên máy chủ (CPU/RAM) lớn. | Kiểm tra các gói tin NoC không bị kẹt vĩnh viễn. |

---

### 3. Nhóm BTOR2 Engines (Word-level Model Checking)
Đây là nhóm engine sử dụng định dạng nhị phân **BTOR2**. Nó giữ nguyên cấu trúc các bit-vector (word-level) nhưng áp dụng các thuật toán kiểm tra mô hình hiện đại.

| Engine | Ưu điểm | Nhược điểm | Use Case tốt nhất |
| :--- | :--- | :--- | :--- |
| **btor btormc** | Là solver "chính chủ" đi kèm với Boolector. Rất nhẹ và nhanh cho BMC. | Chỉ tập trung vào Word-level, ít thuật toán chứng minh (prove) mạnh. | Thay thế `smtbmc boolector` khi cần tốc độ BMC tối đa. Hỗ trợ bmc, cover|
| **btor pono** | Framework hiện đại từ Stanford. Hỗ trợ nhiều thuật toán như PDR, BMC, k-induction ở mức Word-level. | Đang phát triển tích cực nên đôi khi yêu cầu phiên bản công cụ mới nhất. | Khi bạn muốn dùng thuật toán PDR mạnh mẽ nhưng không muốn mạch bị trải ra mức cổng (bit-blast). Hỗ trợ bmc, prove, cover|

**Điểm khác biệt của BTOR Engines bạn cần lưu ý:**

So với các engine `smtbmc` (truyền thống), các engine `btor` (như `btormc` và `pono`) xử lý file thiết kế ở định dạng trung gian BTOR2. Định dạng này **giữ nguyên cấu trúc Word-level** của thiết kế nhưng lại được tối ưu hóa cho các thuật toán Model Checking (giống như AIGER). Đây là "vũ khí bí mật" khi bạn phải verify các module có datapath lớn mà không muốn công cụ bị chậm do phải chuyển hết về cổng logic (bit-blast).

## III. File Cấu hình Master Template (`config.sby`)

Bạn có thể chạy task cụ thể bằng lệnh: `sby -f -j <nthreads> config.sby [tên_task]`.

Lưu ý: mỗi engine chỉ có thể chạy 1 thread.
```toml
[tasks]
# BMC - Tìm lỗi nhanh
bmc_bitwuzla
bmc_boolector

# PROVE - Chứng minh an toàn vĩnh viễn
prove_pdr
prove_avy

# COVER & LIVE - Luồng dữ liệu và tính sống
cover_flow
live_check

[options]
bmc_*:   mode bmc
bmc_*:   depth 20
prove_*: mode prove
cover_*: mode cover
cover_*: depth 100
live_*:  mode live

# Tối ưu hóa file sóng (Cần thiết cho chip 6nm)
fst on
vcd off

[engines]
bmc_bitwuzla:   smtbmc bitwuzla
bmc_boolector:  smtbmc boolector
prove_pdr:      abc pdr
prove_avy:      aiger avy
cover_flow:     smtbmc bitwuzla
live_check:     aiger suprove

[script]
read -formal my_design.sv
prep -top my_design

[files]
my_design.sv
