/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { patch } from "@web/core/utils/patch";
const { onMounted, onWillPatch, onPatched, onWillUnmount, useComponent } = owl.hooks;

patch(Dropdown.prototype, 'fs_real_estate.DropdownHover', {
    setup() {
        this._super(...arguments);
        if (!this.props.manualOnly) {
            onMounted(() => {
                if (this.el) {
                    // Override default click behavior
                    this.el.addEventListener("mouseenter", () => {
                        if (!this.state.open) {
                            this.open();
                        }
                    });

                    this.el.addEventListener("mouseleave", () => {
                        if (this.state.open) {
                            this.close();
                        }
                    });
                }
            });
        }
    },
});