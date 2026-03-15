from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from datetime import datetime, time, timedelta


class UpdateAddress(models.TransientModel):
    _name = 'update.address'

    # From
    street_from_id = fields.Many2one('res.street', 'Đường')
    ward_from_id = fields.Many2one('res.ward', 'Phường')
    district_from_id = fields.Many2one('res.district', 'Quận/Huyện')
    city_from_id = fields.Many2one('res.city', 'Thành phố')
    number_house_from = fields.Char('Số nhà')

    # To
    street_to_id = fields.Many2one('res.street', 'Đường')
    ward_to_id = fields.Many2one('res.ward', 'Phường')
    district_to_id = fields.Many2one('res.district', 'Quận/Huyện')
    city_to_id = fields.Many2one('res.city', 'Thành phố')
    number_house_to = fields.Char('Số nhà')
    line_ids = fields.One2many('update.address.line', 'update_id', string='Thông tin địa chỉ')

    def get_real_estate_ids(self):

        ######## address #########
        street = ''
        if self.street_from_id:
            street = f"AND street_id = {self.street_from_id.id}"
        ward = ''
        if self.ward_from_id:
            ward = f"AND ward_id = {self.ward_from_id.id}"
        district = ''
        if self.district_from_id:
            district = f"AND district_id = {self.district_from_id.id}"
        city = ''
        if self.city_from_id:
            city = f"AND city_id = {self.city_from_id.id}"
        number_house = ''
        if self.number_house_from:
            number_house = f"AND number_house ILIKE '{self.number_house_from}%'"
        #################

        query = f"""
            SELECT id
            FROM real_estate
            WHERE 1 = 1
            {street}
            {ward}
            {district}
            {city}
            {number_house}
           
        """
        self.env.cr.execute(query)
        real_estate_ids = [result.get('id') for result in self.env.cr.dictfetchall()]
        return real_estate_ids

    def search_address(self):
        try:
            self.line_ids = None
            line_ids = self.get_real_estate_ids()
            values = []
            for line in line_ids:
                vals = {
                    'estate_id': line,
                }
                values.append((0, 0, vals))

            self.line_ids = values
        except Exception as e:
            raise ValueError(e)

    def update_address(self):
        for line in self.line_ids:
            if self.street_to_id:
                line.estate_id.write({
                    'street_id': self.street_to_id.id,
                })
            if self.ward_to_id:
                line.estate_id.write({
                    'ward_id': self.ward_to_id.id,
                })
            if self.district_to_id:
                line.estate_id.write({
                    'district_id': self.district_to_id.id,
                })
            if self.city_to_id:
                line.estate_id.write({
                    'city_id': self.city_to_id.id,
                })

            if self.number_house_to:

                line.estate_id.write({
                    'number_house': self.number_house_to,
                })


class UpdateAddressLine(models.TransientModel):
    _name = 'update.address.line'

    update_id = fields.Many2one('update.address', 'Thông tin update')
    estate_id = fields.Many2one('real.estate', 'Nhà đất')
    date_show = fields.Html(string='Ngày', related='estate_id.date_show')
    code_demand_secondary_show = fields.Html(string='Code|Nhu cầu|Hình thức',
                                             related='estate_id.code_demand_secondary_show')
    type_style_direction_show = fields.Html(string='Loại|Kiểu|Hướng', related='estate_id.type_style_direction_show')

    # address_show = fields.Html(string='Địa chỉ', related='estate_id.address_show')
    address_ward_district_show = fields.Html(string='Phường - Quận',related='estate_id.address_ward_district_show'
                                        )
    street_id = fields.Many2one('res.street', 'Đường',related='estate_id.street_id')
    number_house = fields.Char('Số nhà',related='estate_id.number_house')
    horizontal_length_use_area_show = fields.Html(string='Dài|Rộng|KV|SD',
                                                  related='estate_id.horizontal_length_use_area_show')
    total_price = fields.Float('Tổng tiền', related='estate_id.total_price')
    structure_ids = fields.Many2many('estate.structure', string='Cấu trúc', related='estate_id.structure_ids')
    note = fields.Text(string='Ghi chú', related='estate_id.note')
    deposit = fields.Float('Tiền cọc', related='estate_id.deposit')
    paid = fields.Float('Thanh toán', related='estate_id.paid')
    fee = fields.Char('Phí', related='estate_id.fee')
