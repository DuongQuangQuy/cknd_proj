odoo.define('fs_real_estate.favorite_button', function (require) {
    "use strict";

    var core = require('web.core');
    var _t = core._t;
    var session = require('web.session');
    var fieldRegistry = require('web.field_registry');

    // Lấy widget One2ManySelectable từ registry
    var One2ManySelectable = fieldRegistry.get('one2many_selectable');

    // Mở rộng widget One2ManySelectable
    if (One2ManySelectable) {
        One2ManySelectable.include({
            /**
             * Xử lý khi nhấn nút yêu thích
             * @override
             */
            action_favorite_lines: function() {
                var self = this;
                var selected_ids = this.get_selected_ids_one2many();

                if (selected_ids.length === 0) {
                    this.do_warn(_t("Warning"), _t("You must choose at least one record."));
                    return false;
                }

                // Kiểm tra xem widget đang được sử dụng trong model real.estate hay không
                if (this.field && this.field.relation === 'real.estate') {
                    // Lấy thời gian hiện tại định dạng DD/MM/YYYY HH:mm:ss
                    var now = new Date();
                    var formattedDate = now.toLocaleString('vi-VN', {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                        hour12: false
                    });

                    // Mở form real.estate.favorite với context chứa các ID đã chọn
                    this.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'real.estate.favorite',
                        views: [[false, 'form']],
                        target: 'new',
                        context: {
                            'default_estate_ids': selected_ids,
                            'default_name': _t('Favorites ') + formattedDate
                        }
                    });
                } else {
                    // Nếu không phải model real.estate, hiển thị thông báo
                    this.do_warn(_t("Warning"), _t("This feature is only available for real estate records."));
                }
            },
        });
    } else {
        console.error("Widget One2ManySelectable not found in registry");
    }
});