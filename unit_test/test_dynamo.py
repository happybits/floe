#!/usr/bin/env python

import unittest

from floe import dynamoapi

table_name = 'floe_testing'

class TestFeatures(unittest.TestCase):
    def setUp(self):
        dynamoapi.DynamoFloe.create_floe_table(table_name)

    def tearDown(self):
        dynamoapi.DynamoFloe.delete_floe_table(table_name)

    def test_single(self):
        dynamo = dynamoapi.DynamoFloe(table_name)
        k, v = ('test-key', 'test-value')

        dynamo.set(k, v)

        self.assertEquals(dynamo.get(k), v)
        dynamo.delete(k)
        self.assertIsNone(dynamo.get(k))

    def test_multi(self):
        dynamo = dynamoapi.DynamoFloe(table_name)
        data = {
            'key1': 'value1',
            'key2': 'value2'
        }

        dynamo.set_multi(data)
        retrieved = dynamo.get_multi(data.keys())
        for key in data.keys():
            self.assertEquals(data[key], retrieved[key])

        dynamo.delete_multi(data.keys())
        retrieved = dynamo.get_multi(data.keys())
        self.assertEquals(0, len(retrieved))

    def test_ids(self):
        dynamo = dynamoapi.DynamoFloe(table_name)
        data = {
            'key1': 'value1',
            'key2': 'value2'
        }

        dynamo.set_multi(data)
        retrieved = dynamo.ids()

        count = 0
        for key in retrieved:
            count += 1
            self.assertIsNotNone(data[key])

        self.assertEquals(count, 2)

        dynamo.delete_multi(data.keys())
        retrieved = dynamo.get_multi(data.keys())
        self.assertEquals(0, len(retrieved))
