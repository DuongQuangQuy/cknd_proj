# Nhập liệu AI (Gemini) — tài liệu kỹ thuật

Tài liệu này ghi lại thiết kế và các quyết định của tính năng "Nhập liệu AI" trong
module `fs_real_estate`, để lần sau chỉnh sửa không cần đọc lại toàn bộ code để
suy luận lý do.

## 1. Tính năng làm gì

Người dùng dán một đoạn text (có thể chứa **nhiều tin rao nhà đất** viết theo văn
phong tốc ký của môi giới, ví dụ:

```
61/19 Nguyễn Thượng Hiền, P.5, Q.Bình Thạnh
4x8 trệt 2 lầu 3pn 2wc
10tr hh1/2 0903302207
```

vào 1 form, bấm 1 nút → Gemini (bản free) phân tích, tách từng tin, khớp với dữ
liệu địa chỉ/danh mục đã có trong Odoo, rồi **tự tạo các bản ghi `real.estate`**
kèm liên hệ (chủ nhà) tương ứng.

## 2. File map

| File | Vai trò |
|---|---|
| `models/estate_autofill.py` | Toàn bộ logic: gọi Gemini, prompt, matching, tạo `real.estate`. Model `estate.autofill` (persistent, **không phải wizard/transient** — xem mục 4). |
| `models/agent_config.py` | Field cấu hình Gemini API Key/Model trong Settings (`res.config.settings`) + nút chẩn đoán kết nối. |
| `models/real_estate.py` | Field `autofill_id` (Many2one → `estate.autofill`, để lần vết tin nào được tạo từ đợt nhập liệu AI nào) + action mở form nhập liệu từ header. |
| `views/estate_autofill_views.xml` | Form + tree + action cho `estate.autofill`. |
| `views/res_config_settings_views.xml` | UI nhập API Key/Model + nút "🔍 Kiểm tra kết nối". |
| `views/menus.xml` | Menu "Nhà đất > Nhập liệu AI (Gemini)". |
| `security/ir.model.access.csv` | Quyền cho model `estate.autofill` (employee: không xoá; manager: full). |

## 3. Cấu hình

**Cài đặt > Real Estate > "Nhập liệu AI (Gemini)"**:
- `gemini_api_key` (ir.config_parameter: `fs_real_estate.gemini_api_key`) — lấy free tại
  https://aistudio.google.com/apikey (**không** dùng key tạo từ Cloud Console).
- `gemini_model` (ir.config_parameter: `fs_real_estate.gemini_model`) — model *thử đầu tiên*.
  Mặc định `gemini-2.5-flash-lite`.
- Nút **"🔍 Kiểm tra kết nối"** (`agent_config.py: action_test_gemini_connection`) — gửi 1
  request cực nhỏ tới từng model trong `FALLBACK_MODELS` để biết chính xác model nào
  dùng được với key hiện tại, tách bạch lỗi do "prompt quá lớn" với lỗi do "tài khoản/key".

## 4. Vì sao là 1 model persistent, không phải wizard

Phiên bản đầu dùng 2 `TransientModel` (wizard + line con để review/sửa trước khi tạo).
Đã đổi sang **1 model thường** (`estate.autofill`, không có model con) vì:
- User cần **lưu lại raw_text đã dán** để xem lại sau này — TransientModel bị Odoo tự
  vacuum định kỳ, mất dữ liệu.
- User yêu cầu rõ: "không cần cấu trúc con chỉ cần tạo 1 model".

Record `estate.autofill` lưu: `raw_text` (input gốc), `result_log` (log kết quả từng
tin: tạo được / lỗi gì), `estate_ids` (One2many ngược từ `real.estate.autofill_id`) để
xem tin nào được tạo ra từ đợt nhập liệu nào.

## 5. Luồng gọi Gemini (`_call_gemini`)

1. Build **prefix** (`PROMPT_PREFIX_TEMPLATE`, tĩnh: hướng dẫn + danh sách master data)
   và **suffix** (`PROMPT_SUFFIX_TEMPLATE`, chỉ chứa `raw_text` — đổi mỗi lần gọi).
2. Thử **fast path**: dùng Gemini Explicit Context Cache (`_get_or_create_gemini_cache`)
   cho model đã cấu hình — cache phần prefix trên server Google, mỗi lần gọi chỉ gửi
   suffix + `cachedContent`. Đây **chỉ là tối ưu token/độ trễ**, KHÔNG giảm số request
   tính vào giới hạn RPM/RPD. Mọi lỗi khi tạo/dùng cache đều bị nuốt lặng lẽ (free tier
   có thể không hỗ trợ, cần billing, chưa đủ token tối thiểu...) → rơi xuống bước 3.
3. **Full-prompt fallback loop**: thử lần lượt `[model đã cấu hình] + FALLBACK_MODELS`
   (gửi `prefix + suffix` trong 1 request, không cache). Với mỗi model:
   - `500/502/503` (quá tải tạm thời) → đợi 2s, thử lại đúng model đó 1 lần.
   - `429` **chỉ ở model đầu tiên** (`idx==0`) → đọc `retryDelay` Google gợi ý (mặc định
     3s, tối đa 20s) rồi thử lại 1 lần. Các model sau nếu `429` thì bỏ qua ngay (không
     đợi thêm) để tránh cộng dồn thời gian chờ khi phải thử nhiều model.
   - `404`/`429` (sau retry vẫn lỗi) → bỏ qua, thử model tiếp theo.
   - Mã lỗi khác → raise ngay (không thử tiếp).
4. Nếu tất cả model đều lỗi → `UserError` liệt kê lỗi từng model + giải thích 429 có
   thể là **RPM (giới hạn/phút)** chứ không phải hết quota/ngày (xem mục 7).

### Cache phía Odoo (khác với Gemini cache)

`_get_master_data_text()` cache chuỗi master data trong bộ nhớ tiến trình
(`_MASTER_DATA_CACHE`, TTL `MASTER_DATA_CACHE_TTL_SECONDS = 300s`) để tránh query lại
DB mỗi lần bấm liên tiếp trong vài phút. Không liên quan đến Gemini cache ở trên.

## 6. Master data gửi kèm prompt (`_build_master_data_block`)

Để AI **ưu tiên chọn giá trị khớp chính xác có sẵn** thay vì tự đoán mù (đặc biệt
Phường/Quận có vô số cách viết tắt), prompt luôn kèm danh sách:

- Thành phố, Quận/Huyện, Phường/Xã (`"Tên (Quận)"`), Đường (`"Tên đường [Phường liên
  kết]"` — dùng M2M `res.street.ward_ids`), Loại Nhà/MB, Kiểu MT/Hẻm, Cấu trúc.

**Scoping theo `res.city.is_prioritize`**: nếu có Thành phố nào được tích
`is_prioritize=True` (ví dụ Hồ Chí Minh), danh sách Quận→Phường→Đường chỉ lấy trong
phạm vi thành phố đó (đi xuống theo FK `city_id`→`district_id`→qua M2M `ward_ids`).
Lý do: nếu không scope, `limit` cứng (`MASTER_DATA_WARD_LIMIT=800`,
`MASTER_DATA_STREET_LIMIT=1200`) có thể **cắt ngẫu nhiên** mất đúng Phường/Đường cần
dùng khi dữ liệu toàn hệ thống lớn. Nếu chưa tích `is_prioritize` ở đâu, tự động dùng
lại toàn bộ dữ liệu (có giới hạn) như cũ.

**Giới hạn kích thước** (`MASTER_DATA_WARD_LIMIT`, `MASTER_DATA_STREET_LIMIT`): đã
từng bị 429 do prompt quá to (nhiều nghìn Đường) vượt giới hạn *token/phút (TPM)* của
free tier dù request vẫn hợp lệ về mặt cấu trúc — xem mục 7.

## 7. Các lỗi 429/404/503 đã gặp và cách xử lý — tránh đi vòng lại

Thứ tự các nguyên nhân 429 đã thực sự gặp khi phát triển tính năng này (theo đúng độ
ưu tiên nên kiểm tra khi debug lỗi mới):

1. **`limit: 0` cho đúng 1 model cụ thể** (ví dụ `gemini-2.0-flash`) trong khi các
   model khác (`gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-flash-latest`)
   hoạt động bình thường → tài khoản/project **bị chặn quota vĩnh viễn cho riêng model
   đó**, không phải lỗi tạm thời. Dùng nút "Kiểm tra kết nối" để xác nhận chính xác
   model nào bị chặn, rồi đổi `gemini_model` trong Settings sang model còn hoạt động.
2. **RPM (request/phút) dùng chung nhiều model** — bị 429 dù dashboard
   `ai.dev/rate-limit` còn nhiều quota/ngày. Reset sau ~10-60s. Đã xử lý bằng
   retry-with-backoff ở bước 3 mục 5.
3. **TPM (token/phút)** — request tối thiểu (test nhanh) pass ở mọi model, nhưng
   luồng thật (kèm đầy đủ master data, có thể hàng chục nghìn ký tự) vẫn 429 ở MỌI
   model. Đây là lý do `MASTER_DATA_WARD_LIMIT`/`MASTER_DATA_STREET_LIMIT` bị siết lại
   (từ 3000/5000 xuống 800/1200) và thêm scoping theo `is_prioritize` (mục 6) — vừa
   giảm size vừa tăng độ liên quan.
4. **404 "model không tồn tại"** — model bị Google deprecate (ví dụ dòng
   `gemini-1.5-*` đã ngừng hỗ trợ). Xử lý: bỏ khỏi `FALLBACK_MODELS`, coi 404 như 429
   (bỏ qua, thử model khác) thay vì abort toàn bộ.
5. **503 UNAVAILABLE** — quá tải tạm thời phía Google, retry 1 lần sau 2s là đủ.

**Nếu gặp 429 mới**: luôn bấm "Kiểm tra kết nối" trước để phân biệt (1) vs (2)/(3) —
đừng đoán mò sửa code trước khi có dữ liệu chẩn đoán rõ ràng.

## 8. Matching dữ liệu (`_match_many2one`)

Áp dụng cho Thành phố/Quận/Phường/Đường/Loại nhà/Kiểu/Cấu trúc/Nhu cầu — theo thứ tự
fallback tăng dần độ "nới lỏng":

1. `ilike` trực tiếp (SQL `name ILIKE '%text%'`).
2. So khớp **chính xác** sau khi bỏ dấu + hạ chữ thường (`_strip_accents`).
3. So khớp **chứa nhau** (substring, cả 2 chiều) sau khi bỏ dấu.
4. **Bỏ tiền tố hành chính** (`Phường`/`P.`/`Quận`/`Q.` — `ADMIN_PREFIX_RE`) ở CẢ HAI
   phía rồi so phần lõi còn lại. Đây là lớp quan trọng nhất cho dữ liệu VN: xử lý đúng
   trường hợp DB lưu tắt kiểu `"P7"` nhưng AI trả về `"Phường 7"` (hoặc ngược lại) —
   **không phụ thuộc AI có tuân đúng chỉ dẫn prompt hay không**, vì đây là lớp bảo vệ
   ở code, không phải ở prompt.

**Quan trọng — KHÔNG tự tạo mới Thành phố/Quận/Phường/Đường** nếu không khớp được
(quyết định rõ ràng của user: dữ liệu địa chỉ phải do người dùng tự quản lý qua menu
**Real Estate > Cấu hình > Địa chỉ**, không để AI tự phát sinh record địa chỉ rác).

**Loại Nhà/MB và Kiểu MT/Hẻm thì NGƯỢC LẠI**: đây là 2 field `required=True` thật trên
`real.estate` (không thể để trống khi tạo), nhưng KHÔNG bắt buộc phải khớp đúng —
nếu AI đoán sai/không đoán được, `_match_many2one_or_default` tự lấy tạm **bản ghi đầu
tiên hiện có** (không tạo mới) để không chặn tạo tin, và tự thêm ghi chú vào field
`note` của tin: `[AI không xác định được: ... - đã tự chọn tạm, vui lòng kiểm tra
lại]` để người dùng biết tin nào cần sửa tay. `Cấu trúc` (Many2many, không phải
required thật ở tầng ORM) thì đơn giản để trống nếu không khớp được, không chặn, không
cần fallback.

## 9. Điều kiện bắt buộc để tạo được 1 `real.estate` (`_create_real_estate`)

**CHỈ bắt buộc 2 nhóm** (quyết định rõ ràng của user — đã cố tình bỏ bớt so với bản
đầu):

1. **Địa chỉ khớp được**: Số nhà + Đường + Phường + Quận/Huyện + Thành phố (đều phải
   match ra 1 record có sẵn — xem mục 8).
2. **Ít nhất 1 số điện thoại hợp lệ** (để tạo/gắn `res.partner` vào `role_line_ids`).
   Không còn tạo `role_line_ids` rỗng nữa — **mọi role_line đều phải có partner**.

Loại Nhà/MB, Kiểu MT/Hẻm, Cấu trúc **không** nằm trong danh sách bắt buộc (xem mục 8).

Nếu thiếu 1 trong 2 nhóm trên → `UserError` bị bắt bởi `action_process` (savepoint
riêng từng tin), ghi vào `result_log`, **không** làm hỏng các tin khác trong cùng lần
xử lý.

### Ràng buộc số điện thoại từ `res.partner` (`fs_contacts/models/res_partner.py`)

`res.partner.mobile` là `required=True` **và** có `@api.constrains('mobile')` bắt buộc
đúng **10 chữ số** (`^\d{10}$`), cộng thêm chính `create()` override cũng tự
validate lại 1 lần nữa (đọc trực tiếp `vals['mobile']` — sẽ `KeyError` nếu thiếu hẳn
key `mobile` trong vals, nên **luôn phải truyền `mobile`** khi gọi `res.partner.create()`
từ nơi khác trong code, kể cả module này).

→ `_normalize_phone()` xử lý trước khi tạo/tìm partner: bóc hết ký tự không phải số,
tự chuyển `+84.../84...` (11 số) về dạng `0...` (10 số); số nào không chuẩn hoá được
thành đúng 10 số (bắt đầu bằng `0`) thì bị loại (không tính là số hợp lệ, không dùng
để tạo partner). `_get_or_create_partner()` chỉ **search** theo `mobile`/`phone` trước,
chỉ **create** khi thật sự chưa có partner nào dùng số đó.

## 10. Những điều CỐ TÌNH không làm (đừng "sửa lại" nếu không được yêu cầu)

- Không tự tạo `res.city`/`res.district`/`res.ward`/`res.street` khi AI đưa ra tên
  không khớp dữ liệu có sẵn (mục 8).
- Không tự tạo `type.estate`/`estate.style`/`estate.structure` mới (chỉ fallback về
  bản ghi có sẵn, không phát sinh giá trị phân loại mới).
- Không đoán `style_guess` (MT/Hẻm) khi văn bản không có tín hiệu rõ ràng — CHỈ suy
  luận "Hẻm" khi có từ "hẻm" hoặc `number_house` dạng `số/số` (ví dụ `61/19` — quy ước
  số nhà trong hẻm ở VN). Không có tín hiệu thì để trống (rồi fallback ở mục 8, không
  bịa).
- Gemini Explicit Context Cache và cache master-data phía Odoo **không** giải quyết
  giới hạn RPM/RPD — đừng nhầm 2 khái niệm này khi debug lỗi 429 (mục 7).

## 11. Hướng mở rộng nếu cần sau này (chưa làm, chỉ ghi chú ý tưởng)

- Nếu vẫn dính 429 dạng TPM thường xuyên dù đã scope theo `is_prioritize`: cân nhắc
  giảm tiếp `MASTER_DATA_WARD_LIMIT`/`MASTER_DATA_STREET_LIMIT`, hoặc bỏ hẳn phần
  Đường khỏi prompt (giữ lại Quận/Phường) và để `_match_many2one` xử lý Đường thuần
  bằng ilike/accent-fallback như trước.
- Có thể thêm nút "Tạo lại" cho từng dòng lỗi trong `result_log` mà không cần dán lại
  toàn bộ `raw_text` (hiện tại phải bấm "Phân tích & Tạo tin đăng" lại từ đầu, sẽ gọi
  lại Gemini cho cả batch).
- Nút "Kiểm tra kết nối" (`agent_config.py`) hiện chỉ test model, chưa test luôn kích
  thước prompt thật — có thể mở rộng để ước lượng token của `_build_master_data_block()`
  hiện tại và cảnh báo nếu quá lớn.
