"""Run locally without AWS or MySQL: python3 -B backend/shipping/test_lambda.py"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lambda_function as service
from test_db import Connection

SHIPMENT = {'shipmentRequestId': 'CS-test', 'businessId': 'LAB-001',
            'shipmentAddress': {'fullName': 'Lab Test', 'address': '1 Main St',
                                'city': 'Columbus', 'state': 'OH', 'zip': '43210'},
            'packetCount': 2, 'packetWeightsLb': [3.0, 2.0]}


def sns(*bodies):
    return {'Records': [{'Sns': {'Message': json.dumps({
        'source': 'clothingstore.orders', 'detail-type': 'ShippingRequested', 'detail': body})}}
        for body in bodies]}


class ShippingTests(unittest.TestCase):
    def setUp(self):
        self.db = Connection(Path(__file__).resolve().parents[1] / 'db/shipping.sql')
        self.addCleanup(self.db.close)
        replacement = patch.object(service, 'connect', return_value=self.db)
        replacement.start()
        self.addCleanup(replacement.stop)

    def call(self, body):
        response = service.lambda_handler({'httpMethod': 'POST', 'body': json.dumps(body)}, None)
        return response['statusCode'], json.loads(response['body'])

    def test_http_persists_address_weights_and_returns_token(self):
        status, body = self.call(SHIPMENT)
        self.assertEqual(status, 200)
        row = self.db.query('SELECT SHIPPING_TOKEN, ADDRESS_JSON, PACKET_COUNT, WEIGHTS_JSON FROM SHIPMENT')[0]
        self.assertEqual(row[0], body['shippingToken'])
        self.assertEqual(json.loads(row[1]), SHIPMENT['shipmentAddress'])
        self.assertEqual(row[2], 2)
        self.assertEqual(json.loads(row[3]), [3, 2])

    def test_duplicate_http_and_sns_deliveries_create_one_shipment(self):
        first = self.call(SHIPMENT)[1]['shippingToken']
        self.assertEqual(service.lambda_handler(sns(SHIPMENT, SHIPMENT), None), {'processed': 2})
        self.assertEqual(self.call(SHIPMENT)[1]['shippingToken'], first)
        self.assertEqual(self.db.query('SELECT COUNT(*) FROM SHIPMENT'), [(1,)])

    def test_invalid_packet_data_and_address_do_not_persist(self):
        for body in [None, {}, {**SHIPMENT, 'packetCount': True}, {**SHIPMENT, 'packetCount': 0},
                     {**SHIPMENT, 'packetWeightsLb': [1]}, {**SHIPMENT, 'packetWeightsLb': [1, -1]},
                     {**SHIPMENT, 'packetWeightsLb': [1, float('inf')]},
                     {**SHIPMENT, 'shipmentAddress': {'fullName': 'Test'}}]:
            self.assertEqual(self.call(body)[0], 400)
        self.assertEqual(self.db.query('SELECT COUNT(*) FROM SHIPMENT'), [(0,)])

    def test_sns_failure_raises_for_retry_while_http_returns_502(self):
        with patch.object(service, 'connect', side_effect=OSError('offline')):
            with self.assertRaises(OSError):
                service.lambda_handler(sns(SHIPMENT), None)
            self.assertEqual(self.call(SHIPMENT)[0], 502)
        with self.assertRaises(ValueError):
            service.lambda_handler(sns({}), None)

    def test_http_methods_and_bad_json(self):
        self.assertEqual(service.lambda_handler({'httpMethod': 'OPTIONS'}, None)['statusCode'], 204)
        self.assertEqual(service.lambda_handler({'httpMethod': 'GET'}, None)['statusCode'], 405)
        self.assertEqual(service.lambda_handler({'body': '{'}, None)['statusCode'], 400)


if __name__ == '__main__':
    unittest.main()
