import base64
import json
import os
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class RealEstateAPI(http.Controller):

    @http.route('/api/real-estate/update-image-path', type='json', auth='none', methods=['GET'], csrf=False)
    def update_real_estate_image_path(self, **kwargs):
        """
        Update real estate image using file path
        Expected JSON format:
        {
            "old_id": "123",
            "image_path": "/path/to/image.jpg"
        }
        """
        try:
            data = request.jsonrequest
            if not data or 'old_id' not in data or 'image_path' not in data:
                _logger.warning('Missing required fields in request')
                return Response(
                    json.dumps({'status': 'error', 'message': 'Missing required fields: old_id and image_path'}),
                    content_type='application/json',
                    status=400
                )

            old_id = data['old_id']
            image_path = data['image_path']

            _logger.info(f'Processing image import for old_id: {old_id}, image_path: {image_path}')

            existing_log = request.env['import.image.log'].sudo().search([('image_path', '=', image_path)], limit=1)
            if existing_log:
                _logger.info(f'Image path already imported: {image_path}. Skipping.')
                return Response(
                    json.dumps({
                        'status': 'skipped',
                        'message': f'Image path already imported on {existing_log.imported_date}',
                        'old_id': old_id,
                        'image_path': image_path
                    }),
                    content_type='application/json',
                    status=200
                )

            if not os.path.exists(image_path):
                _logger.error(f'Image file not found: {image_path}')
                return Response(
                    json.dumps({'status': 'error', 'message': f'Image file not found: {image_path}'}),
                    content_type='application/json',
                    status=404
                )

            real_estate = request.env['real.estate'].sudo().search([('old_id', '=', old_id)], limit=1)
            if not real_estate:
                _logger.error(f'Real estate with old_id {old_id} not found')
                return Response(
                    json.dumps({'status': 'error', 'message': f'Real estate with old_id {old_id} not found'}),
                    content_type='application/json',
                    status=404
                )

            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read())

            attachment = request.env['ir.attachment'].sudo().create({
                'name': os.path.basename(image_path),
                'type': 'binary',
                'datas': image_data,
                'res_model': 'real.estate',
                'res_id': real_estate.id,
            })

            real_estate.write({
                'attachment_ids': [(4, attachment.id)]
            })

            request.env['import.image.log'].sudo().create({
                'old_id': old_id,
                'image_path': image_path
            })

            _logger.info(f'Image imported successfully for old_id: {old_id}, attachment_id: {attachment.id}')

            return Response(
                json.dumps({
                    'status': 'success',
                    'message': 'Image uploaded successfully',
                    'attachment_id': attachment.id
                }),
                content_type='application/json',
                status=200
            )

        except Exception as e:
            _logger.exception(f'Failed to process image for old_id: {data.get("old_id")}, error: {str(e)}')
            return Response(
                json.dumps({
                    'status': 'error',
                    'message': f'Failed to process image: {str(e)}'
                }),
                content_type='application/json',
                status=500
            )