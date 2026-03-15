from odoo import _, api, fields, models
from lxml import etree
import pyperclip
from bs4 import BeautifulSoup

class AdvertisingSampleWizard(models.TransientModel):
    _name = 'advertising.sample.wizard'
    _description = 'Advertising Sample Wizard'

    real_estate_id = fields.Many2one('real.estate', string='Nhà đất')
    x_advertising_template_0 = fields.Html(compute='_compute_advertising_template')

    @api.depends('real_estate_id')
    def _compute_advertising_template(self):
        advertising_templates = self.env['real.estate.advertising.template'].search([])
        for record in self:
            real_estate = record.real_estate_id
            record.x_advertising_template_0 = ''
            for template in advertising_templates:
                template_str = template.advertising_template or ''

                # Tạo dict dữ liệu để thay thế
                data = {
                    'NhuCau': real_estate.type_demand_id.name or '',
                    'Loai': real_estate.type_estate_id.name or '',
                    'Kieu': real_estate.style_id.name or '',
                    'DiaChi': real_estate._get_address(house=1, street=1, ward=1, district=1) or '',
                    'MaSo': real_estate.code or '',
                    'ChieuRong': real_estate.horizontal or '',
                    'ChieuDai': real_estate.length or '',
                    'KetCau': ', '.join(real_estate.structure_ids.mapped('name')) or '',
                    'Gia': real_estate.total_price or '',
                    'PhucLoi': real_estate.deposit or '',
                }

                # Thay thế các placeholder [Tên] trong template_str bằng giá trị tương ứng
                for key, value in data.items():
                    template_str = template_str.replace(f'[{key}]', str(value))

                # Chuyển xuống dòng thành <br/>
                record[f'x_advertising_template_{template.id}'] = template_str.replace('\n', '<br/>')
    
    @api.model
    def fields_view_get(self, view_id=None, view_type="form", toolbar=False, submenu=False):
        res = super().fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )
        if view_type == "form":
            doc = etree.XML(res["arch"])
            form_view_id = self.env['ir.model.data']._xmlid_to_res_id('fs_real_estate.advertising_sample_wizard_view_form')
            if res.get('view_id') == form_view_id:
                target = doc.xpath("//notebook")
                if target:
                    target = target[0]
                    advertising_templates = self.env['real.estate.advertising.template'].search([])
                    for template in advertising_templates:
                        page = doc.makeelement("page", {"name": f"advertising_template_{template.id}", "string": template.name})
                        page.append(doc.makeelement("button", {"string": "Copy text", "class": "oe_highlight copy_advertising_template", "id": f"x_advertising_template_{template.id}"}))
                        page.append(doc.makeelement("field", {"name": f"x_advertising_template_{template.id}", "widget": "html"}))
                        target.append(page)
                    res["arch"] = etree.tostring(doc, encoding="unicode")
        return res
    
    def copy_sample(self, content):
        if content:
            soup = BeautifulSoup(content.replace('<br>', '\n'), "lxml")
            pyperclip.copy(soup.get_text())